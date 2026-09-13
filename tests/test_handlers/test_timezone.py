"""Tests for timezone callback (opened from /settings)."""

from unittest.mock import AsyncMock, MagicMock

from f1_bot.handlers.timezone import timezone_callback


def _context(repo):
    ctx = MagicMock()
    ctx.bot_data = {"repo": repo}
    return ctx


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


async def test_timezone_callback_set_escapes_underscore_in_iana_id():
    """IANA ids with `_` must be Markdown-escaped in the confirmation, not in storage.

    WHY: `America/New_York` (and Los_Angeles, Sao_Paulo, Mexico_City) are official
    picker buttons. Unescaped `{tz}` inside `*{tz}*` is an unterminated italic
    under legacy ParseMode.MARKDOWN, so Telegram rejects the confirmation after
    the preference has already been written.
    """
    repo = MagicMock()
    repo.set_user_timezone = AsyncMock()
    query = MagicMock()
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    query.data = "tz:set:America/New_York"
    update = MagicMock()
    update.callback_query = query
    update.effective_user.id = 456
    ctx = _context(repo)

    await timezone_callback(update, ctx)

    repo.set_user_timezone.assert_called_once_with(456, "America/New_York")
    text = query.edit_message_text.call_args.args[0]
    assert r"America/New\_York" in text
    assert r"*America/New\_York*" in text


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
