"""Unified /results handler with two-state interaction.

State A (overview): show results for anchor round (the latest round with stored
results, defaulting to its latest stored session). Keyboard has session filter buttons.
State B (filtered): show results for specific session type with round navigation
+ Back button.

All reads are SQL-only — no direct API calls from handlers.
"""

import structlog
from telegram import Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from f1_bot.formatting.context import RenderContext
from f1_bot.formatting.i18n import t
from f1_bot.formatting.messages import (
    format_qualifying_results,
    format_race_results,
    format_session_results,
    format_sprint_results,
    no_data_message,
)
from f1_bot.handlers.context import resolve_context
from f1_bot.handlers.pagination import (
    displayable_sessions,
    load_schedule_and_bounds,
    results_filtered_keyboard,
    results_overview_keyboard,
    rounds_with_results,
)
from f1_bot.models.results import (
    QualifyingResult,
    RaceResult,
    SessionResult,
    SprintResult,
)
from f1_bot.utils.sessions import (
    find_race_session,
    session_label,
)

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
    for result_type in all_types:
        parts = result_type.split(":")
        if len(parts) == 3 and parts[0] == "session" and parts[1] == session_key:
            cached = await repo.get_results_by_type(season, rnd, result_type)
            if cached:
                return [SessionResult.model_validate(r) for r in cached]
    return []


async def _format_results_for_session(
    repo,
    season: int,
    rnd: int,
    race,
    session_key: str,
    drivers_map: dict,
    ctx: RenderContext,
    top_n: int | None = None,
) -> str | None:
    """Format results for a specific session key. Returns formatted text or None."""
    if session_key == "race":
        results = await _get_race_results(repo, season, rnd)
        if results:
            return format_race_results(race, results, ctx, top_n=top_n or 20)
    elif session_key == "qualifying":
        results = await _get_qualifying_results(repo, season, rnd)
        if results:
            return format_qualifying_results(race, results, ctx, top_n=top_n)
    elif session_key == "sprint":
        results = await _get_sprint_results(repo, season, rnd)
        if results:
            return format_sprint_results(race, results, ctx, top_n=top_n)
    elif session_key in ("fp1", "fp2", "fp3", "sprint_qualifying"):
        entry = find_race_session([race], rnd, session_key)
        if entry:
            results = await _get_session_result(repo, season, rnd, session_key)
            if results:
                return format_session_results(entry, results, ctx, drivers_map, top_n=top_n)
    return None


# ---------------------------------------------------------------------------
# /results — State A: overview with session filter keyboard
# ---------------------------------------------------------------------------


async def results_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Entry point: show results for anchor round with session filter buttons."""
    repo = context.bot_data["repo"]
    ctx = await resolve_context(update, repo)

    try:
        races, bounds, season = await load_schedule_and_bounds(context)
    except RuntimeError:
        await update.effective_message.reply_text(no_data_message("common.noun_schedule", ctx))
        return

    # Every navigation decision follows stored results, never the clock: data
    # lands hours after a session starts (2026-10-03 R16 incident).
    sessions_by_round = await repo.get_result_sessions_by_round(season)
    completed = rounds_with_results(sessions_by_round, races, "all")
    if not completed:
        await update.effective_message.reply_text(no_data_message("common.noun_results", ctx))
        return

    rnd = completed[-1]
    race = next(r for r in races if r.round == rnd)

    drivers_map = await repo.get_drivers_by_id_map(season)
    default_session = displayable_sessions(race, sessions_by_round[rnd])[-1]

    text = await _format_results_for_session(
        repo, season, rnd, race, default_session, drivers_map, ctx
    )
    if not text:
        text = no_data_message("common.noun_results", ctx)

    await update.effective_message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=results_overview_keyboard(
            rnd, completed_rounds=completed, active_key=default_session, lang=ctx.lang
        ),
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
    repo = context.bot_data["repo"]
    ctx = await resolve_context(update, repo)

    parts = query.data.split(":")
    if len(parts) < 4:
        await query.answer()
        return

    mode = parts[1]
    session_key = parts[2]
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

    race = next((r for r in races if r.round == rnd), None)
    if not race:
        await query.answer(text=t("common.round_not_found", ctx.lang), show_alert=True)
        return

    # Read only after the round is known to exist — a bad round never costs a query.
    sessions_by_round = await repo.get_result_sessions_by_round(season)
    drivers_map = await repo.get_drivers_by_id_map(season)

    if mode == "back":
        # Return to State A (overview) for the same round
        shown = displayable_sessions(race, sessions_by_round.get(rnd, set()))
        default_session = shown[-1] if shown else None
        text = None
        if default_session:
            text = await _format_results_for_session(
                repo, season, rnd, race, default_session, drivers_map, ctx
            )
        if not text:
            text = no_data_message("common.noun_results", ctx)

        completed = rounds_with_results(sessions_by_round, races, "all")

        try:
            await query.edit_message_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=results_overview_keyboard(
                    rnd, completed_rounds=completed, active_key=default_session, lang=ctx.lang
                ),
            )
        except BadRequest:
            pass
        await query.answer()
        return

    if mode == "filtered":
        # Check if "all" — show combined results
        if session_key == "all":
            text = await _format_all_results(repo, season, rnd, race, drivers_map, ctx)
            completed = rounds_with_results(sessions_by_round, races, "all")
            try:
                await query.edit_message_text(
                    text or no_data_message("common.noun_results", ctx),
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=results_filtered_keyboard(rnd, completed, "all", lang=ctx.lang),
                )
            except BadRequest:
                pass
            await query.answer()
            return

        # Check if session exists for this weekend
        if session_key in ("fp2", "fp3", "sprint_qualifying", "sprint"):
            entry = find_race_session([race], rnd, session_key)
            if entry is None:
                navigable = rounds_with_results(sessions_by_round, races, session_key)
                if not navigable:
                    msg = t(
                        "results.no_session_data",
                        ctx.lang,
                        label=session_label(session_key, ctx.lang),
                    )
                    await query.answer(text=msg, show_alert=True)
                    return
                rnd = navigable[-1]
                race = next((r for r in races if r.round == rnd), None)
                if not race:
                    await query.answer(text=t("common.round_not_found", ctx.lang), show_alert=True)
                    return

        text = await _format_results_for_session(
            repo, season, rnd, race, session_key, drivers_map, ctx
        )
        if not text:
            text = no_data_message(
                "common.noun_session_results", ctx, session=session_label(session_key, ctx.lang)
            )

        completed = rounds_with_results(sessions_by_round, races, session_key)
        try:
            await query.edit_message_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=results_filtered_keyboard(rnd, completed, session_key, lang=ctx.lang),
            )
        except BadRequest:
            pass
        except Exception as e:
            log.warning("results_filtered_failed", error=str(e))
            await query.answer(text=t("common.failed_to_load", ctx.lang), show_alert=True)
            return

        await query.answer()
        return


async def _format_all_results(
    repo, season: int, rnd: int, race, drivers_map: dict, ctx: RenderContext
) -> str | None:
    """Format all available session results for a round into a combined message."""
    all_keys = ("fp1", "fp2", "fp3", "sprint_qualifying", "sprint", "qualifying", "race")

    # Pre-fetch all session texts once (avoids re-querying in Stage 2)
    texts: dict[str, str | None] = {}
    for key in all_keys:
        texts[key] = await _format_results_for_session(
            repo, season, rnd, race, key, drivers_map, ctx
        )

    # Stage 1: All sessions, full results
    sections = [texts[k] for k in all_keys if texts[k]]
    if not sections:
        return None

    combined_text = "\n\n".join(sections)
    if len(combined_text) <= 4096:
        return combined_text

    # Stage 2: Competitive sessions only (reuse pre-fetched texts)
    comp_keys = ("sprint_qualifying", "sprint", "qualifying", "race")
    comp_sections = [texts[k] for k in comp_keys if texts[k]]

    if not comp_sections:
        return None

    filtered_text = "\n\n".join(comp_sections)
    note = t("results.truncated_practice", ctx.lang)
    if len(filtered_text) + len(note) <= 4096:
        return filtered_text + note

    # Stage 3: Truncate competitive sessions to top 10 (requires re-format)
    truncated_sections = []
    for key in comp_keys:
        text = await _format_results_for_session(
            repo, season, rnd, race, key, drivers_map, ctx, top_n=10
        )
        if text:
            truncated_sections.append(text)

    if not truncated_sections:
        return None

    truncated_note = t("results.truncated_top10", ctx.lang)
    return "\n\n".join(truncated_sections) + truncated_note


def register(app: Application) -> None:
    app.add_handler(CommandHandler("results", results_handler))
    app.add_handler(CallbackQueryHandler(_results_callback, pattern=r"^res:"))
