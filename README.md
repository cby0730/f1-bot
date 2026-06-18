# F1 Bot

A public Telegram bot for Formula 1 information — race schedules, standings, results, and more.

## Features

| Command | Description |
|---|---|
| `/next` | Next race weekend overview; tap session buttons (Practice / Qualifying / Sprint / Race) for details |
| `/schedule` | Full season calendar |
| `/countdown` | Time until next race |
| `/standings` | WDC and WCC standings |
| `/results` | Race results overview; tap session buttons to view Qualifying / Sprint / Race / FP results |
| `/pitstops` | Pit stop data — ◀ ▶ button navigation |
| `/laps` | Fastest laps — round navigation + By-Lap / By-Driver view toggle |
| `/driver <name>` | Driver profile and standings |
| `/circuit <name>` | Circuit info |
| `/timezone` | Set your timezone for local race times |

### Two-state interaction pattern

`/next` and `/results` use a unified two-state UX:

- **State A (overview):** Shows a summary for the current round with session filter buttons (e.g., Practice / Qualifying / Sprint / Race).
- **State B (filtered):** Tap a session button to drill into that session type. Shows ◀ ▶ round navigation and a Back button to return to the overview.

## Architecture

Cache-first: a full data sync runs on startup, then background jobs poll on a 1-hour cycle. Telegram handlers are **SQL-only** — they never call external APIs directly.

```
Startup / Scheduler → Jolpica + OpenF1 APIs → SQLite
                                                 ↓
                          Telegram users → handlers → Repository → SQLite (read)
```

### Key design decisions

- **SQL-only handlers:** All handler reads go through `Repository` → SQLite. No API calls from handlers.
- **Startup sync:** `startup_sync()` in `_post_init` fetches schedule, standings, results, pit stops, laps, and session data before the bot starts accepting commands.
- **Unified polling:** All scheduler jobs share a 1-hour interval (`_POLL_INTERVAL` in `scheduler/manager.py`).
- **OpenF1 for laps:** Lap timing data (including sector times) comes from OpenF1, not Jolpica.

## Running with Docker (recommended)

**Prerequisites:** Docker and Docker Compose installed.

```bash
# 1. Clone the repo
git clone https://github.com/your-username/f1-bot.git
cd f1-bot

# 2. Create your .env from the example
cp .env.example .env
# Edit .env and set TELEGRAM_BOT_TOKEN=your_token_here

# 3. Start
docker compose up -d

# 4. Check logs
docker compose logs -f bot
```

To stop: `docker compose down`
To update: `git pull && docker compose up -d --build`

## Running locally (development)

**Prerequisites:** Python 3.13+, [uv](https://docs.astral.sh/uv/) running locally.

```bash
# Install dependencies
uv sync

# Set up environment
cp .env.example .env
# Edit .env: set TELEGRAM_BOT_TOKEN

# Run
uv run -m f1_bot
```

## Running tests

```bash
# Unit tests only (no network required)
uv run pytest -v -m "not integration"

# All tests including real API calls (requires internet)
uv run pytest -v
```

## Getting a Telegram bot token

1. Open Telegram and search for [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow the prompts
3. Copy the token into your `.env` as `TELEGRAM_BOT_TOKEN`

## Deployment

Any Linux VPS with Docker works. Free options:
- [Oracle Cloud Free Tier](https://www.oracle.com/cloud/free/) — 1 GB RAM ARM instance, always free
- [Hetzner](https://www.hetzner.com/cloud) — €4/month CAX11 ARM

The bot uses ~100 MB RAM in steady state.

## Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Yes | — | From @BotFather |
| `F1BOT_SQLITE_PATH` | No | `f1bot.db` | Auto-set to `/data/f1bot.db` by docker-compose |
| `F1BOT_LOG_LEVEL` | No | `INFO` | `DEBUG` / `INFO` / `WARNING` |

## Data sources

- [Jolpica-F1 API](https://api.jolpi.ca/ergast/f1/) — schedule, standings, results, pit stops (free, no auth, 500 req/hr)
- [OpenF1 API](https://openf1.org) — session results, lap timings with sector times (free, no auth, 30 req/min)
