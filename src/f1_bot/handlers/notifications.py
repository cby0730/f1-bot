"""Notification handler: 🔔 Remind Me flow + /remind management."""

from datetime import UTC, datetime, timedelta

import structlog
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from f1_bot.formatting.messages import format_reminders_list
from f1_bot.models.notification import TIMING_PRESETS, NotificationSubscription
from f1_bot.scheduler.notification_sender import schedule_next_notification
from f1_bot.utils.sessions import SESSION_LABELS, find_next_sessions

log = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Shared rendering helper (no query.answer — caller owns that)
# ---------------------------------------------------------------------------


async def _render_timing_page(
    query, repo, session_key: str, round_num: int, telegram_id: int
) -> None:
    """Render the timing preset selection page (edit_message_text only)."""
    season = datetime.now(UTC).year
    rows = []
    for minutes, label in TIMING_PRESETS.items():
        has = await repo.has_notification(telegram_id, season, round_num, session_key, minutes)
        display = f"✅ {label}" if has else label
        rows.append(
            [
                InlineKeyboardButton(
                    display,
                    callback_data=f"notify:set:{minutes}:{session_key}:{round_num}",
                )
            ]
        )

    rows.append([InlineKeyboardButton("🔙 Back", callback_data=f"notify:pick:{round_num}")])

    session_label = SESSION_LABELS.get(session_key, session_key)
    try:
        await query.edit_message_text(
            f"🔔 *{session_label}* — Round {round_num}\n\nHow early do you want to be reminded?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(rows),
        )
    except BadRequest:
        pass


# ---------------------------------------------------------------------------
# Step 1: Pick session (from 🔔 button on /next)
# ---------------------------------------------------------------------------


async def _notify_pick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show session selection for a round."""
    query = update.callback_query

    parts = query.data.split(":")
    try:
        round_num = int(parts[2])
    except (ValueError, IndexError):
        await query.answer("Invalid selection", show_alert=True)
        return

    repo = context.bot_data["repo"]
    season = datetime.now(UTC).year
    races = await repo.get_schedule(season)
    race = next((r for r in races if r.round == round_num), None)
    if not race:
        await query.answer("Race not found", show_alert=True)
        return

    sessions = find_next_sessions([race], limit=20)
    if not sessions:
        await query.answer("No sessions available", show_alert=True)
        return

    seen_keys = set()
    rows = []
    for entry in sessions:
        key = entry.key
        if key in seen_keys:
            continue
        seen_keys.add(key)
        label = SESSION_LABELS.get(key, key)
        rows.append([InlineKeyboardButton(label, callback_data=f"notify:sess:{key}:{round_num}")])

    rows.append([InlineKeyboardButton("🔙 Back", callback_data=f"next:back:_:{round_num}")])

    try:
        await query.edit_message_text(
            f"🔔 *Select Session* — Round {round_num}\n\nWhich session do you want a reminder for?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(rows),
        )
    except BadRequest:
        pass
    await query.answer()


# ---------------------------------------------------------------------------
# Step 2: Pick timing preset
# ---------------------------------------------------------------------------


async def _notify_sess(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show timing preset selection for a session."""
    query = update.callback_query

    parts = query.data.split(":")
    try:
        session_key = parts[2]
        round_num = int(parts[3])
    except (ValueError, IndexError):
        await query.answer("Invalid selection", show_alert=True)
        return

    repo = context.bot_data["repo"]
    telegram_id = update.effective_user.id

    await _render_timing_page(query, repo, session_key, round_num, telegram_id)
    await query.answer()


# ---------------------------------------------------------------------------
# Step 3: Toggle subscription
# ---------------------------------------------------------------------------


async def _notify_set(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Toggle a notification subscription on/off."""
    query = update.callback_query

    parts = query.data.split(":")
    try:
        minutes = int(parts[2])
        session_key = parts[3]
        round_num = int(parts[4])
    except (ValueError, IndexError):
        await query.answer("Invalid selection", show_alert=True)
        return

    repo = context.bot_data["repo"]
    season = datetime.now(UTC).year
    telegram_id = update.effective_user.id

    has = await repo.has_notification(telegram_id, season, round_num, session_key, minutes)

    if has:
        # Unsubscribe
        await repo.unsubscribe_notification(telegram_id, season, round_num, session_key, minutes)
        time_label = TIMING_PRESETS.get(minutes, f"{minutes}min")
        await query.answer(f"🔕 Reminder removed: {time_label}", show_alert=False)
    else:
        # Subscribe: compute fire_at
        races = await repo.get_schedule(season)
        race = next((r for r in races if r.round == round_num), None)
        if not race:
            await query.answer("Race not found", show_alert=True)
            return

        sessions = find_next_sessions([race], limit=20)
        target = next((s for s in sessions if s.key == session_key), None)
        if not target:
            await query.answer("Session not found", show_alert=True)
            return

        fire_at = target.starts_at - timedelta(minutes=minutes)
        sub = NotificationSubscription(
            telegram_id=telegram_id,
            season=season,
            round=round_num,
            session_key=session_key,
            minutes_before=minutes,
            fire_at=fire_at,
        )
        await repo.subscribe_notification(sub)

        time_label = TIMING_PRESETS.get(minutes, f"{minutes}min")
        await query.answer(f"🔔 Reminder set: {time_label} before", show_alert=False)

    # Reschedule notification job
    jq = context.application.job_queue
    await schedule_next_notification(jq, repo)

    # Refresh the timing preset page (re-render with updated ✅)
    await _render_timing_page(query, repo, session_key, round_num, telegram_id)


# ---------------------------------------------------------------------------
# /remind command
# ---------------------------------------------------------------------------


async def _remind_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show all active reminders for the user."""
    repo = context.bot_data["repo"]
    season = datetime.now(UTC).year
    telegram_id = update.effective_user.id
    user_tz = await repo.get_user_timezone(telegram_id)

    subs = await repo.get_user_notifications(telegram_id, season)
    races = await repo.get_schedule(season)

    text = format_reminders_list(subs, races, user_tz)

    rows = []
    if subs:
        rows.append([InlineKeyboardButton("🗑 Clear All", callback_data="notify:clearall:confirm")])

    await update.effective_message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(rows) if rows else None,
    )


# ---------------------------------------------------------------------------
# Clear all confirmation
# ---------------------------------------------------------------------------


async def _notify_clearall(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle clear-all confirmation flow."""
    query = update.callback_query
    parts = query.data.split(":")

    action = parts[2] if len(parts) > 2 else ""

    if action == "confirm":
        await query.answer()
        rows = [
            [
                InlineKeyboardButton("✅ Yes, clear all", callback_data="notify:clearall:yes"),
                InlineKeyboardButton("❌ Cancel", callback_data="notify:clearall:cancel"),
            ]
        ]
        try:
            await query.edit_message_text(
                "🗑 *Are you sure?*\n\nThis will remove all your active reminders.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(rows),
            )
        except BadRequest:
            pass

    elif action == "yes":
        repo = context.bot_data["repo"]
        telegram_id = update.effective_user.id
        count = await repo.delete_all_user_notifications(telegram_id)
        await query.answer(f"Cleared {count} reminder(s)", show_alert=False)

        # Reschedule
        jq = context.application.job_queue
        await schedule_next_notification(jq, repo)

        try:
            await query.edit_message_text(
                "🔔 All reminders cleared.\n\nUse /next and tap 🔔 to set new ones.",
                parse_mode=ParseMode.MARKDOWN,
            )
        except BadRequest:
            pass

    elif action == "cancel":
        await query.answer("Cancelled", show_alert=False)
        # Re-show reminders
        repo = context.bot_data["repo"]
        season = datetime.now(UTC).year
        telegram_id = update.effective_user.id
        user_tz = await repo.get_user_timezone(telegram_id)
        subs = await repo.get_user_notifications(telegram_id, season)
        races = await repo.get_schedule(season)
        text = format_reminders_list(subs, races, user_tz)
        rows = []
        if subs:
            rows.append(
                [InlineKeyboardButton("🗑 Clear All", callback_data="notify:clearall:confirm")]
            )
        try:
            await query.edit_message_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(rows) if rows else None,
            )
        except BadRequest:
            pass


def register(app: Application) -> None:
    app.add_handler(CommandHandler("remind", _remind_command))
    app.add_handler(CallbackQueryHandler(_notify_pick, pattern=r"^notify:pick:"))
    app.add_handler(CallbackQueryHandler(_notify_sess, pattern=r"^notify:sess:"))
    app.add_handler(CallbackQueryHandler(_notify_set, pattern=r"^notify:set:"))
    app.add_handler(CallbackQueryHandler(_notify_clearall, pattern=r"^notify:clearall:"))
