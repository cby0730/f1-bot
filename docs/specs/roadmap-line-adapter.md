# Roadmap — LINE bot adapter

**Status:** Blueprint / deferred — NOT approved for implementation
**Type:** Architecture roadmap (future sub-project)
**Date:** 2026-07-30
**Depends on:** Spec 005 (i18n) + `roadmap-view-model-extraction.md`

> **This is a blueprint, not an implementable spec.** It records intent, why it's
> deferred, and which core layers get reused — so the direction survives across
> sessions. It **deliberately omits file-level detail**; the LINE messaging model
> (webhooks, flex messages, quick replies) must be designed against the real LINE
> Messaging API when work starts, not guessed now. When it starts, it graduates
> into its own numbered spec with full detail.

## The goal

Run the F1 bot on **LINE** in addition to Telegram, reusing the entire
platform-agnostic core (business logic, `Repository`, message catalog / `t()`)
and writing only a thin LINE-specific adapter. The stated intent: "one functional
core exposing all information; adapters only translate that into each platform's
UI — the only code that changes per platform is the adapter block." This is
textbook **hexagonal architecture (ports & adapters)**.

```
        platform-agnostic CORE + PRESENTATION (unchanged)
        business logic · Repository · i18n catalog · view-models
                 │                                  │
        ┌────────┴─────────┐              ┌─────────┴──────────┐
        │ Telegram adapter │              │   LINE adapter     │  ← this sub-project
        │ (existing)       │              │   (new)            │
        └──────────────────┘              └────────────────────┘
```

## Why deferred

- **Needs the view-model boundary first.** Reusing the core cleanly requires
  handlers' data-production to be split from Telegram rendering
  (`roadmap-view-model-extraction.md`). Until that exists, a LINE adapter would
  have to duplicate business logic or import Telegram handlers — both wrong.
- **It is the validating second platform.** The view-model extraction is
  co-designed with this adapter: LINE's very different UI model (no inline
  keyboards; flex messages / quick replies instead) is what proves the
  abstraction isn't Telegram-shaped.

## What the core already provides for reuse (thanks to Spec 005)

- **`t(key, lang, **kwargs) -> str`** — platform-agnostic, never imports
  `telegram`. LINE renders the same catalog strings unchanged.
- **`RenderContext(lang, tz)`** — carries the two per-user preferences; LINE
  populates it from a LINE-specific resolver.
- **Preference storage** — `user_preferences` keyed by a user id; LINE stores its
  own user id in the same table shape. `get_user_language` / `get_user_preference`
  work unchanged.

## Per-platform default language (a locked decision)

The default language is a **platform property**, passed into the resolver, never
a core constant (established in Spec 005):

- **Telegram** default: `en`.
- **LINE** default: `zh-Hant`.

LINE gets its own `resolve_context` equivalent:

- **DB preference > (LINE language signal, if any) > `zh-Hant`.**
- LINE's user-language signal is weaker/different from Telegram's
  `language_code`; the resolver design accounts for that when built. If LINE
  offers no reliable per-user UI-language hint, the chain is simply
  **DB preference > `zh-Hant`**.

## What the LINE adapter must supply (the adapter block)

Enumerated as scope, not design:

- **Transport:** LINE Messaging API webhook intake + reply/push (vs Telegram
  long-polling). A new entrypoint parallel to `main.py`.
- **User id + language resolution:** LINE `resolve_context` with `zh-Hant`
  default.
- **UI rendering:** map view-models → LINE message objects. Telegram inline
  keyboards have **no** direct LINE equivalent — button *intents* in the
  view-model render as LINE quick replies / flex message buttons. This mapping is
  the bulk of the adapter and the main design work.
- **Command model:** LINE has no `/command` menu or `set_my_commands`. Decide the
  LINE interaction entrypoint (rich menu / keyword messages) at design time.
- **Preference commands:** LINE-native equivalents of `/language` and `/timezone`.

## Explicitly NOT reused / NOT shared

- Telegram's `set_my_commands(language_code=…)` — Telegram-only; LINE has no
  equivalent (rich menu is the closest, designed separately).
- Telegram long-polling / `HTTPXRequest` setup.
- Inline-keyboard callback-data protocol — LINE's postback model differs; the
  view-model's abstract action intents are what carry over, not the `cb:` string
  formats.

## Rough ordering (when it starts)

1. Land `roadmap-view-model-extraction.md` (at least the slices LINE needs).
2. Build the LINE transport + `resolve_context` (default `zh-Hant`) + one command
   end-to-end as a vertical slice, to validate the view-model boundary.
3. Roll out remaining commands' LINE rendering, one slice at a time.
4. Decide LINE's command/menu entrypoint model.

## Relationship to other specs

- **Requires:** Spec 005 (i18n) and `roadmap-view-model-extraction.md`.
- **Memory:** `project_f1bot_platform_decouple` (hexagonal architecture intent,
  per-platform default language).
