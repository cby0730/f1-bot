from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

from f1_bot.formatting.i18n import SHIPPED_LANGS, lang_name, t
from f1_bot.handlers.context import resolve_context

_CB_SET = "lang:set:"


def language_keyboard(current: str) -> InlineKeyboardMarkup:
    """Single-level picker over `SHIPPED_LANGS`, current selection ticked.

    Exposed (not inlined) because `/settings` `set:lang` opens the same picker.
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


async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    repo = context.bot_data["repo"]

    if not query.data or not query.data.startswith(_CB_SET):
        # Stale `lang:picker` (and any other leftover `lang:` payload) is a dead
        # button: answered so the client spinner stops, but no edit / no toast.
        return

    code = query.data[len(_CB_SET) :]
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
    app.add_handler(CallbackQueryHandler(language_callback, pattern=r"^lang:"))
