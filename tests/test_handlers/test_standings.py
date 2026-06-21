"""Tests for /standings and standings callback handler."""

from unittest.mock import AsyncMock, MagicMock

from f1_bot.handlers.standings import standings_callback, standings_handler
from f1_bot.models.constructor import Constructor, ConstructorStanding
from f1_bot.models.driver import Driver, DriverStanding


def _driver():
    return Driver(
        driver_id="hamilton", given_name="Lewis", family_name="Hamilton", nationality="British"
    )


def _constructor():
    return Constructor(constructor_id="mercedes", name="Mercedes")


def _driver_standings():
    return [
        DriverStanding(
            position=1, points=100.0, wins=3, driver=_driver(), constructor_name="Mercedes"
        )
    ]


def _constructor_standings():
    return [ConstructorStanding(position=1, points=200.0, wins=5, constructor=_constructor())]


def _context(repo):
    ctx = MagicMock()
    ctx.bot_data = {"repo": repo}
    return ctx


def _update():
    update = MagicMock()
    update.effective_user.id = 123
    update.effective_message.reply_text = AsyncMock()
    return update


async def test_standings_handler_shows_driver_standings():
    repo = MagicMock()
    repo.get_driver_standings = AsyncMock(return_value=_driver_standings())
    update = _update()

    await standings_handler(update, _context(repo))

    assert update.effective_message.reply_text.await_count == 1
    text = update.effective_message.reply_text.await_args.args[0]
    assert "Hamilton" in text
    assert "100" in text


async def test_standings_handler_no_data_shows_warning():
    repo = MagicMock()
    repo.get_driver_standings = AsyncMock(return_value=[])
    update = _update()

    await standings_handler(update, _context(repo))

    text = update.effective_message.reply_text.await_args.args[0]
    assert "standings" in text.lower() or "⚠️" in text


async def test_standings_callback_wdc_shows_driver_standings():
    repo = MagicMock()
    repo.get_driver_standings = AsyncMock(return_value=_driver_standings())
    query = MagicMock()
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    query.data = "standings:wdc"
    update = MagicMock()
    update.callback_query = query
    update.effective_user.id = 123
    ctx = _context(repo)

    await standings_callback(update, ctx)

    query.answer.assert_called_once()
    query.edit_message_text.assert_called_once()
    text = query.edit_message_text.call_args.args[0]
    assert "Hamilton" in text


async def test_standings_callback_wcc_shows_constructor_standings():
    repo = MagicMock()
    repo.get_constructor_standings = AsyncMock(return_value=_constructor_standings())
    query = MagicMock()
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    query.data = "standings:wcc"
    update = MagicMock()
    update.callback_query = query
    update.effective_user.id = 123
    ctx = _context(repo)

    await standings_callback(update, ctx)

    text = query.edit_message_text.call_args.args[0]
    assert "Mercedes" in text


async def test_standings_callback_wcc_no_data_shows_warning():
    repo = MagicMock()
    repo.get_constructor_standings = AsyncMock(return_value=[])
    query = MagicMock()
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    query.data = "standings:wcc"
    update = MagicMock()
    update.callback_query = query
    ctx = _context(repo)

    await standings_callback(update, ctx)

    text = query.edit_message_text.call_args.args[0]
    assert "⚠️" in text


async def test_standings_callback_handles_bad_request():
    """It catches telegram.error.BadRequest gracefully when message is unmodified."""
    from telegram.error import BadRequest

    repo = MagicMock()
    repo.get_driver_standings = AsyncMock(return_value=_driver_standings())
    query = MagicMock()
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock(side_effect=BadRequest("Message is not modified"))
    query.data = "standings:wdc"
    update = MagicMock()
    update.callback_query = query
    update.effective_user.id = 123
    ctx = _context(repo)

    # Should not raise exception
    await standings_callback(update, ctx)
    query.answer.assert_called_once()
    query.edit_message_text.assert_called_once()
