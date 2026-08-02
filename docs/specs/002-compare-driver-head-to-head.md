# Spec 002 — `/compare` driver head-to-head

**Status:** Approved for implementation
**Type:** New feature (command + callback flow)
**Date:** 2026-07-28

## Problem statement

Users frequently want to answer "who is having the better season, driver A or
driver B?" The bot already stores everything needed to answer this — per-round
race results, sprint results, qualifying results (each carrying finishing
`position` / `status`), and the current driver standings — but exposes no command
that aggregates two drivers side by side. `/compare` fills that gap.

## Goals

- Add a `/compare` command that pits two **current-season** drivers head-to-head
  across a fixed "core" stat set.
- Reuse existing infrastructure: the driver grid keyboard, `_esc()` markdown
  escaping, the `Repository` read layer, and the SQL-only handler pattern.
- Zero new data sources, no scheduler changes, no new database tables.

## Non-goals

- **No cross-season / career comparison.** The Repository is scoped to the
  current season and the scheduler only syncs the current season. Historical data
  is not in the database, and fetching it would require live API calls from a
  handler — a violation of the SQL-only architecture. Scope is **current season
  only**, and this is a hard boundary, not a preference.
- **No command arguments.** `/compare` takes no positional args. Driver selection
  is purely through the Telegram inline UI (decided with the user). This removes
  an entire branch of arg-parsing and fuzzy-match-on-arg error handling.
- **No per-round paging.** The comparison is a whole-season aggregate; there is no
  "flip through each round" semantic, so no round navigation.
- **No "swap one driver" shortcut.** Re-selecting from scratch is cheap; a partial
  re-pick is unnecessary complexity (YAGNI).
- **No special-casing of same-surname drivers.** Buttons and the result header
  reuse the existing `{flag} {family_name}` label convention (`extras.py:22`). If
  two current-season drivers ever share a surname, the fix belongs in the shared
  `_driver_menu_keyboard` label logic so `/driver` benefits too — out of scope
  here. (2026 has no same-surname pair.)
- **No stale-keyboard handler.** `cmp:*` is a brand-new callback namespace with no
  legacy formats to migrate (unlike `nsess:`/`qual:`). A button always originates
  from the *current* `get_drivers_map`, so it is valid when generated; the only
  stale path is a user clicking a button on a message left sitting across a
  driver-lineup change (mid-season swap or new season) — rare × rare. It is not
  specially handled: the mandatory callback-parse guard (below) catches it, and
  the result step already looks each driver up by id to render the name, so a
  vanished id degrades naturally to "Invalid selection". No extra validation, no
  bespoke message.

## Compared statistics — the "core pack + DNF", race **and** sprint combined

All six stats are computed over **both the main race and the sprint** of each
completed round, for a single consistent scope. Points come from the official
standings (which already include sprint points), so every row now speaks the same
"race + sprint" language. The result message carries a one-line footnote
`* 含衝刺賽 (incl. sprint)` so the scope is explicit.

Derived purely from current-season race + sprint + qualifying results plus the
current standings. No lap data, no extra source.

| Stat | Source | Notes |
|---|---|---|
| Points + gap | `get_driver_standings(season)` | Season total (already includes sprint). Gap = abs difference of the two drivers' points |
| Qualifying H2H | per-round `get_qualifying_results` | Rounds where each driver out-qualified the other (both must have a quali result that round). Qualifying has no sprint variant and no DNF concept — pure grid position |
| Race + Sprint H2H | per-round `get_race_results` **and** `get_sprint_results` | Counted **per session** — see H2H rule below |
| Wins | `get_race_results` + `get_sprint_results` | `position == 1` in either session type |
| Podiums | `get_race_results` + `get_sprint_results` | `position <= 3` in either session type |
| DNFs | `status` of `get_race_results` + `get_sprint_results` | See DNF rule below; applies identically to both session types |

> **Data-shape note:** `Repository.get_*_results()` returns raw **`list[dict]`**
> (JSONB `data_json` decoded by `json.loads`), **not** Pydantic models. Access
> fields as `r["position"]`, `r["status"]`, `r["driver"]["driver_id"]`. The
> `RaceResult` / `SprintResult` Pydantic classes describe the *shape* of those
> dicts but are not instantiated on the read path.

### DNF classification rule

`status` is a free-text Ergast/Jolpica string (e.g. `"Finished"`, `"+1 Lap"`,
`"Accident"`, `"Engine"`, `"Retired"`) present on **both** race and sprint result
dicts. F1 history has dozens of distinct failure strings, so classify by
**whitelisting "finished" shapes** and treating everything else as a DNF — this
way an unseen failure string is never misread as a finish:

- **Counts as finished:** `status == "Finished"` OR `status` matches `+N Lap(s)`
  (lapped but classified). Concretely: `status == "Finished" or status.startswith("+")`.
- **Counts as DNF:** anything else.

### Head-to-head rule — per session, DNF-aware

Race+Sprint H2H is counted **per session**, not per round: a weekend with both a
race and a sprint can contribute **up to 2** H2H sessions. For each session where
**both** drivers have a result:

- **Both finished, or exactly one DNF:** the driver with the lower `position`
  value wins that session's H2H. A driver who finished while the other retired
  therefore *wins* that session (finishing is itself part of the contest).
- **Both DNF:** the session is **excluded** from H2H. When both retire,
  `position` reflects retirement order, which carries no competitive meaning.
- **Only one driver has a result** (the other didn't contest that session):
  **excluded** — you can't compare a session only one of them ran.

Qualifying H2H follows the same "both must have a result" gate but has no DNF
branch (grid position only).

## Interaction model — three-step stateless state machine

The handler holds no server-side session. Context between steps is carried in the
callback data itself (same pattern as `round_picker`'s `origin` token).

```
/compare
   │
   ▼
[Step 1] Pick driver A          ← driver grid, buttons emit cmp:a:{driver_id}
   │
   ▼
[Step 2] Pick driver B          ← same grid, buttons emit cmp:b:{a_id}:{b_id}
   │                              (driver A's id is baked into every button)
   ▼
[Step 3] Result message         ← static two-column text + [🔙 重新比較] (cmp:list)
```

### Callback data formats

| Pattern | Meaning |
|---|---|
| `cmp:a:{driver_id}` | Step 1 → driver A chosen; render Step 2 grid |
| `cmp:b:{a_id}:{b_id}` | Step 2 → driver B chosen; compute + render result |
| `cmp:list` | Result/Step-2 → return to Step 1 (fresh comparison) |

**64-byte limit:** Telegram caps `callback_data` at 64 bytes. `cmp:b:` + two
driver_id slugs is the longest payload. Driver ids are short slugs
(`max_verstappen`, `norris`), so `5 + len(a) + 1 + len(b)` stays well under 64.
Implementation MUST assert this bound when building Step-2 buttons; if any driver
pairing would exceed it, that is a hard error to surface, not silently truncate.

### Guarding against A == B

Step 2's grid must **exclude driver A** (can't compare a driver to themselves).
Filter A's `driver_id` out of the Step-2 driver list.

## Failure modes & empty-data handling

Every season *starts* in a low-data state (no completed rounds), and individual
rounds may be only partially synced. The aggregation must degrade gracefully
rather than crash or render a misleading all-zero table.

- **A `get_*_results()` call returning `None`** (round/session not yet synced, or
  no sprint that weekend) is **skipped** as if that session doesn't exist. Never
  iterate over `None`.
- **Zero comparable sessions** (pre-season, or both drivers lack any race/sprint
  data): do **not** render a 0–0 table (which would read as a genuine "tied 0:0").
  Instead show an explicit message such as
  `本賽季尚無足夠比賽資料可供對決，請待首場比賽後再試`, with the `🔙 重新比較`
  button. The same message applies if `get_driver_standings` is empty.
- **Standings present but a driver missing from them** (rare mid-season data lag):
  treat that driver's points as unavailable and show `—` for the Points row while
  still rendering the H2H/count rows that *are* computable.

## Data & implementation notes

- **Driver list source:** `Repository.get_drivers_map(season)` returns
  `{driver_id: Driver}` but **includes `openf1_*`-prefixed synthetic ids**. The
  grid MUST filter these out (`not driver_id.startswith("openf1_")`) so each real
  driver appears once. Reuse the 2-column chunking from
  `extras.py:_driver_menu_keyboard` (build a `cmp:`-prefixed variant rather than
  reusing the `drv:detail:` one).
- **Fuzzy match not needed** in the no-args UI flow — selection is by button, so
  `match_driver()` is not called by `/compare`.
- **Aggregation is pure Python** over the per-round result **dicts**. Loop the
  completed rounds (from `get_schedule_bounds`); for each round read the race
  results and — where present — the sprint results, tallying each session
  independently. Access fields as dict keys (`r["position"]`, `r["status"]`,
  `r["driver"]["driver_id"]`), per the data-shape note above.
- **Markdown:** escape driver display names with `_esc()`
  (`formatting/messages.py:21`); the codebase uses legacy `ParseMode.MARKDOWN`
  only. Put the formatter (`format_driver_comparison`) in
  `formatting/messages.py` alongside the others.
- **Callback parse guards:** wrap any `parts[N]` access / int conversion in
  `try/except (ValueError, IndexError)` returning "Invalid selection", per the
  codebase convention for spoofed/malformed callbacks. This is also what catches a
  stale button whose driver id no longer resolves (see the stale-keyboard
  non-goal).
- **`query.answer()` discipline:** answer the callback exactly once per handler
  invocation; do not delegate to a helper that also answers.

## Output format

A single static message, two-column text comparison, with a scope footnote.
Sketch:

```
🆚 *Verstappen*  vs  *Norris*

Points     310  ─  241      (+69)
Quali H2H    8  ─   6
Race+Spr     9  ─   5
Wins         7  ─   3
Podiums     11  ─   9
DNFs         1  ─   2

* 含衝刺賽 (incl. sprint)
```

Followed by a single inline button: `[🔙 重新比較]` → `cmp:list`.

When there is no comparable data, the table is replaced entirely by the
empty-data message from "Failure modes" above (still with the `🔙 重新比較`
button).

## Files touched

| File | Change |
|---|---|
| `src/f1_bot/handlers/compare.py` | **New.** `/compare` command handler + `cmp:*` callback handler + `register(app)` + `_compare_menu_keyboard`. Aggregates race + sprint results. |
| `src/f1_bot/formatting/messages.py` | Add `format_driver_comparison(a, b, stats)` (incl. the sprint footnote and the empty-data message). |
| `src/f1_bot/main.py` | Register the new handler in `_post_init` command setup. |
| `CLAUDE.md` | Add `/compare` to the command table + a `cmp:*` row in the callback-format table. |
| `README.md` | Add `/compare` to the feature table. |
| `tests/test_handlers/test_compare.py` | **New.** Unit tests (see below). |

## Testing approach

Unit tests (no network; dev PostgreSQL via `repo` fixture where needed, else
mocked). Each test encodes *why* the behavior matters, not just what:

- **DNF classification:** `status="Accident"` counts as DNF; `status="+1 Lap"`
  counts as finished. Guards the whitelist rule against regression to a blacklist
  that would misclassify unseen strings.
- **Sprint is included:** a driver's sprint win / sprint DNF is reflected in Wins /
  DNFs and in Race+Sprint H2H — proving the scope is combined, not race-only.
- **H2H counts per session:** a weekend with both a race and a sprint can add 2 to
  the H2H tally, not 1.
- **Single-DNF H2H:** driver A finishes, driver B retires → A wins that session's
  H2H (position-ahead rule with one DNF).
- **Both-DNF excluded:** a session where both drivers DNF contributes 0 to either
  side's H2H.
- **H2H skips absent sessions:** a session where only one driver has a result is
  excluded from both tallies.
- **Qualifying H2H gate:** a round where only one driver has a quali result adds 0
  to the quali tally — guards the "both must have a result" gate on the one branch
  that has *no* DNF fallback, so it must not be conflated with the race H2H rule.
- **Podium boundary:** `position == 3` counts as a podium, `position == 4` does
  not — pins the `<= 3` edge so a `< 3` slip is caught.
- **Empty-data message:** zero completed rounds (or empty standings) yields the
  explicit "no data yet" message, **not** an all-zero table.
- **`None` session skipped:** a round whose `get_race_results` (or
  `get_sprint_results`) returns `None` is stepped over without raising — proves the
  aggregator never iterates `None` in the partial-sync / no-sprint case.
- **Missing-from-standings driver:** a driver absent from `get_driver_standings`
  (but with race data) renders `—` on the Points row while the H2H/count rows still
  compute — the mid-season data-lag path, distinct from the whole-table empty case.
- **A == B excluded:** Step-2 grid never contains driver A.
- **`openf1_*` filtered:** synthetic driver ids never appear as buttons.
- **Callback guards:** malformed `cmp:b:` payload → "Invalid selection", no crash.
- **64-byte bound:** the longest realistic driver pairing produces `callback_data`
  under 64 bytes.
- **Points gap:** gap equals the absolute points difference from standings.
- **Markdown escaping:** a driver display name containing `_` is passed through
  `_esc()` before rendering — guards against an unescaped underscore breaking the
  legacy `MARKDOWN` parse (per the ParseMode convention; use a name with a special
  char in the fixture, never a clean one).
- **Single answer:** the `cmp:*` callback calls `query.answer()` exactly once per
  invocation — guards the known PTB double-answer footgun.
- **Happy path (one smoke test):** `cmp:a` → `cmp:b` walks Step 1 → Step 2 → result
  and renders a populated table — confirms the three stateless steps thread the ids
  correctly end-to-end. One test only; the intermediate invariants (A==B exclusion,
  `openf1_*` filtering) are already covered separately above.

## Trade-offs considered

- **UI-only vs. arg-based selection:** chose UI-only. Costs one-line-power-user
  convenience; buys a simpler stateless handler and fewer error paths. Aligns
  with the user's explicit choice.
- **Combined race+sprint vs. race-only scope:** chose combined, with a footnote.
  Rejected the original draft's implicit mix (points included sprint, everything
  else didn't) — that was an unlabeled inconsistency. One consistent scope, made
  explicit, beats a partial exception.
- **H2H per session vs. per round:** chose per session, consistent with the
  combined scope. A DNF by one driver still counts (finishing is part of the
  contest); a mutual DNF is excluded (retirement order is not competitive signal).
- **Static message vs. round-navigable:** chose static. A season aggregate has no
  per-round paging semantic; navigation would be conceptual noise.
- **Whitelist vs. blacklist for DNF:** chose whitelist ("Finished"/"+N Lap" =
  finished). Robust to novel failure strings.
