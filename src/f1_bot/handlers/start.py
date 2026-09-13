"""/start — short welcome plus an eight-button command grid.

Each ``start:{token}`` callback reuses the existing command handler via
``update.effective_message.reply_text``, so the tap opens a *new* message and
does not duplicate any render logic. The callback resolves the user's language
only on the invalid-token branch — the dispatched handler already does it once.
"""

from telegram import InlineKeyboardButton, LinkPreviewOptions, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from f1_bot.formatting.i18n import t
from f1_bot.handlers.context import resolve_context
from f1_bot.handlers.extras import circuit_handler, driver_handler
from f1_bot.handlers.notifications import remind_handler
from f1_bot.handlers.pagination import two_column_keyboard
from f1_bot.handlers.results import results_handler
from f1_bot.handlers.schedule import next_handler, schedule_handler
from f1_bot.handlers.settings import settings_handler
from f1_bot.handlers.standings import standings_handler

_MENU = (
    ("next", "start.btn_next", next_handler),
    ("schedule", "start.btn_schedule", schedule_handler),
    ("results", "start.btn_results", results_handler),
    ("standings", "start.btn_standings", standings_handler),
    ("driver", "start.btn_driver", driver_handler),
    ("circuit", "start.btn_circuit", circuit_handler),
    ("remind", "start.btn_remind", remind_handler),
    ("settings", "start.btn_settings", settings_handler),
)

_DISPATCH = {token: handler for token, _, handler in _MENU}


def _welcome_text(lang: str) -> str:
    return (
        t("start.welcome_intro", lang)
        + "\n\n"
        + t("start.data_sources", lang)
        + "\n\n"
        + t("start.support", lang)
    )


def _menu_keyboard(lang: str):
    buttons = [
        InlineKeyboardButton(t(key, lang), callback_data=f"start:{token}")
        for token, key, _ in _MENU
    ]
    return two_column_keyboard(buttons)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ctx = await resolve_context(update, context.bot_data["repo"])
    await update.effective_message.reply_text(
        _welcome_text(ctx.lang),
        parse_mode=ParseMode.MARKDOWN,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
        reply_markup=_menu_keyboard(ctx.lang),
    )


async def _start_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    try:
        token = query.data.split(":", 1)[1]
    except (ValueError, IndexError, AttributeError):
        token = None

    handler = _DISPATCH.get(token) if token else None
    if handler is None:
        # Only the error toast needs the user's language; the happy path leaves
        # the single resolve_context call to the dispatched handler.
        ctx = await resolve_context(update, context.bot_data["repo"])
        await query.answer(text=t("common.invalid_selection", ctx.lang), show_alert=True)
        return

    if update.effective_message is None:
        # Telegram reports the welcome as InaccessibleMessage (>48h old or
        # deleted); there is nothing to reply to, so treat it as a dead button.
        await query.answer()
        return

    await query.answer()
    await handler(update, context)


def register(app: Application) -> None:
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CallbackQueryHandler(_start_menu_callback, pattern=r"^start:"))
