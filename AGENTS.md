# AGENTS.md

Dev commands, architecture, and code-level gotchas live in [`CLAUDE.md`](CLAUDE.md)
and [`src/f1_bot/handlers/CLAUDE.md`](src/f1_bot/handlers/CLAUDE.md). Read those
first — this file records only what the *environment* does differently.

## Toolchain

Python 3.13 via `uv` (installed at `~/.local/bin`, already on PATH). `uv sync`
provisions the interpreter and `.venv`. Prefix everything with `uv run`.

Running the bot needs `TELEGRAM_BOT_TOKEN` — a bare env var, no `F1BOT_` prefix,
from @BotFather, never stored in the repo.

**Never run a local bot on production's token.** Telegram allows one
`getUpdates` connection per token, so a second one fights the VM and both become
unreliable. Use a separate test bot.

## Databases

Two unrelated Postgres instances, often confused:

| | Purpose | How it starts |
|---|---|---|
| `mango_pg`, port 31055 | Running the bot locally | `docker-compose.dev.yml` |
| Throwaway, random port | The test suite | Testcontainers, automatic |

The dev DB is **only** for `uv run -m f1_bot`. Tests never touch it (see
CLAUDE.md's Test conventions). Tear it down with
`docker compose -f docker-compose.dev.yml down -v` — the volume is residue, not
a cache.

**On Cursor Cloud there is no Docker.** The dev DB is instead a *native*
PostgreSQL cluster already serving port 31055 with role/db `mango`/`mango`,
matching the default `F1BOT_DATABASE_URL`. Restart it with
`sudo pg_ctlcluster <major> main start` (check `pg_lsclusters`). Schema is
auto-created at startup; there is no migration step. Because the test suite
needs a Docker daemon, **it cannot run in this environment at all** — do not
interpret its absence as a code failure.

## Network

This host's login shell exports `HTTPS_PROXY=http://10.1.1.39:80`, a content
filter that answers `302` to a block page for `api.jolpi.ca` and
`api.openf1.org`. The empty body surfaces as
`JSONDecodeError: Expecting value: line 1 column 1` — which looks like a parser
bug and is not. When many *untouched* tests fail identically, suspect the shared
network path, not the code.

Prefix the working tunnel rather than editing the profile:

```bash
env HTTP_PROXY=http://127.0.0.1:31100 HTTPS_PROXY=http://127.0.0.1:31100 \
    http_proxy=http://127.0.0.1:31100 https_proxy=http://127.0.0.1:31100 \
    uv run pytest -m integration
```

`31100` is a session-scoped tunnel from the user's laptop, **not a daemon here**.
`Connection refused` means they are not currently connected — not a broken
config. Check with `ss -ltn | grep 31100` before changing anything.

## Branches and CI

**PRs target `develop`. `main` is production** — every push to it SSHes into the
OCI VM and rebuilds. Promote `develop` → `main` only as an explicit release
merge.

Both branches are protected, so a direct push is rejected; branch even for a
one-line docs fix.

`test.yml` runs `test` (`pytest -m "not integration"`), `lint`
(`ruff check` + `ruff format --check`) and `audit` (`pip-audit`) on every PR into
`develop`/`main`, every push to `develop`, and via `workflow_call` from
`deploy.yml`. No `services:` block — Testcontainers supplies the database, with
Ryuk disabled since the runner is itself ephemeral.

`deploy.yml` calls that workflow as its own `test` job and the SSH step declares
`needs: test`, so a push to `main` failing `test` or `lint` never reaches the VM.
It is defined once and reused rather than copied — a second copy would drift, and
the copy that drifts is the one guarding production.

**`audit` is exempt by construction.** `continue-on-error: true` makes it report
success, so a CVE published upstream this morning stays visible without holding a
release hostage. Only what this repo controls can block a deploy. For the same
reason it is deliberately *not* a required status check: GitHub reads a required
check's raw conclusion and would ignore `continue-on-error`.

**Two layers, neither replacing the other:** branch protection rejects the
*write*; `needs: test` guards the *deploy*. The gap between them is base drift —
a PR tested against `main`@A merges after someone lands B, and A+B was never
tested together. `needs: test` is the only thing that tests the actual merge
result.

## Deploying

The VM's checkout must be clean before a deploy, or `git pull` aborts and
`set -e` fails the workflow before any container is touched. **This happens even
when a locally edited file is byte-identical to the incoming one** — merge
compares the working tree against the *index*, never against the upstream blob.
Verify equality, then `git checkout -- <file>` to discard.

Untracked files are a different case and do not block: merge only protects paths
it is about to write. They abort a pull only when the incoming commit adds the
same path.

Do not `git add -A` or `git add .` on the VM. `backup/` holds full database
dumps containing real `telegram_id`s; `.gitignore` covers `backup/`, `*.dump`
and `*.bak`, but a forced add still wins.

`docker compose up -d` only recreates services whose config changed. A deploy
that leaves the postgres container untouched never risked the data — which is
also why an eventual postgres-section change deserves far more care than a
routine bot deploy.

## Launch film

`video/` is a Remotion app (Node, not Python): `cd video && npm run render:full`.
Rebuild the README gif with the ffmpeg recipe in `video/README.md`. Do not
`uv run` Remotion, and do not copy `video/` into Docker.
