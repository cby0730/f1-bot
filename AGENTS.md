# AGENTS.md

Standard dev commands (run bot, tests, lint, coverage) and architecture live in
[`CLAUDE.md`](CLAUDE.md) and [`src/f1_bot/handlers/CLAUDE.md`](src/f1_bot/handlers/CLAUDE.md).
Read those first; this file only records non-obvious environment caveats.

## Cursor Cloud specific instructions

- **Python toolchain:** the project targets Python 3.13 and uses `uv`. `uv` is
  installed at `~/.local/bin` (already on PATH). `uv sync` (the startup update
  script) provisions the 3.13 interpreter and the `.venv`. Prefix commands with
  `uv run` (e.g. `uv run -m f1_bot`, `uv run pytest ...`).

- **PostgreSQL is a native cluster, not Docker.** Docker is not available in this
  environment, so `docker-compose.dev.yml` cannot be used. Instead a system
  PostgreSQL 16 cluster serves the dev DB on **port 31055** with role/db
  `mango`/`mango` — this matches the default `F1BOT_DATABASE_URL`
  (`postgresql://mango:mango@localhost:31055/mango`), so no DB env var is needed.
  If the cluster is down after a restart, start it with
  `sudo pg_ctlcluster 16 main start` (check with `pg_lsclusters`). The bot schema
  is auto-created on startup; no migration step.

- **Running the bot needs `TELEGRAM_BOT_TOKEN`** (bare env var, no `F1BOT_` prefix;
  get one from @BotFather). It is intentionally not stored in the repo — export it
  in the shell before `uv run -m f1_bot`.

- **Startup blocks on a full-season sync before polling.** `_post_init` runs
  `startup_sync()` which fetches the whole season from Jolpica + OpenF1 over the
  network (~2 minutes) *before* the bot accepts Telegram updates. `api_rate_limited`
  warnings during this phase are normal and self-recover. The bot is only live once
  the log shows `startup_sync_complete` → `bot_commands_registered` →
  `Application started`.

- **Tests need the DB and (some) network.** Unit tests (`pytest -m "not integration"`)
  use the local Postgres and skip gracefully if it is unavailable. `integration` and
  `tests/test_smoke.py` make real HTTP calls to Jolpica/OpenF1, which works from this
  environment.
