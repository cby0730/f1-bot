# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the project

```bash
uv run -m f1_bot                          # start the bot (requires .env)
uv run pytest -m "not integration"        # unit tests only (~400 tests)
uv run pytest -m integration -v           # integration tests (real HTTP, ~22 tests)
uv run pytest tests/test_smoke.py -v      # full-stack smoke test
uv run pytest tests/test_handlers/test_race_data.py -v  # single test file
uv run ruff check src/ tests/             # lint
uv run ruff format src/ tests/            # auto-format
```

## Architecture

**SQL-only handlers:** background scheduler (JobQueue) fetches from Jolpica + OpenF1 → stores in PostgreSQL. Telegram handlers read exclusively from PostgreSQL via `Repository`. No API calls from handlers.

```
Startup / Scheduler → JolpicaClient + OpenF1Client → PostgreSQL
                                                          ↓
              Telegram users → handlers → Repository → PostgreSQL (read-only)
```

- **Startup sync:** `startup_sync()` runs in `_post_init` before the bot accepts commands. Fetches schedule, standings, results, pit stops, laps, session data. Also runs a historical driver ID backfill migration.
- **Unified hourly sync:** A single `hourly_sync` job replaces the old 6 staggered jobs. All sync work runs sequentially in one cycle (`_POLL_INTERVAL` = 1 hour in `scheduler/manager.py`).
- **Two-state UX:** `/next` and `/results` use a unified two-state interaction: State A (overview with session filter buttons + round navigation) → State B (filtered with round navigation + Back).

## Commands (13 total)

| Command | Handler file |
|---|---|
| `/start`, `/help` | `handlers/start.py` |
| `/next` | `handlers/schedule.py` — unified entry for next session |
| `/schedule`, `/countdown` | `handlers/schedule.py` |
| `/results` | `handlers/results.py` — unified entry for all results |
| `/pitstops`, `/laps` | `handlers/race_data.py` |
| `/standings` | `handlers/standings.py` |
| `/driver`, `/circuit` | `handlers/extras.py` |
| `/timezone` | `handlers/timezone.py` |
| `/remind` | `handlers/notifications.py` — view/manage session reminders |

## Callback data formats

| Pattern | Meaning |
|---|---|
| `next:filtered:{filter}:{round}` | `/next` State B — filter ∈ {fp1, fp2, fp3, qualifying, sprint_qualifying, sprint, race} |
| `next:back:_:{round}` | `/next` return to State A |
| `res:filtered:{session_key}:{round}` | `/results` State B — session_key ∈ {race, qualifying, sprint, fp1, fp2, fp3, sprint_qualifying} |
| `res:back:_:{round}` | `/results` return to State A |
| `pit:{round}` | Pit stops round navigation |
| `lap:{round}:s` / `lap:{round}:l:{lap_num}` / `lap:{round}:dp` / `lap:{round}:d:{driver_id}:{page}` | Laps navigation (summary / per-lap / driver picker / per-driver) |
| `notify:pick:{round}` | Notification session picker |
| `notify:sess:{session_key}:{round}` | Notification timing presets |
| `notify:set:{minutes}:{session_key}:{round}` | Toggle subscription on/off |
| `notify:list:{round}` | List user's reminders for a round |
| `notify:del:{id}:{round}` | Delete a single reminder |
| `notify:back` | Return to reminder overview |
| `notify:clearall:{action}` | Clear all reminders (confirm/yes/cancel) |
| `drv:detail:{driver_id}` / `drv:list` | Driver profile navigation |
| `circ:detail:{circuit_id}` / `circ:list` | Circuit info navigation |
| `tz:region:{region}` / `tz:set:{timezone}` | Timezone picker navigation |
| `standings:wdc` / `standings:wcc` | Standings WDC/WCC toggle |

## Key files

| File | Role |
|---|---|
| `src/f1_bot/main.py` | Application builder; `_post_init` sets up clients, repo, runs `startup_sync`, registers commands |
| `src/f1_bot/config.py` | Pydantic Settings; env vars: `TELEGRAM_BOT_TOKEN`, `F1BOT_DATABASE_URL`, `F1BOT_*` |
| `src/f1_bot/storage/postgres_store.py` | Persistent store (asyncpg); init with `await store.init()` |
| `src/f1_bot/storage/repository.py` | Unified read layer over PostgreSQL; `get_schedule_bounds()` is the source of truth for completed/upcoming rounds |
| `src/f1_bot/scheduler/jobs.py` | `startup_sync()` + `hourly_sync()` + individual `sync_*` callbacks; each takes `(jolpica, repo)` or `(openf1, repo)` |
| `src/f1_bot/scheduler/manager.py` | Registers single `hourly_sync` job via `run_repeating`; owns `_POLL_INTERVAL` |
| `src/f1_bot/handlers/pagination.py` | Shared keyboard builders: `next_overview_keyboard`, `next_filtered_keyboard`, `results_overview_keyboard`, `results_filtered_keyboard`, `round_keyboard`, `schedule_keyboard` |
| `src/f1_bot/formatting/messages.py` | All message formatters (`format_schedule`, `format_driver_standings`, `format_constructor_standings`, `format_session_results`, etc.) |
| `src/f1_bot/formatting/emoji.py` | `pos_icon`, `flag_icon`, `session_icon`, `flag_color`, `country_code_to_flag` — mapping and flag logic |
| `src/f1_bot/formatting/timezone.py` | `combine_race_dt()` — combines race date + time into UTC datetime; used by scheduler and repository |
| `src/f1_bot/utils/rate_limiter.py` | Token bucket; constructor: `RateLimiter(per_second=..., per_period=..., period=...)` |
| `src/f1_bot/utils/fuzzy_match.py` | `match_driver()` / `match_circuit()` using difflib; scores all fields, takes max |
| `src/f1_bot/utils/sessions.py` | `find_next_sessions()` / `find_recent_completed_session()` / `normalize_session_key()` / `session_entries()` — session-level timeline logic |
| `src/f1_bot/utils/logging.py` | structlog setup; `add_taiwan_timestamp` processor; auto-detects TTY for console vs JSON output |
| `src/f1_bot/handlers/notifications.py` | `/remind` command + `notify:*` callback flow (pick session → pick timing → toggle subscription) |
| `src/f1_bot/models/notification.py` | `NotificationSubscription` model + `TIMING_PRESETS` (15/30/60/180 min) |
| `src/f1_bot/scheduler/notification_sender.py` | `schedule_next_notification()` + `send_notifications()` — background delivery via PTB JobQueue |
| `src/f1_bot/handlers/errors.py` | Custom error handler formatting for Telegram command validation / network errors |
| `src/f1_bot/models/live.py` | OpenF1 live data models (`LivePosition`, `LiveInterval`, `RaceControlMessage`, `WeatherData`) — infrastructure for future live features, currently unused by handlers |
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

**Dockerfile stale env var:** The Dockerfile still sets `F1BOT_SQLITE_PATH=/data/f1bot.db` and mounts a `/data` volume — leftovers from the SQLite era. These are unused now (PostgreSQL is the store) but haven't been cleaned up yet.

## Test conventions

- `asyncio_mode = "auto"` — all async tests run without explicit `@pytest.mark.asyncio`
- `pytest.mark.integration` — requires network (Jolpica or OpenF1 HTTP)
- No marker — unit test; uses dev PostgreSQL; safe to run offline
- Fixtures: `pg_store` and `repo` in `tests/conftest.py` connect to dev PostgreSQL (`docker-compose.dev.yml`)
- Mocking HTTP: use `pytest-httpx` (`httpx_mock` fixture) for unit tests
- Scheduler tests: import private constants (`_LIVE_WINDOW_MARGIN`, `_RESULTS_WINDOW`) directly for boundary assertions
- Relative-date fixtures: For testing time-windowed sync functions where `now` is computed internally, use `date.today() - timedelta(days=N)` instead of patching
- Pre-commit hooks: ruff lint+format, gitleaks (secrets), hadolint (Dockerfile), pip-audit (SCA), trailing-whitespace/end-of-file-fixer

## APIs

| API | Base URL | Auth | Limits |
|---|---|---|---|
| Jolpica-F1 | `https://api.jolpi.ca/ergast/f1` | None | 500 req/hr |
| OpenF1 | `https://api.openf1.org/v1` | None | 3 req/s, 30 req/min |

OpenF1 `gmt_offset` field is the source of truth for local track time.
Jolpica race winner points may exceed 25 (fastest lap bonus = +1).
Lap timing data (with sector times) comes from OpenF1, not Jolpica.
