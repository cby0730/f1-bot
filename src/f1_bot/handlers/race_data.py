"""Handlers for /pitstops and /laps — SQL-only reads.

/pitstops: pit stop data from Jolpica (synced by scheduler).
/laps: one personal-best table from OpenF1 lap timings (synced by scheduler).

Both views are also reachable from /results State A. Back always returns to
results State A for that round (intentional hub — including the slash aliases).
"""

import structlog
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from f1_bot.formatting.i18n import DEFAULT_LANG, t
from f1_bot.formatting.messages import (
    format_laps_summary,
    format_pitstops,
    no_data_message,
)
from f1_bot.handlers.context import resolve_context
from f1_bot.handlers.pagination import (
    load_schedule_and_bounds,
    resolve_default_round,
    round_keyboard,
)
from f1_bot.models.results import LapTime, PitStop

log = structlog.get_logger(__name__)


def _with_results_back(
    prefix: str, rnd: int, navigable_rounds: list[int], lang: str = DEFAULT_LANG
) -> InlineKeyboardMarkup:
    """Round pager plus Back to results State A (`res:back:_:{round}`)."""
    nav = round_keyboard(prefix, rnd, navigable_rounds, lang)
    rows = [list(r) for r in nav.inline_keyboard if r]
    rows.append([InlineKeyboardButton(t("common.back", lang), callback_data=f"res:back:_:{rnd}")])
    return InlineKeyboardMarkup(rows)


# ---------------------------------------------------------------------------
# /pitstops (SQL-only)
# ---------------------------------------------------------------------------


async def _get_pitstops(repo, season: int, rnd: int) -> list[PitStop]:
    cached = await repo.get_pit_stops(season, rnd)
    if cached:
        return [PitStop.model_validate(s) for s in cached]
    return []


async def pitstops_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    repo = context.bot_data["repo"]
    ctx = await resolve_context(update, repo)
    try:
        races, bounds, season = await load_schedule_and_bounds(context)
    except RuntimeError:
        await update.effective_message.reply_text(no_data_message("common.noun_schedule", ctx))
        return

    rnd = resolve_default_round(bounds)
    if rnd is None:
        await update.effective_message.reply_text(no_data_message("common.noun_pitstops", ctx))
        return

    race = next((r for r in races if r.round == rnd), None)
    if not race:
        await update.effective_message.reply_text(no_data_message("common.noun_pitstops", ctx))
        return
    stops = await _get_pitstops(repo, season, rnd)
    if not stops:
        await update.effective_message.reply_text(no_data_message("common.noun_pitstops", ctx))
        return

    completed = list(range(1, (bounds.get("last_completed_round") or 0) + 1))
    await update.effective_message.reply_text(
        format_pitstops(race, stops, rnd, ctx),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_with_results_back("pit", rnd, completed, ctx.lang),
    )


async def _pitstops_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    repo = context.bot_data["repo"]
    ctx = await resolve_context(update, repo)
    parts = query.data.split(":")
    try:
        rnd = int(parts[1])
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

    try:
        stops = await _get_pitstops(repo, season, rnd)
        completed = list(range(1, (bounds.get("last_completed_round") or 0) + 1))
        text = (
            format_pitstops(race, stops, rnd, ctx)
            if stops
            else no_data_message("common.noun_pitstops", ctx)
        )
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_with_results_back("pit", rnd, completed, ctx.lang),
        )
    except BadRequest:
        pass
    except Exception as e:
        log.warning("pitstops_callback_failed", error=str(e))
        await query.answer(text=t("common.failed_to_load", ctx.lang), show_alert=True)
        return

    await query.answer()


# ---------------------------------------------------------------------------
# /laps — one personal-best table. Stale lap:l / lap:dp / lap:d fall through
# to the summary (same spirit as nsess:/qual:). lap:{n}:s stays for the picker.
# ---------------------------------------------------------------------------


async def _get_laps(repo, season: int, rnd: int) -> list[LapTime]:
    raw_laps = await repo.get_lap_timings(season, rnd)
    if not raw_laps:
        return []
    if isinstance(raw_laps[0], LapTime):
        return raw_laps
    return [LapTime.model_validate(item) for item in raw_laps]


async def _laps_text_and_keyboard(repo, race, season: int, rnd: int, bounds: dict, ctx):
    laps = await _get_laps(repo, season, rnd)
    completed = list(range(1, (bounds.get("last_completed_round") or 0) + 1))
    keyboard = _with_results_back("lap", rnd, completed, ctx.lang)
    if not laps:
        return no_data_message("common.noun_laps", ctx), keyboard
    drivers_map = await repo.get_drivers_map(season)
    race_results = await repo.get_race_results(season, rnd)
    text = format_laps_summary(
        race,
        laps,
        ctx,
        drivers_map,
        race_results if isinstance(race_results, list) else None,
    )
    return text, keyboard


async def laps_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    repo = context.bot_data["repo"]
    ctx = await resolve_context(update, repo)
    try:
        races, bounds, season = await load_schedule_and_bounds(context)
    except RuntimeError:
        await update.effective_message.reply_text(no_data_message("common.noun_schedule", ctx))
        return

    rnd = resolve_default_round(bounds)
    if rnd is None:
        await update.effective_message.reply_text(no_data_message("common.noun_laps", ctx))
        return

    race = next((r for r in races if r.round == rnd), None)
    if not race:
        await update.effective_message.reply_text(no_data_message("common.noun_laps", ctx))
        return
    laps = await _get_laps(repo, season, rnd)
    if not laps:
        await update.effective_message.reply_text(no_data_message("common.noun_laps", ctx))
        return

    drivers_map = await repo.get_drivers_map(season)
    race_results = await repo.get_race_results(season, rnd)
    completed = list(range(1, (bounds.get("last_completed_round") or 0) + 1))
    await update.effective_message.reply_text(
        format_laps_summary(
            race,
            laps,
            ctx,
            drivers_map,
            race_results if isinstance(race_results, list) else None,
        ),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_with_results_back("lap", rnd, completed, ctx.lang),
    )


async def _laps_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route all lap: callback_data variants to the personal-best summary.

    Formats (new and stale):
      lap:{rnd} / lap:{rnd}:s              → summary
      lap:{rnd}:l:{lap_num}                → summary (stale by-lap)
      lap:{rnd}:dp                         → summary (stale driver picker)
      lap:{rnd}:d:{driver}:{page}          → summary (stale per-driver)
    """
    query = update.callback_query
    repo = context.bot_data["repo"]
    ctx = await resolve_context(update, repo)

    parts = query.data.split(":")
    try:
        rnd = int(parts[1])
    except (ValueError, IndexError):
        await query.answer(text=t("common.invalid_selection", ctx.lang), show_alert=True)
        return

    try:
        races, bounds, season = await load_schedule_and_bounds(context)
    except RuntimeError:
        await query.answer(text=t("common.schedule_unavailable", ctx.lang), show_alert=True)
        return

    race = next((r for r in races if r.round == rnd), None)
    try:
        text, keyboard = await _laps_text_and_keyboard(repo, race, season, rnd, bounds, ctx)
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
    except BadRequest:
        pass
    except Exception as e:
        log.warning("laps_callback_failed", error=str(e))
        await query.answer(text=t("common.failed_to_load", ctx.lang), show_alert=True)
        return

    await query.answer()


def register(app: Application) -> None:
    app.add_handler(CommandHandler("pitstops", pitstops_handler))
    app.add_handler(CommandHandler("laps", laps_handler))
    app.add_handler(CallbackQueryHandler(_pitstops_callback, pattern=r"^pit:"))
    app.add_handler(CallbackQueryHandler(_laps_callback, pattern=r"^lap:"))
