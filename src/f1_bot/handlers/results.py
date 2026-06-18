"""Unified /results handler with two-state interaction.

State A (overview): show results for anchor round (race if available, else most
recent completed session). Keyboard has session filter buttons.
State B (filtered): show results for specific session type with round navigation
+ Back button.

All reads are SQL-only — no direct API calls from handlers.
"""


import structlog
from telegram import Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from f1_bot.formatting.messages import (
    format_qualifying_results,
    format_race_results,
    format_session_results,
    format_sprint_results,
    no_data_message,
)
from f1_bot.handlers.pagination import (
    load_schedule_and_bounds,
    results_filtered_keyboard,
    results_overview_keyboard,
)
from f1_bot.models.results import (
    QualifyingResult,
    RaceResult,
    SessionResult,
    SprintResult,
)
from f1_bot.utils.sessions import find_race_session, find_recent_completed_session

log = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# SQL-only data fetchers (no API calls)
# ---------------------------------------------------------------------------


async def _get_race_results(repo, season: int, rnd: int):
    cached = await repo.get_race_results(season, rnd)
    if cached:
        return [RaceResult.model_validate(r) for r in cached]
    return []


async def _get_qualifying_results(repo, season: int, rnd: int):
    cached = await repo.get_qualifying_results(season, rnd)
    if cached:
        return [QualifyingResult.model_validate(r) for r in cached]
    return []


async def _get_sprint_results(repo, season: int, rnd: int):
    cached = await repo.get_sprint_results(season, rnd)
    if cached:
        return [SprintResult.model_validate(r) for r in cached]
    return []


async def _get_session_result(repo, season: int, rnd: int, session_key: str):
    """Try to find session results by scanning known OpenF1 session keys stored in results table."""
    # session results are stored as "session:{openf1_session_key}" in the results table
    all_types = await repo.get_all_result_types(season, rnd)
    session_prefix = "session:"
    for t in all_types:
        if t.startswith(session_prefix):
            # We can't easily match session_key to OpenF1 key without a mapping,
            # but we know what session types are stored. Try all session:* entries.
            cached = await repo.sqlite.get_results(season, rnd, t)
            if cached:
                return [SessionResult.model_validate(r) for r in cached]
    return []


async def _get_drivers_map(repo, season: int) -> dict:
    """Get driver map from cached drivers (SQL-only)."""
    return await repo.get_drivers_map(season)


async def _format_results_for_session(repo, season: int, rnd: int, race, session_key: str, drivers_map: dict) -> str | None:
    """Format results for a specific session key. Returns formatted text or None."""
    if session_key == "race":
        results = await _get_race_results(repo, season, rnd)
        if results:
            return format_race_results(race, results)
    elif session_key == "qualifying":
        results = await _get_qualifying_results(repo, season, rnd)
        if results:
            return format_qualifying_results(race, results)
    elif session_key == "sprint":
        results = await _get_sprint_results(repo, season, rnd)
        if results:
            return format_sprint_results(race, results)
    elif session_key in ("fp1", "fp2", "fp3", "sprint_qualifying"):
        entry = find_race_session([race], rnd, session_key)
        if entry:
            results = await _get_session_result(repo, season, rnd, session_key)
            if results:
                return format_session_results(entry, results, drivers_map)
    return None


def _get_anchor_round(bounds: dict) -> int | None:
    """Determine the anchor round: latest round with any completed session data."""
    return bounds.get("last_completed_round")


async def _find_default_session(repo, races: list, season: int, rnd: int) -> str | None:
    """Find the default session to display for State A.

    Prefers race, then falls back to most recently completed session.
    """
    # Check if race results exist
    race_results = await repo.get_race_results(season, rnd)
    if race_results:
        return "race"

    # Fall back to most recently completed session of this round
    race = next((r for r in races if r.round == rnd), None)
    if race:
        entry = find_recent_completed_session([race])
        if entry:
            return entry.key
    return None


# ---------------------------------------------------------------------------
# /results — State A: overview with session filter keyboard
# ---------------------------------------------------------------------------


async def results_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Entry point: show results for anchor round with session filter buttons."""
    try:
        races, bounds, season = await load_schedule_and_bounds(context)
    except RuntimeError:
        await update.effective_message.reply_text(no_data_message("schedule"))
        return

    rnd = _get_anchor_round(bounds)
    if rnd is None:
        # Try the latest round with any result data
        rnd = await context.bot_data["repo"].get_last_result_round(season)
    if rnd is None:
        await update.effective_message.reply_text(no_data_message("results"))
        return

    repo = context.bot_data["repo"]
    race = next((r for r in races if r.round == rnd), None)
    if not race:
        await update.effective_message.reply_text(no_data_message("results"))
        return

    drivers_map = await _get_drivers_map(repo, season)
    default_session = await _find_default_session(repo, races, season, rnd)

    if default_session:
        text = await _format_results_for_session(repo, season, rnd, race, default_session, drivers_map)
    else:
        text = None

    if not text:
        text = no_data_message("results")

    await update.effective_message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=results_overview_keyboard(rnd, active_key=default_session),
    )


# ---------------------------------------------------------------------------
# /results callback — routes overview, filtered, back
# ---------------------------------------------------------------------------


async def _results_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all res: callbacks.

    Formats:
      res:filtered:{session_key}:{round}  → State B: show session results
      res:back:_:{round}                  → State A: overview for round
    """
    query = update.callback_query
    await query.answer()

    parts = query.data.split(":")
    if len(parts) < 4:
        return

    mode = parts[1]
    session_key = parts[2]
    rnd = int(parts[3])

    try:
        races, bounds, season = await load_schedule_and_bounds(context)
    except RuntimeError:
        await query.answer(text="Schedule unavailable", show_alert=True)
        return

    repo = context.bot_data["repo"]
    race = next((r for r in races if r.round == rnd), None)
    if not race:
        await query.answer(text="Round not found", show_alert=True)
        return

    drivers_map = await _get_drivers_map(repo, season)

    if mode == "back":
        # Return to State A (overview) for the same round
        default_session = await _find_default_session(repo, races, season, rnd)
        text = None
        if default_session:
            text = await _format_results_for_session(repo, season, rnd, race, default_session, drivers_map)
        if not text:
            text = no_data_message("results")

        try:
            await query.edit_message_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=results_overview_keyboard(rnd, active_key=default_session),
            )
        except BadRequest:
            pass
        return

    if mode == "filtered":
        # Check if "all" — show combined results
        if session_key == "all":
            text = await _format_all_results(repo, season, rnd, race, drivers_map)
            completed = list(range(1, (bounds.get("last_completed_round") or 0) + 1))
            try:
                await query.edit_message_text(
                    text or no_data_message("results"),
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=results_filtered_keyboard(rnd, completed, "all"),
                )
            except BadRequest:
                pass
            return

        # Check if session exists for this weekend
        if session_key in ("fp3", "sprint_qualifying", "sprint"):
            entry = find_race_session([race], rnd, session_key)
            if entry is None:
                label_map = {
                    "fp3": "No FP3 on sprint weekends 🏎",
                    "sprint_qualifying": "No Sprint Qualifying this weekend",
                    "sprint": "No Sprint this weekend",
                }
                msg = label_map.get(session_key, f"No {session_key} session this weekend")
                await query.answer(text=msg, show_alert=True)
                return

        text = await _format_results_for_session(repo, season, rnd, race, session_key, drivers_map)
        if not text:
            text = no_data_message(f"{session_key} results")

        completed = list(range(1, (bounds.get("last_completed_round") or 0) + 1))
        try:
            await query.edit_message_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=results_filtered_keyboard(rnd, completed, session_key),
            )
        except BadRequest:
            pass
        except Exception as e:
            log.warning("results_filtered_failed", error=str(e))
            await query.answer(text="Failed to load data", show_alert=True)
        return


async def _format_all_results(repo, season: int, rnd: int, race, drivers_map: dict) -> str | None:
    """Format all available session results for a round into a combined message."""
    sections = []
    for key in ("fp1", "fp2", "fp3", "sprint_qualifying", "sprint", "qualifying", "race"):
        text = await _format_results_for_session(repo, season, rnd, race, key, drivers_map)
        if text:
            sections.append(text)
    return "\n\n".join(sections) if sections else None


# ---------------------------------------------------------------------------
# Legacy callback handlers for old inline keyboards
# ---------------------------------------------------------------------------


async def _legacy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle old qual:/spr:/sr: callbacks from stale messages."""
    query = update.callback_query
    await query.answer(text="This button is outdated. Use /results again.", show_alert=True)


def register(app: Application) -> None:
    app.add_handler(CommandHandler("results", results_handler))
    app.add_handler(CallbackQueryHandler(_results_callback, pattern=r"^res:"))
    # Legacy handlers for stale inline keyboards
    app.add_handler(CallbackQueryHandler(_legacy_callback, pattern=r"^qual:"))
    app.add_handler(CallbackQueryHandler(_legacy_callback, pattern=r"^spr:"))
    app.add_handler(CallbackQueryHandler(_legacy_callback, pattern=r"^sr:"))
