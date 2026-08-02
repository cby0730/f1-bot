from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram import Update
from telegram.error import NetworkError

from f1_bot.formatting.i18n import t
from f1_bot.handlers.errors import CommandValidationError, error_handler
from f1_bot.models.user import UserPreference


def _zh_hant_repo() -> AsyncMock:
    """A repo whose only user prefers Traditional Chinese.

    The error handler must resolve language *centrally* from this preference, not
    from anything the raise site knows.
    """
    repo = AsyncMock()
    repo.get_user_preference = AsyncMock(
        return_value=UserPreference(telegram_id=1, timezone="UTC", language="zh-Hant")
    )
    return repo


@pytest.mark.asyncio
async def test_error_handler_command_validation():
    """A CommandValidationError is rendered from its catalog key and replied as Markdown.

    Post-005 the exception carries a *key*, not a rendered English string; with no
    resolvable user the handler falls back to English.
    """
    update = MagicMock(spec=Update)
    update.effective_message = AsyncMock()
    context = MagicMock()
    context.bot_data = {}  # no repo → _safe_context falls back to English
    context.error = CommandValidationError("common.round_not_found")

    await error_handler(update, context)

    update.effective_message.reply_text.assert_awaited_once_with(
        t("common.round_not_found", "en"),
        parse_mode="Markdown",
    )


@pytest.mark.asyncio
async def test_error_handler_command_validation_localized():
    """The SAME key raised for a zh-Hant user is replied in Chinese.

    Proves the language is resolved from the user's stored preference in one central
    place, not baked in where the error is raised.
    """
    update = MagicMock(spec=Update)
    update.effective_user = MagicMock()
    update.effective_user.id = 1
    update.effective_message = AsyncMock()
    context = MagicMock()
    context.bot_data = {"repo": _zh_hant_repo()}
    context.error = CommandValidationError("common.round_not_found")

    await error_handler(update, context)

    update.effective_message.reply_text.assert_awaited_once_with(
        t("common.round_not_found", "zh-Hant"),
        parse_mode="Markdown",
    )
    # Sanity: the two languages actually differ, so this asserts more than "some text".
    assert t("common.round_not_found", "zh-Hant") != t("common.round_not_found", "en")


@pytest.mark.asyncio
async def test_error_handler_command_validation_with_kwargs():
    """CommandValidationError kwargs are interpolated into the catalog template."""
    update = MagicMock(spec=Update)
    update.effective_message = AsyncMock()
    context = MagicMock()
    context.bot_data = {}
    context.error = CommandValidationError("common.no_data", what="results")

    await error_handler(update, context)

    update.effective_message.reply_text.assert_awaited_once_with(
        t("common.no_data", "en", what="results"),
        parse_mode="Markdown",
    )


@pytest.mark.asyncio
async def test_error_handler_no_effective_user_falls_back_to_english():
    """The handler must never raise when there is no effective user; it uses English.

    Error reporting is the last line of defence — an Update without a user (or a
    failing DB) must still produce a reply, not a second exception.
    """
    update = MagicMock(spec=Update)
    update.effective_user = None
    update.effective_message = AsyncMock()
    context = MagicMock()
    context.bot_data = {"repo": AsyncMock()}
    context.error = CommandValidationError("common.round_not_found")

    await error_handler(update, context)

    update.effective_message.reply_text.assert_awaited_once_with(
        t("common.round_not_found", "en"),
        parse_mode="Markdown",
    )


@pytest.mark.asyncio
async def test_error_handler_network_error():
    update = MagicMock(spec=Update)
    update.effective_message = AsyncMock()
    context = MagicMock()
    context.bot_data = {}  # repo absent → context resolution never warns
    context.error = NetworkError("httpx.ReadError")

    with patch("f1_bot.handlers.errors.log") as mock_log:
        await error_handler(update, context)
        mock_log.warning.assert_called_once_with(
            "telegram_network_error",
            error="httpx.ReadError",
        )

    # NetworkError should not send message to user
    update.effective_message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_error_handler_unhandled_exception():
    update = MagicMock(spec=Update)
    update.effective_message = AsyncMock()
    context = MagicMock()
    context.bot_data = {}
    context.error = Exception("generic database failure")

    with patch("f1_bot.handlers.errors.log") as mock_log:
        await error_handler(update, context)
        mock_log.error.assert_called_once()
        # Verify the key unhandled_error is logged
        args, kwargs = mock_log.error.call_args
        assert args[0] == "unhandled_error"

    # User should get a generic error message (English fallback: no repo)
    update.effective_message.reply_text.assert_awaited_once_with(
        t("common.generic_error", "en")
    )


@pytest.mark.asyncio
async def test_error_handler_unhandled_exception_localized():
    """The generic-error reply is rendered in the user's language, not hardcoded English."""
    update = MagicMock(spec=Update)
    update.effective_user = MagicMock()
    update.effective_user.id = 1
    update.effective_message = AsyncMock()
    context = MagicMock()
    context.bot_data = {"repo": _zh_hant_repo()}
    context.error = Exception("generic database failure")

    await error_handler(update, context)

    update.effective_message.reply_text.assert_awaited_once_with(
        t("common.generic_error", "zh-Hant")
    )
