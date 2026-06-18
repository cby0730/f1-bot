"""Tests for /pitstops and /laps handlers (SQL-only reads)."""

from datetime import date, time, timedelta
from unittest.mock import AsyncMock, MagicMock

from telegram import InlineKeyboardMarkup

from f1_bot.handlers.race_data import laps_handler, pitstops_handler
from f1_bot.models.race import Circuit, Race


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


def _bounds(races: list | None = None) -> dict:
    races = races or []
    today = date.today()
    completed = [r for r in races if r.date <= today]
    upcoming = [r for r in races if r.date > today]
    return {
        "total_rounds": max((r.round for r in races), default=0),
        "completed_rounds": len(completed),
        "upcoming_rounds": len(upcoming),
        "last_completed_round": completed[-1].round if completed else None,
        "next_upcoming_round": upcoming[0].round if upcoming else None,
        "sprint_rounds": [],
        "completed_sprint_rounds": [],
    }


def _context(repo):
    ctx = MagicMock()
    ctx.bot_data = {"repo": repo}
    ctx.args = []
    return ctx


def _update():
    update = MagicMock()
    update.effective_message.reply_text = AsyncMock()
    return update


# --- /pitstops ---


async def test_pitstops_handler_no_data_no_schedule():
    """When schedule is empty, handler shows no-data message."""
    repo = MagicMock()
    repo.get_schedule = AsyncMock(return_value=[])
    repo.get_schedule_bounds = AsyncMock(return_value=_bounds([]))
    update = _update()

    await pitstops_handler(update, _context(repo))

    text = update.effective_message.reply_text.await_args.args[0]
    assert "\u26a0" in text or "No" in text.lower()


async def test_pitstops_handler_with_data_shows_stops():
    """When SQLite has pit stop data, it is displayed."""
    races = [_race(5)]
    repo = MagicMock()
    repo.get_schedule = AsyncMock(return_value=races)
    repo.get_schedule_bounds = AsyncMock(return_value=_bounds(races))
    # SQL-only: repo returns pre-stored data
    repo.get_pit_stops = AsyncMock(return_value=[
        {"driver_id": "HAM", "lap": 20, "stop_number": 1, "duration": 24.5},
        {"driver_id": "VER", "lap": 25, "stop_number": 1, "duration": 22.1},
    ])
    update = _update()

    await pitstops_handler(update, _context(repo))

    call_kwargs = update.effective_message.reply_text.await_args.kwargs
    text = update.effective_message.reply_text.await_args.args[0]
    assert "HAM" in text
    assert "Lap 20" in text
    assert isinstance(call_kwargs.get("reply_markup"), InlineKeyboardMarkup)


async def test_pitstops_handler_no_stops_shows_no_data():
    """When SQLite has no pit stops for the round, shows no-data."""
    races = [_race(5)]
    repo = MagicMock()
    repo.get_schedule = AsyncMock(return_value=races)
    repo.get_schedule_bounds = AsyncMock(return_value=_bounds(races))
    repo.get_pit_stops = AsyncMock(return_value=None)
    update = _update()

    await pitstops_handler(update, _context(repo))

    text = update.effective_message.reply_text.await_args.args[0]
    assert "\u26a0" in text or "No" in text.lower()


async def test_pitstops_handler_uses_cache():
    """When repo returns data, no API calls are needed."""
    races = [_race(5)]
    repo = MagicMock()
    repo.get_schedule = AsyncMock(return_value=races)
    repo.get_schedule_bounds = AsyncMock(return_value=_bounds(races))
    repo.get_pit_stops = AsyncMock(
        return_value=[
            {"driver_id": "NOR", "lap": 12, "stop_number": 1, "duration": 21.0}
        ]
    )
    update = _update()

    await pitstops_handler(update, _context(repo))

    text = update.effective_message.reply_text.await_args.args[0]
    assert "NOR" in text


# --- /laps ---


async def test_laps_handler_no_data_no_schedule():
    repo = MagicMock()
    repo.get_schedule = AsyncMock(return_value=[])
    repo.get_schedule_bounds = AsyncMock(return_value=_bounds([]))
    update = _update()

    await laps_handler(update, _context(repo))

    text = update.effective_message.reply_text.await_args.args[0]
    assert "\u26a0" in text or "No" in text.lower()


async def test_laps_handler_shows_summary_with_keyboard():
    """Default /laps shows summary view with round nav + mode buttons."""
    races = [_race(5)]
    repo = MagicMock()
    repo.get_schedule = AsyncMock(return_value=races)
    repo.get_schedule_bounds = AsyncMock(return_value=_bounds(races))
    repo.get_lap_timings = AsyncMock(return_value=[
        {"lap_number": 1, "driver_id": "HAM", "time": "1:32.456", "position": 1},
        {"lap_number": 1, "driver_id": "VER", "time": "1:32.789", "position": 2},
        {"lap_number": 2, "driver_id": "HAM", "time": "1:31.000", "position": 1},
        {"lap_number": 2, "driver_id": "VER", "time": "1:31.200", "position": 2},
    ])
    update = _update()

    await laps_handler(update, _context(repo))

    call_kwargs = update.effective_message.reply_text.await_args.kwargs
    text = update.effective_message.reply_text.await_args.args[0]
    assert "HAM" in text
    assert "Summary" in text
    assert isinstance(call_kwargs.get("reply_markup"), InlineKeyboardMarkup)


async def test_laps_handler_no_laps_shows_no_data():
    races = [_race(5)]
    repo = MagicMock()
    repo.get_schedule = AsyncMock(return_value=races)
    repo.get_schedule_bounds = AsyncMock(return_value=_bounds(races))
    repo.get_lap_timings = AsyncMock(return_value=None)
    update = _update()

    await laps_handler(update, _context(repo))

    text = update.effective_message.reply_text.await_args.args[0]
    assert "\u26a0" in text or "No" in text.lower()


async def test_laps_handler_uses_cache():
    """When repo returns lap data, it is displayed directly."""
    races = [_race(5)]
    repo = MagicMock()
    repo.get_schedule = AsyncMock(return_value=races)
    repo.get_schedule_bounds = AsyncMock(return_value=_bounds(races))
    repo.get_lap_timings = AsyncMock(
        return_value=[
            {"lap_number": 1, "driver_id": "LEC", "time": "1:33.100", "position": 3}
        ]
    )
    update = _update()

    await laps_handler(update, _context(repo))

    text = update.effective_message.reply_text.await_args.args[0]
    assert "LEC" in text
