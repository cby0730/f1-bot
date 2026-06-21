from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from f1_bot.handlers.errors import CommandValidationError, error_handler
from telegram import Update
from telegram.error import NetworkError


@pytest.mark.asyncio
async def test_error_handler_command_validation():
    update = MagicMock(spec=Update)
    update.effective_message = AsyncMock()
    context = MagicMock()
    context.error = CommandValidationError("Invalid round parameter")

    await error_handler(update, context)

    update.effective_message.reply_text.assert_awaited_once_with(
        "Invalid round parameter",
        parse_mode="Markdown",
    )


@pytest.mark.asyncio
async def test_error_handler_network_error():
    update = MagicMock(spec=Update)
    update.effective_message = AsyncMock()
    context = MagicMock()
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
    context.error = Exception("generic database failure")

    with patch("f1_bot.handlers.errors.log") as mock_log:
        await error_handler(update, context)
        mock_log.error.assert_called_once()
        # Verify the key unhandled_error is logged
        args, kwargs = mock_log.error.call_args
        assert args[0] == "unhandled_error"

    # User should get a generic error message
    update.effective_message.reply_text.assert_awaited_once_with(
        "Something went wrong. Please try again in a moment."
    )
