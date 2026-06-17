import traceback

import structlog
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

log = structlog.get_logger(__name__)

_USER_MSG = "Something went wrong. Please try again in a moment."


class CommandValidationError(Exception):
    """Raised when user input for a bot command is invalid or out-of-bounds."""

    pass


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    if isinstance(context.error, CommandValidationError):
        if isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text(
                str(context.error),
                parse_mode=ParseMode.MARKDOWN,
            )
            return

    log.error(
        "unhandled_error",
        error=str(context.error),
        traceback=traceback.format_exception(
            type(context.error), context.error, context.error.__traceback__
        ),
    )

    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(_USER_MSG)
