import traceback

import structlog
from telegram import Update
from telegram.constants import ParseMode
from telegram.error import BadRequest, NetworkError
from telegram.ext import ContextTypes

from f1_bot.formatting.context import RenderContext
from f1_bot.formatting.i18n import t
from f1_bot.handlers.context import resolve_context

log = structlog.get_logger(__name__)

_BENIGN_BAD_REQUESTS = ("Message is not modified", "Query is too old")


class CommandValidationError(Exception):
    """Raised when user input for a bot command is invalid or out-of-bounds.

    Carries a **catalog key + kwargs**, not a rendered string: the raise site has no
    business knowing the user's language, and a pre-rendered message would bake
    English into every validation path.
    """

    def __init__(self, key: str, **kwargs) -> None:
        self.key = key
        self.kwargs = kwargs
        super().__init__(key)


async def _safe_context(update: object, repo) -> RenderContext:
    """Resolve the render context without ever raising.

    The error handler is the last line of defence — if it throws, the user gets
    silence. Error paths can fire without an `Update` or an effective user, and the
    DB may be exactly what failed, so any failure here falls back to English.
    """
    try:
        if isinstance(update, Update) and repo is not None:
            return await resolve_context(update, repo)
    except Exception:  # noqa: BLE001 - error reporting must never fail
        log.warning("error_handler_context_failed", exc_info=True)
    return RenderContext()


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    ctx = await _safe_context(update, context.bot_data.get("repo"))

    if isinstance(context.error, CommandValidationError):
        if isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text(
                t(context.error.key, ctx.lang, **context.error.kwargs),
                parse_mode=ParseMode.MARKDOWN,
            )
            return

    # BadRequest subclasses NetworkError in PTB. Most BadRequests are our bug (e.g. a
    # Markdown parse failure) and fall through to unhandled_error — except these two,
    # which unguarded edit paths raise on a double-tap or a slow tap and are harmless.
    if isinstance(context.error, NetworkError) and (
        not isinstance(context.error, BadRequest)
        or any(s in str(context.error) for s in _BENIGN_BAD_REQUESTS)
    ):
        log.warning(
            "telegram_network_error",
            error=str(context.error),
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
        await update.effective_message.reply_text(t("common.generic_error", ctx.lang))
