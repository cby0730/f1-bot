import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from f1_bot.formatting.messages import (
    format_constructor_standings,
    format_driver_standings,
    no_data_message,
)

_WDC = "standings:wdc"
_WCC = "standings:wcc"


async def standings_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    repo = context.bot_data["repo"]
    season = datetime.date.today().year
    standings = await repo.get_driver_standings(season)
    if not standings:
        await update.effective_message.reply_text(no_data_message("standings"))
        return
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🏆 Drivers", callback_data=_WDC),
                InlineKeyboardButton("🏭 Constructors", callback_data=_WCC),
            ]
        ]
    )
    await update.effective_message.reply_text(
        format_driver_standings(standings, season),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard,
    )


async def standings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    repo = context.bot_data["repo"]
    season = datetime.date.today().year
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🏆 Drivers", callback_data=_WDC),
                InlineKeyboardButton("🏭 Constructors", callback_data=_WCC),
            ]
        ]
    )
    if query.data == _WDC:
        standings = await repo.get_driver_standings(season)
        text = (
            format_driver_standings(standings, season)
            if standings
            else no_data_message("standings")
        )
    else:
        standings = await repo.get_constructor_standings(season)
        text = (
            format_constructor_standings(standings, season)
            if standings
            else no_data_message("standings")
        )

    try:
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
    except BadRequest:
        pass


def register(app: Application) -> None:
    app.add_handler(CommandHandler("standings", standings_handler))
    app.add_handler(CallbackQueryHandler(standings_callback, pattern=r"^standings:"))
