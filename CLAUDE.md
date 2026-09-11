# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the project

```bash
uv run -m f1_bot                          # start the bot (requires .env)
uv run pytest -m "not integration"        # unit tests only (~565 tests, dev PostgreSQL)
uv run pytest -m integration -v           # integration tests (real HTTP, ~19 tests)
uv run pytest tests/test_smoke.py -v      # full-stack smoke test

# Coverage — NOT `pytest --cov` (segfaults, see gotcha below)
uv run coverage run --source=f1_bot -m pytest -m "not integration" -p no:randomly
uv run coverage report
```

## Architecture

**SQL-only handlers:** background scheduler (JobQueue) fetches from Jolpica + OpenF1 → stores in PostgreSQL. Telegram handlers read exclusively from PostgreSQL via `Repository`. No API calls from handlers.

```
Startup / Scheduler → JolpicaClient + OpenF1Client → PostgreSQL
                                                          ↓
              Telegram users → handlers → Repository → PostgreSQL (read-only)
```

- **Two-state UX:** `/next` and `/results` use a unified two-state interaction: State A (overview with session filter buttons + round navigation) → State B (filtered with round navigation + Back).
- **i18n (three layers, `en` + `zh-Hant`):** no user-facing string lives in feature code.

```
CORE (language-agnostic)        models/ storage/ utils/ scheduler/ api/
PRESENTATION (platform-agnostic) formatting/i18n/ t(key, lang, **kwargs) · RenderContext(lang, tz)
PLATFORM (Telegram)              handlers/ resolve_context(update, repo) · set_my_commands(language_code=)
```

  `t()` never imports `telegram` and never sees an `Update`, so a future LINE
  adapter reuses the catalog unchanged — it only supplies its own
  `resolve_context` and platform default. Language resolution is **two layers:
  DB preference > platform default (`en`)**. There is deliberately **no
  `language_code` auto-detection** (see spec 005's rollout section — combined
  with the backfill migration it would have silently pinned existing users to
  English, unrecoverably).
- **Source repository:** Hosted at `https://github.com/cby0730/f1-bot` (the `/start` welcome message links here for stars).

## Commands and callback data

The 9-command visible menu → handler map and the full `callback_data` pattern table live in
`src/f1_bot/handlers/CLAUDE.md`, which loads automatically when working under that directory.

## Key files

| File | Role |
|---|---|
| `src/f1_bot/main.py` | Application builder; `_post_init` sets up clients, repo, runs `startup_sync`, registers commands |
| `src/f1_bot/config.py` | Pydantic Settings; env vars: `TELEGRAM_BOT_TOKEN`, `F1BOT_DATABASE_URL`, `F1BOT_*` |
| `src/f1_bot/storage/postgres_store.py` | Persistent store (asyncpg); init with `await store.init()` |
| `src/f1_bot/storage/repository.py` | Unified read layer over PostgreSQL; `get_schedule_bounds()` is the source of truth for completed/upcoming rounds |
| `src/f1_bot/scheduler/jobs.py` | `startup_sync()` + `hourly_sync()` + individual `sync_*` callbacks; each takes `(jolpica, repo)` or `(openf1, repo)` |
| `src/f1_bot/scheduler/manager.py` | Registers single `hourly_sync` job via `run_repeating`; owns `_POLL_INTERVAL` |
| `src/f1_bot/handlers/pagination.py` | Shared keyboard builders: `next_overview_keyboard`, `next_filtered_keyboard`, `results_overview_keyboard`, `results_filtered_keyboard`, `round_keyboard`, `schedule_keyboard`; also `round_picker_keyboard`/`round_picker_text` and the round-set helpers (`upcoming_rounds`, `get_completed_rounds_for_session`) the picker reuses |
| `src/f1_bot/handlers/round_picker.py` | Round picker overlay handler (`rpk:` callbacks); `_compute_navigable_rounds(origin, ...)` maps the `origin` token back to the caller's navigable rounds |
| `src/f1_bot/handlers/compare.py` | `cmp:a` / `cmp:b` from a driver profile; aggregates current-season race+sprint results into a two-driver head-to-head. Reads PostgreSQL only |
| `src/f1_bot/utils/championship.py` | Pure clinch math (DB-free): `remaining_events`, `max_remaining_points`, `clinch_status`, `ClinchStatus`; point constants `WDC_RACE_MAX`/`WDC_SPRINT_MAX` (25/8), `WCC_RACE_MAX`/`WCC_SPRINT_MAX` (43/15) |
| `src/f1_bot/formatting/i18n/core.py` | `t(key, lang, /, **kwargs)` (the `/` is load-bearing — see gotcha), `lang_name()`, `check_catalog_complete()`, `SHIPPED_LANGS` (`en`, `zh-Hant`), `DEFAULT_LANG` |
| `src/f1_bot/formatting/i18n/catalog/` | The message catalog, split by domain (`common`, `schedule`, `results`, `standings`, `race_data`, `extras`, `notifications`, `settings`, `start`, `commands`, `datetime`). Nested dict, language on the inner level; `__init__.py` merges them and raises on a duplicate key |
| `src/f1_bot/formatting/context.py` | `RenderContext(lang, tz)` frozen dataclass — the render-time seam threaded into every formatter |
| `src/f1_bot/handlers/context.py` | `resolve_context(update, repo, default_lang)` — the single source of truth for "which language + tz for this request" |
| `src/f1_bot/handlers/language.py` | `lang:set:` callbacks + `language_keyboard()` reused by `/settings` `set:lang` |
| `src/f1_bot/handlers/settings.py` | `/settings` hub; `set:tz` / `set:lang` edit onto the existing timezone and language pickers |
| `src/f1_bot/formatting/messages.py` | All message formatters (`format_schedule`, `format_driver_standings`, `format_constructor_standings`, `format_session_results`, `_clinch_strip`, etc.). Every one takes `ctx: RenderContext` as its last arg |
| `src/f1_bot/formatting/emoji.py` | `pos_icon`, `flag_icon`, `session_icon`, `flag_color`, `country_code_to_flag` — mapping and flag logic |
| `src/f1_bot/formatting/timezone.py` | `combine_race_dt()` — combines race date + time into UTC datetime; used by scheduler and repository |
| `src/f1_bot/utils/rate_limiter.py` | Token bucket; constructor: `RateLimiter(per_second=..., per_period=..., period=...)` |
| `src/f1_bot/utils/sessions.py` | `find_next_sessions()` / `find_recent_completed_session()` / `normalize_session_key()` / `session_entries()` — session-level timeline logic |
| `src/f1_bot/utils/logging.py` | structlog setup; `add_taiwan_timestamp` processor; auto-detects TTY for console vs JSON output |
| `src/f1_bot/handlers/notifications.py` | `/remind` command + `notify:*` callback flow (pick session → pick timing → toggle subscription) |
| `src/f1_bot/models/notification.py` | `NotificationSubscription` model + `TIMING_PRESETS` (15/30/60/180 min) |
| `src/f1_bot/scheduler/notification_sender.py` | `schedule_next_notification()` + `send_notifications()` — background delivery via PTB JobQueue |
| `src/f1_bot/handlers/errors.py` | Custom error handler formatting for Telegram command validation / network errors |
| `tests/conftest.py` | `pg_store`, `repo` fixtures (dev PostgreSQL) |

## Known gotchas

**Pydantic field shadowing:** `models/race.py` has fields named `time` and `date`.
These shadow `from datetime import time, date`. Use `from datetime import time as dt_time`
when both are needed in the same file.

**JobQueue callback signature:** python-telegram-bot requires `async def job(context)` —
single argument only.

**Docker image:** Use `python:3.13-slim`, not `python:3.13-alpine`. Alpine's musl libc
breaks `httpx` C extensions.

**Pydantic v2 frozen models in tests:** Use `object.__setattr__(model, "field", value)` to
set fields on frozen Pydantic models during test setup (e.g., attaching a `sprint` session to a `Race`).

**startup_sync in tests:** Patch `f1_bot.main.startup_sync` with `AsyncMock` in E2E/main tests to avoid real HTTP calls.

**Never measure coverage with `pytest --cov` — it segfaults (exit 139).** Any test
that opens an asyncpg connection dies inside the Cython
`asyncpg.protocol.protocol.Protocol` constructor, killing the whole run rather
than one test. Bisected to a three-way interaction: pytest + pytest-cov's `--cov`
+ **asyncpg >= 0.31.0** (`pyproject.toml` pins `~= 0.30`, which admits 0.31).
`asyncpg==0.30.0` does not crash, and neither does `coverage run -m pytest` — so
it is not coverage's tracer (`COVERAGE_CORE=sysmon` crashes too) nor
pytest-asyncio/anyio/pytest-httpx. Use the `coverage run` recipe at the top of
this file; it runs the full suite clean. Production is unaffected — the bot never
runs under pytest-cov.

**Legacy callback handlers:** `schedule.py` and `results.py` register legacy callback patterns (e.g., `nsess:`, `qual:`) that respond with "please use /next" — these handle stale inline keyboards from before the refactoring.

**PTB InlineKeyboardMarkup stores tuples:** `kb.inline_keyboard` returns tuples-of-tuples, not lists. Assert with `((),)` not `[[]]`.

**Lazy imports in jobs.py:** `match_openf1_session` and `find_race_session` are imported inside function bodies. Patch at `f1_bot.utils.sessions.match_openf1_session`, not `f1_bot.scheduler.jobs.match_openf1_session`.

**Driver ID Mapping:** OpenF1 driver profiles use a composite ID `openf1_<driver_number>_<last_name>`. These are mapped to Jolpica's driver objects when querying results using `Repository.get_drivers_by_id_map()`.

**Telegram proxy & timeout settings:** The bot supports `TELEGRAM_PROXY`, `TELEGRAM_CONNECT_TIMEOUT`, and `TELEGRAM_READ_TIMEOUT` configured directly from the Pydantic Settings class. PTB creates **two separate httpx clients** — `.request()` for API calls and `.get_updates_request()` for long-polling. Both must be configured with the same proxy/timeout; missing `get_updates_request` silently breaks polling. The proxy is also passed to `JolpicaClient` and `OpenF1Client` via `BaseAPIClient(proxy=...)`.

**PTB_TIMEDELTA environment variable:** The bot runs with `PTB_TIMEDELTA=1` to opt-in to python-telegram-bot's new timedelta-based error handling API, which silences PTBDeprecationWarning warnings. Set before any PTB import — done at the top of `main.py`.

**Shared state via `app.bot_data`:** All shared dependencies (settings, store, repo, jolpica, openf1, notification_limiter) live in `app.bot_data`, not in globals. Every handler and job accesses them through `context.bot_data`.

**JSONB storage pattern:** Most PostgresStore tables store their full model as `data_json JSONB` alongside a few extracted columns (for primary keys and common filters). This avoids schema migrations when models change.

**`BadRequest` silent swallow:** Throughout handlers, `except BadRequest: pass` is common — it handles the case where `edit_message_text` is called with unchanged text (Telegram raises `BadRequest` in that case). Do not remove these.

**Results "All" mode truncation:** When showing all sessions for a round, text can exceed Telegram's 4096-char limit. A 3-stage fallback applies: (1) all sessions full, (2) competitive sessions only, (3) top 10 with truncation note.

**Notification 20-reminder cap:** Users are limited to 20 active reminders. Checked in the handler before saving.

**Schedule audit log:** `save_schedule` in PostgresStore compares old vs. new data and logs changes to `schedule_audit_log`, enabling tracking of F1 schedule changes.

**Laps In-Memory Caching:** `Repository.get_lap_timings()` returns and caches `list[LapTime]` objects (LRU, max 30 entries). This cache prevents CPU-heavy validation overhead on pagination clicks. Ensure new sync saves (e.g. `save_lap_timings()`) invalidate the cache for that round.

**PostgreSQL Transactions:** Write operations use explicit `conn.transaction()` context managers via asyncpg. The store uses a connection pool (`asyncpg.create_pool`).

**Callback Parsing Guards:** Always wrap callback integer parameters conversion (`int(parts[N])`) in a `try-except (ValueError, IndexError)` block to prevent crashing on spoofed/malformed queries, displaying "Invalid selection" if caught.

**Markdown Escaping:** Codebase uses `ParseMode.MARKDOWN` (legacy) exclusively. The `_esc()` helper only escapes 4 chars (`_ * \` [`). Never use `MARKDOWN_V2` without a dedicated escaper.

**Notification reschedule triggers:** `schedule_next_notification(jq, repo)` only runs at: (1) bot startup, (2) after `send_notifications` completes, (3) after a user toggles a reminder. Direct DB inserts are invisible until one of these triggers fires.

**Notification DELETE strategy:** `mark_notifications_sent()` DELETEs rows instead of setting `notified=TRUE`. This prevents row accumulation and avoids unique constraint conflicts on re-subscription. `save_notification()` uses `ON CONFLICT DO UPDATE SET notified=FALSE, fire_at=EXCLUDED.fire_at` to handle re-subscriptions cleanly.

**`/standings` remaining-events alignment (two-clocks fix):** `/standings` must derive remaining races/sprints from the **standings snapshot's own `round_after`** (via `repo.get_standings_round(season, table)`), NOT from live `now()` (`get_schedule_bounds()["upcoming_rounds"]`). Points are an hourly snapshot; `upcoming_rounds` flips the moment a race start-time passes — mixing the two lets a near-clinch leader flash a false 🔒 CLINCHED mid-weekend. Each view uses its **own** table's `round_after` (WDC→`standings_drivers`, WCC→`standings_constructors`) because a partial sync can leave the two tables at different rounds. `remaining_events()` **enumerates** `round > N` over `get_schedule()` — never `total - N` (would mis-count on schedule gaps). Wire this in **both** `standings_handler` and `standings_callback`.

**No user-facing literals in feature code:** every string goes through
`t(key, ctx.lang, **kwargs)`. Three guard tests enforce this and will fail CI
(all in `tests/test_i18n/`): Guard A scans `handlers/` + `formatting/` (excluding
`i18n/catalog/`) for CJK codepoints; Guard B AST-scans the same trees for
`reply_text`/`edit_message_text`/`answer` called with a bare string literal;
Guard C (`test_markdown_escape_guard.py`) AST-scans `formatting/` for external
free text interpolated into a `t()` template without `_esc()`.
Never compose a translated template with an untranslated English fragment — pass
everything as named kwargs, and make the fragment itself a catalog key.

**Guard C — why `formatting/` only, and why AST:** over half the catalog templates
carry Telegram Markdown markers, so an API string containing `_`/`*`/`` ` ``/`[`
interpolated into one either mis-renders or makes Telegram reject the message —
which handlers swallow via `except BadRequest: pass`, so the user sees nothing
happen. `handlers/` is deliberately **out of scope**: its free-text
interpolations feed inline-button labels and `answer(show_alert=True)` popups,
neither of which Telegram parses as Markdown, so escaping there would surface
literal backslashes. The guard follows escaping done at the assignment
(`title = _esc(race.name)` → `t(..., title=title)` passes) and treats `_esc`,
`t` and the `*_label` catalog helpers as safe. Add a kwarg name to
`FREE_TEXT_KWARGS` when a new template interpolates external text.

**Guard blind spot — helpers with `lang: str = DEFAULT_LANG`:** the guards only
catch *literals*. A call site that simply **omits** the `lang` argument to a
defaulted helper (e.g. `round_picker_text(rnd, races)`) renders catalog English
with no literal to find, so both guards pass while zh-Hant users see English.
After adding a `lang`/`ctx` parameter to a shared helper, grep its call sites —
don't rely on the guards to prove the migration is complete.

**`t(key, lang, /, **kwargs)` — the `/` is load-bearing, never delete it:** it makes
`key`/`lang` **positional-only** so a catalog template is free to use `{key}` or
`{lang}` as a placeholder name. Without it, `t("settings.lang_saved", code, lang=...)`
binds `lang` both positionally and by keyword → `TypeError`, which silently killed
language switching (the remaining `{lang}` sites: `settings.lang_picker` via
`/settings` → `set:lang`, and `lang_saved`). Same class as the Pydantic
field-shadowing gotcha above. `test_set_lang_renders_lang_picker` and
`test_callback_set_persists_and_confirms_in_new_language` in
`tests/test_handlers/test_language.py` are the regression guard — they fail
loudly if the `/` is removed.

**`t()` failure modes are asymmetric by design:** an *unknown key* raises
`KeyError` (a programmer typo — loud), while a *known key missing one language*
falls back to the `en` template (a user must never see a raw key). The
`check_catalog_complete()` test is the merge gate; startup is deliberately **not**
gated, so a translation gap blocks merge without taking down a running bot.

**Single-column preference upserts:** `set_user_timezone` / `set_user_language`
each write only their own column via one `ON CONFLICT DO UPDATE`. Never
reintroduce a whole-object `upsert_user_preference` — it clobbers the other
column with its default, and the read-modify-write "fix" reintroduces the same
bug as a TOCTOU race across two `await`s. Either command creates the row; the
other column takes its schema `DEFAULT`. `created_at` is written on the INSERT
branch only.

**`strftime` is never used for weekday/month names:** those come from the
`datetime.*` catalog keys. `strftime` names depend on the process-global C
locale — not thread-safe under async and impossible to vary per user.
`format_dt(dt, tz_name, lang)` formats only the numeric parts with `strftime`.

**CJK monospace padding:** code-block tables pad labels with `_pad_display()`
(stdlib `unicodedata.east_asian_width`), not `{label:<10}`. Python field widths
count code points, but CJK glyphs occupy two display columns, so code-point
padding drifts the number columns on translated rows.

**Notification sender has no `Update`:** it localizes via
`await repo.get_user_language(telegram_id)`, not `resolve_context`. It passes
**lang only, no tz** — the push message renders no clock time, so a recipient-tz
lookup would be dead weight on a hot job path.

**`CommandValidationError` carries a key, not a message:** raise it as
`CommandValidationError("schedule.invalid_round", round=n)`. `error_handler`
resolves the user's language centrally and renders it; `_safe_context()` falls
back to English when there is no `Update`/user so the error handler itself can
never raise.

## Test conventions

- `pytest.mark.integration` — requires network (Jolpica or OpenF1 HTTP)
- No marker — unit test; uses dev PostgreSQL; safe to run offline
- Mocking HTTP: use `pytest-httpx` (`httpx_mock` fixture) for unit tests
- Scheduler tests: import private constants (`_LIVE_WINDOW_MARGIN`, `_RESULTS_WINDOW`) directly for boundary assertions
- Relative-date fixtures: For testing time-windowed sync functions where `now` is computed internally, use `date.today() - timedelta(days=N)` instead of patching

## APIs

| API | Base URL | Auth | Limits |
|---|---|---|---|
| Jolpica-F1 | `https://api.jolpi.ca/ergast/f1` | None | 500 req/hr |
| OpenF1 | `https://api.openf1.org/v1` | None | 3 req/s, 30 req/min |

OpenF1 `gmt_offset` field is the source of truth for local track time.
Jolpica race winner points may exceed 25 (fastest lap bonus = +1).
Lap timing data (with sector times) comes from OpenF1, not Jolpica.
