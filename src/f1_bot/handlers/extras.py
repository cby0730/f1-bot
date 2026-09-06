"""Handlers for /driver and /circuit — interactive menus over current season data."""

import datetime

import structlog
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from f1_bot.formatting.context import RenderContext
from f1_bot.formatting.emoji import circuit_flag_icon, flag_icon
from f1_bot.formatting.i18n import t
from f1_bot.formatting.messages import (
    format_circuit_info,
    format_driver_profile,
    no_data_message,
)
from f1_bot.handlers.context import resolve_context
from f1_bot.handlers.pagination import two_column_keyboard

log = structlog.get_logger(__name__)


def _profile_keyboard(driver_id: str, lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    t("extras.compare_with", lang), callback_data=f"cmp:a:{driver_id}"
                )
            ],
            [InlineKeyboardButton(t("common.back", lang), callback_data="drv:list")],
        ]
    )


def _driver_menu_keyboard(drivers: list) -> InlineKeyboardMarkup:
    """Build a 2-column inline keyboard for selecting a driver."""
    buttons = []
    for d in drivers:
        flag = flag_icon(d.nationality)
        label = f"{flag} {d.family_name}"
        buttons.append(InlineKeyboardButton(label, callback_data=f"drv:detail:{d.driver_id}"))

    return two_column_keyboard(buttons)


def _circuit_menu_keyboard(round_circuits: list) -> InlineKeyboardMarkup:
    """Build a 2-column inline keyboard for selecting a circuit."""
    buttons = []
    for rnd, c in round_circuits:
        flag = circuit_flag_icon(c.country)
        label = f"R{rnd} {flag} {c.locality}"
        buttons.append(InlineKeyboardButton(label, callback_data=f"circ:detail:{c.circuit_id}"))

    return two_column_keyboard(buttons)


async def driver_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    repo = context.bot_data.get("repo")
    ctx = await resolve_context(update, repo) if repo else RenderContext()
    season = datetime.date.today().year

    if not repo:
        await update.effective_message.reply_text(no_data_message("common.noun_driver_list", ctx))
        return
    try:
        standings = await repo.get_driver_standings(season)
    except Exception:
        standings = []

    if not standings:
        await update.effective_message.reply_text(no_data_message("common.noun_driver_list", ctx))
        return

    drivers = [s.driver for s in sorted(standings, key=lambda s: s.position)]
    keyboard = _driver_menu_keyboard(drivers)
    await update.effective_message.reply_text(
        t("extras.select_driver", ctx.lang),
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN,
    )


async def circuit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    repo = context.bot_data.get("repo")
    ctx = await resolve_context(update, repo) if repo else RenderContext()
    season = datetime.date.today().year

    if not repo:
        await update.effective_message.reply_text(no_data_message("common.noun_circuit_list", ctx))
        return
    try:
        round_circuits = await repo.get_circuits_for_season(season)
    except Exception:
        round_circuits = []

    if not round_circuits:
        await update.effective_message.reply_text(no_data_message("common.noun_circuit_list", ctx))
        return

    keyboard = _circuit_menu_keyboard(round_circuits)
    await update.effective_message.reply_text(
        t("extras.select_circuit", ctx.lang),
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN,
    )


async def _extras_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return

    repo = context.bot_data.get("repo")
    ctx = await resolve_context(update, repo) if repo else RenderContext()

    data = query.data
    try:
        parts = data.split(":", 2)
        prefix = parts[0]
        action = parts[1]
        target_id = parts[2] if len(parts) > 2 else None
    except (ValueError, IndexError):
        try:
            await query.answer(text=t("common.invalid_selection", ctx.lang), show_alert=True)
        except Exception:  # noqa: S110
            pass
        return

    if not repo:
        try:
            await query.answer(text=t("common.database_unavailable", ctx.lang), show_alert=True)
        except Exception:  # noqa: S110
            pass
        return

    season = datetime.date.today().year

    try:
        if prefix == "drv":
            standings = await repo.get_driver_standings(season)
            if action == "list":
                if not standings:
                    await query.answer()
                    await query.edit_message_text(
                        text=no_data_message("common.noun_driver_list", ctx),
                        parse_mode=ParseMode.MARKDOWN,
                    )
                    return
                drivers = [s.driver for s in sorted(standings, key=lambda s: s.position)]
                keyboard = _driver_menu_keyboard(drivers)
                await query.answer()
                await query.edit_message_text(
                    text=t("extras.select_driver", ctx.lang),
                    reply_markup=keyboard,
                    parse_mode=ParseMode.MARKDOWN,
                )
            elif action == "detail" and target_id:
                standing = next((s for s in standings if s.driver.driver_id == target_id), None)
                if standing:
                    driver = standing.driver
                else:
                    drivers_map = await repo.get_drivers_by_id_map(season)
                    driver = drivers_map.get(target_id)

                if not driver:
                    await query.answer(text=t("extras.driver_not_found", ctx.lang), show_alert=True)
                    return

                text = format_driver_profile(driver, standing, ctx)
                keyboard = _profile_keyboard(driver.driver_id, ctx.lang)
                await query.answer()
                await query.edit_message_text(
                    text=text,
                    reply_markup=keyboard,
                    parse_mode=ParseMode.MARKDOWN,
                )

        elif prefix == "circ":
            if action == "list":
                round_circuits = await repo.get_circuits_for_season(season)
                if not round_circuits:
                    await query.answer()
                    await query.edit_message_text(
                        text=no_data_message("common.noun_circuit_list", ctx),
                        parse_mode=ParseMode.MARKDOWN,
                    )
                    return
                keyboard = _circuit_menu_keyboard(round_circuits)
                await query.answer()
                await query.edit_message_text(
                    text=t("extras.select_circuit", ctx.lang),
                    reply_markup=keyboard,
                    parse_mode=ParseMode.MARKDOWN,
                )
            elif action == "detail" and target_id:
                schedule = await repo.get_schedule(season)
                circuit = next(
                    (r.circuit for r in schedule if r.circuit.circuit_id == target_id), None
                )

                if not circuit:
                    await query.answer(
                        text=t("extras.circuit_not_found", ctx.lang), show_alert=True
                    )
                    return

                recent_races = [r for r in schedule if r.circuit.circuit_id == target_id]

                text = format_circuit_info(circuit, recent_races, ctx)
                keyboard = InlineKeyboardMarkup(
                    [[InlineKeyboardButton(t("common.back", ctx.lang), callback_data="circ:list")]]
                )
                await query.answer()
                await query.edit_message_text(
                    text=text,
                    reply_markup=keyboard,
                    parse_mode=ParseMode.MARKDOWN,
                )
    except Exception:
        log.exception("extras_callback_failed")
        try:
            await query.answer(text=t("common.error_occurred", ctx.lang), show_alert=True)
        except Exception:  # noqa: S110
            pass


def register(app: Application) -> None:
    app.add_handler(CommandHandler("driver", driver_handler))
    app.add_handler(CommandHandler("circuit", circuit_handler))
    app.add_handler(CallbackQueryHandler(_extras_callback, pattern=r"^(drv|circ):"))
