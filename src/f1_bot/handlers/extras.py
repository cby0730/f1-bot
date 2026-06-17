"""Handlers for /driver and /circuit — fuzzy search over current season data."""

import datetime

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

from f1_bot.formatting.messages import (
    _esc,
    format_circuit_info,
    format_driver_profile,
    no_data_message,
)
from f1_bot.utils.fuzzy_match import match_circuit, match_driver


async def driver_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.effective_message.reply_text("Usage: /driver <name>  e.g. /driver hamilton")
        return

    query = " ".join(context.args)
    jolpica = context.bot_data["jolpica"]
    season = str(datetime.date.today().year)

    try:
        drivers = await jolpica.get_drivers(season)
    except Exception:
        await update.effective_message.reply_text(no_data_message("driver list"))
        return

    driver = match_driver(query, drivers)
    if not driver:
        await update.effective_message.reply_text(
            f"❓ No driver found matching *{_esc(query)}*. Try a last name or 3-letter code.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # Try to find their current standing for extra context
    standing = None
    try:
        standings = await jolpica.get_driver_standings(season)
        standing = next((s for s in standings if s.driver.driver_id == driver.driver_id), None)
    except Exception:
        pass

    await update.effective_message.reply_text(
        format_driver_profile(driver, standing),
        parse_mode=ParseMode.MARKDOWN,
    )


async def circuit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.effective_message.reply_text("Usage: /circuit <name>  e.g. /circuit monaco")
        return

    query = " ".join(context.args)
    jolpica = context.bot_data["jolpica"]
    season = str(datetime.date.today().year)

    try:
        circuits = await jolpica.get_circuits(season)
    except Exception:
        await update.effective_message.reply_text(no_data_message("circuit list"))
        return

    circuit = match_circuit(query, circuits)
    if not circuit:
        await update.effective_message.reply_text(
            f"❓ No circuit found matching *{_esc(query)}*.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # Find races at this circuit for recent winner context
    recent_races = None
    try:
        schedule = await jolpica.get_current_schedule()
        recent_races = [r for r in schedule if r.circuit.circuit_id == circuit.circuit_id]
    except Exception:
        pass

    await update.effective_message.reply_text(
        format_circuit_info(circuit, recent_races),
        parse_mode=ParseMode.MARKDOWN,
    )


def register(app: Application) -> None:
    app.add_handler(CommandHandler("driver", driver_handler))
    app.add_handler(CommandHandler("circuit", circuit_handler))
