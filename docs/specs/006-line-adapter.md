# Spec 006 — LINE adapter (transport bridge)

**Status:** Implemented
**Date:** 2026-10-16
**Supersedes (for now):** `roadmap-line-adapter.md` ordering step 1 — see "Why a bridge, not the view-model refactor first"

## Goal

Serve the same bot on LINE alongside Telegram, from one process, with feature
parity on day one: every command, every button flow, reminders, language and
timezone preferences.

## Approach

LINE events are translated into the `telegram.Update` the equivalent Telegram
interaction would have produced, and run through the **same** PTB `Application`
and the **same** handlers. The handlers are not modified.

```
LINE webhook ─▶ verify X-Line-Signature ─▶ LineBridge.handle_event(event)
                                             │  text "/standings" → command Update
                                             │  postback "standings:wcc" → CallbackQuery Update
                                             ▼
                          app.process_update(update)   ← unchanged handlers
                                             │  update bound to _RecordingBot, not the Telegram bot
                                             ▼
                     recorded reply_text / edit_message_text / answer(show_alert)
                                             ▼
                     render: Markdown → plain text, InlineKeyboard → Flex buttons
                                             ▼
                          one LINE reply call (reply tokens are single-use)
```

This works because every handler talks to Telegram **only** through the
`Update` it receives (`update.effective_message.reply_text`,
`query.edit_message_text`, `query.answer`) — never `context.bot`. PTB binds those
shortcuts to whatever bot the `Update` was deserialised with, so binding a
recorder captures all output without touching handler code.

### Why a bridge, not the view-model refactor first

`roadmap-view-model-extraction.md` would rewrite the control flow of all ~2.8k
lines of handlers before LINE could show a single message, with every regression
landing on the live Telegram bot. The bridge reaches parity with zero handler
changes and confines LINE knowledge to `src/f1_bot/line/`. The view-model work
stays open: if LINE-specific UX later outgrows "Telegram flow rendered on LINE",
the bridge is the single seam to replace, and LINE now exists as the second
consumer that roadmap was waiting for.

## Mapping rules

| Telegram | LINE |
|---|---|
| `/command` text | Text message. Leading `/` optional, case-insensitive (`next`, `/Next`). Anything else → `/start` menu |
| — | `follow` event (user adds the bot) → `/start` |
| — | `unfollow` (user blocks the bot) → delete their reminders (`remove_dead_user`), the LINE equivalent of the sender's `Forbidden` path |
| Inline keyboard button | Flex bubble, one horizontal box per keyboard row, postback buttons. `callback_data` is reused verbatim as postback `data` (64 B ≤ LINE's 300) |
| `edit_message_text` | A **new** message — LINE cannot edit sent messages |
| `answer(text=…)` (alert / toast) | A text message; a bare `answer()` produces nothing |
| `ParseMode.MARKDOWN` | Markup stripped (`*`, `_`, backticks, code fences, `\` escapes). `[label](url)` → `label: url` |

Limits enforced in rendering (verified against `/v2/bot/message/validate/reply`):
button label ≤ 40 chars, `altText` ≤ 400, text ≤ 5000, ≤ 5 messages per reply.

## Identity

Handlers key everything on an integer `effective_user.id`. LINE user ids are
strings (`U` + 32 hex), so `line_users` maps each one to an internal id from a
**descending identity starting at -1**. Telegram user ids are always positive,
so the two never collide in `user_preferences` / `notification_subscriptions`,
and no existing table or repository signature changes. The notification sender
routes `telegram_id < 0` to LINE push.

## Default language

Per the roadmap's locked decision, LINE defaults to `zh-Hant`. It is written as
the user's preference the first time a LINE user is seen (when the `line_users`
row is created), so `resolve_context`, the notification sender and `/settings`
all read it through the existing DB-preference layer with no platform branch.

## Configuration

| Env var | Default | Notes |
|---|---|---|
| `LINE_CHANNEL_SECRET` | unset | Verifies webhook signatures |
| `LINE_CHANNEL_ACCESS_TOKEN` | unset | Long-lived channel access token |
| `F1BOT_LINE_WEBHOOK_HOST` | `0.0.0.0` | |
| `F1BOT_LINE_WEBHOOK_PORT` | `8080` | Webhook path is `/line/webhook` |

LINE is enabled only when both secrets are set. `TELEGRAM_BOT_TOKEN` remains
required: the PTB `Application` is the shared runtime (handlers, JobQueue, error
handler) for both platforms. The channel ID is not needed at runtime.

## Deployment (outside this repo)

1. LINE requires an **HTTPS** webhook with a valid certificate. Terminate TLS on
   the VM (e.g. Caddy) or use a tunnel, forwarding to `127.0.0.1:8080`
   (published by `docker-compose.yml`).
2. LINE Developers console → Messaging API: set Webhook URL to
   `https://<host>/line/webhook`, enable **Use webhook**, press **Verify**.
3. LINE Official Account Manager: turn **off** auto-reply and greeting messages,
   otherwise LINE answers alongside the bot.

## Known limits

- **Push quota.** Replies are free; reminders are push messages, which count
  against the plan's monthly quota (200 on the free plan). Over quota, LINE
  answers 429 and the reminder follows the sender's existing retry-then-expire path.
- Every button tap appends a message instead of editing in place.
- Monospace tables (results, standings) render in LINE's proportional font, so
  columns do not align perfectly.
- No rich menu yet; entry is the `/start` button grid, re-shown for any
  unrecognised text.
