# Handlers

Every handler resolves the caller's language + timezone **once** via
`await resolve_context(update, repo)` (`handlers/context.py`) and threads the
resulting `RenderContext(lang, tz)` into the formatters. Handlers never hold
user-facing literals — all text goes through `t(key, ctx.lang, **kwargs)`.

## Commands (visible menu: 9; hidden aliases stay registered)

| Command | Handler file |
|---|---|
| `/start` | `handlers/start.py` — welcome + language button |
| `/next` | `handlers/schedule.py` — weekend overview. `/countdown` is a hidden alias of `/next` |
| `/schedule` | `handlers/schedule.py` |
| `/results` | `handlers/results.py` — State A also links Pit + Laps |
| `/standings` | `handlers/standings.py` — WDC/WCC table + 2-line clinch strip (two-clocks via `get_standings_round`). `/title` is a hidden alias; stale `title:*` still renders this view |
| `/driver`, `/circuit` | `handlers/extras.py` — interactive pickers over current-season data; driver profile has Compare. `/compare` is a hidden alias that still opens pick-A |
| `/remind` | `handlers/notifications.py` — view/manage session reminders |
| `/settings` | `handlers/settings.py` — hub (`set:tz` / `set:lang` edit in place). `/timezone` and `/language` stay as pickers (typed args ignored) |
| `/pitstops`, `/laps` | `handlers/race_data.py` — also reachable from `/results`; Back returns to results State A |

## Callback data formats

| Pattern | Meaning |
|---|---|
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
| `cmp:a:{driver_id}` / `cmp:b:{a_id}:{b_id}` / `cmp:list` | `/compare` — pick A / pick B + compute / legacy pick-A restart |
| `drv:detail:{driver_id}` / `drv:list` | Driver profile navigation (profile includes Compare → `cmp:a:{id}`) |
| `circ:detail:{circuit_id}` / `circ:list` | Circuit info navigation |
| `tz:region:{region}` / `tz:set:{timezone}` | Timezone picker navigation (region is a stable slug — `asia`/`europe`/`americas`/`other`; `__back__` returns to continent menu) |
| `set:tz` / `set:lang` | `/settings` hub — edit in place onto the timezone region menu / language picker |
| `lang:picker` | Open the language picker as a *new* message (emitted by `/start`'s persistent `🌐 Language / 語言` button — do not reuse from `/settings`) |
| `lang:set:{code}` | Set language; `code` ∈ `SHIPPED_LANGS` (`en`, `zh-Hant`), validated — unknown code answers "Invalid selection" and writes nothing |
| `standings:wdc` / `standings:wcc` | Standings WDC/WCC toggle |
| `title:wdc` / `title:wcc` | Stale `/title` keyboards — render the standings view (new messages emit `standings:wdc` / `standings:wcc`) |
| `rpk:{origin}:{round}` | Round picker overlay — `origin` ∈ {`nb`, `nf:{filter}`, `rb`, `rf:{session_key}`, `pit`, `lap`} encodes the caller so it can return to the right view. Emitted by `pagination.py` as the round-counter center button whenever a nav row spans >1 round |
