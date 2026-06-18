# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the project

```bash
uv run -m f1_bot                          # start the bot (requires .env)
uv run pytest -m "not integration"        # unit tests only (~288 tests, ~16s)
uv run pytest -m integration -v           # integration tests (real HTTP)
uv run pytest tests/test_smoke.py -v      # full-stack smoke test
uv run pytest tests/test_handlers/test_race_data.py -v  # single test file
uv run ruff check src/ tests/             # lint
```

## Architecture

**SQL-only handlers:** background scheduler (JobQueue) fetches from Jolpica + OpenF1 → stores in SQLite. Telegram handlers read exclusively from SQLite via `Repository`. No API calls from handlers.

```
Startup / Scheduler → JolpicaClient + OpenF1Client → SQLite
                                                        ↓
              Telegram users → handlers → Repository → SQLite (read-only)
```

- **Startup sync:** `startup_sync()` runs in `_post_init` before the bot accepts commands. Fetches schedule, standings, results, pit stops, laps, session data.
- **Polling cycle:** All scheduler jobs share `_POLL_INTERVAL` (1 hour) in `scheduler/manager.py`.
- **Two-state UX:** `/next` and `/results` use a unified two-state interaction: State A (overview with session filter buttons) → State B (filtered with round navigation + Back).

## Commands (12 total)

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

## Callback data formats

| Pattern | Meaning |
|---|---|
| `next:filtered:{filter}:{round}` | `/next` State B — filter ∈ {practice, qualifying, sprint, race} |
| `next:back:_:{round}` | `/next` return to State A |
| `res:filtered:{session_key}:{round}` | `/results` State B — session_key ∈ {race, qualifying, sprint, fp1, fp2, fp3, sq, spr} |
| `res:back:_:{round}` | `/results` return to State A |
| `pit:{round}` | Pit stops round navigation |
| `lap:{round}:{view}` | Laps round/view navigation |

## Key files

| File | Role |
|---|---|
| `src/f1_bot/main.py` | Application builder; `_post_init` sets up clients, repo, runs `startup_sync`, registers commands |
| `src/f1_bot/config.py` | Pydantic Settings; env vars: `TELEGRAM_BOT_TOKEN`, `F1BOT_*` |
| `src/f1_bot/storage/sqlite_store.py` | Persistent store; init with `await store.init()` (not `initialize()`) |
| `src/f1_bot/storage/repository.py` | Unified read layer over SQLite; `get_schedule_bounds()` is the source of truth for completed/upcoming rounds |
| `src/f1_bot/scheduler/jobs.py` | `startup_sync()` + individual `sync_*` callbacks; each takes `(jolpica, repo)` or `(openf1, repo)` |
| `src/f1_bot/scheduler/manager.py` | Registers all jobs via `run_repeating`; owns `_POLL_INTERVAL` |
| `src/f1_bot/handlers/pagination.py` | Shared keyboard builders: `next_overview_keyboard`, `next_filtered_keyboard`, `results_overview_keyboard`, `results_filtered_keyboard`, `round_keyboard`, `schedule_keyboard` |
| `src/f1_bot/formatting/messages.py` | All message formatters (`format_schedule`, `format_standings`, `format_session_results`, etc.) |
| `src/f1_bot/formatting/emoji.py` | `pos_icon`, `flag_icon`, `session_icon`, `flag_color` — pure mapping functions |
| `src/f1_bot/utils/rate_limiter.py` | Token bucket; constructor: `RateLimiter(per_second=..., per_period=..., period=...)` |
| `src/f1_bot/utils/fuzzy_match.py` | `match_driver()` / `match_circuit()` using difflib; scores all fields, takes max |
| `src/f1_bot/utils/sessions.py` | `find_next_sessions()` / `find_recent_completed_session()` / `normalize_session_key()` — session-level timeline logic |
| `tests/conftest.py` | `sqlite_store`, `repo` fixtures (tmp SQLite) |

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

## Test conventions

- `asyncio_mode = "auto"` — all async tests run without explicit `@pytest.mark.asyncio`
- `pytest.mark.integration` — requires network (Jolpica or OpenF1 HTTP)
- No marker — unit test; uses in-memory SQLite; safe to run offline
- Fixtures: `sqlite_store` and `repo` in `tests/conftest.py` provide tmp SQLite
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
