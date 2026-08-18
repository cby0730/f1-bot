"""/settings hub — launch pad onto the existing timezone and language pickers.

``set:tz`` and ``set:lang`` *edit* the hub message in place. ``lang:picker`` (the
/start welcome button) is a different path that *replies a new message* so the
welcome is not swallowed — do not reuse it here.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from f1_bot.formatting.i18n import lang_name, t
from f1_bot.handlers.context import resolve_context
from f1_bot.handlers.language import language_keyboard
from f1_bot.handlers.timezone import _region_keyboard

_CB_TZ = "set:tz"
_CB_LANG = "set:lang"


def _hub_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(t("settings.btn_timezone", lang), callback_data=_CB_TZ),
                InlineKeyboardButton(t("settings.btn_language", lang), callback_data=_CB_LANG),
            ]
        ]
    )


async def settings_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ctx = await resolve_context(update, context.bot_data["repo"])
    await update.effective_message.reply_text(
        t("settings.hub", ctx.lang),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_hub_keyboard(ctx.lang),
    )


async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    repo = context.bot_data["repo"]
    ctx = await resolve_context(update, repo)

    try:
        if query.data == _CB_TZ:
            await query.edit_message_text(
                t("settings.tz_picker", ctx.lang, tz=ctx.tz),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=_region_keyboard(ctx.lang),
            )
        elif query.data == _CB_LANG:
            await query.edit_message_text(
                t("settings.lang_picker", ctx.lang, lang=lang_name(ctx.lang, ctx.lang)),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=language_keyboard(ctx.lang),
            )
    except BadRequest:
        pass


def register(app: Application) -> None:
    app.add_handler(CommandHandler("settings", settings_handler))
    app.add_handler(CallbackQueryHandler(settings_callback, pattern=r"^set:"))
