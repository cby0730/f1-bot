"""Notification handler: 🔔 Remind Me flow + /remind management."""

from collections import defaultdict
from datetime import UTC, datetime, timedelta

import structlog
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from f1_bot.formatting.messages import _esc
from f1_bot.models.notification import TIMING_PRESETS, NotificationSubscription
from f1_bot.scheduler.notification_sender import schedule_next_notification
from f1_bot.utils.sessions import SESSION_LABELS, find_next_sessions

log = structlog.get_logger(__name__)

MAX_REMINDERS = 20


# ---------------------------------------------------------------------------
# Shared rendering helpers (no query.answer — caller owns that)
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


async def _build_remind_view(
    repo, telegram_id: int, *, target_round: int | None = None
) -> tuple[str, InlineKeyboardMarkup | None]:
    """Build the /remind view (text + keyboard).

    Returns State A (overview by round) or State B (single-round detail).
    Auto-skips to State B when all reminders belong to one round.
    Pass target_round to force State B for a specific round.
    """
    season = datetime.now(UTC).year
    subs = await repo.get_user_notifications(telegram_id, season)

    if not subs:
        return "🔔 You have no active reminders.\n\nUse /next and tap 🔔 to set one.", None

    races = await repo.get_schedule(season)
    race_map = {r.round: r for r in races}

    by_round: dict[int, list[NotificationSubscription]] = defaultdict(list)
    for sub in subs:
        by_round[sub.round].append(sub)

    rounds = sorted(by_round)
    single_round = len(rounds) == 1

    if target_round is not None or single_round:
        rnd = target_round if target_round is not None else rounds[0]
        round_subs = by_round.get(rnd, [])
        if not round_subs:
            return await _build_remind_view(repo, telegram_id)

        race = race_map.get(rnd)
        race_name = _esc(race.name) if race else f"Round {rnd}"
        text = f"🔔 *R{rnd} — {race_name}*"

        rows = []
        for sub in sorted(round_subs, key=lambda s: s.fire_at):
            label = SESSION_LABELS.get(sub.session_key, sub.session_key)
            time_label = TIMING_PRESETS.get(sub.minutes_before, f"{sub.minutes_before}min")
            rows.append(
                [
                    InlineKeyboardButton(
                        f"🗑 {label} — {time_label}",
                        callback_data=f"notify:del:{sub.id}:{rnd}",
                    )
                ]
            )
        if not single_round:
            rows.append([InlineKeyboardButton("🔙 Back", callback_data="notify:back")])

        return text, InlineKeyboardMarkup(rows)

    # State A: overview by round
    text = "🔔 *Your Active Reminders*"
    rows = []
    for rnd in rounds:
        race = race_map.get(rnd)
        race_name = _esc(race.name) if race else f"Round {rnd}"
        count = len(by_round[rnd])
        rows.append(
            [
                InlineKeyboardButton(
                    f"🔔 R{rnd} — {race_name} ({count})",
                    callback_data=f"notify:list:{rnd}",
                )
            ]
        )
    rows.append([InlineKeyboardButton("🗑 Clear All", callback_data="notify:clearall:confirm")])

    return text, InlineKeyboardMarkup(rows)


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

    if minutes not in TIMING_PRESETS:
        await query.answer("Invalid selection", show_alert=True)
        return

    repo = context.bot_data["repo"]
    season = datetime.now(UTC).year
    telegram_id = update.effective_user.id

    has = await repo.has_notification(telegram_id, season, round_num, session_key, minutes)
    time_label = TIMING_PRESETS.get(minutes, f"{minutes}min")

    if has:
        # Unsubscribe
        await repo.unsubscribe_notification(telegram_id, season, round_num, session_key, minutes)
        await query.answer(f"🔕 Reminder removed: {time_label}", show_alert=False)
    else:
        # Check cap
        subs = await repo.get_user_notifications(telegram_id, season)
        if len(subs) >= MAX_REMINDERS:
            await query.answer(
                f"⚠️ Limit reached ({MAX_REMINDERS}). Remove some with /remind first.",
                show_alert=True,
            )
            return

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
    telegram_id = update.effective_user.id

    text, keyboard = await _build_remind_view(repo, telegram_id)

    await update.effective_message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard,
    )


# ---------------------------------------------------------------------------
# /remind State A → State B (drill into a round)
# ---------------------------------------------------------------------------


async def _notify_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show per-reminder delete buttons for a specific round (State B)."""
    query = update.callback_query

    parts = query.data.split(":")
    try:
        round_num = int(parts[2])
    except (ValueError, IndexError):
        await query.answer("Invalid selection", show_alert=True)
        return

    repo = context.bot_data["repo"]
    telegram_id = update.effective_user.id

    text, keyboard = await _build_remind_view(repo, telegram_id, target_round=round_num)

    try:
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard,
        )
    except BadRequest:
        pass
    await query.answer()


# ---------------------------------------------------------------------------
# Delete individual reminder
# ---------------------------------------------------------------------------


async def _notify_del(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Delete a single reminder and refresh the view."""
    query = update.callback_query

    parts = query.data.split(":")
    try:
        notification_id = int(parts[2])
        round_num = int(parts[3])
    except (ValueError, IndexError):
        await query.answer("Invalid selection", show_alert=True)
        return

    repo = context.bot_data["repo"]
    telegram_id = update.effective_user.id

    deleted = await repo.unsubscribe_notification_by_id(notification_id, telegram_id)
    if not deleted:
        await query.answer("Reminder not found", show_alert=True)
        return

    await query.answer("🗑 Reminder removed", show_alert=False)

    # Reschedule
    jq = context.application.job_queue
    await schedule_next_notification(jq, repo)

    # Stay in State B for the same round (auto-skip handles empty round → State A)
    text, keyboard = await _build_remind_view(repo, telegram_id, target_round=round_num)

    try:
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard,
        )
    except BadRequest:
        pass


# ---------------------------------------------------------------------------
# Back to State A from State B
# ---------------------------------------------------------------------------


async def _notify_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Return to the remind overview (State A)."""
    query = update.callback_query

    repo = context.bot_data["repo"]
    telegram_id = update.effective_user.id

    text, keyboard = await _build_remind_view(repo, telegram_id)

    try:
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard,
        )
    except BadRequest:
        pass
    await query.answer()


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
        repo = context.bot_data["repo"]
        telegram_id = update.effective_user.id

        text, keyboard = await _build_remind_view(repo, telegram_id)
        try:
            await query.edit_message_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=keyboard,
            )
        except BadRequest:
            pass


def register(app: Application) -> None:
    app.add_handler(CommandHandler("remind", _remind_command))
    app.add_handler(CallbackQueryHandler(_notify_pick, pattern=r"^notify:pick:"))
    app.add_handler(CallbackQueryHandler(_notify_sess, pattern=r"^notify:sess:"))
    app.add_handler(CallbackQueryHandler(_notify_set, pattern=r"^notify:set:"))
    app.add_handler(CallbackQueryHandler(_notify_list, pattern=r"^notify:list:"))
    app.add_handler(CallbackQueryHandler(_notify_del, pattern=r"^notify:del:"))
    app.add_handler(CallbackQueryHandler(_notify_back, pattern=r"^notify:back"))
    app.add_handler(CallbackQueryHandler(_notify_clearall, pattern=r"^notify:clearall:"))
