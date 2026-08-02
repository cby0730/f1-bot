import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from f1_bot.formatting.i18n import t
from f1_bot.formatting.messages import (
    format_constructor_standings,
    format_driver_standings,
    no_data_message,
)
from f1_bot.handlers.context import resolve_context

_WDC = "standings:wdc"
_WCC = "standings:wcc"


def _toggle_keyboard(lang: str) -> InlineKeyboardMarkup:
    # callback_data stays a stable slug; only the button label is translated.
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(t("standings.btn_drivers", lang), callback_data=_WDC),
                InlineKeyboardButton(t("standings.btn_constructors", lang), callback_data=_WCC),
            ]
        ]
    )


async def standings_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    repo = context.bot_data["repo"]
    ctx = await resolve_context(update, repo)
    season = datetime.date.today().year
    standings = await repo.get_driver_standings(season)
    if not standings:
        await update.effective_message.reply_text(no_data_message("common.noun_standings", ctx))
        return
    await update.effective_message.reply_text(
        format_driver_standings(standings, season, ctx),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_toggle_keyboard(ctx.lang),
    )


async def standings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    repo = context.bot_data["repo"]
    ctx = await resolve_context(update, repo)
    season = datetime.date.today().year
    if query.data == _WDC:
        standings = await repo.get_driver_standings(season)
        text = (
            format_driver_standings(standings, season, ctx)
            if standings
            else no_data_message("common.noun_standings", ctx)
        )
    else:
        standings = await repo.get_constructor_standings(season)
        text = (
            format_constructor_standings(standings, season, ctx)
            if standings
            else no_data_message("common.noun_standings", ctx)
        )

    try:
        await query.edit_message_text(
            text, parse_mode=ParseMode.MARKDOWN, reply_markup=_toggle_keyboard(ctx.lang)
        )
    except BadRequest:
        pass


def register(app: Application) -> None:
    app.add_handler(CommandHandler("standings", standings_handler))
    app.add_handler(CallbackQueryHandler(standings_callback, pattern=r"^standings:"))
