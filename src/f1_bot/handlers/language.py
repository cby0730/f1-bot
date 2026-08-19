from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from f1_bot.formatting.i18n import SHIPPED_LANGS, lang_name, t
from f1_bot.handlers.context import resolve_context

_CB_SET = "lang:set:"
CB_PICKER = "lang:picker"


def language_keyboard(current: str) -> InlineKeyboardMarkup:
    """Single-level picker over `SHIPPED_LANGS`, current selection ticked.

    Exposed (not inlined) because `/start`'s welcome button opens the same picker.
    No region/group drill-down — with two options that would be pure friction.
    Each language is named in *itself*, so a user stranded in a language they
    cannot read can still find their way back.
    """
    rows = [
        [
            InlineKeyboardButton(
                f"{'✅ ' if code == current else ''}{lang_name(code, code)}",
                callback_data=f"{_CB_SET}{code}",
            )
        ]
        for code in SHIPPED_LANGS
    ]
    return InlineKeyboardMarkup(rows)


async def language_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    repo = context.bot_data["repo"]
    ctx = await resolve_context(update, repo)

    await update.effective_message.reply_text(
        t("settings.lang_picker", ctx.lang, lang=lang_name(ctx.lang, ctx.lang)),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=language_keyboard(ctx.lang),
    )


async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    repo = context.bot_data["repo"]

    if query.data == CB_PICKER:
        # Opened from /start's welcome button. Reply with a *new* message rather
        # than editing: the welcome carries the whole command list, and swallowing
        # it to show a two-button picker would be a bad trade.
        ctx = await resolve_context(update, repo)
        await update.effective_message.reply_text(
            t("settings.lang_picker", ctx.lang, lang=lang_name(ctx.lang, ctx.lang)),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=language_keyboard(ctx.lang),
        )
        return

    code = query.data[len(_CB_SET) :] if query.data.startswith(_CB_SET) else ""
    if code not in SHIPPED_LANGS:
        ctx = await resolve_context(update, repo)
        await query.edit_message_text(
            t("common.invalid_selection", ctx.lang), parse_mode=ParseMode.MARKDOWN
        )
        return
    await _save_lang(repo, update.effective_user.id, code, query)


async def _save_lang(repo, telegram_id: int, code: str, query) -> None:
    """Persist the choice and confirm in the **newly chosen** language.

    Confirming in the old language would be the one message guaranteed to be
    unreadable to the user who just asked to switch away from it.
    """
    await repo.set_user_language(telegram_id, code)
    text = t("settings.lang_saved", code, lang=lang_name(code, code))
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)


def register(app: Application) -> None:
    app.add_handler(CommandHandler("language", language_handler))
    app.add_handler(CallbackQueryHandler(language_callback, pattern=r"^lang:"))
