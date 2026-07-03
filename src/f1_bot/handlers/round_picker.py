"""Handler for the round picker overlay (rpk: callbacks)."""

import structlog
from telegram import Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

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

    if len(parts) < 3:
        await query.answer(text="Invalid selection", show_alert=True)
        return

    try:
        current_round = int(parts[-1])
    except ValueError:
        await query.answer(text="Invalid selection", show_alert=True)
        return

    origin = ":".join(parts[1:-1])

    try:
        races, bounds, season = await load_schedule_and_bounds(context)
    except RuntimeError:
        await query.answer(text="Schedule unavailable", show_alert=True)
        return

    navigable = _compute_navigable_rounds(origin, races, bounds)
    if not navigable:
        await query.answer(text="No rounds available", show_alert=True)
        return

    if current_round not in navigable:
        current_round = navigable[-1]

    try:
        await query.edit_message_text(
            round_picker_text(current_round, races),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=round_picker_keyboard(origin, current_round, navigable, races),
        )
    except BadRequest:
        pass

    await query.answer()


def register(app: Application) -> None:
    app.add_handler(CallbackQueryHandler(_round_picker_callback, pattern=r"^rpk:"))
