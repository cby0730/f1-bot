"""Handlers for /pitstops and /laps — SQL-only reads.

/pitstops: pit stop data from Jolpica (synced by scheduler).
/laps: lap timing data from OpenF1 (synced by scheduler), with sector times.
"""

import structlog
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from f1_bot.formatting.messages import (
    format_laps_by_driver,
    format_laps_by_lap,
    format_laps_driver_picker,
    format_laps_summary,
    format_pitstops,
    no_data_message,
)
from f1_bot.handlers.pagination import (
    load_schedule_and_bounds,
    resolve_default_round,
    round_keyboard,
)
from f1_bot.models.driver import Driver
from f1_bot.models.results import LapTime, PitStop

log = structlog.get_logger(__name__)

_LAPS_PAGE_SIZE = 20


# ---------------------------------------------------------------------------
# /pitstops (SQL-only)
# ---------------------------------------------------------------------------


async def _get_pitstops(repo, season: int, rnd: int) -> list[PitStop]:
    cached = await repo.get_pit_stops(season, rnd)
    if cached:
        return [PitStop.model_validate(s) for s in cached]
    return []


async def pitstops_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        races, bounds, season = await load_schedule_and_bounds(context)
    except RuntimeError:
        await update.effective_message.reply_text(no_data_message("schedule"))
        return

    rnd = resolve_default_round(bounds)
    if rnd is None:
        await update.effective_message.reply_text(no_data_message("pit stop data"))
        return

    repo = context.bot_data["repo"]
    race = next((r for r in races if r.round == rnd), None)
    if not race:
        await update.effective_message.reply_text(no_data_message("pit stop data"))
        return
    stops = await _get_pitstops(repo, season, rnd)
    if not stops:
        await update.effective_message.reply_text(no_data_message("pit stop data"))
        return

    completed = list(range(1, (bounds.get("last_completed_round") or 0) + 1))
    await update.effective_message.reply_text(
        format_pitstops(race, stops, rnd),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=round_keyboard("pit", rnd, completed),
    )


async def _pitstops_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    parts = query.data.split(":")
    try:
        rnd = int(parts[1])
    except (ValueError, IndexError):
        await query.answer(text="Invalid selection", show_alert=True)
        return

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

    try:
        stops = await _get_pitstops(repo, season, rnd)
        completed = list(range(1, (bounds.get("last_completed_round") or 0) + 1))
        text = format_pitstops(race, stops, rnd) if stops else no_data_message("pit stop data")
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=round_keyboard("pit", rnd, completed),
        )
    except BadRequest:
        pass
    except Exception as e:
        log.warning("pitstops_callback_failed", error=str(e))
        await query.answer(text="Failed to load data", show_alert=True)
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


def _laps_summary_keyboard(rnd: int, navigable_rounds: list[int]) -> InlineKeyboardMarkup:
    nav_row = round_keyboard("lap", rnd, navigable_rounds).inline_keyboard[0]
    mode_row = [
        InlineKeyboardButton("📊 By Lap", callback_data=f"lap:{rnd}:l:1"),
        InlineKeyboardButton("🏎 By Driver", callback_data=f"lap:{rnd}:dp"),
    ]
    return InlineKeyboardMarkup([nav_row, mode_row])


def _laps_per_lap_keyboard(rnd: int, current_lap: int, total_laps: int) -> InlineKeyboardMarkup:
    nav_row: list[InlineKeyboardButton] = []
    if current_lap > 1:
        nav_row.append(InlineKeyboardButton("◀", callback_data=f"lap:{rnd}:l:{current_lap - 1}"))
    nav_row.append(
        InlineKeyboardButton(
            f"Lap {current_lap}/{total_laps}",
            callback_data=f"lap:{rnd}:l:{current_lap}",
        )
    )
    if current_lap < total_laps:
        nav_row.append(InlineKeyboardButton("▶", callback_data=f"lap:{rnd}:l:{current_lap + 1}"))
    back_row = [InlineKeyboardButton("🔙 Summary", callback_data=f"lap:{rnd}:s")]
    return InlineKeyboardMarkup([nav_row, back_row])


def _laps_driver_picker_keyboard(
    rnd: int, driver_ids: list[str], drivers: dict[int, Driver] | None = None
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
    rows.append([InlineKeyboardButton("🔙 Summary", callback_data=f"lap:{rnd}:s")])
    return InlineKeyboardMarkup(rows)


def _laps_per_driver_keyboard(
    rnd: int, driver_id: str, page: int, total_laps: int
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
            f"{start}–{end} of {total_laps}",
            callback_data=f"lap:{rnd}:d:{driver_id}:{page}",
        )
    )
    if page < total_pages - 1:
        nav_row.append(
            InlineKeyboardButton("▶", callback_data=f"lap:{rnd}:d:{driver_id}:{page + 1}")
        )
    back_row = [InlineKeyboardButton("🔙 Drivers", callback_data=f"lap:{rnd}:dp")]
    return InlineKeyboardMarkup([nav_row, back_row])


async def laps_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        races, bounds, season = await load_schedule_and_bounds(context)
    except RuntimeError:
        await update.effective_message.reply_text(no_data_message("schedule"))
        return

    rnd = resolve_default_round(bounds)
    if rnd is None:
        await update.effective_message.reply_text(no_data_message("lap data"))
        return

    repo = context.bot_data["repo"]
    race = next((r for r in races if r.round == rnd), None)
    if not race:
        await update.effective_message.reply_text(no_data_message("lap data"))
        return
    laps = await _get_laps(repo, season, rnd)
    if not laps:
        await update.effective_message.reply_text(no_data_message("lap data"))
        return

    drivers_map = await repo.get_drivers_map(season)

    completed = list(range(1, (bounds.get("last_completed_round") or 0) + 1))
    await update.effective_message.reply_text(
        format_laps_summary(race, laps, drivers_map),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_laps_summary_keyboard(rnd, completed),
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

    parts = query.data.split(":")  # e.g. ["lap", "10", "d", "VER", "0"] or ["lap", "10"]
    try:
        rnd = int(parts[1])
    except (ValueError, IndexError):
        await query.answer(text="Invalid selection", show_alert=True)
        return
    mode = parts[2] if len(parts) > 2 else "s"

    try:
        races, bounds, season = await load_schedule_and_bounds(context)
    except RuntimeError:
        await query.answer(text="Schedule unavailable", show_alert=True)
        return

    repo = context.bot_data["repo"]
    race = next((r for r in races if r.round == rnd), None)
    completed = list(range(1, (bounds.get("last_completed_round") or 0) + 1))
    drivers_map = await repo.get_drivers_map(season)

    try:
        laps = await _get_laps(repo, season, rnd)
        if not laps:
            await query.answer(text="No lap data available", show_alert=True)
            return

        if mode == "s":
            # Summary
            text = format_laps_summary(race, laps, drivers_map)
            keyboard = _laps_summary_keyboard(rnd, completed)

        elif mode == "l":
            # Per-lap
            if len(parts) < 4:
                await query.answer(text="Invalid selection", show_alert=True)
                return
            try:
                lap_num = int(parts[3])
            except ValueError:
                await query.answer(text="Invalid selection", show_alert=True)
                return
            total_laps = max(lap.lap_number for lap in laps)
            lap_num = max(1, min(lap_num, total_laps))
            text = format_laps_by_lap(race, laps, lap_num, total_laps, drivers_map)
            keyboard = _laps_per_lap_keyboard(rnd, lap_num, total_laps)

        elif mode == "dp":
            # Driver picker
            driver_ids = sorted({lap.driver_id for lap in laps})
            text = format_laps_driver_picker(race)
            keyboard = _laps_driver_picker_keyboard(rnd, driver_ids, drivers_map)

        elif mode == "d":
            # Per-driver
            if len(parts) < 5:
                await query.answer(text="Invalid selection", show_alert=True)
                return
            driver_id = parts[3]
            try:
                page = int(parts[4])
            except ValueError:
                await query.answer(text="Invalid selection", show_alert=True)
                return
            driver_laps = [lap for lap in laps if lap.driver_id == driver_id]
            if not driver_laps:
                await query.answer(text=f"No data for driver {driver_id}", show_alert=True)
                return
            total_laps = len(driver_laps)
            total_pages = (total_laps + _LAPS_PAGE_SIZE - 1) // _LAPS_PAGE_SIZE
            page = max(0, min(page, total_pages - 1))
            text = format_laps_by_driver(race, laps, driver_id, page, drivers_map)
            keyboard = _laps_per_driver_keyboard(rnd, driver_id, page, total_laps)

        else:
            return

        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

    except BadRequest:
        pass
    except Exception as e:
        log.warning("laps_callback_failed", error=str(e))
        await query.answer(text="Failed to load data", show_alert=True)
        return

    await query.answer()


def register(app: Application) -> None:
    app.add_handler(CommandHandler("pitstops", pitstops_handler))
    app.add_handler(CommandHandler("laps", laps_handler))
    app.add_handler(CallbackQueryHandler(_pitstops_callback, pattern=r"^pit:"))
    app.add_handler(CallbackQueryHandler(_laps_callback, pattern=r"^lap:"))
