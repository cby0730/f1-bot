import datetime

import structlog
from telegram import Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from f1_bot.formatting.i18n import t
from f1_bot.formatting.messages import (
    format_countdown_msg,
    format_next_race,
    format_next_session,
    format_schedule,
    no_data_message,
)
from f1_bot.handlers.context import resolve_context
from f1_bot.handlers.pagination import (
    load_schedule_and_bounds,
    next_filtered_keyboard,
    next_overview_keyboard,
    upcoming_rounds,
)
from f1_bot.utils.sessions import find_next_sessions, session_label

log = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# /next — State A: overview (session filter keyboard)
# ---------------------------------------------------------------------------


async def next_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Entry point: show next race weekend overview with session filter buttons."""
    repo = context.bot_data["repo"]
    ctx = await resolve_context(update, repo)

    try:
        races, bounds, season = await load_schedule_and_bounds(context)
    except RuntimeError:
        await update.effective_message.reply_text(
            no_data_message("common.noun_upcoming_race", ctx)
        )
        return

    today = datetime.datetime.now(tz=datetime.UTC).date()
    upcoming = [r for r in races if r.date >= today]
    if not upcoming:
        await update.effective_message.reply_text(
            no_data_message("common.noun_upcoming_race", ctx)
        )
        return

    race = upcoming[0]
    nav_rounds = upcoming_rounds(races, "all")
    await update.effective_message.reply_text(
        format_next_race(race, ctx),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=next_overview_keyboard(race.round, nav_rounds, ctx.lang),
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
    repo = context.bot_data["repo"]
    ctx = await resolve_context(update, repo)

    parts = query.data.split(":")
    if len(parts) < 4:
        await query.answer()
        return

    mode = parts[1]
    session_filter = parts[2]
    try:
        rnd = int(parts[3])
    except (ValueError, IndexError):
        await query.answer(text=t("common.invalid_selection", ctx.lang), show_alert=True)
        return

    try:
        races, bounds, season = await load_schedule_and_bounds(context)
    except RuntimeError:
        await query.answer(text=t("common.schedule_unavailable", ctx.lang), show_alert=True)
        return

    if mode == "back":
        # Return to State A (overview) for the same round
        nav_rounds = upcoming_rounds(races, "all")
        if not nav_rounds:
            await query.answer(text=t("schedule.no_upcoming_races", ctx.lang), show_alert=True)
            return

        if rnd not in nav_rounds:
            rnd = nav_rounds[0]

        race = next((r for r in races if r.round == rnd), None)
        if race is None:
            race = next((r for r in races if r.round == nav_rounds[0]), None)

        if race is None:
            await query.answer(text=t("schedule.no_upcoming_races", ctx.lang), show_alert=True)
            return

        try:
            await query.edit_message_text(
                format_next_race(race, ctx),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=next_overview_keyboard(race.round, nav_rounds, ctx.lang),
            )
        except BadRequest:
            pass
        await query.answer()
        return

    if mode == "filtered":
        # State B: show next upcoming session of this filter type
        none_left = t(
            "schedule.no_upcoming_filtered",
            ctx.lang,
            session=session_label(session_filter, ctx.lang),
        )
        nav_rounds = upcoming_rounds(races, session_filter)
        if not nav_rounds:
            await query.answer(text=none_left, show_alert=True)
            return

        # If requested round no longer has sessions, snap to first
        if rnd not in nav_rounds:
            rnd = nav_rounds[0]

        now = datetime.datetime.now(tz=datetime.UTC)
        entries = find_next_sessions(races, session_filter, limit=len(races) * 7, now=now)
        entry = next((e for e in entries if e.race.round == rnd), None)
        if entry is None:
            rnd = nav_rounds[0]
            entry = next((e for e in entries if e.race.round == rnd), None)

        if entry is None:
            await query.answer(text=none_left, show_alert=True)
            return

        try:
            await query.edit_message_text(
                format_next_session(entry, ctx),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=next_filtered_keyboard(rnd, nav_rounds, session_filter, ctx.lang),
            )
        except BadRequest:
            pass
        except Exception as e:
            log.warning("next_filtered_callback_failed", error=str(e))
            await query.answer(text=t("common.failed_to_load", ctx.lang), show_alert=True)
            return

        await query.answer()
        return


# ---------------------------------------------------------------------------
# /schedule and /countdown (unchanged — single-view)
# ---------------------------------------------------------------------------


async def schedule_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    repo = context.bot_data["repo"]
    ctx = await resolve_context(update, repo)
    try:
        races, bounds, season = await load_schedule_and_bounds(context)
    except RuntimeError:
        await update.effective_message.reply_text(no_data_message("common.noun_schedule", ctx))
        return

    await update.effective_message.reply_text(
        format_schedule(races, ctx), parse_mode=ParseMode.MARKDOWN
    )


async def countdown_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    repo = context.bot_data["repo"]
    ctx = await resolve_context(update, repo)
    season = datetime.date.today().year
    race = await repo.get_next_race(season)
    if not race:
        await update.effective_message.reply_text(
            no_data_message("common.noun_upcoming_race", ctx)
        )
        return
    await update.effective_message.reply_text(
        format_countdown_msg(race, ctx), parse_mode=ParseMode.MARKDOWN
    )


# ---------------------------------------------------------------------------
# Legacy callback handler for stale old-format inline keyboards
# ---------------------------------------------------------------------------


async def _legacy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle old nsess:/nprac:/nqual:/nspr: callbacks from stale messages."""
    query = update.callback_query
    ctx = await resolve_context(update, context.bot_data["repo"])
    await query.answer(text=t("schedule.outdated_next", ctx.lang), show_alert=True)


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
