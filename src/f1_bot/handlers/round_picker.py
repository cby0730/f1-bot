"""Handler for the round picker overlay (rpk: callbacks)."""

import structlog
from telegram import Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

from f1_bot.formatting.i18n import t
from f1_bot.handlers.context import resolve_context
from f1_bot.handlers.pagination import (
    get_completed_rounds_for_session,
    load_schedule_and_bounds,
    round_picker_keyboard,
    round_picker_text,
    upcoming_rounds,
)

log = structlog.get_logger(__name__)


def _compute_navigable_rounds(origin: str, races: list, bounds: dict) -> list[int]:
    """Determine which rounds are navigable based on the picker's origin."""
    if origin == "nb":
        return upcoming_rounds(races, "all")
    if origin.startswith("nf:"):
        session_filter = origin[3:]
        return upcoming_rounds(races, session_filter)
    if origin == "rb":
        return get_completed_rounds_for_session(races, "all")
    if origin.startswith("rf:"):
        session_key = origin[3:]
        return get_completed_rounds_for_session(races, session_key)
    if origin == "pit":
        return list(range(1, (bounds.get("last_completed_round") or 0) + 1))
    if origin == "lap":
        return list(range(1, (bounds.get("last_completed_round") or 0) + 1))
    return []


async def _round_picker_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle rpk:{origin}:{round} callbacks — display the round picker grid."""
    query = update.callback_query
    parts = query.data.split(":")
    ctx = await resolve_context(update, context.bot_data["repo"])

    if len(parts) < 3:
        await query.answer(text=t("common.invalid_selection", ctx.lang), show_alert=True)
        return

    try:
        current_round = int(parts[-1])
    except ValueError:
        await query.answer(text=t("common.invalid_selection", ctx.lang), show_alert=True)
        return

    origin = ":".join(parts[1:-1])

    try:
        races, bounds, season = await load_schedule_and_bounds(context)
    except RuntimeError:
        await query.answer(text=t("common.schedule_unavailable", ctx.lang), show_alert=True)
        return

    try:
        navigable = _compute_navigable_rounds(origin, races, bounds)
    except ValueError:
        await query.answer(text=t("common.invalid_selection", ctx.lang), show_alert=True)
        return

    if not navigable:
        await query.answer(text=t("common.no_rounds_available", ctx.lang), show_alert=True)
        return

    if current_round not in navigable:
        if origin == "nb" or origin.startswith("nf:"):
            current_round = navigable[0]
        else:
            current_round = navigable[-1]

    try:
        await query.edit_message_text(
            round_picker_text(current_round, races, ctx.lang),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=round_picker_keyboard(origin, current_round, navigable, races, ctx.lang),
        )
    except BadRequest:
        pass

    await query.answer()


def register(app: Application) -> None:
    app.add_handler(CallbackQueryHandler(_round_picker_callback, pattern=r"^rpk:"))
