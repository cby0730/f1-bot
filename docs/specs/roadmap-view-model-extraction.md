# Roadmap — view-model extraction (handler ↔ rendering split)

**Status:** Blueprint / deferred — NOT approved for implementation
**Type:** Architecture roadmap (future sub-project)
**Date:** 2026-07-30
**Depends on:** Spec 005 (i18n) landed first

> **This is a blueprint, not an implementable spec.** It records intent,
> ordering, and dependencies so the direction survives across sessions. It
> **deliberately omits file-level and function-level detail** — those decisions
> must be made against a *second* real platform (see
> `roadmap-line-adapter.md`), not designed speculatively against Telegram alone.
> Writing them now would bake in Telegram-shaped assumptions and get redesigned.
> When this work actually starts, it graduates into its own numbered spec
> (`docs/specs/NNN-…`) with full detail.

## The goal

Today each handler does three things in one place:

1. **Read the request** — pull parameters out of a Telegram `Update` / callback.
2. **Produce data** — call `Repository` / business logic, aggregate results.
3. **Render + reply** — format strings and send via the Telegram API.

Steps 1 and 3 are Telegram-specific; step 2 is platform-agnostic but currently
entangled with them. The goal is to extract step 2 into **platform-agnostic
functions that return a view-model** — a plain data structure (dataclass / dict)
describing *what to show*, containing **no platform types and no final strings** —
so that any platform adapter can consume the same view-model and render it its own
way.

```
handler (platform)          core service (agnostic)        adapter (platform)
  read Update      ──▶   produce_next_race_view(repo,…)  ──▶   render + reply
                          → returns NextRaceView (data)
```

## Why deferred (not part of i18n)

- **Bigger than i18n and touches every handler.** i18n purifies the presentation
  layer (strings) and preference layer (language); this splits the *control flow*
  of every command. Bundling them would make Spec 005's diff unreviewable.
- **YAGNI until a second platform exists.** With only Telegram live, the
  view-model boundary has nothing to validate it. A boundary designed against one
  consumer reliably encodes that consumer's assumptions. The right time is when
  the LINE adapter is being built, so two real consumers pin the shape.

## What i18n (Spec 005) already lays down

The hardest groundwork is done by Spec 005 so this refactor is cheaper later:

- **`t(key, lang, **kwargs) -> str`** is already platform-agnostic and
  language-aware — the rendering half of the split has a clean, reusable core.
- **`RenderContext(lang, tz)`** is the minimal seam that a view-model renderer
  consumes; it already flows through the presentation layer.
- **Language/preference resolution** is already isolated in a platform-specific
  helper (`resolve_context`), which is exactly where step 1 (read the request)
  will consolidate.

## Rough ordering (when it starts)

1. Pick **one** command as a vertical slice (e.g. `/next`). Define its view-model
   as plain data. Extract a `produce_*_view` core function; leave rendering in the
   handler but fed by the view-model.
2. Validate the boundary against the LINE adapter's needs (this is why it waits
   for LINE). Adjust the view-model shape with two real consumers.
3. Roll the pattern across the remaining commands, one slice at a time — each
   independently verifiable, matching the codebase's incremental style.
4. Land a probable new package for the agnostic services (e.g. `core/` or
   `services/`) — **decided then**, not now.

## Open questions (resolve at implementation time, with LINE in hand)

- View-model granularity: one type per command, or shared composable pieces?
- Where do inline-keyboard/button *intents* live — in the view-model as abstract
  actions, rendered per platform? (LINE has no inline keyboards; it has quick
  replies / flex messages — the abstraction must not assume Telegram buttons.)
- Does the agnostic service layer get its own package, or live beside handlers?

## Relationship to other specs

- **Requires:** Spec 005 (i18n) — provides the agnostic rendering core + seam.
- **Enables / co-designed with:** `roadmap-line-adapter.md` — the second platform
  that validates the view-model boundary.
- **Memory:** `project_f1bot_platform_decouple` (hexagonal architecture intent).
