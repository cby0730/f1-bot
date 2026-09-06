"""/title is a hidden alias of /standings.

Stale ``title:wdc`` / ``title:wcc`` keyboards still render the standings view
(with the clinch strip). New messages emit ``standings:wdc`` / ``standings:wcc``.
"""

from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from f1_bot.handlers.standings import render_standings_callback, standings_handler

_WDC = "title:wdc"


async def title_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await standings_handler(update, context)


async def title_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    table = "drivers" if query.data == _WDC else "constructors"
    await render_standings_callback(update, context, table)


def register(app: Application) -> None:
    app.add_handler(CommandHandler("title", title_handler))
    app.add_handler(CallbackQueryHandler(title_callback, pattern=r"^title:"))
