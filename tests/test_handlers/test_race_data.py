"""Tests for /pitstops and /laps handlers."""

from datetime import date, time, timedelta
from unittest.mock import AsyncMock, MagicMock

from f1_bot.handlers.race_data import laps_handler, pitstops_handler
from f1_bot.models.race import Circuit, Race
from f1_bot.models.results import LapTime, PitStop


def _circuit():
    return Circuit(
        circuit_id="monaco", name="Circuit de Monaco", locality="Monte-Carlo", country="Monaco"
    )


def _race(round_num: int = 5) -> Race:
    past = date.today() - timedelta(days=1)
    return Race(
        season=date.today().year,
        round=round_num,
        name="Monaco Grand Prix",
        circuit=_circuit(),
        date=past,
        time=time(13, 0),
    )


def _context(repo, jolpica):
    ctx = MagicMock()
    ctx.bot_data = {"repo": repo, "jolpica": jolpica}
    ctx.args = []
    return ctx


def _update():
    update = MagicMock()
    update.effective_message.reply_text = AsyncMock()
    return update


# --- /pitstops ---


async def test_pitstops_handler_no_round_no_data():
    """When no round is resolvable, handler shows no-data message."""
    repo = MagicMock()
    repo.sqlite = MagicMock()
    repo.sqlite.get_last_race_round = AsyncMock(return_value=None)
    repo.get_schedule = AsyncMock(return_value=[])
    jolpica = MagicMock()
    update = _update()

    await pitstops_handler(update, _context(repo, jolpica))

    text = update.effective_message.reply_text.await_args.args[0]
    assert "⚠️" in text or "pit stop" in text.lower()


async def test_pitstops_handler_with_data_shows_stops():
    repo = MagicMock()
    repo.sqlite = MagicMock()
    repo.sqlite.get_last_race_round = AsyncMock(return_value=5)
    repo.get_schedule = AsyncMock(return_value=[_race(5)])
    stops = [
        PitStop(driver_id="HAM", lap=20, stop_number=1, duration=24.5),
        PitStop(driver_id="VER", lap=25, stop_number=1, duration=22.1),
    ]
    jolpica = MagicMock()
    jolpica.get_pit_stops = AsyncMock(return_value=stops)
    update = _update()

    await pitstops_handler(update, _context(repo, jolpica))

    text = update.effective_message.reply_text.await_args.args[0]
    assert "HAM" in text
    assert "Lap 20" in text


async def test_pitstops_handler_round_arg_overrides_last_round():
    repo = MagicMock()
    repo.sqlite = MagicMock()
    repo.sqlite.get_last_race_round = AsyncMock(return_value=1)  # should be ignored
    repo.get_schedule = AsyncMock(return_value=[_race(7)])
    stops = [PitStop(driver_id="NOR", lap=10, stop_number=1, duration=21.0)]
    jolpica = MagicMock()
    jolpica.get_pit_stops = AsyncMock(return_value=stops)
    ctx = _context(repo, jolpica)
    ctx.args = ["7"]
    update = _update()

    await pitstops_handler(update, ctx)

    jolpica.get_pit_stops.assert_called_once()
    call_args = jolpica.get_pit_stops.call_args
    assert "7" in call_args.args or call_args.kwargs.get("round_num") == "7"


async def test_pitstops_handler_no_stops_shows_no_data():
    repo = MagicMock()
    repo.sqlite = MagicMock()
    repo.sqlite.get_last_race_round = AsyncMock(return_value=5)
    repo.get_schedule = AsyncMock(return_value=[_race(5)])
    jolpica = MagicMock()
    jolpica.get_pit_stops = AsyncMock(return_value=[])
    update = _update()

    await pitstops_handler(update, _context(repo, jolpica))

    text = update.effective_message.reply_text.await_args.args[0]
    assert "⚠️" in text


# --- /laps ---


async def test_laps_handler_no_round_no_data():
    repo = MagicMock()
    repo.sqlite = MagicMock()
    repo.sqlite.get_last_race_round = AsyncMock(return_value=None)
    repo.get_schedule = AsyncMock(return_value=[])
    jolpica = MagicMock()
    update = _update()

    await laps_handler(update, _context(repo, jolpica))

    text = update.effective_message.reply_text.await_args.args[0]
    assert "⚠️" in text or "lap" in text.lower()


async def test_laps_handler_with_data_shows_laps():
    repo = MagicMock()
    repo.sqlite = MagicMock()
    repo.sqlite.get_last_race_round = AsyncMock(return_value=5)
    repo.get_schedule = AsyncMock(return_value=[_race(5)])
    laps = [
        LapTime(lap_number=1, driver_id="HAM", time="1:32.456", position=1),
        LapTime(lap_number=1, driver_id="VER", time="1:32.789", position=2),
    ]
    jolpica = MagicMock()
    jolpica.get_fastest_laps = AsyncMock(return_value=laps)
    update = _update()

    await laps_handler(update, _context(repo, jolpica))

    text = update.effective_message.reply_text.await_args.args[0]
    assert "HAM" in text
    assert "1:32.456" in text


async def test_laps_handler_no_laps_shows_no_data():
    repo = MagicMock()
    repo.sqlite = MagicMock()
    repo.sqlite.get_last_race_round = AsyncMock(return_value=5)
    repo.get_schedule = AsyncMock(return_value=[_race(5)])
    jolpica = MagicMock()
    jolpica.get_fastest_laps = AsyncMock(return_value=[])
    update = _update()

    await laps_handler(update, _context(repo, jolpica))

    text = update.effective_message.reply_text.await_args.args[0]
    assert "⚠️" in text
