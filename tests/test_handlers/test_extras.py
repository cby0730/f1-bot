"""Tests for /driver and /circuit handlers."""

from unittest.mock import AsyncMock, MagicMock

from f1_bot.handlers.extras import circuit_handler, driver_handler
from f1_bot.models.driver import Driver
from f1_bot.models.race import Circuit


def _driver():
    return Driver(
        driver_id="hamilton",
        given_name="Lewis",
        family_name="Hamilton",
        nationality="British",
        permanent_number="44",
        code="HAM",
    )


def _circuit():
    return Circuit(
        circuit_id="monaco",
        name="Circuit de Monaco",
        locality="Monte-Carlo",
        country="Monaco",
    )


def _context(jolpica):
    ctx = MagicMock()
    ctx.bot_data = {"jolpica": jolpica}
    return ctx


def _update():
    update = MagicMock()
    update.effective_user.id = 123
    update.effective_message.reply_text = AsyncMock()
    return update


# --- /driver ---


async def test_driver_handler_no_args_shows_usage():
    ctx = MagicMock()
    ctx.args = []
    ctx.bot_data = {}
    update = _update()

    await driver_handler(update, ctx)

    text = update.effective_message.reply_text.await_args.args[0]
    assert "Usage" in text or "/driver" in text


async def test_driver_handler_match_found_shows_profile():
    jolpica = MagicMock()
    jolpica.get_drivers = AsyncMock(return_value=[_driver()])
    jolpica.get_driver_standings = AsyncMock(return_value=[])
    ctx = _context(jolpica)
    ctx.args = ["hamilton"]
    update = _update()

    await driver_handler(update, ctx)

    text = update.effective_message.reply_text.await_args.args[0]
    assert "Lewis Hamilton" in text
    assert "HAM" in text


async def test_driver_handler_no_match_shows_not_found():
    jolpica = MagicMock()
    jolpica.get_drivers = AsyncMock(return_value=[_driver()])
    jolpica.get_driver_standings = AsyncMock(return_value=[])
    ctx = _context(jolpica)
    ctx.args = ["xyznosuchdriver"]
    update = _update()

    await driver_handler(update, ctx)

    text = update.effective_message.reply_text.await_args.args[0]
    assert "No driver found" in text or "❓" in text


async def test_driver_handler_jolpica_exception_shows_no_data():
    jolpica = MagicMock()
    jolpica.get_drivers = AsyncMock(side_effect=Exception("network error"))
    ctx = _context(jolpica)
    ctx.args = ["hamilton"]
    update = _update()

    await driver_handler(update, ctx)

    text = update.effective_message.reply_text.await_args.args[0]
    assert "⚠️" in text or "driver list" in text.lower()


# --- /circuit ---


async def test_circuit_handler_no_args_shows_usage():
    ctx = MagicMock()
    ctx.args = []
    ctx.bot_data = {}
    update = _update()

    await circuit_handler(update, ctx)

    text = update.effective_message.reply_text.await_args.args[0]
    assert "Usage" in text or "/circuit" in text


async def test_circuit_handler_match_found_shows_circuit_info():
    jolpica = MagicMock()
    jolpica.get_circuits = AsyncMock(return_value=[_circuit()])
    jolpica.get_current_schedule = AsyncMock(return_value=[])
    ctx = _context(jolpica)
    ctx.args = ["monaco"]
    update = _update()

    await circuit_handler(update, ctx)

    text = update.effective_message.reply_text.await_args.args[0]
    assert "Circuit de Monaco" in text
    assert "Monte-Carlo" in text


async def test_circuit_handler_no_match_shows_not_found():
    jolpica = MagicMock()
    jolpica.get_circuits = AsyncMock(return_value=[_circuit()])
    jolpica.get_current_schedule = AsyncMock(return_value=[])
    ctx = _context(jolpica)
    ctx.args = ["xyznosuchcircuit12345678"]
    update = _update()

    await circuit_handler(update, ctx)

    text = update.effective_message.reply_text.await_args.args[0]
    assert "No circuit found" in text or "❓" in text


async def test_circuit_handler_jolpica_exception_shows_no_data():
    jolpica = MagicMock()
    jolpica.get_circuits = AsyncMock(side_effect=Exception("network error"))
    ctx = _context(jolpica)
    ctx.args = ["monaco"]
    update = _update()

    await circuit_handler(update, ctx)

    text = update.effective_message.reply_text.await_args.args[0]
    assert "⚠️" in text or "circuit list" in text.lower()
