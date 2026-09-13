"""Tests for pit-stop and lap callbacks (SQL-only reads, opened from /results)."""

from datetime import date, time, timedelta
from unittest.mock import AsyncMock, MagicMock

from telegram import InlineKeyboardMarkup

from f1_bot.handlers.race_data import _laps_callback, _pitstops_callback
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
    if not isinstance(repo.get_drivers_map, AsyncMock):
        repo.get_drivers_map = AsyncMock(return_value={})
    if not isinstance(getattr(repo, "get_race_results", None), AsyncMock):
        repo.get_race_results = AsyncMock(return_value=[])
    return ctx


def _cb(data: str):
    update = MagicMock()
    update.callback_query.data = data
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    return update


# --- pit: ---


async def test_pitstops_callback_no_schedule():
    """Empty schedule answers schedule-unavailable; no edit."""
    repo = MagicMock()
    repo.get_schedule = AsyncMock(return_value=[])
    repo.get_schedule_bounds = AsyncMock(return_value=_bounds([]))
    update = _cb("pit:5")

    await _pitstops_callback(update, _context(repo))

    update.callback_query.answer.assert_awaited_once()
    assert "unavailable" in update.callback_query.answer.await_args.kwargs["text"].lower()
    update.callback_query.edit_message_text.assert_not_called()


async def test_pitstops_callback_with_data_shows_stops():
    """When Postgres has pit stop data, it is displayed on the pit: path."""
    races = [_race(5)]
    repo = MagicMock()
    repo.get_schedule = AsyncMock(return_value=races)
    repo.get_schedule_bounds = AsyncMock(return_value=_bounds(races))
    repo.get_pit_stops = AsyncMock(
        return_value=[
            {"driver_id": "HAM", "lap": 20, "stop_number": 1, "duration": 24.5},
            {"driver_id": "VER", "lap": 25, "stop_number": 1, "duration": 22.1},
        ]
    )
    update = _cb("pit:5")

    await _pitstops_callback(update, _context(repo))

    call_kwargs = update.callback_query.edit_message_text.await_args.kwargs
    text = update.callback_query.edit_message_text.await_args.args[0]
    assert "HAM" in text
    assert "Lap 20" in text
    assert isinstance(call_kwargs.get("reply_markup"), InlineKeyboardMarkup)
    data = [b.callback_data for row in call_kwargs["reply_markup"].inline_keyboard for b in row]
    assert "res:back:_:5" in data


async def test_pitstops_callback_no_stops_shows_no_data():
    """None from get_pit_stops is treated as empty (same as [])."""
    races = [_race(5)]
    repo = MagicMock()
    repo.get_schedule = AsyncMock(return_value=races)
    repo.get_schedule_bounds = AsyncMock(return_value=_bounds(races))
    repo.get_pit_stops = AsyncMock(return_value=None)
    update = _cb("pit:5")

    await _pitstops_callback(update, _context(repo))

    text = update.callback_query.edit_message_text.await_args.args[0]
    assert "\u26a0" in text or "No" in text.lower()


async def test_pitstops_callback_uses_cache():
    """When repo returns data, no API calls are needed."""
    races = [_race(5)]
    repo = MagicMock()
    repo.get_schedule = AsyncMock(return_value=races)
    repo.get_schedule_bounds = AsyncMock(return_value=_bounds(races))
    repo.get_pit_stops = AsyncMock(
        return_value=[{"driver_id": "NOR", "lap": 12, "stop_number": 1, "duration": 21.0}]
    )
    update = _cb("pit:5")

    await _pitstops_callback(update, _context(repo))

    text = update.callback_query.edit_message_text.await_args.args[0]
    assert "NOR" in text


async def test_pitstops_callback_empty_from_results_keeps_back():
    """No pit data on a results tap still shows Back so the user is not trapped."""
    races = [_race(5)]
    repo = MagicMock()
    repo.get_schedule = AsyncMock(return_value=races)
    repo.get_schedule_bounds = AsyncMock(return_value=_bounds(races))
    repo.get_pit_stops = AsyncMock(return_value=[])

    update = _cb("pit:5")
    await _pitstops_callback(update, _context(repo))

    text = update.callback_query.edit_message_text.await_args.args[0]
    assert "⚠" in text or "no" in text.lower()
    kb = update.callback_query.edit_message_text.await_args.kwargs["reply_markup"]
    cbs = [b.callback_data for row in kb.inline_keyboard for b in row]
    assert "res:back:_:5" in cbs


async def test_pitstops_callback_round_not_found():
    """pit:{n} for a round missing from the schedule answers round-not-found."""
    races = [_race(5)]
    repo = MagicMock()
    repo.get_schedule = AsyncMock(return_value=races)
    bounds = _bounds(races)
    bounds["last_completed_round"] = 3
    repo.get_schedule_bounds = AsyncMock(return_value=bounds)
    update = _cb("pit:3")

    await _pitstops_callback(update, _context(repo))

    update.callback_query.answer.assert_awaited_once()
    assert "not found" in update.callback_query.answer.await_args.kwargs["text"].lower()
    update.callback_query.edit_message_text.assert_not_called()


async def test_pitstops_callback_invalid_round_value_error():
    update = _cb("pit:not_an_int")
    ctx = _context(MagicMock())
    await _pitstops_callback(update, ctx)

    assert update.callback_query.answer.call_count == 1
    update.callback_query.answer.assert_called_with(text="Invalid selection", show_alert=True)
    update.callback_query.edit_message_text.assert_not_called()


async def test_pitstops_callback_with_none_last_completed_round():
    """bounds with None last_completed_round should not crash."""
    races = [_race(5)]
    repo = MagicMock()
    repo.get_schedule = AsyncMock(return_value=races)
    bounds = _bounds(races)
    bounds["last_completed_round"] = None
    repo.get_schedule_bounds = AsyncMock(return_value=bounds)
    repo.get_pit_stops = AsyncMock(
        return_value=[{"driver_id": "HAM", "lap": 20, "stop_number": 1, "duration": 24.5}]
    )

    update = _cb("pit:5")
    await _pitstops_callback(update, _context(repo))
    update.callback_query.answer.assert_called()


# --- lap: ---


async def test_laps_callback_no_schedule():
    repo = MagicMock()
    repo.get_schedule = AsyncMock(return_value=[])
    repo.get_schedule_bounds = AsyncMock(return_value=_bounds([]))
    update = _cb("lap:5:s")

    await _laps_callback(update, _context(repo))

    update.callback_query.answer.assert_awaited_once()
    assert "unavailable" in update.callback_query.answer.await_args.kwargs["text"].lower()
    update.callback_query.edit_message_text.assert_not_called()


async def test_laps_callback_shows_summary_with_keyboard():
    """Default lap:{n}:s shows summary view with round nav + Back."""
    races = [_race(5)]
    repo = MagicMock()
    repo.get_schedule = AsyncMock(return_value=races)
    repo.get_schedule_bounds = AsyncMock(return_value=_bounds(races))
    repo.get_lap_timings = AsyncMock(
        return_value=[
            {"lap_number": 1, "driver_id": "HAM", "time": "1:32.456", "position": 1},
            {"lap_number": 1, "driver_id": "VER", "time": "1:32.789", "position": 2},
            {"lap_number": 2, "driver_id": "HAM", "time": "1:31.000", "position": 1},
            {"lap_number": 2, "driver_id": "VER", "time": "1:31.200", "position": 2},
        ]
    )
    update = _cb("lap:5:s")

    await _laps_callback(update, _context(repo))

    call_kwargs = update.callback_query.edit_message_text.await_args.kwargs
    text = update.callback_query.edit_message_text.await_args.args[0]
    assert "HAM" in text
    assert "Lap Times" in text
    assert isinstance(call_kwargs.get("reply_markup"), InlineKeyboardMarkup)
    back = [
        b
        for row in call_kwargs["reply_markup"].inline_keyboard
        for b in row
        if b.callback_data.startswith("res:back:")
    ]
    assert back and back[0].callback_data == "res:back:_:5"


async def test_laps_callback_no_laps_shows_no_data():
    races = [_race(5)]
    repo = MagicMock()
    repo.get_schedule = AsyncMock(return_value=races)
    repo.get_schedule_bounds = AsyncMock(return_value=_bounds(races))
    repo.get_lap_timings = AsyncMock(return_value=None)
    update = _cb("lap:5:s")

    await _laps_callback(update, _context(repo))

    text = update.callback_query.edit_message_text.await_args.args[0]
    assert "\u26a0" in text or "No" in text.lower()


async def test_laps_callback_uses_cache():
    """When repo returns lap data, it is displayed directly."""
    races = [_race(5)]
    repo = MagicMock()
    repo.get_schedule = AsyncMock(return_value=races)
    repo.get_schedule_bounds = AsyncMock(return_value=_bounds(races))
    repo.get_lap_timings = AsyncMock(
        return_value=[{"lap_number": 1, "driver_id": "LEC", "time": "1:33.100", "position": 3}]
    )
    update = _cb("lap:5:s")

    await _laps_callback(update, _context(repo))

    text = update.callback_query.edit_message_text.await_args.args[0]
    assert "LEC" in text


async def test_laps_callback_shows_summary_with_lap_duration():
    """Verify that lap_duration is used when time is None."""
    races = [_race(5)]
    repo = MagicMock()
    repo.get_schedule = AsyncMock(return_value=races)
    repo.get_schedule_bounds = AsyncMock(return_value=_bounds(races))
    repo.get_lap_timings = AsyncMock(
        return_value=[
            {
                "lap_number": 1,
                "driver_id": "HAM",
                "time": None,
                "lap_duration": 92.456,
                "position": 1,
            },
            {
                "lap_number": 1,
                "driver_id": "VER",
                "time": None,
                "lap_duration": 92.789,
                "position": 2,
            },
        ]
    )
    update = _cb("lap:5:s")

    await _laps_callback(update, _context(repo))

    text = update.callback_query.edit_message_text.await_args.args[0]
    assert "HAM" in text
    assert "1:32.456" in text
    assert "VER" in text
    assert "1:32.789" in text


async def test_laps_callback_handles_two_part_data():
    """Verify that _laps_callback handles 'lap:{rnd}' callback data without IndexError."""
    races = [_race(5)]
    repo = MagicMock()
    repo.get_schedule = AsyncMock(return_value=races)
    repo.get_schedule_bounds = AsyncMock(return_value=_bounds(races))
    repo.get_lap_timings = AsyncMock(
        return_value=[
            {
                "lap_number": 1,
                "driver_id": "HAM",
                "time": None,
                "lap_duration": 92.456,
                "position": 1,
            },
        ]
    )

    update = _cb("lap:5")
    await _laps_callback(update, _context(repo))

    update.callback_query.answer.assert_called_once()
    call_args = update.callback_query.edit_message_text.await_args
    assert call_args is not None
    text = call_args.args[0]
    assert "HAM" in text
    assert "1:32.456" in text


async def test_laps_callback_resolves_driver_code():
    """Verify that driver numbers are resolved to codes in the summary."""
    races = [_race(5)]
    repo = MagicMock()
    repo.get_schedule = AsyncMock(return_value=races)
    repo.get_schedule_bounds = AsyncMock(return_value=_bounds(races))

    from f1_bot.models.driver import Driver

    repo.get_drivers_map = AsyncMock(
        return_value={
            44: Driver(
                driver_id="hamilton",
                permanent_number="44",
                code="HAM",
                given_name="Lewis",
                family_name="Hamilton",
            ),
            81: Driver(
                driver_id="piastri",
                permanent_number="81",
                code="PIA",
                given_name="Oscar",
                family_name="Piastri",
            ),
        }
    )

    repo.get_lap_timings = AsyncMock(
        return_value=[
            {"lap_number": 1, "driver_id": "44", "time": "1:32.456", "position": 1},
            {"lap_number": 1, "driver_id": "81", "time": "1:32.789", "position": 2},
        ]
    )

    update = _cb("lap:5:s")
    await _laps_callback(update, _context(repo))

    text = update.callback_query.edit_message_text.await_args.args[0]
    assert "HAM" in text
    assert "PIA" in text
    assert "44" not in text
    assert "81" not in text


async def test_laps_stale_modes_fall_through_to_summary():
    """Stale lap:l / lap:dp / lap:d buttons edit to the personal-best summary.

    WHY: leftover keyboards from before this merge must not 404 as Invalid selection.
    """
    races = [_race(5)]
    repo = MagicMock()
    repo.get_schedule = AsyncMock(return_value=races)
    repo.get_schedule_bounds = AsyncMock(return_value=_bounds(races))
    repo.get_lap_timings = AsyncMock(
        return_value=[
            {
                "lap_number": 1,
                "driver_id": "44",
                "time": None,
                "lap_duration": 92.456,
                "position": 1,
            },
        ]
    )

    for data in ("lap:5:l:1", "lap:5:dp", "lap:5:d:4:0", "lap:5:l", "lap:5:d:VER:abc"):
        update = _cb(data)
        await _laps_callback(update, _context(repo))
        text = update.callback_query.edit_message_text.await_args.args[0]
        assert "Lap Times" in text
        kb = update.callback_query.edit_message_text.await_args.kwargs["reply_markup"]
        cbs = [b.callback_data for row in kb.inline_keyboard for b in row]
        assert "res:back:_:5" in cbs
        update.callback_query.answer.assert_called_once()


async def test_laps_callback_empty_from_results_keeps_back():
    """No lap data on a results tap still shows Back so the user is not trapped."""
    races = [_race(5)]
    repo = MagicMock()
    repo.get_schedule = AsyncMock(return_value=races)
    repo.get_schedule_bounds = AsyncMock(return_value=_bounds(races))
    repo.get_lap_timings = AsyncMock(return_value=[])

    update = _cb("lap:5:s")
    await _laps_callback(update, _context(repo))

    text = update.callback_query.edit_message_text.await_args.args[0]
    assert "⚠" in text or "no" in text.lower()
    kb = update.callback_query.edit_message_text.await_args.kwargs["reply_markup"]
    cbs = [b.callback_data for row in kb.inline_keyboard for b in row]
    assert "res:back:_:5" in cbs


async def test_laps_callback_invalid_round_value_error():
    update = _cb("lap:not_an_int:s")
    ctx = _context(MagicMock())
    await _laps_callback(update, ctx)

    assert update.callback_query.answer.call_count == 1
    update.callback_query.answer.assert_called_with(text="Invalid selection", show_alert=True)
    update.callback_query.edit_message_text.assert_not_called()


async def test_laps_callback_with_none_last_completed_round():
    """bounds with None last_completed_round should not crash _laps_callback."""
    races = [_race(5)]
    repo = MagicMock()
    repo.get_schedule = AsyncMock(return_value=races)
    bounds = _bounds(races)
    bounds["last_completed_round"] = None
    repo.get_schedule_bounds = AsyncMock(return_value=bounds)
    repo.get_drivers_map = AsyncMock(return_value={})
    repo.get_lap_timings = AsyncMock(return_value=[])

    update = _cb("lap:5:s")
    await _laps_callback(update, _context(repo))
    update.callback_query.answer.assert_called()


async def test_laps_callback_missing_round_in_schedule():
    """lap:{n} for a round not in the schedule still shows no-data, no crash."""
    races = [_race(5)]
    repo = MagicMock()
    repo.get_schedule = AsyncMock(return_value=races)
    bounds = _bounds(races)
    bounds["last_completed_round"] = 3
    repo.get_schedule_bounds = AsyncMock(return_value=bounds)
    repo.get_drivers_map = AsyncMock(return_value={})
    repo.get_lap_timings = AsyncMock(return_value=[])

    update = _cb("lap:3:s")
    await _laps_callback(update, _context(repo))

    text = update.callback_query.edit_message_text.await_args.args[0]
    assert "no" in text.lower() or "⚠" in text
