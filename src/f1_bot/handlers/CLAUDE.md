# Handlers

Every handler resolves the caller's language + timezone **once** via
`await resolve_context(update, repo)` (`handlers/context.py`) and threads the
resulting `RenderContext(lang, tz)` into the formatters. Handlers never hold
user-facing literals — all text goes through `t(key, ctx.lang, **kwargs)`.

## Commands (visible menu: 9; no hidden slash aliases)

| Command | Handler file |
|---|---|
| `/start` | `handlers/start.py` — short welcome + eight-button menu (`start:{command}`) |
| `/next` | `handlers/schedule.py` — weekend overview |
| `/schedule` | `handlers/schedule.py` |
| `/results` | `handlers/results.py` — State A also links Pit + Laps |
| `/standings` | `handlers/standings.py` — WDC/WCC table + 2-line clinch strip (two-clocks via `get_standings_round`) |
| `/driver`, `/circuit` | `handlers/extras.py` — interactive pickers over current-season data; driver profile has Compare |
| `/remind` | `handlers/notifications.py` — view/manage session reminders |
| `/settings` | `handlers/settings.py` — hub (`set:tz` / `set:lang` edit in place). Only language/timezone entry |

## Callback data formats

| Pattern | Meaning |
|---|---|
| `start:{command}` | `/start` menu — command ∈ {next, schedule, results, standings, driver, circuit, remind, settings}; replies a **new** message by calling the matching command handler |
| `next:filtered:{filter}:{round}` | `/next` State B — filter ∈ {fp1, fp2, fp3, qualifying, sprint_qualifying, sprint, race} |
| `next:back:_:{round}` | `/next` return to State A |
| `res:filtered:{session_key}:{round}` | `/results` State B — session_key ∈ {race, qualifying, sprint, fp1, fp2, fp3, sprint_qualifying, all} |
| `res:back:_:{round}` | `/results` return to State A |
| `pit:{round}` | Pit stops round navigation; Back is `res:back:_:{round}` |
| `lap:{round}:s` | Laps personal-best summary (stale `lap:{n}:l:…` / `:dp` / `:d:…` fall through to summary) |
| `notify:pick:{round}` | Notification session picker |
| `notify:sess:{session_key}:{round}` | Notification timing presets |
| `notify:set:{minutes}:{session_key}:{round}` | Toggle subscription on/off |
| `notify:list:{round}` | List user's reminders for a round |
| `notify:del:{id}:{round}` | Delete a single reminder |
| `notify:back` | Return to reminder overview |
| `notify:clearall:{action}` | Clear all reminders (confirm/yes/cancel) |
| `cmp:a:{driver_id}` / `cmp:b:{a_id}:{b_id}` | Compare from a driver profile — pick opponent / compute |
| `drv:detail:{driver_id}` / `drv:list` | Driver profile navigation (profile includes Compare → `cmp:a:{id}`) |
| `circ:detail:{circuit_id}` / `circ:list` | Circuit info navigation |
| `tz:region:{region}` / `tz:set:{timezone}` | Timezone picker navigation (region is a stable slug — `asia`/`europe`/`americas`/`other`; `__back__` returns to continent menu) |
| `set:tz` / `set:lang` | `/settings` hub — edit in place onto the timezone region menu / language picker |
| `lang:set:{code}` | Set language; `code` ∈ `SHIPPED_LANGS` (`en`, `zh-Hant`), validated — unknown code answers "Invalid selection" and writes nothing |
| `standings:wdc` / `standings:wcc` | Standings WDC/WCC toggle |
| `rpk:{origin}:{round}` | Round picker overlay — `origin` ∈ {`nb`, `nf:{filter}`, `rb`, `rf:{session_key}`, `pit`, `lap`} encodes the caller so it can return to the right view. Emitted by `pagination.py` as the round-counter center button whenever a nav row spans >1 round |
