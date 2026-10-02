# Formatting

The presentation layer: `t()`, the message catalog, and every formatter. This
file loads only when working under `formatting/`. The always-loaded rules —
no user-facing literals in feature code, and the load-bearing `/` in
`t(key, lang, /, **kwargs)` — stay in the root [`CLAUDE.md`](../../../CLAUDE.md).

**Guard C — why `formatting/` only, and why AST:** over half the catalog templates
carry Telegram Markdown markers, so an API string containing `_`/`*`/`` ` ``/`[`
interpolated into one either mis-renders or makes Telegram reject the message —
which handlers swallow via `except BadRequest: pass`, so the user sees nothing
happen. `handlers/` is deliberately **out of scope**: its free-text
interpolations feed inline-button labels and `answer(show_alert=True)` popups,
neither of which Telegram parses as Markdown, so escaping there would surface
literal backslashes. The guard follows escaping done at the assignment
(`title = _esc(race.name)` → `t(..., title=title)` passes) and treats `_esc`,
`t` and the `*_label` catalog helpers as safe. Add a kwarg name to
`FREE_TEXT_KWARGS` when a new template interpolates external text.

**`t()` failure modes are asymmetric by design:** an *unknown key* raises
`KeyError` (a programmer typo — loud), while a *known key missing one language*
falls back to the `en` template (a user must never see a raw key). The
`check_catalog_complete()` test is the merge gate; startup is deliberately **not**
gated, so a translation gap blocks merge without taking down a running bot.

**`strftime` is never used for weekday/month names:** those come from the
`datetime.*` catalog keys. `strftime` names depend on the process-global C
locale — not thread-safe under async and impossible to vary per user.
`format_dt(dt, tz_name, lang)` formats only the numeric parts with `strftime`.

**CJK monospace padding:** code-block tables pad labels with `_pad_display()`
(stdlib `unicodedata.east_asian_width`), not `{label:<10}`. Python field widths
count code points, but CJK glyphs occupy two display columns, so code-point
padding drifts the number columns on translated rows.
