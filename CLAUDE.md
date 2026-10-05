# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the project

```bash
uv run -m f1_bot                          # start the bot (requires .env)
uv run pytest -m "not integration"        # unit tests (575; needs only a Docker daemon)
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

## Directory-scoped guidance

Two files load automatically when working under their directory, and hold the
detail that only matters there:

- `src/f1_bot/handlers/CLAUDE.md` — the 9-command visible menu → handler map and
  the full `callback_data` pattern table.
- `src/f1_bot/formatting/CLAUDE.md` — Guard C's scope rationale, `t()`'s
  asymmetric failure modes, the `strftime` ban, and CJK padding.

## Key files

| File | Role |
|---|---|
| `src/f1_bot/main.py` | Application builder; `_post_init` sets up clients, repo, runs `startup_sync`, registers commands |
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
| `src/f1_bot/utils/sessions.py` | `find_next_sessions()` / `find_recent_completed_session()` / `normalize_session_key()` / `session_entries()` — session-level timeline logic |
| `src/f1_bot/handlers/notifications.py` | `/remind` command + `notify:*` callback flow (pick session → pick timing → toggle subscription) |
| `src/f1_bot/scheduler/notification_sender.py` | `schedule_next_notification()` + `send_notifications()` — background delivery via PTB JobQueue |
| `tests/conftest.py` | `pg_url` (session-scoped Testcontainers PostgreSQL), `pg_store`, `repo` fixtures |
| `video/` | Remotion launch film (Node). README hero `docs/demo.gif` is the 30 fps GIF export |

## Known gotchas

**Pydantic field shadowing:** `models/race.py` has fields named `time` and `date`.
These shadow `from datetime import time, date`. Use `from datetime import time as dt_time`
when both are needed in the same file.

**JobQueue callback signature:** python-telegram-bot requires `async def job(context)` —
single argument only.

**Docker image:** Use `python:3.13-slim`, not `python:3.13-alpine`. Alpine's musl libc
breaks `httpx` C extensions. The image copies `src/` only — do not add `video/` or
`docs/demo.gif` to the Dockerfile.

**README hero gif:** rebuild `docs/demo.gif` from `video/out/full.mp4` with the ffmpeg
recipe in `video/README.md`. Do not recapture Telegram Web for the README.

**Pydantic v2 frozen models in tests:** Use `object.__setattr__(model, "field", value)` to
set fields on frozen Pydantic models during test setup (e.g., attaching a `sprint` session to a `Race`).

**startup_sync in tests:** Patch `f1_bot.main.startup_sync` with `AsyncMock` in E2E/main tests to avoid real HTTP calls.

**`src/` uses no `random`, so pytest-randomly's reseeding is inert — for now.**
The plugin calls `random.seed()` before every test; `grep -rn "random" src/f1_bot/`
is currently empty, so that has no effect on production code paths. Introduce
randomness in `src/` and tests may start behaving differently per seed. Its
shuffling does not cost an extra container either: `_reorganize_items` shuffles
*within* each module and then orders the modules, so the session-scoped `pg_url`
container is still built once (verified by polling `docker ps` during a run).
When a shuffled run fails, rerun with the printed `--randomly-seed=N` to
reproduce and fix the test — do not paper over it with `-p no:randomly`. That
flag belongs only in the coverage recipe above, where it is now load-bearing
rather than the no-op it was before the plugin was actually installed.

**A Postgres major bump is never just the tag — `PGDATA` moved in 18.** The
official image changed it from `/var/lib/postgresql/data` to
`/var/lib/postgresql/<major>/docker`, so the mount goes one level up at
`/var/lib/postgresql`. Keep the old mount and the container starts and
immediately exits: `There appears to be PostgreSQL data in
/var/lib/postgresql/data (unused mount/volume)`. **Tag and mount are one change;
neither is valid alone.** Both compose files are on `18-alpine` with the new
layout. Confirm the path for any image with
`docker run --rm postgres:<tag> env | grep PGDATA`.

Production was upgraded by dump/restore on 2026-09-22 (not pgautoupgrade, not
`pg_upgrade --link`). The pre-upgrade volume `f1-bot_pgdata` is still PG 16 and
is retained as the rollback — compose no longer references it, so
`docker volume prune` offers to remove it. **It is not an orphan to clean up.**

**A deploy goes green on an empty database.** `deploy.yml`'s health check reads
`postgres=healthy` (from `pg_isready`, which verifies neither data nor password
auth) and `bot=running` (the bot service declares no healthcheck, so this only
means the process has not exited). Total data loss therefore reports
`deploy healthy`. The consequence is a hard ordering rule: **upgrade and verify
the VM first, and only then let a compose change reach the repo** — the reverse
order hides a silent wipe behind a green check.

The real post-deploy gate is the startup log (see `notification_scheduled` below).

**`docker-compose.dev.yml` is only for actually running the bot locally.** No test
needs it (see Test conventions). Starting `mango_pg` before a test run does
nothing — and pointing tests at it would be actively wrong, since the fixtures
TRUNCATE every public table. `tests/test_db_isolation.py` enforces this by
asserting on the URL `pg_url` actually hands out, not a module constant, closing
the bypass `tests/test_e2e.py` used to have with its own hardcoded URL. Tear it
down with `down -v` when finished; a leftover volume is residue, not a cache.

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

**Dead callbacks are intentionally unregistered:** stale buttons from deleted flows (`title:*`, `nsess:*`, `nprac:*`, `nqual:*`, `nspr:*`, `qual:*`, `spr:*`, `sr:*`) have **no** handler and get no "outdated" toast — do not add a catch-all. `lang:picker` and `cmp:list` are answered with a bare `query.answer()` (no alert, no edit) only because a live prefix pattern (`^lang:` / `^cmp:`) still catches them. `tests/test_handlers/test_command_surface.py` pins the registered pattern set; `test_dead_callbacks_are_silent` in `tests/test_e2e.py` asserts no send/edit/alert.

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

**Schedule audit log is not wired up:** the `schedule_audit_log` table and `log_schedule_change()` (store + repository) exist, but nothing calls them — `save_schedule` does not compare old vs. new data, and no commit ever added a caller. Expect the table to be empty. Wiring the comparison into `save_schedule` is an unbuilt feature, not a regression; do not drop the table without a decision (it is production schema).

**Laps In-Memory Caching:** `Repository.get_lap_timings()` returns and caches `list[LapTime]` objects (LRU, max 30 entries). This cache prevents CPU-heavy validation overhead on pagination clicks. Ensure new sync saves (e.g. `save_lap_timings()`) invalidate the cache for that round.

**PostgreSQL Transactions:** Write operations use explicit `conn.transaction()` context managers via asyncpg. The store uses a connection pool (`asyncpg.create_pool`).

**Callback Parsing Guards:** Always wrap callback integer parameters conversion (`int(parts[N])`) in a `try-except (ValueError, IndexError)` block to prevent crashing on spoofed/malformed queries, displaying "Invalid selection" if caught.

**Markdown Escaping:** Codebase uses `ParseMode.MARKDOWN` (legacy) exclusively. The `_esc()` helper only escapes 4 chars (`_ * \` [`). Never use `MARKDOWN_V2` without a dedicated escaper.

**Notification reschedule triggers:** `schedule_next_notification(jq, repo)` only runs at: (1) bot startup, (2) after `send_notifications` completes, (3) after a user toggles a reminder. Direct DB inserts are invisible until one of these triggers fires.

**`notification_scheduled` is absent, not failed, when the DB is empty — and it
is the only proof production data survived a deploy.**
`schedule_next_notification()` wraps its work in `if next_fire:` with **no else**,
so `get_next_fire_at()` returning `None` logs nothing: no error, no warning.
Every other startup event has a failure twin (`startup_sync_complete` ↔
`startup_sync_incomplete_due_to_failures`, `bot_commands_registered` ↔
`failed_to_set_bot_commands`); this one does not, so **absence is the signal**.
On an empty local DB that same absence is correct behaviour — the two are
indistinguishable, so always judge it against the environment.

The startup sequence, in `_post_init` order:
`startup` → `startup_sync_begin` → `startup_sync_complete` →
`notification_scheduled` → `bot_commands_registered`. Note the last two: the
scheduler runs *before* command registration. `Application started` is PTB's own
message, not a structlog event — do not gate on it.

To verify a log line actually came from this run rather than a stale tail,
cross-check its arithmetic: `fire_at` minus `delay_s` must equal the line's own
timestamp. The three values come from the DB, a live computation, and structlog
independently, so agreement cannot be faked by copying counts. An 8-hour (28800s)
discrepancy would mean a `timestamptz` timezone misread.

**`startup_sync` costs ~2.5 minutes on every start, not just the first.** The
`sync_*` callbacks re-fetch and upsert rather than working incrementally, so a
populated database is no faster. `_post_init` blocks until it finishes, so the
bot ignores Telegram updates for that whole window, and `api_rate_limited`
warnings during it are normal (Jolpica allows 500 req/hr). **Wait a full three
minutes before reading a deploy's logs** — checking earlier looks exactly like
`startup_sync_complete` never arriving.

**Notification DELETE strategy:** `mark_notifications_sent()` DELETEs rows instead of setting `notified=TRUE`. This prevents row accumulation and avoids unique constraint conflicts on re-subscription. `save_notification()` uses `ON CONFLICT DO UPDATE SET notified=FALSE, fire_at=EXCLUDED.fire_at` to handle re-subscriptions cleanly.

**`/standings` remaining-events alignment (two-clocks fix):** `/standings` must derive remaining races/sprints from the **standings snapshot's own `round_after`** (via `repo.get_standings_round(season, table)`), NOT from live `now()` (`get_schedule_bounds()["upcoming_rounds"]`). Points are an hourly snapshot; `upcoming_rounds` flips the moment a race start-time passes — mixing the two lets a near-clinch leader flash a false 🔒 CLINCHED mid-weekend. Each view uses its **own** table's `round_after` (WDC→`standings_drivers`, WCC→`standings_constructors`) because a partial sync can leave the two tables at different rounds. `remaining_events()` **enumerates** `round > N` over `get_schedule()` — never `total - N` (would mis-count on schedule gaps). Wire this in **both** `standings_handler` and `standings_callback`. The write side obeys the same rule: `sync_standings` tags each table with the `round` Jolpica returns alongside the points (`get_*_standings()` → `(round, list)`), never `get_schedule_bounds()` — Jolpica lags a race start by hours, so a live-clock tag would mislabel stale points as the newer round.

**No user-facing literals in feature code:** every string goes through
`t(key, ctx.lang, **kwargs)`. Three guard tests enforce this and will fail CI
(all in `tests/test_i18n/`): Guard A scans `handlers/` + `formatting/` (excluding
`i18n/catalog/`) for CJK codepoints; Guard B AST-scans the same trees for
`reply_text`/`edit_message_text`/`answer` called with a bare string literal;
Guard C (`test_markdown_escape_guard.py`) AST-scans `formatting/` for external
free text interpolated into a `t()` template without `_esc()`.
Never compose a translated template with an untranslated English fragment — pass
everything as named kwargs, and make the fragment itself a catalog key.

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

**Single-column preference upserts:** `set_user_timezone` / `set_user_language`
each write only their own column via one `ON CONFLICT DO UPDATE`. Never
reintroduce a whole-object `upsert_user_preference` — it clobbers the other
column with its default, and the read-modify-write "fix" reintroduces the same
bug as a TOCTOU race across two `await`s. Either command creates the row; the
other column takes its schema `DEFAULT`. `created_at` is written on the INSERT
branch only.

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

- **Tests bring their own database.** The session-scoped `pg_url` fixture starts
  a throwaway `postgres:18-alpine` via Testcontainers on a random port, so a
  Docker daemon is the only host requirement — no host DB, no psql, no env var.
  It starts lazily, so DB-free suites (`tests/test_i18n/`) still finish in under
  a second. `pg_store`/`repo` stay function-scoped, giving each test a fresh
  store and a fresh `Repository._laps_cache`; only `pg_url` is shared.
  Expect **0 skipped, 0 error** — a skip or connection error is a real defect,
  never "the DB is merely absent".
- `pytest.mark.integration` means **calls a real external API**, not "needs a
  database" — both halves get one, and `test_smoke.py` needs a real DB *and*
  real HTTP. These 19 tests are deliberately out of CI so a red run always means
  *this PR* is broken rather than that a third party is having a bad day; do not
  "helpfully" add them. Run locally (see `AGENTS.md` for this host's proxy
  tunnel). If they ever belong in CI, give them a `workflow_dispatch` workflow
  that cannot block a merge.
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
