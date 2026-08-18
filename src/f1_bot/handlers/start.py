from telegram import InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

from f1_bot.formatting.i18n import t
from f1_bot.handlers.context import resolve_context
from f1_bot.handlers.language import CB_PICKER


def _welcome_text(lang: str) -> str:
    return (
        t("start.welcome_intro", lang)
        + "\n\n"
        + t("start.help", lang)
        + "\n\n"
        + t("start.data_sources", lang)
        + "\n\n"
        + t("start.support", lang)
    )


def _language_button(lang: str) -> InlineKeyboardMarkup:
    """Persistent `🌐 Language / 語言` entry point on the welcome message.

    Deliberately bilingual and always shown: new users default to the platform
    language (`en` on Telegram) with no auto-detection, so this button is what stops
    a zh-Hant reader from being stranded in an English wall of text. It routes to
    `lang:picker`, handled by `handlers/language.py` — the picker keyboard itself is
    built there, in one place.
    """
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(t("settings.lang_button", lang), callback_data=CB_PICKER)]]
    )


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ctx = await resolve_context(update, context.bot_data["repo"])
    await update.effective_message.reply_text(
        _welcome_text(ctx.lang),
        parse_mode=ParseMode.MARKDOWN,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
        reply_markup=_language_button(ctx.lang),
    )


# Hidden alias: same welcome + language button as /start.
help_handler = start_handler


def register(app: Application) -> None:
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))
