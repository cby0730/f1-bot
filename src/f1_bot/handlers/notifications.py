"""Notification handler: 🔔 Remind Me flow + /remind management."""

from collections import defaultdict
from datetime import UTC, datetime, timedelta

import structlog
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from f1_bot.formatting.i18n import t
from f1_bot.formatting.messages import _esc
from f1_bot.handlers.context import resolve_context
from f1_bot.models.notification import TIMING_PRESETS, NotificationSubscription, timing_label
from f1_bot.scheduler.notification_sender import schedule_next_notification
from f1_bot.utils.sessions import find_next_sessions, session_label

log = structlog.get_logger(__name__)

MAX_REMINDERS = 20


# ---------------------------------------------------------------------------
# Shared rendering helpers (no query.answer — caller owns that)
# ---------------------------------------------------------------------------


async def _render_timing_page(
    query, repo, session_key: str, round_num: int, telegram_id: int, lang: str
) -> None:
    """Render the timing preset selection page (edit_message_text only)."""
    season = datetime.now(UTC).year
    rows = []
    for minutes in TIMING_PRESETS:
        has = await repo.has_notification(telegram_id, season, round_num, session_key, minutes)
        label = timing_label(minutes, lang)
        display = f"✅ {label}" if has else label
        rows.append(
            [
                InlineKeyboardButton(
                    display,
                    callback_data=f"notify:set:{minutes}:{session_key}:{round_num}",
                )
            ]
        )

    rows.append(
        [InlineKeyboardButton(t("common.back", lang), callback_data=f"notify:pick:{round_num}")]
    )

    try:
        await query.edit_message_text(
            t(
                "notifications.pick_timing",
                lang,
                session=session_label(session_key, lang),
                round=round_num,
            ),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(rows),
        )
    except BadRequest:
        pass


async def _build_remind_view(
    repo, telegram_id: int, lang: str, *, target_round: int | None = None
) -> tuple[str, InlineKeyboardMarkup | None]:
    """Build the /remind view (text + keyboard).

    Returns State A (overview by round) or State B (single-round detail).
    Auto-skips to State B when all reminders belong to one round.
    Pass target_round to force State B for a specific round.
    """
    season = datetime.now(UTC).year
    subs = await repo.get_user_notifications(telegram_id, season)

    if not subs:
        return t("notifications.none_active", lang), None

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
            return await _build_remind_view(repo, telegram_id, lang)

        race = race_map.get(rnd)
        race_name = _esc(race.name) if race else t("notifications.round_btn", lang, round=rnd)
        text = t("notifications.round_header", lang, round=rnd, name=race_name)

        rows = []
        for sub in sorted(round_subs, key=lambda s: s.fire_at):
            rows.append(
                [
                    InlineKeyboardButton(
                        t(
                            "notifications.delete_btn",
                            lang,
                            session=session_label(sub.session_key, lang),
                            timing=timing_label(sub.minutes_before, lang),
                        ),
                        callback_data=f"notify:del:{sub.id}:{rnd}",
                    )
                ]
            )
        if not single_round:
            rows.append([InlineKeyboardButton(t("common.back", lang), callback_data="notify:back")])

        return text, InlineKeyboardMarkup(rows)

    # State A: overview by round
    text = t("notifications.list_header", lang)
    rows = []
    for rnd in rounds:
        race = race_map.get(rnd)
        race_name = _esc(race.name) if race else t("notifications.round_btn", lang, round=rnd)
        count = len(by_round[rnd])
        rows.append(
            [
                InlineKeyboardButton(
                    t(
                        "notifications.round_count_btn",
                        lang,
                        round=rnd,
                        name=race_name,
                        count=count,
                    ),
                    callback_data=f"notify:list:{rnd}",
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                t("notifications.clear_all_btn", lang), callback_data="notify:clearall:confirm"
            )
        ]
    )

    return text, InlineKeyboardMarkup(rows)


# ---------------------------------------------------------------------------
# Step 1: Pick session (from 🔔 button on /next)
# ---------------------------------------------------------------------------


async def _notify_pick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show session selection for a round."""
    query = update.callback_query
    repo = context.bot_data["repo"]
    ctx = await resolve_context(update, repo)

    parts = query.data.split(":")
    try:
        round_num = int(parts[2])
    except (ValueError, IndexError):
        await query.answer(t("common.invalid_selection", ctx.lang), show_alert=True)
        return

    season = datetime.now(UTC).year
    races = await repo.get_schedule(season)
    race = next((r for r in races if r.round == round_num), None)
    if not race:
        await query.answer(t("common.race_not_found", ctx.lang), show_alert=True)
        return

    sessions = find_next_sessions([race], limit=20)
    if not sessions:
        await query.answer(t("notifications.no_sessions", ctx.lang), show_alert=True)
        return

    seen_keys = set()
    rows = []
    for entry in sessions:
        key = entry.key
        if key in seen_keys:
            continue
        seen_keys.add(key)
        rows.append(
            [
                InlineKeyboardButton(
                    session_label(key, ctx.lang), callback_data=f"notify:sess:{key}:{round_num}"
                )
            ]
        )

    rows.append(
        [InlineKeyboardButton(t("common.back", ctx.lang), callback_data=f"next:back:_:{round_num}")]
    )

    try:
        await query.edit_message_text(
            t("notifications.pick_session", ctx.lang, round=round_num),
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
    repo = context.bot_data["repo"]
    ctx = await resolve_context(update, repo)

    parts = query.data.split(":")
    try:
        session_key = parts[2]
        round_num = int(parts[3])
    except (ValueError, IndexError):
        await query.answer(t("common.invalid_selection", ctx.lang), show_alert=True)
        return

    telegram_id = update.effective_user.id

    await _render_timing_page(query, repo, session_key, round_num, telegram_id, ctx.lang)
    await query.answer()


# ---------------------------------------------------------------------------
# Step 3: Toggle subscription
# ---------------------------------------------------------------------------


async def _notify_set(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Toggle a notification subscription on/off."""
    query = update.callback_query
    repo = context.bot_data["repo"]
    ctx = await resolve_context(update, repo)

    parts = query.data.split(":")
    try:
        minutes = int(parts[2])
        session_key = parts[3]
        round_num = int(parts[4])
    except (ValueError, IndexError):
        await query.answer(t("common.invalid_selection", ctx.lang), show_alert=True)
        return

    if minutes not in TIMING_PRESETS:
        await query.answer(t("common.invalid_selection", ctx.lang), show_alert=True)
        return

    season = datetime.now(UTC).year
    telegram_id = update.effective_user.id

    has = await repo.has_notification(telegram_id, season, round_num, session_key, minutes)
    time_label = timing_label(minutes, ctx.lang)

    if has:
        # Unsubscribe
        await repo.unsubscribe_notification(telegram_id, season, round_num, session_key, minutes)
        await query.answer(
            t("notifications.removed", ctx.lang, timing=time_label), show_alert=False
        )
    else:
        # Check cap
        subs = await repo.get_user_notifications(telegram_id, season)
        if len(subs) >= MAX_REMINDERS:
            await query.answer(
                t("notifications.limit_reached", ctx.lang, max=MAX_REMINDERS),
                show_alert=True,
            )
            return

        # Subscribe: compute fire_at
        races = await repo.get_schedule(season)
        race = next((r for r in races if r.round == round_num), None)
        if not race:
            await query.answer(t("common.race_not_found", ctx.lang), show_alert=True)
            return

        sessions = find_next_sessions([race], limit=20)
        target = next((s for s in sessions if s.key == session_key), None)
        if not target:
            await query.answer(t("notifications.session_not_found", ctx.lang), show_alert=True)
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

        await query.answer(t("notifications.set", ctx.lang, timing=time_label), show_alert=False)

    # Reschedule notification job
    jq = context.application.job_queue
    await schedule_next_notification(jq, repo)

    # Refresh the timing preset page (re-render with updated ✅)
    await _render_timing_page(query, repo, session_key, round_num, telegram_id, ctx.lang)


# ---------------------------------------------------------------------------
# /remind command
# ---------------------------------------------------------------------------


async def _remind_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show all active reminders for the user."""
    repo = context.bot_data["repo"]
    ctx = await resolve_context(update, repo)
    telegram_id = update.effective_user.id

    text, keyboard = await _build_remind_view(repo, telegram_id, ctx.lang)

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
    repo = context.bot_data["repo"]
    ctx = await resolve_context(update, repo)

    parts = query.data.split(":")
    try:
        round_num = int(parts[2])
    except (ValueError, IndexError):
        await query.answer(t("common.invalid_selection", ctx.lang), show_alert=True)
        return

    telegram_id = update.effective_user.id

    text, keyboard = await _build_remind_view(repo, telegram_id, ctx.lang, target_round=round_num)

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
    repo = context.bot_data["repo"]
    ctx = await resolve_context(update, repo)

    parts = query.data.split(":")
    try:
        notification_id = int(parts[2])
        round_num = int(parts[3])
    except (ValueError, IndexError):
        await query.answer(t("common.invalid_selection", ctx.lang), show_alert=True)
        return

    telegram_id = update.effective_user.id

    deleted = await repo.unsubscribe_notification_by_id(notification_id, telegram_id)
    if not deleted:
        await query.answer(t("notifications.not_found", ctx.lang), show_alert=True)
        return

    await query.answer(t("notifications.removed_toast", ctx.lang), show_alert=False)

    # Reschedule
    jq = context.application.job_queue
    await schedule_next_notification(jq, repo)

    # Stay in State B for the same round (auto-skip handles empty round → State A)
    text, keyboard = await _build_remind_view(repo, telegram_id, ctx.lang, target_round=round_num)

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
    ctx = await resolve_context(update, repo)
    telegram_id = update.effective_user.id

    text, keyboard = await _build_remind_view(repo, telegram_id, ctx.lang)

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
    repo = context.bot_data["repo"]
    ctx = await resolve_context(update, repo)
    parts = query.data.split(":")

    action = parts[2] if len(parts) > 2 else ""

    if action == "confirm":
        await query.answer()
        rows = [
            [
                InlineKeyboardButton(
                    t("notifications.confirm_yes", ctx.lang), callback_data="notify:clearall:yes"
                ),
                InlineKeyboardButton(
                    t("notifications.confirm_no", ctx.lang),
                    callback_data="notify:clearall:cancel",
                ),
            ]
        ]
        try:
            await query.edit_message_text(
                t("notifications.confirm_text", ctx.lang),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(rows),
            )
        except BadRequest:
            pass

    elif action == "yes":
        telegram_id = update.effective_user.id
        count = await repo.delete_all_user_notifications(telegram_id)
        await query.answer(
            t("notifications.cleared_toast", ctx.lang, count=count), show_alert=False
        )

        # Reschedule
        jq = context.application.job_queue
        await schedule_next_notification(jq, repo)

        try:
            await query.edit_message_text(
                t("notifications.cleared_text", ctx.lang),
                parse_mode=ParseMode.MARKDOWN,
            )
        except BadRequest:
            pass

    elif action == "cancel":
        await query.answer(t("notifications.cancelled", ctx.lang), show_alert=False)
        telegram_id = update.effective_user.id

        text, keyboard = await _build_remind_view(repo, telegram_id, ctx.lang)
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
