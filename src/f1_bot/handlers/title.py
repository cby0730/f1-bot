"""/title is a hidden alias of /standings.

Stale ``title:wdc`` / ``title:wcc`` keyboards still render the standings view
(with the clinch strip). New messages emit ``standings:wdc`` / ``standings:wcc``.
"""

from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from f1_bot.handlers.standings import standings_callback, standings_handler

_WDC = "title:wdc"
_WCC = "title:wcc"


async def title_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await standings_handler(update, context)


async def title_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query.data == _WDC:
        query.data = "standings:wdc"
    elif query.data == _WCC:
        query.data = "standings:wcc"
    await standings_callback(update, context)


def register(app: Application) -> None:
    app.add_handler(CommandHandler("title", title_handler))
    app.add_handler(CallbackQueryHandler(title_callback, pattern=r"^title:"))
