"""Tests for /settings hub — launch pad onto timezone/language pickers."""

from unittest.mock import AsyncMock, MagicMock

from f1_bot.handlers.settings import settings_callback, settings_handler


def _context(repo):
    ctx = MagicMock()
    ctx.bot_data = {"repo": repo}
    return ctx


def _update():
    update = MagicMock()
    update.effective_user.id = 123
    update.effective_message.reply_text = AsyncMock()
    return update


async def test_settings_handler_shows_two_buttons():
    """/settings keyboard is timezone + language (`set:tz`, `set:lang`)."""
    repo = MagicMock()
    update = _update()

    await settings_handler(update, _context(repo))

    kwargs = update.effective_message.reply_text.await_args.kwargs
    kb = kwargs["reply_markup"].inline_keyboard
    assert len(kb) == 1
    assert len(kb[0]) == 2
    assert kb[0][0].callback_data == "set:tz"
    assert kb[0][1].callback_data == "set:lang"


async def test_set_lang_edits_in_place():
    """set:lang edits the hub message — it must not reply a new one.

    WHY: the hub must edit in place. A new-message path would leave the hub
    sitting above the picker.
    """
    repo = MagicMock()
    query = MagicMock()
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    query.data = "set:lang"
    update = MagicMock()
    update.callback_query = query
    update.effective_message.reply_text = AsyncMock()

    await settings_callback(update, _context(repo))

    query.answer.assert_awaited_once()
    query.edit_message_text.assert_awaited_once()
    update.effective_message.reply_text.assert_not_called()
    kb = query.edit_message_text.await_args.kwargs["reply_markup"].inline_keyboard
    assert {row[0].callback_data for row in kb} == {"lang:set:en", "lang:set:zh-Hant"}


async def test_set_tz_edits_to_region_keyboard():
    repo = MagicMock()
    query = MagicMock()
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    query.data = "set:tz"
    update = MagicMock()
    update.callback_query = query

    await settings_callback(update, _context(repo))

    query.edit_message_text.assert_awaited_once()
    kb = query.edit_message_text.await_args.kwargs["reply_markup"]
    data = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    assert any(d.startswith("tz:region:") for d in data)
