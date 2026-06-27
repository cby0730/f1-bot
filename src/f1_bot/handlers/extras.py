"""Handlers for /driver and /circuit — fuzzy search or interactive menu over current season data."""

import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from f1_bot.formatting.emoji import circuit_flag_icon, flag_icon
from f1_bot.formatting.messages import (
    _esc,
    format_circuit_info,
    format_driver_profile,
    no_data_message,
)
from f1_bot.utils.fuzzy_match import match_circuit, match_driver


def _driver_menu_keyboard(drivers: list) -> InlineKeyboardMarkup:
    """Build a 2-column inline keyboard for selecting a driver."""
    buttons = []
    for d in drivers:
        flag = flag_icon(d.nationality)
        label = f"{flag} {d.family_name}"
        buttons.append(InlineKeyboardButton(label, callback_data=f"drv:detail:{d.driver_id}"))

    # Chunk into 2 columns
    keyboard = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
    return InlineKeyboardMarkup(keyboard)


def _circuit_menu_keyboard(round_circuits: list) -> InlineKeyboardMarkup:
    """Build a 2-column inline keyboard for selecting a circuit."""
    buttons = []
    for rnd, c in round_circuits:
        flag = circuit_flag_icon(c.country)
        label = f"R{rnd} {flag} {c.locality}"
        buttons.append(InlineKeyboardButton(label, callback_data=f"circ:detail:{c.circuit_id}"))

    # Chunk into 2 columns
    keyboard = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
    return InlineKeyboardMarkup(keyboard)


async def driver_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    repo = context.bot_data.get("repo")
    season = datetime.date.today().year

    if not context.args:
        if not repo:
            await update.effective_message.reply_text(no_data_message("driver list"))
            return
        try:
            standings = await repo.get_driver_standings(season)
        except Exception:
            standings = []

        if not standings:
            await update.effective_message.reply_text(no_data_message("driver list"))
            return

        drivers = [s.driver for s in sorted(standings, key=lambda s: s.position)]
        keyboard = _driver_menu_keyboard(drivers)
        await update.effective_message.reply_text(
            "🏎 Select a driver:",
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    query = " ".join(context.args)
    if not repo:
        await update.effective_message.reply_text(no_data_message("driver list"))
        return

    try:
        standings = await repo.get_driver_standings(season)
        drivers = [s.driver for s in standings]
    except Exception:
        standings = []
        drivers = []

    if not drivers:
        try:
            drivers_map = await repo.get_drivers_by_id_map(season)
            seen_ids = set()
            drivers = []
            for d in drivers_map.values():
                if d.driver_id not in seen_ids:
                    seen_ids.add(d.driver_id)
                    drivers.append(d)
        except Exception:  # noqa: S110
            pass

    if not drivers:
        await update.effective_message.reply_text(no_data_message("driver list"))
        return

    driver = match_driver(query, drivers)
    if not driver:
        await update.effective_message.reply_text(
            f"❓ No driver found matching *{_esc(query)}*. Try a last name or 3-letter code.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    standing = None
    if standings:
        standing = next((s for s in standings if s.driver.driver_id == driver.driver_id), None)

    await update.effective_message.reply_text(
        format_driver_profile(driver, standing),
        parse_mode=ParseMode.MARKDOWN,
    )


async def circuit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    repo = context.bot_data.get("repo")
    season = datetime.date.today().year

    if not context.args:
        if not repo:
            await update.effective_message.reply_text(no_data_message("circuit list"))
            return
        try:
            round_circuits = await repo.get_circuits_for_season(season)
        except Exception:
            round_circuits = []

        if not round_circuits:
            await update.effective_message.reply_text(no_data_message("circuit list"))
            return

        keyboard = _circuit_menu_keyboard(round_circuits)
        await update.effective_message.reply_text(
            "📍 Select a circuit:",
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    query = " ".join(context.args)
    if not repo:
        await update.effective_message.reply_text(no_data_message("circuit list"))
        return

    try:
        schedule = await repo.get_schedule(season)
    except Exception:
        schedule = []

    if not schedule:
        await update.effective_message.reply_text(no_data_message("circuit list"))
        return

    seen = set()
    circuits = []
    for r in schedule:
        if r.circuit.circuit_id not in seen:
            seen.add(r.circuit.circuit_id)
            circuits.append(r.circuit)

    circuit = match_circuit(query, circuits)
    if not circuit:
        await update.effective_message.reply_text(
            f"❓ No circuit found matching *{_esc(query)}*.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    recent_races = [r for r in schedule if r.circuit.circuit_id == circuit.circuit_id]

    await update.effective_message.reply_text(
        format_circuit_info(circuit, recent_races),
        parse_mode=ParseMode.MARKDOWN,
    )


async def _extras_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return

    data = query.data
    try:
        parts = data.split(":", 2)
        prefix = parts[0]
        action = parts[1]
        target_id = parts[2] if len(parts) > 2 else None
    except (ValueError, IndexError):
        try:
            await query.answer(text="Invalid selection", show_alert=True)
        except Exception:  # noqa: S110
            pass
        return

    repo = context.bot_data.get("repo")
    if not repo:
        try:
            await query.answer(text="Database unavailable", show_alert=True)
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
                        text=no_data_message("driver list"),
                        parse_mode=ParseMode.MARKDOWN,
                    )
                    return
                drivers = [s.driver for s in sorted(standings, key=lambda s: s.position)]
                keyboard = _driver_menu_keyboard(drivers)
                await query.answer()
                await query.edit_message_text(
                    text="🏎 Select a driver:",
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
                    await query.answer(text="Driver not found", show_alert=True)
                    return

                text = format_driver_profile(driver, standing)
                keyboard = InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🔙 Back", callback_data="drv:list")]]
                )
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
                        text=no_data_message("circuit list"),
                        parse_mode=ParseMode.MARKDOWN,
                    )
                    return
                keyboard = _circuit_menu_keyboard(round_circuits)
                await query.answer()
                await query.edit_message_text(
                    text="📍 Select a circuit:",
                    reply_markup=keyboard,
                    parse_mode=ParseMode.MARKDOWN,
                )
            elif action == "detail" and target_id:
                schedule = await repo.get_schedule(season)
                circuit = next(
                    (r.circuit for r in schedule if r.circuit.circuit_id == target_id), None
                )

                if not circuit:
                    await query.answer(text="Circuit not found", show_alert=True)
                    return

                recent_races = [r for r in schedule if r.circuit.circuit_id == target_id]

                text = format_circuit_info(circuit, recent_races)
                keyboard = InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🔙 Back", callback_data="circ:list")]]
                )
                await query.answer()
                await query.edit_message_text(
                    text=text,
                    reply_markup=keyboard,
                    parse_mode=ParseMode.MARKDOWN,
                )
    except Exception:
        try:
            await query.answer(text="An error occurred", show_alert=True)
        except Exception:  # noqa: S110
            pass


def register(app: Application) -> None:
    app.add_handler(CommandHandler("driver", driver_handler))
    app.add_handler(CommandHandler("circuit", circuit_handler))
    app.add_handler(CallbackQueryHandler(_extras_callback, pattern=r"^(drv|circ):"))
