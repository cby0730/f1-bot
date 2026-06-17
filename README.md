# F1 Bot

A public Telegram bot for Formula 1 information — race schedules, standings, results, and more.

## Features

| Command | Description |
|---|---|
| `/next [N]` | Next N races + countdown + sessions in your timezone |
| `/nextsession [N]` | Next N sessions: practice, qualifying, sprint, or race |
| `/nextpractice [N]` | Next N practice sessions |
| `/nextqualifying [N]` | Next N qualifying or sprint qualifying sessions |
| `/nextsprint [N]` | Next N sprint-related sessions |
| `/schedule` | Full season calendar |
| `/countdown` | Time until next race |
| `/standings` | WDC and WCC standings |
| `/results [N or rN]` | Race results (N for last N, rN for specific round) |
| `/qualifying [N or rN]` | Qualifying results |
| `/sprint [N or rN]` | Sprint results |
| `/sessionresult [N or rN] [session]` | Timed session results |
| `/pitstops [N or rN]` | Pit stop data |
| `/laps [N or rN]` | Fastest laps |
| `/driver <name>` | Driver profile and standings |
| `/circuit <name>` | Circuit info |
| `/timezone` | Set your timezone for local race times |

## Architecture

Cache-first: background jobs fetch from [Jolpica-F1](https://api.jolpi.ca) and [OpenF1](https://openf1.org) → store in SQLite. Telegram handlers only read from the local SQLite cache.

```
Jolpica + OpenF1 APIs
        ↓  (background scheduler)
      SQLite (persistent)
        ↓  (handlers read)
Telegram users
```

Off-weekend polling is every 1–6 hours.

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

- [Jolpica-F1 API](https://api.jolpi.ca/ergast/f1/) — schedule, standings, results (free, no auth, 500 req/hr)
- [OpenF1 API](https://openf1.org) — live timing, weather, race control (free, no auth, 30 req/min)
