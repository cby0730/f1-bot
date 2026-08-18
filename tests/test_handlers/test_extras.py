"""Tests for /driver and /circuit handlers and callbacks."""

import datetime
from unittest.mock import AsyncMock, MagicMock

from f1_bot.handlers.extras import _extras_callback, circuit_handler, driver_handler
from f1_bot.models.driver import Driver, DriverStanding
from f1_bot.models.race import Circuit, Race


def _driver():
    return Driver(
        driver_id="hamilton",
        given_name="Lewis",
        family_name="Hamilton",
        nationality="British",
        permanent_number="44",
        code="HAM",
    )


def _standing():
    return DriverStanding(
        position=1,
        points=25.0,
        wins=1,
        driver=_driver(),
        constructor_name="Mercedes",
    )


def _circuit():
    return Circuit(
        circuit_id="monaco",
        name="Circuit de Monaco",
        locality="Monte-Carlo",
        country="Monaco",
    )


def _race(circuit=None, round_num=1):
    return Race(
        season=2026,
        round=round_num,
        name="Monaco Grand Prix",
        circuit=circuit or _circuit(),
        date=datetime.date(2026, 5, 24),
        time=datetime.time(15, 0, 0),
    )


def _context(repo):
    ctx = MagicMock()
    ctx.bot_data = {"repo": repo}
    return ctx


def _update():
    update = MagicMock()
    update.effective_user.id = 123
    update.effective_message.reply_text = AsyncMock()
    return update


def _callback_update(data: str):
    update = MagicMock()
    query = AsyncMock()
    query.data = data
    update.callback_query = query
    return update


# --- Refactored /driver command tests ---


async def test_driver_handler_no_args_shows_menu():
    repo = MagicMock()
    repo.get_driver_standings = AsyncMock(return_value=[_standing()])
    ctx = _context(repo)
    ctx.args = []
    update = _update()

    await driver_handler(update, ctx)

    text = update.effective_message.reply_text.await_args.kwargs.get("text", "")
    if not text:
        text = update.effective_message.reply_text.await_args.args[0]
    assert "Select a driver" in text
    reply_markup = update.effective_message.reply_text.await_args.kwargs.get("reply_markup")
    assert reply_markup is not None
    # Check 2-column layout indexing
    button = reply_markup.inline_keyboard[0][0]
    assert button.callback_data == "drv:detail:hamilton"
    assert "Hamilton" in button.text


async def test_driver_handler_match_found_shows_profile():
    repo = MagicMock()
    repo.get_driver_standings = AsyncMock(return_value=[_standing()])
    ctx = _context(repo)
    ctx.args = ["hamilton"]
    update = _update()

    await driver_handler(update, ctx)

    text = update.effective_message.reply_text.await_args.args[0]
    assert "Lewis Hamilton" in text
    assert "HAM" in text
    markup = update.effective_message.reply_text.await_args.kwargs.get("reply_markup")
    assert markup is not None
    data = [b.callback_data for row in markup.inline_keyboard for b in row]
    assert "cmp:a:hamilton" in data
    assert "drv:list" in data


async def test_driver_handler_no_match_shows_not_found():
    repo = MagicMock()
    repo.get_driver_standings = AsyncMock(return_value=[_standing()])
    ctx = _context(repo)
    ctx.args = ["xyznosuchdriver"]
    update = _update()

    await driver_handler(update, ctx)

    text = update.effective_message.reply_text.await_args.args[0]
    assert "No driver found" in text or "❓" in text


async def test_driver_handler_repo_exception_shows_no_data():
    repo = MagicMock()
    repo.get_driver_standings = AsyncMock(side_effect=Exception("database error"))
    ctx = _context(repo)
    ctx.args = ["hamilton"]
    update = _update()

    await driver_handler(update, ctx)

    text = update.effective_message.reply_text.await_args.args[0]
    assert "⚠️" in text or "driver list" in text.lower()


# --- Refactored /circuit command tests ---


async def test_circuit_handler_no_args_shows_menu():
    repo = MagicMock()
    repo.get_circuits_for_season = AsyncMock(return_value=[(1, _circuit())])
    ctx = _context(repo)
    ctx.args = []
    update = _update()

    await circuit_handler(update, ctx)

    text = update.effective_message.reply_text.await_args.kwargs.get("text", "")
    if not text:
        text = update.effective_message.reply_text.await_args.args[0]
    assert "Select a circuit" in text
    reply_markup = update.effective_message.reply_text.await_args.kwargs.get("reply_markup")
    assert reply_markup is not None
    button = reply_markup.inline_keyboard[0][0]
    assert button.callback_data == "circ:detail:monaco"
    assert "R1" in button.text
    assert "Monte-Carlo" in button.text


async def test_circuit_handler_match_found_shows_circuit_info():
    repo = MagicMock()
    repo.get_schedule = AsyncMock(return_value=[_race()])
    ctx = _context(repo)
    ctx.args = ["monaco"]
    update = _update()

    await circuit_handler(update, ctx)

    text = update.effective_message.reply_text.await_args.args[0]
    assert "Circuit de Monaco" in text
    assert "Monte-Carlo" in text


async def test_circuit_handler_no_match_shows_not_found():
    repo = MagicMock()
    repo.get_schedule = AsyncMock(return_value=[_race()])
    ctx = _context(repo)
    ctx.args = ["xyznosuchcircuit12345678"]
    update = _update()

    await circuit_handler(update, ctx)

    text = update.effective_message.reply_text.await_args.args[0]
    assert "No circuit found" in text or "❓" in text


async def test_circuit_handler_repo_exception_shows_no_data():
    repo = MagicMock()
    repo.get_circuits_for_season = AsyncMock(side_effect=Exception("database error"))
    ctx = _context(repo)
    ctx.args = ["monaco"]
    update = _update()

    await circuit_handler(update, ctx)

    text = update.effective_message.reply_text.await_args.args[0]
    assert "⚠️" in text or "circuit list" in text.lower()


# --- New Callback and Guard Tests ---


async def test_extras_callback_driver_detail():
    repo = MagicMock()
    repo.get_driver_standings = AsyncMock(return_value=[_standing()])
    ctx = _context(repo)
    update = _callback_update("drv:detail:hamilton")

    await _extras_callback(update, ctx)

    update.callback_query.answer.assert_called_once()
    text = update.callback_query.edit_message_text.await_args.kwargs.get("text", "")
    assert "Lewis Hamilton" in text
    assert "HAM" in text
    reply_markup = update.callback_query.edit_message_text.await_args.kwargs.get("reply_markup")
    assert reply_markup is not None
    data = [b.callback_data for row in reply_markup.inline_keyboard for b in row]
    assert "cmp:a:hamilton" in data
    assert "drv:list" in data


async def test_extras_callback_driver_list():
    repo = MagicMock()
    repo.get_driver_standings = AsyncMock(return_value=[_standing()])
    ctx = _context(repo)
    update = _callback_update("drv:list")

    await _extras_callback(update, ctx)

    update.callback_query.answer.assert_called_once()
    text = update.callback_query.edit_message_text.await_args.kwargs.get("text", "")
    assert "Select a driver" in text
    reply_markup = update.callback_query.edit_message_text.await_args.kwargs.get("reply_markup")
    assert reply_markup is not None
    button = reply_markup.inline_keyboard[0][0]
    assert button.callback_data == "drv:detail:hamilton"


async def test_extras_callback_circuit_detail():
    repo = MagicMock()
    repo.get_schedule = AsyncMock(return_value=[_race()])
    ctx = _context(repo)
    update = _callback_update("circ:detail:monaco")

    await _extras_callback(update, ctx)

    update.callback_query.answer.assert_called_once()
    text = update.callback_query.edit_message_text.await_args.kwargs.get("text", "")
    assert "Circuit de Monaco" in text
    assert "Monte-Carlo" in text
    reply_markup = update.callback_query.edit_message_text.await_args.kwargs.get("reply_markup")
    assert reply_markup is not None
    button = reply_markup.inline_keyboard[0][0]
    assert button.callback_data == "circ:list"


async def test_extras_callback_circuit_list():
    repo = MagicMock()
    repo.get_circuits_for_season = AsyncMock(return_value=[(1, _circuit())])
    ctx = _context(repo)
    update = _callback_update("circ:list")

    await _extras_callback(update, ctx)

    update.callback_query.answer.assert_called_once()
    text = update.callback_query.edit_message_text.await_args.kwargs.get("text", "")
    assert "Select a circuit" in text
    reply_markup = update.callback_query.edit_message_text.await_args.kwargs.get("reply_markup")
    assert reply_markup is not None
    button = reply_markup.inline_keyboard[0][0]
    assert button.callback_data == "circ:detail:monaco"


async def test_extras_callback_malformed_query():
    repo = MagicMock()
    ctx = _context(repo)
    update = _callback_update("drv")  # split results in length 1, less than 2

    await _extras_callback(update, ctx)

    update.callback_query.answer.assert_called_once_with(text="Invalid selection", show_alert=True)
    update.callback_query.edit_message_text.assert_not_called()


async def test_driver_handler_no_args_empty_db():
    repo = MagicMock()
    repo.get_driver_standings = AsyncMock(return_value=[])
    ctx = _context(repo)
    ctx.args = []
    update = _update()

    await driver_handler(update, ctx)

    text = update.effective_message.reply_text.await_args.args[0]
    assert "⚠️" in text
    assert "driver list" in text.lower()


async def test_circuit_handler_no_args_empty_db():
    repo = MagicMock()
    repo.get_circuits_for_season = AsyncMock(return_value=[])
    ctx = _context(repo)
    ctx.args = []
    update = _update()

    await circuit_handler(update, ctx)

    text = update.effective_message.reply_text.await_args.args[0]
    assert "⚠️" in text
    assert "circuit list" in text.lower()


async def test_driver_handler_deduplication():
    repo = MagicMock()
    # Force query search fallback by providing empty standings
    repo.get_driver_standings = AsyncMock(return_value=[])

    # Create two duplicate drivers inside the mapping
    d1 = _driver()
    d2 = _driver()
    repo.get_drivers_by_id_map = AsyncMock(return_value={"1": d1, "2": d2})

    ctx = _context(repo)
    ctx.args = ["hamilton"]
    update = _update()

    await driver_handler(update, ctx)

    text = update.effective_message.reply_text.await_args.args[0]
    assert "Lewis Hamilton" in text


async def test_extras_callback_single_answer_not_found():
    repo = MagicMock()
    repo.get_driver_standings = AsyncMock(return_value=[])
    repo.get_drivers_by_id_map = AsyncMock(return_value={})
    ctx = _context(repo)
    update = _callback_update("drv:detail:nonexistent")

    await _extras_callback(update, ctx)

    update.callback_query.answer.assert_called_once_with(text="Driver not found", show_alert=True)


async def test_extras_callback_single_answer_exception():
    repo = MagicMock()
    repo.get_driver_standings = AsyncMock(side_effect=Exception("DB fail"))
    ctx = _context(repo)
    update = _callback_update("drv:detail:hamilton")

    await _extras_callback(update, ctx)

    update.callback_query.answer.assert_called_once_with(text="An error occurred", show_alert=True)


async def test_circuit_handler_single_query():
    repo = MagicMock()
    repo.get_schedule = AsyncMock(return_value=[_race()])
    repo.get_circuits_for_season = AsyncMock()

    ctx = _context(repo)
    ctx.args = ["monaco"]
    update = _update()

    await circuit_handler(update, ctx)

    repo.get_schedule.assert_called_once_with(2026)
    repo.get_circuits_for_season.assert_not_called()
