"""Handlers for /pitstops and /laps — SQL-only reads.

/pitstops: pit stop data from Jolpica (synced by scheduler).
/laps: lap timing data from OpenF1 (synced by scheduler), with sector times.
"""

import structlog
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from f1_bot.formatting.i18n import DEFAULT_LANG, t
from f1_bot.formatting.messages import (
    _LAPS_PAGE_SIZE,
    format_laps_by_driver,
    format_laps_by_lap,
    format_laps_driver_picker,
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
from f1_bot.models.driver import Driver
from f1_bot.models.results import LapTime, PitStop

log = structlog.get_logger(__name__)


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
        reply_markup=round_keyboard("pit", rnd, completed, ctx.lang),
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
            reply_markup=round_keyboard("pit", rnd, completed, ctx.lang),
        )
    except BadRequest:
        pass
    except Exception as e:
        log.warning("pitstops_callback_failed", error=str(e))
        await query.answer(text=t("common.failed_to_load", ctx.lang), show_alert=True)
        return

    await query.answer()


# ---------------------------------------------------------------------------
# /laps — multi-mode: summary | per-lap | driver picker | per-driver
# SQL-only reads — data synced from OpenF1 by scheduler
# ---------------------------------------------------------------------------


async def _get_laps(repo, season: int, rnd: int) -> list[LapTime]:
    raw_laps = await repo.get_lap_timings(season, rnd)
    if not raw_laps:
        return []
    if isinstance(raw_laps[0], LapTime):
        return raw_laps
    return [LapTime.model_validate(item) for item in raw_laps]


def _laps_summary_keyboard(
    rnd: int, navigable_rounds: list[int], lang: str = DEFAULT_LANG
) -> InlineKeyboardMarkup:
    nav_row = round_keyboard("lap", rnd, navigable_rounds, lang).inline_keyboard[0]
    mode_row = [
        InlineKeyboardButton(t("race_data.btn_by_lap", lang), callback_data=f"lap:{rnd}:l:1"),
        InlineKeyboardButton(t("race_data.btn_by_driver", lang), callback_data=f"lap:{rnd}:dp"),
    ]
    return InlineKeyboardMarkup([nav_row, mode_row])


def _laps_per_lap_keyboard(
    rnd: int, current_lap: int, total_laps: int, lang: str = DEFAULT_LANG
) -> InlineKeyboardMarkup:
    nav_row: list[InlineKeyboardButton] = []
    if current_lap > 1:
        nav_row.append(InlineKeyboardButton("◀", callback_data=f"lap:{rnd}:l:{current_lap - 1}"))
    nav_row.append(
        InlineKeyboardButton(
            t("race_data.btn_lap_counter", lang, current=current_lap, total=total_laps),
            callback_data=f"lap:{rnd}:l:{current_lap}",
        )
    )
    if current_lap < total_laps:
        nav_row.append(InlineKeyboardButton("▶", callback_data=f"lap:{rnd}:l:{current_lap + 1}"))
    back_row = [
        InlineKeyboardButton(t("race_data.btn_summary", lang), callback_data=f"lap:{rnd}:s")
    ]
    return InlineKeyboardMarkup([nav_row, back_row])


def _laps_driver_picker_keyboard(
    rnd: int,
    driver_ids: list[str],
    drivers: dict[int, Driver] | None = None,
    lang: str = DEFAULT_LANG,
) -> InlineKeyboardMarkup:
    cols = 4
    rows: list[list[InlineKeyboardButton]] = []
    for i in range(0, len(driver_ids), cols):
        row_drivers = driver_ids[i : i + cols]
        row_buttons = []
        for d in row_drivers:
            label = d
            try:
                num = int(d)
                if drivers and num in drivers:
                    label = drivers[num].code or d
            except ValueError:
                pass
            row_buttons.append(InlineKeyboardButton(label, callback_data=f"lap:{rnd}:d:{d}:0"))
        rows.append(row_buttons)
    rows.append(
        [InlineKeyboardButton(t("race_data.btn_summary", lang), callback_data=f"lap:{rnd}:s")]
    )
    return InlineKeyboardMarkup(rows)


def _laps_per_driver_keyboard(
    rnd: int, driver_id: str, page: int, total_laps: int, lang: str = DEFAULT_LANG
) -> InlineKeyboardMarkup:
    total_pages = (total_laps + _LAPS_PAGE_SIZE - 1) // _LAPS_PAGE_SIZE
    nav_row: list[InlineKeyboardButton] = []
    if page > 0:
        nav_row.append(
            InlineKeyboardButton("◀", callback_data=f"lap:{rnd}:d:{driver_id}:{page - 1}")
        )
    start = page * _LAPS_PAGE_SIZE + 1
    end = min((page + 1) * _LAPS_PAGE_SIZE, total_laps)
    nav_row.append(
        InlineKeyboardButton(
            t("race_data.btn_page_range", lang, start=start, end=end, total=total_laps),
            callback_data=f"lap:{rnd}:d:{driver_id}:{page}",
        )
    )
    if page < total_pages - 1:
        nav_row.append(
            InlineKeyboardButton("▶", callback_data=f"lap:{rnd}:d:{driver_id}:{page + 1}")
        )
    back_row = [
        InlineKeyboardButton(t("race_data.btn_drivers", lang), callback_data=f"lap:{rnd}:dp")
    ]
    return InlineKeyboardMarkup([nav_row, back_row])


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

    completed = list(range(1, (bounds.get("last_completed_round") or 0) + 1))
    await update.effective_message.reply_text(
        format_laps_summary(race, laps, ctx, drivers_map),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_laps_summary_keyboard(rnd, completed, ctx.lang),
    )


async def _laps_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route all lap: callback_data variants to the correct view.

    Formats:
      lap:{rnd}:s              → summary
      lap:{rnd}:l:{lap_num}    → per-lap
      lap:{rnd}:dp             → driver picker
      lap:{rnd}:d:{driver}:{page} → per-driver
    """
    query = update.callback_query
    repo = context.bot_data["repo"]
    ctx = await resolve_context(update, repo)

    parts = query.data.split(":")  # e.g. ["lap", "10", "d", "VER", "0"] or ["lap", "10"]
    try:
        rnd = int(parts[1])
    except (ValueError, IndexError):
        await query.answer(text=t("common.invalid_selection", ctx.lang), show_alert=True)
        return
    mode = parts[2] if len(parts) > 2 else "s"

    try:
        races, bounds, season = await load_schedule_and_bounds(context)
    except RuntimeError:
        await query.answer(text=t("common.schedule_unavailable", ctx.lang), show_alert=True)
        return

    race = next((r for r in races if r.round == rnd), None)
    completed = list(range(1, (bounds.get("last_completed_round") or 0) + 1))
    drivers_map = await repo.get_drivers_map(season)

    try:
        laps = await _get_laps(repo, season, rnd)
        if not laps:
            await query.answer(text=t("race_data.no_lap_data", ctx.lang), show_alert=True)
            return

        if mode == "s":
            # Summary
            text = format_laps_summary(race, laps, ctx, drivers_map)
            keyboard = _laps_summary_keyboard(rnd, completed, ctx.lang)

        elif mode == "l":
            # Per-lap
            if len(parts) < 4:
                await query.answer(text=t("common.invalid_selection", ctx.lang), show_alert=True)
                return
            try:
                lap_num = int(parts[3])
            except ValueError:
                await query.answer(text=t("common.invalid_selection", ctx.lang), show_alert=True)
                return
            total_laps = max(lap.lap_number for lap in laps)
            lap_num = max(1, min(lap_num, total_laps))
            text = format_laps_by_lap(race, laps, lap_num, total_laps, ctx, drivers_map)
            keyboard = _laps_per_lap_keyboard(rnd, lap_num, total_laps, ctx.lang)

        elif mode == "dp":
            # Driver picker
            driver_ids = sorted({lap.driver_id for lap in laps})
            text = format_laps_driver_picker(race, ctx)
            keyboard = _laps_driver_picker_keyboard(rnd, driver_ids, drivers_map, ctx.lang)

        elif mode == "d":
            # Per-driver
            if len(parts) < 5:
                await query.answer(text=t("common.invalid_selection", ctx.lang), show_alert=True)
                return
            driver_id = parts[3]
            try:
                page = int(parts[4])
            except ValueError:
                await query.answer(text=t("common.invalid_selection", ctx.lang), show_alert=True)
                return
            driver_laps = [lap for lap in laps if lap.driver_id == driver_id]
            if not driver_laps:
                await query.answer(
                    text=t("race_data.no_driver_data", ctx.lang, driver=driver_id),
                    show_alert=True,
                )
                return
            total_laps = len(driver_laps)
            total_pages = (total_laps + _LAPS_PAGE_SIZE - 1) // _LAPS_PAGE_SIZE
            page = max(0, min(page, total_pages - 1))
            text = format_laps_by_driver(race, laps, driver_id, page, ctx, drivers_map)
            keyboard = _laps_per_driver_keyboard(rnd, driver_id, page, total_laps, ctx.lang)

        else:
            return

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
