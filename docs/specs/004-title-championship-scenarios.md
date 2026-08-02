# Spec 004 — `/title` Championship Clinch Analysis

## Problem

`/standings` answers *"who is leading?"* but not the question fans actually ask late
in a season: *"can the leader still lose it, and if not — when did they clinch?"*
Spec 001's follow-up list called `/title` out as the natural next command:
**championship scenario math from standings + remaining schedule, deterministic,
fits the SQL-only architecture perfectly.**

There is a real information gap today. Nothing in the bot surfaces the *magic number*
(how many more points the leader needs to be mathematically uncatchable) or a
**CLINCHED** verdict once the title is decided.

## Goals

- New `/title` command showing **clinch analysis** for both championships:
  - **WDC** (drivers) — default view
  - **WCC** (constructors) — reached via an inline toggle, mirroring `/standings`
- For each championship, show:
  - Round progress + points still available this season
  - A **🔒 CLINCHED** banner naming the champion once the title is mathematically
    decided, OR
  - The **Top 3** with each chaser's **magic number** (points the leader still needs
    to become uncatchable by *that* chaser) when the title is still open.
- All computation is a **pure deterministic function** of data already in PostgreSQL.
  Zero new DB queries beyond the two existing reads; zero API calls; Markdown-only
  output. Fully inside the SQL-only handler architecture.

## Non-goals

- **No tie-break math.** Clinch is decided on **points only**. Ties (equal points, or
  a magic number that lands exactly on equality) resolve to **"not clinched"** — the
  conservative default. F1's real "most-wins" (then most-2nds, …) tie-break is *not*
  modelled. Rationale: modelling it requires simulating the chaser's win-count under
  a max-points run and has no clean analogue for constructors (no "wins" symmetry for
  the two-car sum). The edge it covers — a title decided *only* by count-back on the
  final lap — is vanishingly rare, and the failure mode of omitting it is safe (we
  under-claim "clinched", never over-claim it).
- **No full "who can still win" enumeration.** Analysis is fixed to the **Top 3** of
  each standings table. Early-season drivers ranked 4th+ who retain a theoretical
  shot are **not** listed. Rationale (decided with the user): predictable output
  length, clean layout; the interesting clinch/magic-number story is always about the
  leader vs. the immediate chasers, and the table naturally collapses to 2–3 relevant
  names by the point in the season when clinch questions matter.
- **No what-if simulator.** No per-round "if X wins the next race, then…" interactive
  input. That is a separate, much larger feature (its own callback state machine) and
  is explicitly deferred.
- **No cross-season / historical titles.** Current season only, same hard boundary as
  every other handler (the scheduler only syncs the current season).
- **No command arguments.** `/title` takes no positional args; the only interaction is
  the WDC/WCC toggle button, mirroring `/standings`.

## Background — data already available

The points data already has Repository methods; **no schema migration and no scheduler
change** are needed. The only additive storage change is a new *read* of the existing
`round_after` column (see "New Repository method" below) — no writes change.

- `repo.get_driver_standings(season) -> list[DriverStanding]`
  (`position`, `points: float`, `wins`, `driver`, `constructor_name`)
- `repo.get_constructor_standings(season) -> list[ConstructorStanding]`
  (`position`, `points: float`, `wins`, `constructor`)
- `repo.get_schedule(season) -> list[Race]` — the full season calendar. Each `Race`
  has `.round: int` and `.sprint: RaceSession | None`.

### Remaining events MUST align to the standings snapshot, not to `now()`

**This is the single most important correctness decision in the spec.** The naive
approach — `remaining_races = bounds["upcoming_rounds"]` from `get_schedule_bounds` —
is **wrong** and will falsely announce a champion during a race weekend. Reason:

- **Standings points** are a background snapshot, refreshed at most hourly by
  `sync_standings` (jobs.py:129). Each snapshot is stamped with a `round_after` = the
  round it reflects (stored in the `standings_drivers` / `standings_constructors`
  primary key).
- **`upcoming_rounds`** from `get_schedule_bounds` is computed from **live `now()`**:
  the moment a race's *start time* passes, that race flips to "completed" and
  `upcoming_rounds` drops by one — hours before the result exists and long before the
  next standings sync publishes new points.

During that window the two inputs are drawn from **two different clocks**:
`max_remaining` shrinks (race counted done) while `points` still reflect pre-race
gaps. If the leader was near-clinch, `leader > chaser + max_remaining` can flip to
`True` mid-race → a **false 🔒 CLINCHED** verdict that later retracts. This is the
exact opposite of the "under-claim, never over-claim" rule.

**Fix (decided with user — "A方案"):** derive remaining events from the standings
snapshot's own `round_after`, so points and remaining-count come from the *same*
round `N`. `/title` then behaves like `/standings`: a single self-consistent snapshot
that may lag reality by up to an hour but is **never internally contradictory**.

```
N = round_after of the standings snapshot being displayed   (per table — see below)
remaining_races   = count of races in get_schedule() with round > N
remaining_sprints = count of races in get_schedule() with round > N AND .sprint is not None
```

> **Enumerate, never subtract.** Remaining counts are computed by **iterating the
> races that actually exist** in `get_schedule()` and testing `round > N` on each —
> NOT by endpoint subtraction like `total_rounds - N`. The schedule may be
> incomplete (a round not yet synced) or non-contiguous; enumeration counts only what
> the DB actually knows about, which is exactly "events still to run after snapshot
> `N`". Subtraction would mis-count on any gap. An implementation that uses
> `total - N` is a defect.

### Per-table alignment: WDC uses the drivers table's `round_after`, WCC uses the constructors table's

Driver and constructor standings live in **separate tables** with **independent**
`round_after` stamps. `sync_standings` writes them in two independent `try/except`
blocks, so a partial sync (drivers saved at round 15, constructors' fetch fails and
stays at round 14) leaves the two tables at **different** `round_after` values.

Therefore each view aligns its remaining-event cutoff to **its own** source table:

| View | Points source | `round > N` cutoff `N` |
|---|---|---|
| **WDC** (drivers) | `standings_drivers` | that table's `round_after` |
| **WCC** (constructors) | `standings_constructors` | that table's `round_after` |

Cross-borrowing one `round_after` for both views would reintroduce the same
two-clocks desync on whichever view got the wrong table's cutoff. Each view reads its
own clock; the two never cross.

### New Repository method (additive — no existing signature changes)

```python
async def get_standings_round(self, season: int, table: str) -> int | None:
    """MAX(round_after) for the given standings table ('drivers' | 'constructors'),
    or None if that table has no row for the season. Reads the SAME snapshot that
    get_driver_standings / get_constructor_standings return (both use
    ORDER BY round_after DESC LIMIT 1), so points and cutoff stay aligned."""
```

This is strictly additive: `get_driver_standings` / `get_constructor_standings` keep
their current signatures, so `/standings` and every existing caller are untouched
(Rule 3). The underlying store gains a matching read of `MAX(round_after)` (or
`ORDER BY round_after DESC LIMIT 1`) parameterised by table.

> **`round_after` is never used as an empty-data guard.** When a standings table has
> no row, `get_standings_round` returns `None` — but `/title` never reaches the line
> that uses it, because the empty-`standings` guard (which returns `no_data_message`
> to avoid an `IndexError` on `standings[1]`) fires first. So `None` needs no separate
> branch; the empty-standings guard covers both. A `round_after` of **0** with a real
> "0-point opening" standings list renders normally: every race is `round > 0` →
> `remaining` = whole season → `max_remaining` huge → verdict necessarily "not
> clinched".

### Points-per-event constants (F1 2025+ rules)

Fastest-lap bonus was removed for 2025, so a race win is a flat 25.

| | Race (max) | Sprint (max) |
|---|---|---|
| **WDC** (one driver) | 25 | 8 |
| **WCC** (two cars summed) | 25 + 18 = **43** | 8 + 7 = **15** |

> **WCC rationale (author-confirmed against F1 rules, not asked of the user):**
> constructor points are the sum of *both* the team's cars. The theoretical single-event
> maximum for a team is therefore a 1–2 finish: 25 + 18 = 43 in a race, 8 + 7 = 15 in a
> sprint. This is the correct ceiling for "max points a constructor can still gain."

## Design

### New module: `src/f1_bot/utils/championship.py`

A pure, DB-free module holding the clinch math. Mirrors the existing pure-logic utils
(`utils/sessions.py`, `utils/fuzzy_match.py`). Unit-testable directly, no fixtures.

```python
from dataclasses import dataclass

# F1 2025+ single-event maximum points (no fastest-lap bonus).
WDC_RACE_MAX = 25
WDC_SPRINT_MAX = 8
WCC_RACE_MAX = 43   # 25 + 18, a 1-2 finish
WCC_SPRINT_MAX = 15  # 8 + 7


def remaining_events(races: list, round_after: int) -> tuple[int, int]:
    """(remaining_races, remaining_sprints) for events after snapshot `round_after`.

    ENUMERATES the races that actually exist and tests round > round_after on each —
    never `total - round_after`. Immune to schedule gaps / non-contiguous rounds.
    `races` is get_schedule()'s list; each item has .round and .sprint. Kept here
    (not in the formatter) so it is a pure, directly-testable function.
    """
    remaining = [r for r in races if r.round > round_after]
    return len(remaining), sum(1 for r in remaining if r.sprint is not None)


def max_remaining_points(remaining_races: int, remaining_sprints: int,
                         race_max: int, sprint_max: int) -> int:
    """Largest points total still winnable across all remaining events."""
    return remaining_races * race_max + remaining_sprints * sprint_max


@dataclass(frozen=True)
class ClinchStatus:
    clinched: bool          # leader is mathematically uncatchable by the chaser
    magic_number: int | None  # points leader still needs; None once clinched


def clinch_status(leader_pts: float, chaser_pts: float, max_remaining: int) -> ClinchStatus:
    """Points-only clinch test of leader vs. ONE chaser.

    Clinched iff  leader_pts > chaser_pts + max_remaining  (STRICT; equality =>
    not clinched, the conservative choice — a tie is decided by count-back we do
    not model, so we never claim a title that count-back could still flip).

    magic_number = points the leader must still add to become uncatchable =
        (chaser_pts + max_remaining) - leader_pts + 1
    Clamped to >= 0; reported only while not clinched.
    """
    if leader_pts > chaser_pts + max_remaining:
        return ClinchStatus(clinched=True, magic_number=None)
    gap = (chaser_pts + max_remaining) - leader_pts + 1
    return ClinchStatus(clinched=False, magic_number=max(0, int(gap)))
```

**Clinch is always leader-vs-the-single-strongest-chaser.** With standings sorted by
position, that is index `[1]`. If the leader has clinched against the 2nd-placed
competitor, they have clinched against everyone. The magic number shown for the leader
is therefore computed against `[1]`.

> **Float points.** `points` is a `float` in both models (Jolpica has historically
> emitted `.5` in some series and the model keeps the type). In practice current-era
> F1 points are whole numbers. `magic_number` casts to `int` after the `+1`, which is
> correct for whole-number points; if a fractional total ever appears, the cast floors
> the gap — acceptable because the banner also renders points with `:.0f` elsewhere.

### Formatters: `src/f1_bot/formatting/messages.py`

Two new formatters, next to `format_driver_standings` / `format_constructor_standings`.
They own **layout only** — all math comes from `championship.py`. A shared private
helper renders the common body so WDC/WCC layout stays identical.

```
format_title_wdc(standings: list[DriverStanding],
                 remaining_races: int, remaining_sprints: int, season: int) -> str
format_title_wcc(standings: list[ConstructorStanding],
                 remaining_races: int, remaining_sprints: int, season: int) -> str
```

The formatters take **already-counted** remaining events, not `bounds` and not a
schedule — keeping them pure layout + math with no `round > N` iteration inside. The
handler computes the counts (via the pure helper below) and passes them in.

Each formatter:
1. Guards empty standings → returns `no_data_message("standings")` (caller also guards;
   see Error handling).
2. Computes `max_remaining` via `max_remaining_points(remaining_races,
   remaining_sprints, ...)` with the right constants for the championship.
3. Sorts standings by `position`, takes the top-3 slice for display.
4. Runs `clinch_status(leader, chaser=standings[1], max_remaining)` **once** — this
   single call drives the whole verdict. Its `clinched` flag chooses banner vs.
   magic-number line; its `magic_number` is the one figure shown.
5. Renders each row (positions 1–3):
   - **Leader (pos 1):** name + points, bold.
   - **Chasers (pos 2, 3):** name + points + **deficit to the leader** in points
     (`leader.points - row.points`, a plain subtraction — *not* a per-row
     `clinch_status` call). The deficit answers "how far back are they", which is the
     only per-chaser number that carries meaning; there is exactly **one** magic
     number per view and it belongs to the leader-vs-runner-up race (step 4).

> **Why only one magic number.** The magic number is a property of *the title race*,
> not of each individual — it is the points the **leader** needs to be uncatchable by
> the **strongest** remaining rival (pos 2). Computing a separate magic number per
> chaser row would display several different numbers for the same question and confuse
> more than it informs. Chaser rows therefore show a plain points **deficit**, and the
> leader-vs-pos-2 magic number is stated once on its own line.

**Name/label conventions reuse existing helpers** — `pos_icon`, `flag_icon`,
`{given_name} {family_name}` for drivers (as in `format_driver_standings`); constructor
`name` for WCC. Legacy `ParseMode.MARKDOWN`, `_esc()` on any free text if needed
(team/driver names are not user input, so escaping is not required here — matches how
`format_driver_standings` already renders them raw).

#### Rendered layout (title still open)

The round-progress line reads `Round {round_after} of {len(schedule)}` — i.e. the
*snapshot* round `N`, not a live `now()` round. "left" counts come from
`remaining_events`.

```
🏆 *2026 WDC Title Race*

Round 14 of 24 · 10 races + 3 sprints left
Max points still available: *274*

🥇 Verstappen — *310 pts*
🥈 Norris — 258 pts  (−52)
🥉 Leclerc — 221 pts  (−89)

_Magic number: Verstappen clinches with *17* more points._
```

#### Rendered layout (clinched)

```
🏆 *2026 WDC Title Race*

Round 22 of 24 · 2 races + 0 sprints left
Max points still available: *50*

🔒 *CLINCHED* — Max Verstappen is your 2026 World Drivers' Champion

🥇 Verstappen — *401 pts*
🥈 Norris — 320 pts
🥉 Leclerc — 265 pts
```

WCC is the same structure with 🏭 and constructor names; the banner reads
`… World Constructors' Champion` and the team name replaces the driver name.

> Exact emoji/wording are illustrative; the implementation may refine copy. The
> **structural contract** that tests assert: (a) a title line, (b) a round-progress
> line containing the remaining race & sprint counts, (c) a "max points available"
> figure, (d) either a `CLINCHED` banner naming the leader **or** a magic-number line,
> (e) up to three ranked rows.

### Handler: `src/f1_bot/handlers/title.py`

A near-clone of `handlers/standings.py` — the established two-view toggle pattern.

```python
_WDC = "title:wdc"
_WCC = "title:wcc"

async def _render_view(repo, season: int, table: str) -> str:
    """Build the title text for one championship, aligning remaining events to that
    table's own standings snapshot (round_after). Returns no_data text if empty."""
    if table == "drivers":
        standings = await repo.get_driver_standings(season)
        fmt = format_title_wdc
    else:
        standings = await repo.get_constructor_standings(season)
        fmt = format_title_wcc
    if not standings:
        return no_data_message("standings")
    n = await repo.get_standings_round(season, table)   # same snapshot as `standings`
    races = await repo.get_schedule(season)
    rem_races, rem_sprints = remaining_events(races, n or 0)
    return fmt(standings, rem_races, rem_sprints, season)

async def title_handler(update, context):
    repo = context.bot_data["repo"]; season = date.today().year
    text = await _render_view(repo, season, "drivers")
    await update.effective_message.reply_text(
        text, parse_mode=ParseMode.MARKDOWN, reply_markup=_toggle_keyboard())

async def title_callback(update, context):
    query = update.callback_query; await query.answer()
    repo = context.bot_data["repo"]; season = date.today().year
    table = "drivers" if query.data == _WDC else "constructors"
    text = await _render_view(repo, season, table)
    try:
        await query.edit_message_text(
            text, parse_mode=ParseMode.MARKDOWN, reply_markup=_toggle_keyboard())
    except BadRequest:
        pass
```

`n or 0` maps a `None` `round_after` to 0, but that branch is unreachable when
`standings` is non-empty (the guard above already returned) — it is only a
belt-and-braces default so `remaining_events` never receives `None`.

`_toggle_keyboard()` returns the two-button row `[🏆 Drivers | 🏭 Constructors]` with
`callback_data` `title:wdc` / `title:wcc` — identical shape to `standings.py`, distinct
namespace so there is no collision with the `standings:` handler.

`register(app)` adds `CommandHandler("title", title_handler)` and
`CallbackQueryHandler(title_callback, pattern=r"^title:")`.

### Integration points (exact locations)

1. `src/f1_bot/handlers/__init__.py` — add `title` to the import tuple and call
   `title.register(app)` (place it right after `standings.register(app)` to keep the
   championship commands together).
2. `src/f1_bot/main.py` — add `BotCommand("title", "WDC + WCC title clinch analysis")`
   to the `set_my_commands` list, directly after the `standings` entry (line ~51).
3. `src/f1_bot/handlers/start.py` — add `/title — …` under the `*Standings*` section of
   `_HELP_TEXT`, right below the `/standings` line.

## Error handling

- **No standings yet** (pre-season, or standings not synced) → both the command and the
  callback branch fall back to `no_data_message("standings")`. The formatter also guards
  internally so it is never called with an empty list that would `IndexError` on
  `standings[1]`.
- **Fewer than 2 competitors** (degenerate; effectively impossible in F1 but must not
  crash) → with only a leader and no chaser, `max_remaining` is irrelevant: treat as
  **clinched** (nobody can catch a lone competitor). The formatter checks
  `len(standings) < 2` before indexing `[1]`.
- **Fewer than 3 competitors** → the Top-3 slice simply renders 1–2 rows; no padding.
- **Season over** (no race in `get_schedule()` has `round > round_after`, so
  `remaining_events` returns `(0, 0)`) → `max_remaining == 0`, so `clinch_status`
  returns `clinched=True` for any nonzero lead; the banner shows the final champion.
  A dead-heat at season end (equal points) stays "not clinched" by the strict rule —
  acceptable and rare; the real tie-break is out of scope (non-goal).
- **`edit_message_text` unchanged-text** `BadRequest` → swallowed, matching every other
  toggle handler.
- **Callback parse** — `title:*` is a brand-new namespace with only two fixed literal
  values and no positional parameters, so there is nothing to `int()`-parse and no
  spoofable integer field; the `if/else` on `query.data` is exhaustive (anything that
  is not `title:wdc` falls into the WCC branch, which is safe). No legacy-format
  migration handler is needed (unlike `nsess:`/`qual:`).

## Testing approach

The math + formatting tests are **DB-free** — the math is a pure module and the
formatters take plain objects + pre-counted ints (no `bounds`, no schedule). Only the
new `get_standings_round` store test needs the dev DB (like the rest of
`tests/test_storage/`, it auto-skips when the container is down). Run the DB-free
signal with `uv run pytest tests/test_handlers/ tests/test_formatting/ tests/test_utils/`.

### `tests/test_utils/test_championship.py` (new) — the math, exhaustively

Per Rule 9 (tests encode *why*), the boundary cases are the point of this suite:

- `max_remaining_points` — race-only, sprint-only, mixed; zero remaining → 0.
- `clinch_status` **not clinched**: leader ahead but catchable → `clinched=False`,
  `magic_number` == exact expected gap.
- `clinch_status` **magic number of 1**: leader one point short of uncatchable →
  `magic_number == 1`, still `clinched=False` (the off-by-one boundary — the single
  most important assertion in the suite).
- `clinch_status` **exact clinch**: leader exactly `chaser + max_remaining + 1` →
  `clinched=True`, `magic_number is None`.
- `clinch_status` **tie stays open**: `leader_pts == chaser_pts + max_remaining`
  (equality) → `clinched=False` (conservative rule; asserts we never over-claim on a
  tie).
- `clinch_status` **season over**: `max_remaining == 0`, leader ahead → clinched.
- `remaining_events` **basic**: mixed schedule, `round_after=N` → counts only
  `round > N`, and sprints only where `.sprint is not None`.
- `remaining_events` **enumerate-not-subtract (the desync guard)**: schedule rounds
  `[1,2,3,7]` (a gap — rounds 4–6 not in the DB) with `round_after=3` → asserts
  **1** remaining (only round 7). A `max_round - N` subtraction would give `7-3=4`;
  the correct enumeration gives 1. This is the assertion that forbids the subtraction
  shortcut.
- `remaining_events` **round_after=0**: whole schedule remaining.

### `tests/test_formatting/test_title.py` (new) — layout contract

Build `DriverStanding` / `ConstructorStanding` lists and pass **pre-counted**
`remaining_races` / `remaining_sprints` ints directly (no DB, no `bounds`, no
schedule). Assert the **structural contract** (a)–(e) above, not exact glyphs:

- **Open title:** output contains the round-progress line, the max-points figure
  (== `max_remaining_points(remaining_races, remaining_sprints, …)`), **exactly one**
  magic-number line naming the leader, and up to three ranked rows. Chaser rows show
  their points **deficit to the leader** (assert the pos-2 deficit equals
  `leader.points - runner_up.points`). No `CLINCHED` banner present.
- **Clinched title:** pass `remaining_races=remaining_sprints=0` (or small enough that
  the leader is uncatchable) → output contains the `CLINCHED` banner naming the leader;
  no magic-number line.
- **WCC:** constructor names render (not driver names); 🏭 present; max-points figure
  uses the 43/15 constants (a race-only remaining count yields `43*n`, proving the WCC
  constants are wired, not the WDC 25).
- Special chars: none required (names are not Markdown-hostile here), but include a
  driver whose data round-trips through `:.0f` points formatting.

### `tests/test_storage/test_standings_round.py` (new) — the cutoff read (needs dev DB)

- After `save_driver_standings(season, …, round_after=7)`, `get_standings_round(season,
  "drivers") == 7`; independently, `get_standings_round(season, "constructors")`
  reflects only the constructors table.
- **Per-table independence (the partial-sync guard):** save drivers at `round_after=15`
  and constructors at `round_after=14` → `get_standings_round(…, "drivers") == 15` and
  `get_standings_round(…, "constructors") == 14`, proving the two views read distinct
  cutoffs.
- Empty table → `get_standings_round` returns `None`.
- Reads the **same** snapshot as `get_driver_standings` (both `ORDER BY round_after
  DESC LIMIT 1`): after saving two snapshots (round 5 then round 8), the method returns
  8, matching the standings list `get_driver_standings` returns.

### `tests/test_handlers/test_title.py` (new) — wiring + toggle

Mirror `tests/test_handlers/test_standings.py`, with a mock `repo` whose
`get_standings_round` / `get_schedule` return canned values:

- `/title` with populated standings → replies with WDC text + a 2-button keyboard
  (assert with **tuple-of-tuples**, `kb.inline_keyboard[0]` has two buttons with
  `callback_data` `title:wdc` / `title:wcc`).
- `/title` with empty standings → `no_data_message("standings")`, no keyboard crash,
  and **`get_standings_round` / `get_schedule` are not required to have been called**
  (the empty guard short-circuits before the cutoff read).
- `title:wcc` callback → calls `get_standings_round(season, "constructors")` (assert the
  `"constructors"` arg — the per-table alignment) and edits to WCC text.
- `title:wdc` callback after WCC → edits back to WDC text; a repeat toggle raising
  `BadRequest` is swallowed (no exception escapes).

### Full-suite expectation

`uv run pytest -m "not integration"` will still report the pre-existing 26
`test_e2e.py` DB-offline **errors** when the dev container is down — unrelated to this
change (see `reference-e2e-tests-error-offline`). The new tests must all pass and add
**zero** new errors. `ruff check`/`format` clean.

## Trade-offs considered

- **Pure `championship.py` module vs. inlining math in the formatters.** Chose the
  module: the clinch boundaries (magic-number-of-1, tie-stays-open) are exactly what
  Rule 9 says to test directly, and a pure function lets the test assert integers
  instead of reverse-parsing a rendered string. One extra file; worth it.
- **Top-3 fixed vs. "everyone still alive" enumeration.** Chose fixed Top-3 (user
  decision): predictable length, and the leader-vs-chasers framing is what carries the
  clinch story. Documented as a non-goal so a future reader knows it was deliberate.
- **Points-only clinch vs. full count-back tie-break.** Chose points-only (user
  decision): one inequality, safe failure mode (under-claims, never over-claims),
  no constructor-side asymmetry to hack around.
- **New `/title` command vs. folding into `/standings` as a third toggle.** Chose a
  separate command: `/standings` answers "current order", `/title` answers "is it
  decided" — distinct intents, and a 3-way toggle muddies both. Discoverability via
  `/help` + `set_my_commands` covers the "will users find it" concern.
- **Remaining events from `round_after` vs. live `now()` (`bounds["upcoming_rounds"]`).**
  Chose `round_after` (the "A方案" from the grill session). Live `now()` desyncs from
  the hourly standings snapshot during a race weekend and can flip a near-clinch leader
  to a false 🔒 CLINCHED mid-race. Aligning remaining-count to the snapshot's own
  `round_after` makes `/title` a self-consistent view of one snapshot — like
  `/standings` — that lags reality by at most an hour but never contradicts itself.
  Cost: one additive `get_standings_round(season, table)` read; no signature change to
  existing methods (Rule 3).
- **Per-table `round_after` vs. one shared cutoff.** Chose per-table: drivers and
  constructors are separate tables synced in independent `try/except` blocks, so a
  partial sync can leave them at different rounds. Each view aligns to its own table's
  cutoff so a constructors-sync failure can't desync the WCC view against a drivers
  cutoff.
- **`get_standings_round(season, table)` param vs. two methods.** Chose one method with
  a `table` param over `get_driver_standings_round` / `get_constructor_standings_round`:
  the read is identical bar the table name, and the handler already branches on `table`.
```
