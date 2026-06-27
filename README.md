# F1 Bot

A Telegram bot for Formula 1 information — race schedules, standings, results, pit stops, and lap timing data.

## Features

| Command | Description |
|---|---|
| `/next` | Next race weekend overview; tap session buttons (Practice / Qualifying / Sprint / Race) for details |
| `/schedule` | Full season calendar |
| `/countdown` | Time until next race |
| `/standings` | WDC and WCC standings |
| `/results` | Race results overview; tap session buttons to view Qualifying / Sprint / Race / FP results |
| `/pitstops` | Pit stop data with ◀ ▶ round navigation |
| `/laps` | Fastest laps — round navigation + By-Lap / By-Driver view toggle |
| `/driver <name>` | Driver profile and standings (fuzzy name matching) |
| `/circuit <name>` | Circuit info (fuzzy name matching) |
| `/timezone` | Set your timezone for local race times |
| `/remind` | View and manage your session reminders |
| `/start`, `/help` | Welcome message and command list |

### Two-state interaction pattern

`/next` and `/results` use a unified two-state UX:

- **State A (overview):** Shows a summary for the current round with session filter buttons (e.g., Practice / Qualifying / Sprint / Race) and `◀ ▶` round navigation.
- **State B (filtered):** Tap a session button to drill into that session type. Shows `◀ ▶` round navigation and a Back button to return to the overview.

## Architecture

Cache-first: a full data sync runs on startup, then background jobs poll on a 1-hour cycle. Telegram handlers are **SQL-only** — they never call external APIs directly.

```
Startup / Scheduler → Jolpica + OpenF1 APIs → PostgreSQL
                                                   ↓
                       Telegram users → handlers → Repository → PostgreSQL (read)
```

### Key design decisions

- **SQL-only handlers:** All handler reads go through `Repository` → PostgreSQL. No API calls from handlers.
- **Startup sync:** `startup_sync()` in `_post_init` fetches schedule, standings, results, pit stops, laps, and session data before the bot starts accepting commands.
- **Unified polling:** All scheduler jobs share a 1-hour interval (`_POLL_INTERVAL` in `scheduler/manager.py`).
- **OpenF1 for laps:** Lap timing data (including sector times) comes from OpenF1, not Jolpica.
- **PostgreSQL storage:** All data is stored in PostgreSQL via asyncpg. Write operations use explicit transactions for atomicity.
- **Notification system:** Users subscribe to session reminders via inline keyboard flow. A background `notification_sender` schedules PTB `run_once` jobs based on the earliest pending `fire_at` in the database, auto-rescheduling after each delivery.
- **Laps in-memory cache:** Validated `LapTime` objects are cached inside `Repository` on retrieval, preventing costly database reads and repetitive CPU-heavy Pydantic validation on pagination clicks. Saving new laps invalidates this cache.
- **Input and formatting guards:** Callback query parameter parsing is guarded against parsing errors (`ValueError`), and markdown-sensitive fields are escaped to prevent Telegram Markdown parse failures.
- **Fuzzy matching:** `/driver` and `/circuit` commands use difflib-based fuzzy matching across all name fields.
- **Driver mapping & cache enrichment:** OpenF1 driver profiles are cached and enriched with country flags mapped from ISO 3-letter codes. OpenF1 session results are mapped to Jolpica's driver entities using their permanent numbers via `Repository.get_drivers_by_id_map()`.

### Project structure

```
src/f1_bot/
├── api/            # HTTP clients (Jolpica, OpenF1) with rate limiting
├── formatting/     # Message formatting, emoji helpers, timezone display
├── handlers/       # Telegram command & callback handlers (read-only from SQLite)
├── models/         # Pydantic v2 models (frozen)
├── scheduler/      # Background sync jobs and job manager
├── storage/        # PostgreSQL store + Repository read layer
└── utils/          # Rate limiter, fuzzy match, session helpers, logging
```

## Running with Docker (recommended)

**Prerequisites:** Docker and Docker Compose installed.

```bash
# 1. Clone the repo
git clone https://github.com/your-username/f1-bot.git
cd f1-bot

# 2. Create your .env from the example
cp .env.example .env
# Edit .env: set TELEGRAM_BOT_TOKEN and POSTGRES_PASSWORD

# 3. Start (bot + PostgreSQL)
docker compose up -d

# 4. Check logs
docker compose logs -f bot
```

To stop: `docker compose down`
To update: `git pull && docker compose up -d --build`

PostgreSQL data is persisted in a Docker volume (`pgdata`).

## Running locally (development)

**Prerequisites:** Python 3.13+, [uv](https://docs.astral.sh/uv/), PostgreSQL (or use dev container).

```bash
# Start dev PostgreSQL
docker compose -f docker-compose.dev.yml up -d

# Install dependencies
uv sync

# Set up environment
cp .env.example .env
# Edit .env: set TELEGRAM_BOT_TOKEN and F1BOT_DATABASE_URL

# Run
uv run -m f1_bot
```

## Running tests

```bash
# Start dev PostgreSQL (required for tests)
docker compose -f docker-compose.dev.yml up -d

# Unit tests only (~411 tests, no network required)
uv run pytest -m "not integration"

# Integration tests (real API calls, requires internet)
uv run pytest -m integration -v

# Single test file
uv run pytest tests/test_handlers/test_race_data.py -v

# Lint
uv run ruff check src/ tests/
```

## Getting a Telegram bot token

1. Open Telegram and search for [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow the prompts
3. Copy the token into your `.env` as `TELEGRAM_BOT_TOKEN`

## Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Yes | — | From @BotFather |
| `POSTGRES_PASSWORD` | Yes (Docker) | — | PostgreSQL password (used by docker-compose) |
| `F1BOT_DATABASE_URL` | No | `postgresql://...@localhost:31050/...` | PostgreSQL connection URL (auto-set in Docker) |
| `TELEGRAM_PROXY` | No | — | Proxy URL for Telegram client (e.g., `socks5://127.0.0.1:7890`) |
| `TELEGRAM_CONNECT_TIMEOUT` | No | `20.0` | Connection timeout for Telegram client in seconds |
| `TELEGRAM_READ_TIMEOUT` | No | `20.0` | Read timeout for Telegram client in seconds |
| `F1BOT_LOG_LEVEL` | No | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `F1BOT_LOG_FORMAT` | No | `auto` | `auto` (JSON if not TTY) / `console` / `json` |

## Deployment

Any Linux VPS with Docker works. Free/cheap options:
- [Oracle Cloud Free Tier](https://www.oracle.com/cloud/free/) — 1 GB RAM ARM instance, always free
- [Hetzner](https://www.hetzner.com/cloud) — €4/month CAX11 ARM

The bot uses ~100 MB RAM in steady state.

## Data sources

| API | Purpose | Auth | Rate limits |
|---|---|---|---|
| [Jolpica-F1](https://api.jolpi.ca/ergast/f1/) | Schedule, standings, results, pit stops | None | 500 req/hr |
| [OpenF1](https://openf1.org) | Session results, lap timings with sector times | None | 3 req/s, 30 req/min |

## Tech stack

- **Runtime:** Python 3.13, [python-telegram-bot](https://python-telegram-bot.org/) (PTB) 22.x with JobQueue
- **Data:** PostgreSQL via asyncpg, Pydantic v2 models
- **HTTP:** httpx with token-bucket rate limiting
- **Logging:** structlog (JSON in production, colored console in dev)
- **Build:** uv, multi-stage Docker (python:3.13-slim)
- **Testing:** pytest, pytest-asyncio, pytest-httpx
- **Linting:** ruff
