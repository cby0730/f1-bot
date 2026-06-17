# F1 Bot — Project Instructions

## Running the project

```bash
uv run -m f1_bot                          # start the bot (requires .env)
uv run pytest -m "not integration"        # unit tests only (~0.35s)
uv run pytest -m integration -v           # integration tests (real HTTP)
uv run pytest tests/test_smoke.py -v      # full-stack smoke test (4 tests)
uv run ruff check src/ tests/             # lint
```

## Architecture

Cache-first: background jobs (APScheduler via python-telegram-bot JobQueue) fetch
from Jolpica → store in SQLite. Telegram handlers read from the local SQLite cache;
on cache misses, they fetch on-demand from Jolpica / OpenF1 and save to SQLite.

```
Telegram users → handlers → Repository → SQLite
                   ↓                     ↑
             JolpicaClient /        Scheduler → jobs → JolpicaClient
             OpenF1Client
```

## Key files

| File | Role |
|---|---|
| `src/f1_bot/config.py` | Pydantic Settings; env vars: `TELEGRAM_BOT_TOKEN`, `F1BOT_*` |
| `src/f1_bot/storage/sqlite_store.py` | Persistent store; init with `await store.init()` (not `initialize()`) |
| `src/f1_bot/storage/repository.py` | Unified read: pure SQLite store |
| `src/f1_bot/scheduler/jobs.py` | Individual fetch functions; each takes a `context` with `bot_data["jolpica"]` and `bot_data["repo"]` |
| `src/f1_bot/utils/rate_limiter.py` | Token bucket; constructor: `RateLimiter(per_second=..., per_period=..., period=...)` |
| `src/f1_bot/utils/fuzzy_match.py` | `match_driver()` / `match_circuit()` using difflib; scores all fields, takes max |
| `tests/conftest.py` | `sqlite_store`, `repo` fixtures (tmp SQLite) |
| `tests/test_smoke.py` | Full-stack integration test; exercises actual persistence and schema logic |

## Known gotchas

**Pydantic field shadowing:** `models/race.py` has fields named `time` and `date`.
These shadow `from datetime import time, date`. Use `from datetime import time as dt_time`
when both are needed in the same file.

**JobQueue callback signature:** python-telegram-bot requires `async def job(context)` —
single argument only.

**Docker image:** Use `python:3.13-slim`, not `python:3.13-alpine`. Alpine's musl libc
breaks `httpx` C extensions.

## Test markers

- `pytest.mark.integration` — requires network (Jolpica or OpenF1 HTTP)
- No marker — unit test; uses in-memory SQLite; safe to run offline

## APIs

| API | Base URL | Auth | Limits |
|---|---|---|---|
| Jolpica-F1 | `https://api.jolpi.ca/ergast/f1` | None | 500 req/hr |
| OpenF1 | `https://api.openf1.org/v1` | None | 3 req/s, 30 req/min |

OpenF1 `gmt_offset` field is the source of truth for local track time.
Jolpica race winner points may exceed 25 (fastest lap bonus = +1).
