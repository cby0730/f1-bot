import datetime

import structlog
from telegram import Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from f1_bot.formatting.messages import (
    format_countdown_msg,
    format_next_race,
    format_next_session,
    format_schedule,
    no_data_message,
)
from f1_bot.handlers.pagination import (
    load_schedule_and_bounds,
    next_filtered_keyboard,
    next_overview_keyboard,
)
from f1_bot.utils.sessions import find_next_sessions

log = structlog.get_logger(__name__)


def _upcoming_rounds(races: list, group: str = "all") -> list[int]:
    """Return sorted list of round numbers that have at least one upcoming session in the group."""
    now = datetime.datetime.now(tz=datetime.UTC)
    entries = find_next_sessions(races, group, limit=len(races) * 7, now=now)
    seen: list[int] = []
    for entry in entries:
        if entry.race.round not in seen:
            seen.append(entry.race.round)
    return seen


# ---------------------------------------------------------------------------
# /next — State A: overview (session filter keyboard)
# ---------------------------------------------------------------------------


async def next_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Entry point: show next race weekend overview with session filter buttons."""
    try:
        races, bounds, season = await load_schedule_and_bounds(context)
    except RuntimeError:
        await update.effective_message.reply_text(no_data_message("upcoming race"))
        return

    repo = context.bot_data["repo"]
    user_tz = await repo.get_user_timezone(update.effective_user.id)

    today = datetime.datetime.now(tz=datetime.UTC).date()
    upcoming = [r for r in races if r.date >= today]
    if not upcoming:
        await update.effective_message.reply_text(no_data_message("upcoming race"))
        return

    race = upcoming[0]
    upcoming_rounds = _upcoming_rounds(races, "all")
    await update.effective_message.reply_text(
        format_next_race(race, user_tz),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=next_overview_keyboard(race.round, upcoming_rounds),
    )


# ---------------------------------------------------------------------------
# /next callback — routes overview, filtered, and back
# ---------------------------------------------------------------------------


async def _next_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all next: callbacks.

    Formats:
      next:filtered:{filter}:{round}  → State B: show next session of type
      next:back:_:{round}             → State A: overview for round
    """
    query = update.callback_query

    parts = query.data.split(":")
    if len(parts) < 4:
        await query.answer()
        return

    mode = parts[1]
    session_filter = parts[2]
    rnd = int(parts[3])

    try:
        races, bounds, season = await load_schedule_and_bounds(context)
    except RuntimeError:
        await query.answer(text="Schedule unavailable", show_alert=True)
        return

    repo = context.bot_data["repo"]
    user_tz = await repo.get_user_timezone(update.effective_user.id)

    if mode == "back":
        # Return to State A (overview) for the same round
        upcoming_rounds = _upcoming_rounds(races, "all")
        if not upcoming_rounds:
            await query.answer(text="No upcoming races", show_alert=True)
            return

        if rnd not in upcoming_rounds:
            rnd = upcoming_rounds[0]

        race = next((r for r in races if r.round == rnd), None)
        if race is None:
            race = next((r for r in races if r.round == upcoming_rounds[0]), None)

        if race is None:
            await query.answer(text="No upcoming races", show_alert=True)
            return

        try:
            await query.edit_message_text(
                format_next_race(race, user_tz),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=next_overview_keyboard(race.round, upcoming_rounds),
            )
        except BadRequest:
            pass
        await query.answer()
        return

    if mode == "filtered":
        # State B: show next upcoming session of this filter type
        upcoming_rounds = _upcoming_rounds(races, session_filter)
        if not upcoming_rounds:
            await query.answer(text=f"No upcoming {session_filter} sessions", show_alert=True)
            return

        # If requested round no longer has sessions, snap to first
        if rnd not in upcoming_rounds:
            rnd = upcoming_rounds[0]

        now = datetime.datetime.now(tz=datetime.UTC)
        entries = find_next_sessions(races, session_filter, limit=len(races) * 7, now=now)
        entry = next((e for e in entries if e.race.round == rnd), None)
        if entry is None:
            rnd = upcoming_rounds[0]
            entry = next((e for e in entries if e.race.round == rnd), None)

        if entry is None:
            await query.answer(text=f"No upcoming {session_filter} sessions", show_alert=True)
            return

        try:
            await query.edit_message_text(
                format_next_session(entry, user_tz),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=next_filtered_keyboard(rnd, upcoming_rounds, session_filter),
            )
        except BadRequest:
            pass
        except Exception as e:
            log.warning("next_filtered_callback_failed", error=str(e))
            await query.answer(text="Failed to load data", show_alert=True)
            return

        await query.answer()
        return


# ---------------------------------------------------------------------------
# /schedule and /countdown (unchanged — single-view)
# ---------------------------------------------------------------------------


async def schedule_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        races, bounds, season = await load_schedule_and_bounds(context)
    except RuntimeError:
        await update.effective_message.reply_text(no_data_message("schedule"))
        return

    repo = context.bot_data["repo"]
    user_tz = await repo.get_user_timezone(update.effective_user.id)
    await update.effective_message.reply_text(
        format_schedule(races, user_tz), parse_mode=ParseMode.MARKDOWN
    )


async def countdown_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    repo = context.bot_data["repo"]
    season = datetime.date.today().year
    user_tz = await repo.get_user_timezone(update.effective_user.id)
    race = await repo.get_next_race(season)
    if not race:
        await update.effective_message.reply_text(no_data_message("upcoming race"))
        return
    await update.effective_message.reply_text(
        format_countdown_msg(race, user_tz), parse_mode=ParseMode.MARKDOWN
    )


# ---------------------------------------------------------------------------
# Legacy callback handler for stale old-format inline keyboards
# ---------------------------------------------------------------------------


async def _legacy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle old nsess:/nprac:/nqual:/nspr: callbacks from stale messages."""
    query = update.callback_query
    await query.answer(text="This button is outdated. Use /next again.", show_alert=True)


def register(app: Application) -> None:
    app.add_handler(CommandHandler("next", next_handler))
    app.add_handler(CommandHandler("schedule", schedule_handler))
    app.add_handler(CommandHandler("countdown", countdown_handler))
    app.add_handler(CallbackQueryHandler(_next_callback, pattern=r"^next:"))
    # Legacy handlers for stale inline keyboards
    app.add_handler(CallbackQueryHandler(_legacy_callback, pattern=r"^nsess:"))
    app.add_handler(CallbackQueryHandler(_legacy_callback, pattern=r"^nprac:"))
    app.add_handler(CallbackQueryHandler(_legacy_callback, pattern=r"^nqual:"))
    app.add_handler(CallbackQueryHandler(_legacy_callback, pattern=r"^nspr:"))
