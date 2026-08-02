# Handlers

Every handler resolves the caller's language + timezone **once** via
`await resolve_context(update, repo)` (`handlers/context.py`) and threads the
resulting `RenderContext(lang, tz)` into the formatters. Handlers never hold
user-facing literals — all text goes through `t(key, ctx.lang, **kwargs)`.

## Commands (16 total)

| Command | Handler file |
|---|---|
| `/start`, `/help` | `handlers/start.py` |
| `/next` | `handlers/schedule.py` — unified entry for next session |
| `/schedule`, `/countdown` | `handlers/schedule.py` |
| `/results` | `handlers/results.py` — unified entry for all results |
| `/pitstops`, `/laps` | `handlers/race_data.py` |
| `/standings` | `handlers/standings.py` |
| `/title` | `handlers/title.py` — WDC + WCC championship clinch analysis (magic number / 🔒 CLINCHED); WDC/WCC toggle, current-season, SQL-only |
| `/driver`, `/circuit` | `handlers/extras.py` — profile/info with fuzzy matching; interactive menu if run without arguments |
| `/compare` | `handlers/compare.py` — two-driver head-to-head; UI-only selection, current-season, race+sprint combined |
| `/timezone` | `handlers/timezone.py` |
| `/language` | `handlers/language.py` — single-level `en` / `zh-Hant` picker; also accepts `/language zh-Hant` |
| `/remind` | `handlers/notifications.py` — view/manage session reminders |

## Callback data formats

| Pattern | Meaning |
|---|---|
| `next:filtered:{filter}:{round}` | `/next` State B — filter ∈ {fp1, fp2, fp3, qualifying, sprint_qualifying, sprint, race} |
| `next:back:_:{round}` | `/next` return to State A |
| `res:filtered:{session_key}:{round}` | `/results` State B — session_key ∈ {race, qualifying, sprint, fp1, fp2, fp3, sprint_qualifying, all} |
| `res:back:_:{round}` | `/results` return to State A |
| `pit:{round}` | Pit stops round navigation |
| `lap:{round}:s` / `lap:{round}:l:{lap_num}` / `lap:{round}:dp` / `lap:{round}:d:{driver_id}:{page}` | Laps navigation (summary / per-lap / driver picker / per-driver, paginated by 20) |
| `notify:pick:{round}` | Notification session picker |
| `notify:sess:{session_key}:{round}` | Notification timing presets |
| `notify:set:{minutes}:{session_key}:{round}` | Toggle subscription on/off |
| `notify:list:{round}` | List user's reminders for a round |
| `notify:del:{id}:{round}` | Delete a single reminder |
| `notify:back` | Return to reminder overview |
| `notify:clearall:{action}` | Clear all reminders (confirm/yes/cancel) |
| `cmp:a:{driver_id}` / `cmp:b:{a_id}:{b_id}` / `cmp:list` | `/compare` — pick A / pick B + compute / restart |
| `drv:detail:{driver_id}` / `drv:list` | Driver profile navigation |
| `circ:detail:{circuit_id}` / `circ:list` | Circuit info navigation |
| `tz:region:{region}` / `tz:set:{timezone}` | Timezone picker navigation (region is a stable slug — `asia`/`europe`/`americas`/`other`; `__back__` returns to continent menu) |
| `lang:picker` | Open the language picker (emitted by `/start`'s persistent `🌐 Language / 語言` button) |
| `lang:set:{code}` | Set language; `code` ∈ `SHIPPED_LANGS` (`en`, `zh-Hant`), validated — unknown code answers "Invalid selection" and writes nothing |
| `standings:wdc` / `standings:wcc` | Standings WDC/WCC toggle |
| `title:wdc` / `title:wcc` | `/title` WDC/WCC clinch-analysis toggle |
| `rpk:{origin}:{round}` | Round picker overlay — `origin` ∈ {`nb`, `nf:{filter}`, `rb`, `rf:{session_key}`, `pit`, `lap`} encodes the caller so it can return to the right view. Emitted by `pagination.py` as the round-counter center button whenever a nav row spans >1 round |
