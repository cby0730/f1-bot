"""Tests for /timezone handler and callback."""

from unittest.mock import AsyncMock, MagicMock

from f1_bot.handlers.timezone import timezone_callback, timezone_handler


def _context(repo):
    ctx = MagicMock()
    ctx.bot_data = {"repo": repo}
    return ctx


def _update(args=None):
    update = MagicMock()
    update.effective_user.id = 123
    update.effective_message.reply_text = AsyncMock()
    ctx = MagicMock()
    ctx.args = args or []
    return update, ctx


async def test_timezone_handler_no_args_shows_region_picker():
    repo = MagicMock()
    repo.get_user_timezone = AsyncMock(return_value="UTC")
    update, _ = _update()
    ctx = _context(repo)
    ctx.args = []

    await timezone_handler(update, ctx)

    update.effective_message.reply_text.assert_called_once()
    text = update.effective_message.reply_text.call_args.args[0]
    assert "timezone" in text.lower() or "🌍" in text


async def test_timezone_handler_valid_timezone_saves_and_confirms():
    repo = MagicMock()
    repo.set_user_timezone = AsyncMock()
    update, _ = _update()
    ctx = _context(repo)
    ctx.args = ["Asia/Taipei"]

    await timezone_handler(update, ctx)

    # Single-column upsert: (telegram_id, tz) — never a whole UserPreference (which
    # would carry the language default and clobber the user's saved language).
    repo.set_user_timezone.assert_called_once_with(123, "Asia/Taipei")
    text = update.effective_message.reply_text.await_args.args[0]
    assert "Asia/Taipei" in text


async def test_timezone_handler_invalid_timezone_shows_error():
    repo = MagicMock()
    update, _ = _update()
    ctx = _context(repo)
    ctx.args = ["Mars/Olympus"]

    await timezone_handler(update, ctx)

    text = update.effective_message.reply_text.await_args.args[0]
    assert "❌" in text or "Unknown" in text
    repo.set_user_timezone.assert_not_called()


async def test_timezone_callback_region_shows_city_picker():
    """Selecting a region presents city buttons."""
    repo = MagicMock()
    query = MagicMock()
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    # Region slugs are stable lowercase identifiers carried in callback_data.
    query.data = "tz:region:asia"
    update = MagicMock()
    update.callback_query = query
    update.effective_user.id = 123
    ctx = _context(repo)

    await timezone_callback(update, ctx)

    query.answer.assert_called_once()
    query.edit_message_text.assert_called_once()
    text = query.edit_message_text.call_args.args[0]
    assert "Asia" in text


async def test_timezone_callback_back_shows_region_picker():
    repo = MagicMock()
    query = MagicMock()
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    query.data = "tz:region:__back__"
    update = MagicMock()
    update.callback_query = query
    update.effective_user.id = 123
    ctx = _context(repo)

    await timezone_callback(update, ctx)

    query.edit_message_text.assert_called_once()
    text = query.edit_message_text.call_args.args[0]
    assert "region" in text.lower() or "🌍" in text


async def test_timezone_callback_set_saves_timezone():
    repo = MagicMock()
    repo.set_user_timezone = AsyncMock()
    query = MagicMock()
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    query.data = "tz:set:Europe/London"
    update = MagicMock()
    update.callback_query = query
    update.effective_user.id = 456
    ctx = _context(repo)

    await timezone_callback(update, ctx)

    repo.set_user_timezone.assert_called_once_with(456, "Europe/London")
    text = query.edit_message_text.call_args.args[0]
    assert "Europe/London" in text


async def test_timezone_callback_rejects_invalid_timezone():
    """Crafted callback data with an invalid tz must not save anything."""
    repo = MagicMock()
    repo.set_user_timezone = AsyncMock()
    query = MagicMock()
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    query.data = "tz:set:Mars/Olympus"
    update = MagicMock()
    update.callback_query = query
    update.effective_user.id = 789
    ctx = _context(repo)

    await timezone_callback(update, ctx)

    repo.set_user_timezone.assert_not_called()
    text = query.edit_message_text.call_args.args[0]
    assert "❌" in text or "Unknown" in text
