# Spec 005 — i18n / language switching (en + zh-Hant)

**Status:** Approved for implementation
**Type:** New feature (full internationalization) + `/language` command
**Date:** 2026-07-30

## Problem statement

Every user-facing string in the bot is hardcoded inline in f-strings, spread
across ~17 files (~150–180 distinct strings after de-duplication). The bot is
effectively English-only, with three stray Traditional-Chinese literals leaking
from the `/compare` feature (`messages.py`, `compare.py`) — itself proof that
scattering strings through feature code is unmaintainable.

Users have no way to choose a language, and there is no mechanism that would let
them. This spec introduces **full internationalization**: every user-facing
string moves into a platform-agnostic message catalog keyed by a stable string
id, a `/language` command lets each user pick a language, and every message +
button + command-menu entry renders in the chosen language.

Two languages ship: **English (`en`)** and **Traditional Chinese (`zh-Hant`)**.

## Goals

- Extract **all** user-facing strings into a message catalog under
  `formatting/i18n/`, keyed by stable ids. Feature code references keys, never
  literals.
- A `t(key, lang, **kwargs) -> str` lookup function: pure `(str, str) -> str`,
  **never imports `telegram` and never touches `Update`** — so it is reusable by
  a future LINE adapter unchanged.
- Per-user language preference, stored the same way `timezone` is (a new column
  on `user_preferences`), with a `/language` picker mirroring `/timezone`.
- A `RenderContext(lang, tz)` value object threaded into every formatter. Only
  ~4 formatters take a bare `user_tz` today; for the other ~17, `ctx` is a **new**
  argument, not a replacement.
- Language resolution order **DB preference > platform default (`en`)**, isolated
  in one platform-specific helper. No `language_code` auto-detection (see the
  rollout rationale below) — the default is a passed parameter so a future LINE
  adapter can pass `zh-Hant`.
- Localized Telegram command menu via `set_my_commands(..., language_code=...)`.
- A completeness check (a test) that fails when any key is missing a translation
  in any shipped language; a runtime English fallback as a safety net.

## Non-goals

- **No third language, no simplified Chinese.** `en` + `zh-Hant` only. The
  catalog structure supports N languages by adding a dict key, but only these two
  are translated and completeness-checked. Adding a language later is a separate,
  code-only change (no feature-code edits).
- **No hexagonal/view-model refactor.** Handlers keep doing "produce data +
  render reply" in one place. Splitting that is a **separate future sub-project**
  (see `roadmap-view-model-extraction.md`) deferred until a second platform
  exists to validate the abstraction. This spec only purifies the *presentation*
  layer (strings) and the *preference* layer (language), which is the groundwork
  that refactor will build on.
- **No directory restructure.** The existing 7-package layout
  (`api/scheduler/storage/models/utils/formatting/handlers`) already maps cleanly
  onto the target architecture. This spec **adds** `formatting/i18n/` and
  `formatting/context.py` and one `handlers/language.py`; it does **not** move
  existing files between packages.
- **City names in the timezone picker are NOT translated.** `TIMEZONE_REGIONS`
  city labels (`Tokyo`, `São Paulo`, `Taipei / Beijing`) stay as-is — they are
  proper nouns whose recognizability drops when translated, and the IANA code is
  the value actually persisted. Only the **region headers** (`🌏 Asia` → `🌏 亞洲`)
  are translated.
- **Session-status abbreviations `DSQ`/`DNS`/`DNF`/`TBD` are NOT translated.**
  These are universal motorsport abbreviations; leaving them stable avoids
  confusion. (Revisit only if a user requests it.)
- **No free-text/user-generated translation.** Only static UI strings. Driver
  names, circuit names, team names come from the API and render as-is.
- **No language auto-detection at all.** No `language_code` sniffing, no IP geo,
  no message-content detection. New users get the platform default (`en` on
  Telegram); they switch explicitly via `/language`. Rationale below.
- **`set_my_commands(language_code=...)` is still used** for the command menu —
  that is Telegram *serving* the right menu when a client asks for a given locale,
  which is free and lossless. It is **not** the same as us guessing a user's
  content language, which we deliberately don't do.

## Language code format — BCP-47 (`en`, `zh-Hant`)

Stored in DB, used as the catalog dict key, and used verbatim as the
`set_my_commands(language_code=...)` argument. BCP-47 is chosen so no conversion
is needed when interoperating with Telegram's menu localization or a future LINE
adapter. The two shipped codes are exactly `en` and `zh-Hant`.

## Architecture

Three layers, matching the existing package boundaries:

```
CORE (platform-agnostic, language-agnostic)
  models/ · storage/ · utils/ · scheduler/ · api/     ← unchanged by this spec
        │  (produces data: Race, Standing, results dicts…)
        ▼
PRESENTATION (language-aware, platform-agnostic)
  formatting/i18n/  t(key, lang, **kwargs) -> str      ← NEW
  formatting/messages.py, timezone.py, emoji.py        ← strings → t(), take RenderContext
  formatting/context.py  RenderContext(lang, tz)       ← NEW
        │  (produces user-visible strings)
        ▼
PLATFORM (Telegram-specific)
  handlers/*.py  resolve_context(update, repo)         ← reads user id → DB pref or default
  handlers/language.py  /language + lang: callbacks    ← NEW
  main.py  set_my_commands per language_code
```

### The message catalog — `formatting/i18n/`

Nested-dict catalog, language on the inner level, split by domain into modules
(the chosen "i18n/ package" option — keeps any single catalog file small and
review-friendly):

```
formatting/i18n/
├── __init__.py          # re-exports t(), and check_catalog_complete()
├── core.py              # t(key, lang, **kwargs), fallback, completeness check
└── catalog/
    ├── __init__.py      # merges the domain dicts into one CATALOG
    ├── common.py        # shared buttons/toasts: back, invalid_selection, generic_error, …
    ├── schedule.py      # /next /schedule /countdown strings
    ├── results.py       # /results, race/quali/sprint/session headers
    ├── standings.py     # /standings /title
    ├── race_data.py     # /pitstops /laps
    ├── extras.py        # /driver /circuit /compare
    ├── notifications.py # /remind flow
    ├── settings.py      # /timezone /language prompts + region headers
    ├── start.py         # /start /help + welcome
    ├── commands.py      # set_my_commands descriptions (14 entries)
    └── datetime.py      # weekday/month names, countdown units + phrases
```

Catalog entry shape (nested dict, language inner):

```python
CATALOG = {
    "schedule.next_race_header": {
        "en": "🏁 *Next Race: {name}*",
        "zh-Hant": "🏁 *下一場比賽：{name}*",
    },
    ...
}
```

### `t()` — lookup, interpolation, fallback

```python
def t(key: str, lang: str, **kwargs) -> str:
    entry = CATALOG.get(key)
    if entry is None:
        raise KeyError(f"Unknown i18n key: {key}")      # programmer error — loud
    template = entry.get(lang) or entry["en"]           # runtime fallback to en
    return template.format(**kwargs) if kwargs else template
```

- **Unknown key** → `KeyError`. That is a programmer bug (typo'd key), surfaced
  loudly, and caught by tests before shipping.
- **Missing translation for a *known* key** → returns the `en` template
  (runtime safety net so a user never sees a raw key or a crash).
- **Interpolation** is `str.format(**kwargs)` — all dynamic data passed as named
  kwargs. This forbids the current anti-pattern of composing a translatable
  template with an untranslated English fragment (e.g. `no_data_message(what)`,
  `f"No {label} data yet this season"`). Every such site becomes a fully
  parameterized key, e.g. `t("results.no_session_data", lang, session=...)`
  where `session` is itself a translated label, not a raw English word.

### Completeness check — Fail Loud via test (chosen option)

`check_catalog_complete()` asserts every key has a non-empty string for **every**
shipped language (`SHIPPED_LANGS = ("en", "zh-Hant")`). It is invoked by a
**pytest test** (`test_i18n_catalog_complete`) so a missing translation turns CI
red before merge. The runtime path additionally falls back to `en` (above) as a
safety net, so a slipped-through gap degrades to English rather than crashing.
(We deliberately do NOT gate bot startup on this — a translation gap should block
*merge*, not take down a running production bot; the en fallback covers the
runtime case.)

### `RenderContext` — `formatting/context.py`

```python
@dataclass(frozen=True)
class RenderContext:
    lang: str = "en"
    tz: str = "UTC"
```

Platform-agnostic (no `telegram` import). Replaces the bare `user_tz` string
threaded through formatters today. Frozen, matching the codebase's frozen-model
convention. Every formatter signature changes from `(…, user_tz)` to `(…, ctx)`
and reads `ctx.lang` / `ctx.tz`.

### Language resolution — `resolve_context()` (platform layer)

Lives in a **new** shared helper module `handlers/context.py` (Telegram-specific,
reads `Update`), **not** in the platform-agnostic core and **not** bundled into
`handlers/language.py` (which owns the `/language` command — a separate
responsibility). Single source of truth for "which language + tz for this
request", so the priority logic is not duplicated across handlers:

```python
async def resolve_context(update, repo, default_lang="en") -> RenderContext:
    pref = await repo.get_user_preference(update.effective_user.id)
    if pref:
        return RenderContext(lang=pref.language, tz=pref.timezone)
    return RenderContext(lang=default_lang, tz="UTC")
```

- **`default_lang` is a parameter**, not a hardcoded constant — Telegram passes
  `"en"`; a future LINE adapter will pass `"zh-Hant"` (see
  `roadmap-line-adapter.md`). The core stays default-agnostic.
- Order: **DB preference > `default_lang`**. Two layers, not three — there is no
  `language_code` middle layer and no `_lang_from_telegram()` normalization
  helper. See "Rollout & first-run behavior" for why auto-detection was dropped.
- Because the `language` column is `NOT NULL DEFAULT 'en'`, `pref.language` is
  always a concrete value; there is no "unset" state to disambiguate.
- `get_user_language(telegram_id) -> str` is also added to `Repository`
  (mirroring `get_user_timezone`), returning `pref.language` or `"en"`, for the
  code paths that need only the language and have no `Update` (e.g. the
  notification sender — see below).

## Rollout & first-run behavior

This section exists because an earlier draft coupled two individually-reasonable
choices into a silent regression. Recording the resolution so it is not
re-introduced.

**The trap (rejected design):** resolution order `DB pref > language_code >
default` **plus** migration `ADD COLUMN language NOT NULL DEFAULT 'en'`. A
`user_preferences` row exists today **only if the user ran `/timezone`** (the sole
row-creating path). The migration backfills every such row to `language='en'`, and
`resolve_context` returns the DB value whenever a row exists — so every existing
timezone-setter is **pinned to English and never consults `language_code`**,
silently degrading exactly the zh-Hant cohort most likely to have set a timezone.
The backfill is a one-way migration; the damage is unrecoverable after deploy.

**The resolution (adopted design):** drop `language_code` auto-detection entirely.

- **New users get the platform default** (`en` on Telegram), full stop. They
  switch explicitly via `/language`.
- This is *consistent with the already-decided per-platform default* (Telegram =
  `en`): auto-detecting a zh-Hant client into Chinese would have quietly overridden
  that stated default anyway.
- It makes `resolve_context` two layers instead of three, removes the
  normalization helper, and lets the migration stay the simplest possible
  `NOT NULL DEFAULT 'en'` with no nullable/"unset" state to reason about.
- Trade-off accepted: a zh-Hant-client user sees English until they run
  `/language`. `language_code` is the *client UI* language, not a reading-
  preference signal, so auto-detect would guess wrong for some users regardless.

**Discoverability mitigation (required, cheap):** so a non-English-reading user is
not stranded in an English wall, `/start`'s welcome includes a persistent
`🌐 Language / 語言` inline button (bilingual label, always shown) that opens the
same picker as `/language`. `/language` is also in the command menu. This buys
discoverability without any resolution-chain complexity.

- `handlers/start.py`: welcome keyboard gains the `🌐 Language / 語言` button
  emitting the `/language` picker (reuses `handlers/language.py`'s picker builder).

## Data model & storage changes

### `models/user.py`

Add `language` to `UserPreference`:

```python
class UserPreference(BaseModel):
    telegram_id: int
    timezone: str = "UTC"
    language: str = "en"          # NEW
    created_at: datetime | None = None
    updated_at: datetime | None = None
```

### `storage/postgres_store.py`

1. **Schema** (`SCHEMA` constant `user_preferences` block): add
   `language TEXT NOT NULL DEFAULT 'en'`.
2. **Migration in `init()`**: because `CREATE TABLE IF NOT EXISTS` will NOT alter
   an already-deployed table, add — next to the existing ad-hoc `DELETE`
   migration —
   ```sql
   ALTER TABLE user_preferences ADD COLUMN IF NOT EXISTS language TEXT NOT NULL DEFAULT 'en'
   ```
   so existing rows backfill to `'en'`.
3. **`get_user_preference`**: add `language` to the `SELECT` and to the
   `UserPreference(...)` construction.
4. **Replace the whole-object `upsert_user_preference` with two single-column
   upserts** — `set_user_timezone(telegram_id, tz)` and
   `set_user_language(telegram_id, lang)`. See the clobber/race fix below.

### Upsert clobber & race fix (critical) — single-column upserts

Today `_save_tz` constructs a *fresh* `UserPreference(telegram_id=…, timezone=…)`
and calls a whole-object upsert whose `ON CONFLICT DO UPDATE SET timezone=…` works
**only because `timezone` is the sole field**. Two problems appear once `language`
is added:

1. **Clobber:** writing one field via a whole object would carry the *other*
   field's default (set language → timezone reverts to `"UTC"`, and vice-versa).
2. **Race (the subtler one):** a read-modify-write fix (load → mutate one field →
   write whole object) spans two `await`s on the connection pool. Two concurrent
   edits from the same user (fast `/timezone` then `/language`) interleave: both
   read the old row, each writes back its field **plus the other's stale value** —
   reintroducing the clobber as a TOCTOU race.

**Fix — each save updates only its own column, as one atomic statement:**

```sql
-- set_user_timezone
INSERT INTO user_preferences (telegram_id, timezone, created_at, updated_at)
VALUES ($1, $2, $now, $now)
ON CONFLICT (telegram_id) DO UPDATE
  SET timezone = EXCLUDED.timezone, updated_at = EXCLUDED.updated_at;

-- set_user_language
INSERT INTO user_preferences (telegram_id, language, created_at, updated_at)
VALUES ($1, $2, $now, $now)
ON CONFLICT (telegram_id) DO UPDATE
  SET language = EXCLUDED.language, updated_at = EXCLUDED.updated_at;
```

Why this is strictly better than read-modify-write:

- **Atomic, no TOCTOU:** a single `ON CONFLICT` statement; the DB resolves the
  conflict inside one transaction. No read-then-write window.
- **Either command creates the row; the PRIMARY KEY prevents duplicates.** A user
  who runs only `/language` (never `/timezone`) gets a row created with
  `timezone` taking its column `DEFAULT 'UTC'`; a `/timezone`-only user gets
  `language` taking `DEFAULT 'en'`. Both column defaults are exactly the intended
  "hasn't chosen yet" fallbacks, so this stays consistent with the rollout design.
- **`created_at` is written only on the INSERT branch**, not touched by
  `DO UPDATE` — fixing an existing latent bug where the whole-object upsert
  overwrote `created_at` with `now()` on every update.
- **Smaller change to `_save_tz`:** it calls `set_user_timezone(...)` instead of
  constructing a fresh `UserPreference`.

`_save_tz` (timezone handler) is a required change, not just new code. The new
language save uses `set_user_language`. `upsert_user_preference` is removed (or
kept only if another caller needs a whole-object write — audit at implementation
time; today `_save_tz` is the only caller).

## The `/language` command — `handlers/language.py` (NEW)

Mirrors `handlers/timezone.py`, with a distinct callback namespace `lang:` so the
routers don't collide with `tz:`.

- `/language` → shows a **single-level** picker listing the shipped languages
  (English / 繁體中文), with the current selection indicated. Each button emits
  `lang:set:{code}`. Unlike `/timezone`, there is **no region/group intermediate
  step** (`tz:region:` has no `lang:` counterpart) — with two options a drill-down
  is pure friction. This stays true as long as the list fits one screen; a future
  third/fourth language does not change it.
- Direct form `/language zh-Hant` is accepted too (validated against
  `SHIPPED_LANGS`), mirroring `/timezone Asia/Taipei`.
- `lang:set:{code}` callback → validate code ∈ `SHIPPED_LANGS`, then call
  `set_user_language(telegram_id, code)` (single-column upsert), confirm in the
  **newly chosen** language.
- `register(app)` adds the `CommandHandler("language", …)` and
  `CallbackQueryHandler(pattern=r"^lang:")`.
- The picker keyboard builder is also reused by `handlers/start.py`'s welcome
  `🌐 Language / 語言` button (see rollout section), so expose it as a shared
  helper rather than inlining it in the command handler.

### Callback data formats

| Pattern | Meaning |
|---|---|
| `lang:set:{code}` | User picked a language; validate, save, confirm |

`{code}` ∈ `{en, zh-Hant}`. Short and well under Telegram's 64-byte limit.
Callback-parse guard: unknown/malformed code → answer "Invalid selection", per
the codebase convention.

## Shared-constant conversion (the string-extraction amplifier)

Three module-level dicts feed **both** formatters and handlers and must change
from static constants to language-aware lookups. This is the bulk of the
mechanical work.

| Constant | Location | Change |
|---|---|---|
| `SESSION_LABELS` | `utils/sessions.py` | Add `session_label(key, lang) -> str` (via catalog). **Remove the `SessionEntry.label` property** — it hides a language dependency and would leave two ways to get a label. Its `if normalized in SESSION_LABELS` **membership check is a key-set test, language-independent — keep that dict (or a `SESSION_KEYS` set) for membership; only the display path moves to the catalog.** |
| `TIMING_PRESETS` | `models/notification.py` | Add `timing_label(preset, lang) -> str`; presets (`15min`/`1hr`…) render via catalog. |
| `TIMEZONE_REGIONS` | `formatting/timezone.py` | Region **headers** (`🌏 Asia`) render via catalog (`settings.region_asia` …); **city labels stay literal** (non-goal). Picker builds header text through `t()`, keeps `(city_label, iana)` tuples as-is. |

> **Read-before-write:** `SessionEntry.label` has exactly **3** call sites, **all
> in `formatting/messages.py`** (`98`, `101`, `294`) — none in `handlers/`. Each
> becomes `session_label(entry.key, ctx.lang)`. Blast radius is formatting-only;
> still verify with a grep before removing the property.

## Date / time localization (`formatting/timezone.py`)

Date formatting is itself an i18n concern and currently English-only:

- `format_dt` uses `strftime("%a %b %d, %H:%M")` → English `"Mon Jul 30"`.
  `strftime` weekday/month names depend on the **process-global C locale** —
  non-thread-safe under async and unusable for per-user language (same class of
  bug as global gettext). **Do not** switch process locale.
- **Fix:** `format_dt(dt, ctx)` (or `(dt, tz, lang)`) formats the numeric parts
  with `strftime` (locale-independent: `%H:%M`, day number) and pulls
  **weekday/month names from the catalog** (`datetime.weekday_short.*`,
  `datetime.month_short.*`). zh-Hant renders e.g. `7月30日 (週一) 22:00`.
- `format_countdown`: `"In progress / finished"`, `"< 1 minute"`, and the
  `d`/`h`/`m` unit suffixes move to the catalog (`datetime.*`) and take `lang`.

The exact zh-Hant date layout (ordering of weekday/month/day) is a catalog
template, so it can differ structurally from the en layout without code changes.

## Monospace table alignment — CJK display width (`/compare`, code-block tables)

`/compare` renders its stat grid inside a ` ``` ` monospace code block using
Python field-width padding:

```python
def _cmp_row(label, a_str, b_str, extra=""):
    return f"{label:<10}{a_str:>3} ─ {b_str:>3}{extra}"
```

`{label:<10}` pads to **10 code points**. Once labels are translated, this breaks:
`"Points"` (6 code points, 6 display columns) becomes `"積分"` (**2 code points but
4 display columns** — CJK glyphs are double-width in a monospace font). `str`
padding counts code points, so `"積分"` is padded to `積分` + 8 spaces = 12 display
columns while the English row is 10 — the numeric columns on CJK rows drift right
and the `─` separators no longer line up.

**Decision (chosen): display-width-aware padding, keep the monospace grid.**

- Add a helper in `messages.py`:
  ```python
  from unicodedata import east_asian_width

  def _display_width(s: str) -> int:
      return sum(2 if east_asian_width(c) in ("W", "F") else 1 for c in s)

  def _pad_display(s: str, width: int) -> str:
      return s + " " * max(0, width - _display_width(s))
  ```
  Standard-library `unicodedata` — **no new dependency** (Rule 2). `_cmp_row`
  pads the label via `_pad_display(label, TARGET)` instead of `{label:<10}`.
- **Target column width bumps from 10 to ~12 display columns**: the longest
  zh-Hant label (`正賽+衝刺` = 4+1+4 = 9 cols, `桿位對決` = 8 cols) plus a
  min-gap must not collide with the number column. Size the target off the widest
  shipped label in **both** languages and assert it in a test, rather than
  hard-coding 10.
- Ambiguous-width chars (`east_asian_width` category `"A"`, e.g. the `─` box-drawing
  separator) are counted as **1**. `─` is identical on every row, so it shifts all
  rows equally and never affects *cross-row* alignment; only the label column width
  matters. The shipped zh labels are all category `"W"`, so this choice is safe for
  them — a test asserts each shipped label's `_display_width` to catch a future
  label that sneaks in an ambiguous char.
- Labels move into the catalog (`extras.py`): `Points`, `Quali H2H`, `Race+Spr`,
  `Wins`, `Podiums`, `DNFs` become `extras.compare_row_*` keys with en + zh-Hant.
  The two existing stray zh literals (`_COMPARE_NO_DATA`, the sprint footnote) move
  there too, fixing the leakage.

**Known limitation (Fail Loud, accepted):** column alignment in a Telegram
monospace block is **font-dependent**. iOS / Android / macOS / most desktop clients
render CJK at exactly 2× the Latin monospace advance and align correctly; a few Web
/ fallback-font clients may render CJK at non-2× width and drift 1–2 columns. This
is a ceiling of monospace+CJK, not fixable by any padding math. Accepted for a
hobby F1 bot; documented so it is not mistaken for a bug later. (The rejected
alternative — moving labels out of the code block into proportional text — is
bulletproof across clients but loses the aligned-grid table, judged a worse UX.)

**Generalizes:** any other code-block table whose labels/headers get translated to
CJK reuses `_pad_display`. Audit `laps` / `pitstops` / `standings` renderers for
translated CJK headers at implementation time (grep for `:<` / `:>` field widths in
`messages.py`); apply the same helper where found. Data columns (driver codes,
numbers) are ASCII from the API and unaffected.

## Telegram command menu localization (`main.py`)

`set_my_commands` is called **once per shipped language** with `language_code`:

- Default (no `language_code`) and `language_code="en"`: English descriptions.
- `language_code="zh-Hant"`: Traditional-Chinese descriptions, pulled from the
  `commands.*` catalog keys.

The **15** `BotCommand` descriptions currently inline in `_post_init`
(`main.py:45-59`) move into the `commands.py` catalog module — **16** once
`/language` is added. `_post_init` builds each language's list from the catalog
and registers it. Telegram then shows each user the menu matching their client
language natively. (The catalog `commands.py` must hold all 16; Telegram silently
ignores a mismatched list, so a wrong count will not fail loudly — size it
correctly and assert the count in a test.)

> **Note:** `set_my_commands(language_code=...)` is the **one** Telegram-native
> localization mechanism with no LINE equivalent — it correctly lives in the
> platform layer (`main.py`), not the catalog core.

## Notification sender (`scheduler/notification_sender.py`)

`send_notifications` runs from a JobQueue job with **no `Update`** — it has the
target `telegram_id` but cannot call `resolve_context`. It must render each
reminder in the recipient's language via
`lang = await repo.get_user_language(telegram_id)`.

**`lang` only — no tz.** `format_notification_message` (`messages.py:685-691`)
takes `(race, session_key, minutes_before)` and renders **no time** ("starts in N
minutes"); `send_notifications` never fetches a recipient tz. So pass
`RenderContext(lang=lang, tz="UTC")` (or just `lang`) — do **not** add a
recipient-tz lookup the message doesn't use (that would be speculative state on a
hot job path). `get_user_language` exists on `Repository` purely because this path
has no `Update`, independent of the resolver.

## Error handler (`handlers/errors.py`) — localized errors

Two English literals leak here and are the last user-facing gap after the
formatters are done:

1. `_USER_MSG = "Something went wrong. Please try again in a moment."` — the
   generic unhandled-error reply (`errors.py:45`).
2. `CommandValidationError` carries an **already-rendered English string** that
   `error_handler` replies verbatim via `str(context.error)` (`errors.py:23`). Every
   `raise CommandValidationError("…english…")` site bakes in English.

**Fix — errors carry a key, `error_handler` resolves the language centrally.**
`error_handler` already receives `update`, so it can call `resolve_context` — the
same seam every command uses. It is the natural single place to localize both
error paths:

```python
# errors.py
class CommandValidationError(Exception):
    def __init__(self, key: str, **kwargs):
        self.key = key
        self.kwargs = kwargs
        super().__init__(key)

async def error_handler(update, context):
    repo = context.bot_data["repo"]
    ctx = await _safe_context(update, repo)   # resolve_context, or RenderContext() if no Update/user
    if isinstance(context.error, CommandValidationError):
        if isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text(
                t(context.error.key, ctx.lang, **context.error.kwargs),
                parse_mode=ParseMode.MARKDOWN,
            )
            return
    # … NetworkError log-only branch unchanged …
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(t("common.generic_error", ctx.lang))
```

- `_USER_MSG` → catalog key `common.generic_error`.
- `CommandValidationError` now carries a **key + kwargs**, not a rendered string.
  **Every `raise CommandValidationError(...)` site changes** to pass a key
  (validation messages live in each command's domain catalog module, e.g.
  `schedule.invalid_round`). **Read-before-write:** grep all
  `raise CommandValidationError(` sites and convert each — the count and locations
  are an implementation-time audit, listed in the PR.
- `_safe_context`: if `update` is not an `Update` or has no `effective_user`
  (error paths can fire without one), fall back to `RenderContext()` (en) rather
  than crashing the error handler itself — the handler must never raise.

Without this, "全部都翻譯" has a visible hole: a zh-Hant user typing a bad
argument still gets an English validation message.

## Anti-regression guard — no un-catalogued user-facing strings

A completeness check proves the catalog is *filled*; it does not prove feature
code actually *uses* it. Nothing stops a future edit from re-introducing an inline
literal (exactly how the three stray `/compare` zh strings arose). Add a guard
test so "everything is translated" stays enforced, not just true once:

- **Guard A (primary, zero-false-positive):** scan every `.py` under
  `handlers/` and `formatting/` **except** `formatting/i18n/catalog/` for CJK
  codepoints (`　-鿿` + CJK punctuation ranges). Any hit is a leaked
  hardcoded translation → test fails, pointing at file:line. This directly targets
  the documented original sin (hardcoded zh) with **no** heuristics and thus no
  false positives — all Chinese must live in the catalog, full stop.
- **Guard B (complementary, AST-based):** walk the same trees' ASTs for calls to
  `reply_text` / `edit_message_text` / `answer` (the user-output boundary) whose
  text argument is a **string literal** rather than a `t(...)` call or a variable.
  Catches hardcoded *English* at the point it reaches a user. A small allowlist
  covers legitimate literals (empty string, the non-translated abbreviations
  `DSQ`/`DNS`/`DNF`/`TBD` per non-goals, pure-`%`/format scaffolding).

Guard A is the must-have (trivial, exact). Guard B is recommended but ships with an
allowlist to keep it low-maintenance; if the allowlist starts churning, Guard A
alone still enforces the property that matters most (no silent zh, and English is
the safe fallback anyway).

## Files touched

| File | Change |
|---|---|
| `formatting/i18n/` (package) | **New.** `core.py` (`t`, `check_catalog_complete`), `catalog/` domain modules, `__init__.py`. |
| `formatting/context.py` | **New.** `RenderContext(lang, tz)` frozen dataclass. |
| `formatting/messages.py` | All ~20 formatters: signatures `(…, user_tz)` → `(…, ctx)`; every literal string → `t(key, ctx.lang, …)`. Remove `_COMPARE_NO_DATA`/footnote literals into catalog (fixes the zh leakage). Add `_display_width`/`_pad_display` (stdlib `unicodedata`); `_cmp_row` pads labels by display width, target col width sized off the widest shipped label (CJK-alignment fix). |
| `formatting/timezone.py` | `format_dt`/`format_countdown` take `lang`; weekday/month/units via catalog. `TIMEZONE_REGIONS` region headers via catalog; city labels unchanged. |
| `utils/sessions.py` | Add `session_label(key, lang)`; **remove `SessionEntry.label`**; keep key-set for membership checks. |
| `models/notification.py` | Add `timing_label(preset, lang)`; presets render via catalog. |
| `models/user.py` | Add `language: str = "en"` to `UserPreference`. |
| `storage/postgres_store.py` | Schema `+language`; `ALTER TABLE … ADD COLUMN IF NOT EXISTS language TEXT NOT NULL DEFAULT 'en'` in `init()`; `language` in `get_user_preference`. Replace whole-object `upsert_user_preference` with single-column upserts `set_user_timezone` / `set_user_language` (clobber+race fix); `created_at` written only on INSERT branch. |
| `storage/repository.py` | Add `get_user_language(telegram_id) -> str`; add `set_user_timezone` / `set_user_language` pass-throughs mirroring `get_user_timezone`. |
| `handlers/language.py` | **New.** `/language` command + `lang:` callback + `register`; exposes a shared picker-keyboard builder (reused by `start.py`). Saves via `set_user_language`. |
| `handlers/__init__.py` | Import `language`; call `language.register(app)`. |
| `handlers/start.py` | Welcome keyboard gains a persistent `🌐 Language / 語言` inline button opening the `/language` picker (discoverability, see rollout). Welcome/help strings via `t()`. |
| `handlers/timezone.py` | `_save_tz` → call `set_user_timezone` (drops fresh-object construction; clobber+race fix). Prompts/confirmations via `t()`. |
| `handlers/context.py` | **New.** `resolve_context(update, repo, default_lang="en")` — two-layer (DB pref > default), **no** `language_code`/`_lang_from_telegram` normalization. Shared by all handlers. |
| `handlers/*.py` (all others) | Replace `repo.get_user_timezone(...)` + literal strings with `resolve_context(update, repo)` (from `handlers/context.py`) + `t(...)`; pass `ctx` into formatters. Note: ~8 handlers do no preference lookup today and gain one per-request DB read (see Failure modes). |
| `handlers/errors.py` | `_USER_MSG` → `common.generic_error` via `t()`. `CommandValidationError` carries a **key + kwargs** (not a rendered string); `error_handler` resolves lang via `resolve_context` and renders through `t()`, falling back to en (`_safe_context`) when there is no `Update`/user. **All `raise CommandValidationError(...)` sites** convert to pass a key (implementation-time grep audit). |
| `scheduler/notification_sender.py` | Render reminders via `get_user_language` (lang only, no tz). |
| `main.py` | `set_my_commands` per `language_code` from `commands.*` catalog. Register `/language` (via `register_all_handlers`). |
| `CLAUDE.md` | Add `/language` to command table; `lang:*` callback row; i18n architecture note; new key files. |
| `README.md` | Add `/language` + i18n to feature list. |
| `tests/…` | New tests (below), including the anti-regression guard (Guard A CJK scan + Guard B AST output-boundary scan). |

## Performance & failure modes

- **Extra per-request preference read.** Today only `schedule.py` (×4) and
  `timezone.py` (×1) call `get_user_timezone`; ~8 other handlers do **no**
  preference lookup. Threading `resolve_context` through every handler adds one
  `user_preferences` read per command **and per callback** — including
  callback-heavy flows (pagination, `/compare` stepping) where it fires on every
  click. **Decision:** accept the single indexed primary-key lookup (cheap; the
  DB is already the hot path for every handler). If it shows up in profiling,
  cache the resolved `RenderContext` on `context` for the lifetime of one update
  (one read per update regardless of how many formatters run) — noted, not built
  (YAGNI). Do **not** add a recipient-tz read on the notification path (it renders
  no time; see Notification sender).
- **Message length after translation.** zh-Hant is typically *shorter* per glyph
  than en, so the 4096-char Telegram limit is lower-risk after translation. The
  existing `/results` "All" 3-stage truncation and the laps tables already run
  near the limit; a test asserting the longest zh-Hant render stays under 4096
  de-risks it.
- **CJK monospace-table alignment (resolved).** `/compare`'s code-block table
  aligns via display-width-aware padding (`_pad_display`, stdlib
  `unicodedata.east_asian_width`) — see "Monospace table alignment" above. Keeps
  the grid on mainstream clients; documented font-dependent drift on rare
  fallback-font clients accepted (Fail Loud, not a silent gap).

## Testing approach

Unit tests (no network; dev PostgreSQL via `repo` fixture where needed). Each
test encodes **why** the behavior matters:

- **Catalog completeness (Fail Loud):** `check_catalog_complete()` passes for the
  full catalog; a deliberately-removed `zh-Hant` entry makes it raise. Guards the
  merge gate — a missing translation must turn CI red, not ship silently.
- **`t()` unknown key raises `KeyError`:** a typo'd key is a loud programmer
  error, never a silent empty string.
- **`t()` runtime fallback:** a known key missing one language returns the `en`
  template (constructed via a patched catalog), proving the user never sees a raw
  key even if the completeness gate were bypassed.
- **`t()` interpolation:** `t("…", lang, name="X")` fills `{name}`; kwargs are
  named — guards against re-introducing positional English-fragment composition.
- **`resolve_context` two-layer priority:** a user with a DB pref gets that lang;
  a user with **no** row gets `default_lang`; passing `default_lang="zh-Hant"`
  (simulating LINE) is honored for a no-row user. Proves the documented order and
  the platform-parameterized default. (No `language_code` case — auto-detection
  was dropped; see rollout.)
- **First-run / rollout (no silent English-pinning):** a user with an existing
  `user_preferences` row that has never set a language reads back `language ==
  "en"` (the column default) and `resolve_context` returns `en` — matching the
  intended default, **not** a regression. Documents the adopted rollout so the
  rejected auto-detect trap is not re-introduced.
- **Upsert clobber fix:** set timezone then set language via the handlers; reload
  → **both** persist. Regression test — must fail against the old fresh-object
  whole-row upsert.
- **Single-column upsert / either-command-creates-row:** calling
  `set_user_language` for a user with **no** prior row creates the row with
  `timezone == "UTC"` (column default); calling `set_user_timezone` for a no-row
  user creates it with `language == "en"`. Proves either command can create the
  row and the PRIMARY KEY yields no duplicate. `created_at` is unchanged by a
  subsequent update to the other column (proves `created_at` is INSERT-only).
- **`ALTER TABLE` migration:** against a `user_preferences` table created without
  `language` (simulating a deployed DB), `init()` adds the column and existing
  rows read back `language == "en"`. Guards the "schema constant alone is
  insufficient" gotcha.
- **`/language` set + confirm-in-new-language:** `lang:set:zh-Hant` persists
  `zh-Hant` and the confirmation renders from the `zh-Hant` catalog (not `en`) —
  the user sees the language they just chose.
- **`/language` callback guard:** malformed/unknown `lang:set:xx` → "Invalid
  selection", no crash and no write.
- **`session_label` localization + `.label` removal:** `session_label("race",
  "zh-Hant")` returns the zh label; a reference to the removed
  `SessionEntry.label` no longer exists (grep-guard or import test). Proves the
  amplifier constant fully moved and the property didn't linger as a second path.
- **Date localization:** `format_dt` with `lang="zh-Hant"` renders zh weekday/
  month and does **not** depend on process locale (assert stable regardless of
  `LC_TIME`). Guards the strftime-global-locale trap.
- **Notification language:** a reminder for a user whose pref is `zh-Hant`
  renders via the zh catalog — proves the `Update`-less job path localizes
  correctly through `get_user_language`.
- **Command-menu per language:** `set_my_commands` is invoked with a `zh-Hant`
  `language_code` list distinct from the default list (assert on the mocked bot).
- **Compare zh-leakage fixed:** the previously-hardcoded `本賽季…` / `重新比較`
  strings now come from the catalog and render `en` when `lang="en"` — proves the
  pre-existing inconsistency is resolved, not merely relocated.
- **CJK table alignment (`_pad_display`):** `_display_width("積分") == 4` and
  `_display_width("Points") == 6`; every shipped zh-Hant compare label pads to the
  **same** display-column start as its en counterpart, so the `─` separators align
  across a mixed en/zh render. Also asserts the chosen target width ≥ the widest
  shipped label's `_display_width` (guards a future long label from silently
  overflowing the number column). Encodes *why*: a code-point-width regression
  (reverting to `{label:<10}`) must fail this test.
- **Markdown escaping preserved:** interpolated dynamic values containing `_`/`*`
  still pass through `_esc()` before landing in a `t()` template (use a
  special-char fixture), per the legacy-`MARKDOWN` convention.
- **`query.answer()` discipline:** the `lang:` callback answers exactly once.
- **Localized errors (Grill #6):** a `CommandValidationError("schedule.invalid_round",
  …)` raised for a `zh-Hant` user is replied in Chinese (resolved via
  `resolve_context`, not the raise site); the generic-error path renders
  `common.generic_error` in the user's language. Encodes *why*: errors must not be
  the one un-translatable surface. Also assert `error_handler` never raises when
  `update` has no `effective_user` (falls back to en `RenderContext`).
- **Anti-regression guard (Grill #5):** Guard A — a fixture file containing a CJK
  literal under `handlers/`/`formatting/` (outside `catalog/`) makes the scan fail;
  the real tree passes. Guard B — a `reply_text("hardcoded")` string-literal call
  fails the AST scan while `reply_text(t(...))` and `reply_text(var)` pass; the
  allowlisted abbreviations (`DNF` …) pass. Encodes *why*: proves the catalog is
  actually *used*, not just filled — the property that stops the original leak from
  recurring.

## Trade-offs considered

- **i18n package vs single file:** chose a `formatting/i18n/catalog/` package
  split by domain. Costs a little more structure; buys review-friendly,
  small-file catalogs at 150+ keys (a single 150-entry file is hard to diff).
- **Nested dict (lang inner) vs per-language files:** chose nested dict so each
  key's translations sit side-by-side — a missing language is visible in review,
  and the completeness check is trivial. Per-language files would need cross-file
  diffing to spot gaps.
- **BCP-47 (`zh-Hant`) vs short (`zh`):** chose BCP-47 for zero-conversion
  interop with Telegram `language_code`, `set_my_commands`, and future LINE. `zh`
  would force normalization and can't distinguish Traditional/Simplified later.
- **Test-gate completeness vs startup-gate:** chose test-gate (CI red) + runtime
  en fallback. A translation gap should block *merge*, not crash a running bot;
  the fallback covers the runtime edge. Startup-gate risks taking prod down for a
  cosmetic gap.
- **`RenderContext` vs bare `lang` scalar:** chose to bundle `lang`+`tz`. `tz` was
  already threaded everywhere; adding `lang` as a second scalar doubles the
  signature churn on every future preference. The context object is also the
  minimal seam a future LINE adapter / view-model layer reuses. Costs one
  refactor of formatter signatures now (unavoidable for full i18n regardless).
- **City names translated vs kept:** kept. Proper nouns lose recognizability when
  translated and the IANA code is the real value; only region headers translate.
- **Per-platform default as parameter vs core constant:** chose parameter.
  Telegram defaults `en`, LINE will default `zh-Hant`; baking `en` into the core
  resolver would force an edit when LINE arrives. The default is the platform's
  property, not the preference logic's.
- **`language_code` auto-detect vs explicit-only:** chose explicit-only (default +
  `/language`). Auto-detect from the Telegram client locale looked friendlier but
  (a) combined with the backfill migration it silently pinned existing users to
  `en` — an unrecoverable one-way regression (see Rollout); (b) `language_code` is
  the client *UI* language, not a content-reading preference, so it mis-guesses
  regardless; (c) it quietly contradicts the chosen Telegram default of `en`. Cost
  of explicit-only: a zh-Hant user sees English until `/language` — mitigated by
  the always-visible `🌐 Language / 語言` welcome button. Simpler resolver,
  simplest migration, no silent data loss.

## Relationship to future work

This spec deliberately lays the groundwork for two deferred sub-projects, each
with its own roadmap spec:

- `roadmap-view-model-extraction.md` — splitting handler data-production from
  rendering. The `RenderContext` seam and the platform-agnostic `t()` are the
  hardest parts of that groundwork, done here.
- `roadmap-line-adapter.md` — a LINE bot reusing the language-agnostic core and
  the platform-agnostic catalog, with its own `resolve_context` (default
  `zh-Hant`) and UI rendering.
