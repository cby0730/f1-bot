# Spec 001 — Remove paid-tier live code & SQLite documentation residue

**Status:** Approved for implementation
**Type:** Dead-code removal + documentation correction
**Date:** 2026-07-27

## Problem statement

Two pieces of dead weight exist in the codebase, both tracing back to abandoned
directions:

1. **Paid-tier "live" data code.** `models/live.py` and four `OpenF1Client`
   methods (`get_positions`, `get_intervals`, `get_race_control`, `get_weather`)
   target OpenF1's real-time endpoints (`/position`, `/intervals`,
   `/race_control`, `/weather`). These endpoints require a paid subscription to
   query during a live session, so the bot will never use them. No handler,
   scheduler job, or repository references them — they are leaf dead code.

2. **SQLite documentation residue.** CLAUDE.md still carries a "Dockerfile stale
   env var" gotcha claiming the Dockerfile sets `F1BOT_SQLITE_PATH=/data/f1bot.db`
   and mounts a `/data` volume. A repo-wide grep confirms **this is no longer
   true** — the Dockerfile is clean and the only remaining "SQLite" string in the
   entire repo is that gotcha itself. The note now describes a problem that does
   not exist, which actively misleads.

## Goals

- Remove all code that targets OpenF1 paid live endpoints, along with its models
  and tests.
- Remove the one remaining stale SQLite reference (the CLAUDE.md gotcha).
- Keep CLAUDE.md and its pointer file GEMINI.md accurate and in sync.

## Non-goals

- **No new features.** `/compare`, `/title`, and the points chart are separate,
  later brainstorming cycles (see "Follow-up work").
- **Do not touch `_is_in_live_window()`** (or `_LIVE_WINDOW_MARGIN`, or the
  `jobs.py` module-docstring note about the live window) in `scheduler/jobs.py`.
  Despite the name, this guard does the *opposite* of the removed code: it
  *skips* syncing a session during the window `(starts_at − 30min) ≤ now ≤
  (session_end + 30min)` — i.e. the session plus a 30-minute buffer before and
  after — because the OpenF1 free tier does not serve that session's data during
  that window. The name "live window" refers to this real, still-correct concept
  (the interval when a session is live), not to the paid live-data capability
  being removed. It has no dependency on the removed methods and must stay.
- **Do not touch the Dockerfile or compose files.** They are already clean. The
  two `/data` matches in compose (`/var/lib/postgresql/data`) are correct
  PostgreSQL volume mounts.
- **Do not remove** `get_meetings`, `get_sessions`, `get_pit`, `get_laps`,
  `get_session_results`, or `get_drivers` — these use static/post-race endpoints
  and are actively used.

## Scope (exact footprint)

Verified by grep across `src/` and `tests/`.

| # | Action | File |
|---|--------|------|
| 1 | Delete entire file | `src/f1_bot/models/live.py` |
| 2 | Remove 4 methods (`get_positions`, `get_intervals`, `get_race_control`, `get_weather`) and the top-of-file `from f1_bot.models.live import (...)` block | `src/f1_bot/api/openf1.py` |
| 2b | Correct the `OpenF1Client` class docstring: drop the "live timing" claim (the client no longer provides it after step 2), e.g. → `"""Client for the OpenF1 API — sessions, results, laps, pit stops, and timezone offsets."""` | `src/f1_bot/api/openf1.py` |
| 3 | Mixed file — surgically remove live tests only, keeping meetings/sessions/pit/laps tests | `tests/test_api/test_openf1.py` |
| 4 | Mixed file — surgically remove live tests only, keeping sessions/session_results/pit/laps/meetings tests | `tests/test_api/test_openf1_unit.py` |
| 5 | **Final step — single consolidated CLAUDE.md pass, done after all code/test changes above are complete.** See "CLAUDE.md consolidated update" below. | `CLAUDE.md` |
| 6 | No edit expected (GEMINI.md is a one-line pointer to CLAUDE.md; it references no specific line numbers or counts, so it stays valid) | `GEMINI.md` |

### CLAUDE.md consolidated update (do last, in one pass)

All CLAUDE.md edits happen together *after* the code and test changes land, so
the counts and references reflect the final state:

- Delete the `models/live.py` key-file table row (currently L92).
- Delete the "Dockerfile stale env var" gotcha (currently L148) — it describes a
  residue that no longer exists.
- Update the test-count line to the actual approximate values at that point
  (re-count via `uv run pytest --co -q`). **Keep the `~` approximate phrasing and
  do not write exact numbers** — precise counts drift on every future test
  change and become the next stale fact.
- No changes needed to GEMINI.md (pointer only).

### Test removal detail

Both files are mixed — they contain live tests interleaved with tests that must
stay. Remove only the named live tests below; keep everything else.

- `tests/test_api/test_openf1.py` (integration): remove
  `test_get_positions_abu_dhabi_race`, `test_get_weather_abu_dhabi_race`,
  `test_get_race_control_abu_dhabi`, and their section-comment headers. **Keep**
  `test_get_meeting_abu_dhabi_2024`, `test_get_sessions_abu_dhabi_2024`,
  `test_get_pit_stops_abu_dhabi_race`, `test_get_laps_abu_dhabi_race_single_driver`.
  Note this file's live import is `from f1_bot.models.live import LivePosition,
  RaceControlMessage, WeatherData` (three names, no `LiveInterval`; no
  `get_intervals` test exists here).
- `tests/test_api/test_openf1_unit.py` (unit): remove
  `test_get_positions_parses_position_and_driver`,
  `test_get_intervals_none_gap_handled`,
  `test_get_race_control_parses_messages`,
  `test_get_weather_parses_all_fields`,
  `test_get_race_control_skips_record_without_session_key`,
  `test_get_weather_skips_record_without_session_key`, and their section-comment
  headers. **Keep** the `get_sessions`, `get_session_results`, `get_pit`,
  `get_laps`, and `get_meetings` tests (including their "skips record" variants).
  This file imports no live models directly — the removed methods return live
  models but the tests assert on plain fields, so no import edit is needed here.

**Import-cleanup rule (both files):** after removing test functions, delete only
the symbols in each `import` line that are no longer referenced — do not delete
whole import lines that still bind used names (e.g. `test_openf1.py` also imports
`Meeting`, `LapTime`, `PitStop`, which stay). Verify with `ruff check` (F401
catches any leftover unused import).

## Trade-offs considered

- **Delete now vs. keep as "future infrastructure."** The models were originally
  kept speculatively (CLAUDE.md called them "infrastructure for future live
  features"). Given the paid-endpoint constraint is permanent, the feature will
  never ship on the free tier — so this is a YAGNI removal, not a reversible
  bet. If a paid tier is ever adopted, the code is trivially recoverable from
  git history.
- **Editing the Dockerfile vs. only editing docs.** The obvious reading of the
  gotcha suggests editing the Dockerfile — but the Dockerfile is already clean.
  The correct fix is to the documentation that lies about it.

## Error handling / risk

- **Lowest-risk class of change:** the removed methods are leaf nodes with zero
  in-repo callers (grep-verified). No call chains break.
- Primary risk is *over-deletion* in the mixed test file. Mitigated by the
  explicit test-name list above.

## Testing approach

**Run the full suite** — this is a removal, so the point is to prove nothing was
collaterally broken; do not narrow to just the touched files.

**Test database lifecycle (ephemeral):** the unit suite needs the dev PostgreSQL
(fixtures `pg_store`/`repo` connect to it). Bring it up only for the run and
**tear it down completely afterward, including its volume**, so nothing is left
running on the shared host:

```bash
docker compose -f docker-compose.dev.yml up -d     # starts postgres on port 31055 (non-standard, host network)
uv run pytest -m "not integration"                 # full unit suite
uv run pytest -m integration -v                    # full integration suite (real HTTP)
uv run ruff check src/ tests/                       # no dangling f1_bot.models.live imports
docker compose -f docker-compose.dev.yml down -v    # REQUIRED: remove container AND volume when done
```

- The dev DB port is **31055** (set in `docker-compose.dev.yml` via
  `command: postgres -c port=31055`, host network) — this non-standard port is
  intentional, to avoid colliding with any standard-5432 PostgreSQL already
  running on the shared host. Do not change it. (Note: `.env.example`'s comment
  example says `31050` — a pre-existing typo, out of scope for this spec.)
- `uv run pytest -m "not integration"` must pass with the live unit tests gone
  and all others intact.
- `uv run pytest -m integration -v` count drops by the 3 removed integration
  tests.
- `uv run ruff check src/ tests/` must pass — confirms no dangling imports of
  `f1_bot.models.live` remain anywhere.
- The `down -v` teardown is a hard requirement of this task, not a suggestion —
  leaving the container or `mango_pgdata` volume behind on the shared host is a
  defect.
- Verification success criteria (scoped to executable code + config only — the
  spec doc and CLAUDE.md are allowed to mention these terms, so `docs/` and `*.md`
  are deliberately excluded to avoid self-referential false positives):
  - `grep -rn "models.live\|get_positions\|get_intervals\|get_race_control\|get_weather" src/ tests/`
    returns **zero** — these are code symbols; no surviving file should reference them.
  - `grep -rni "sqlite" src/ tests/ Dockerfile docker-compose.yml docker-compose.dev.yml .env.example`
    returns **zero**.

## Follow-up work (separate cycles, not this spec)

1. **`/compare`** — two-driver head-to-head from the `results` table (text-only,
   zero architectural risk). Highest fan-demand.
2. **`/title`** — championship scenario math from standings + remaining schedule
   (deterministic, fits SQL-only perfectly).
3. **Points chart** — per-round cumulative points as an image. Deferred to its
   own cycle because it introduces a *new output modality* (binary image via
   `bot.send_photo`) and a new dependency (matplotlib or SVG), breaking the
   current "all handlers emit Markdown text" invariant. Worth a full
   brainstorm of its own.
