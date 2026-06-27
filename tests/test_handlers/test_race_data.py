"""Tests for /pitstops and /laps handlers (SQL-only reads)."""

from datetime import date, time, timedelta
from unittest.mock import AsyncMock, MagicMock

from telegram import InlineKeyboardMarkup

from f1_bot.handlers.race_data import (
    _laps_callback,
    _pitstops_callback,
    laps_handler,
    pitstops_handler,
)
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
    """When Postgres has pit stop data, it is displayed."""
    races = [_race(5)]
    repo = MagicMock()
    repo.get_schedule = AsyncMock(return_value=races)
    repo.get_schedule_bounds = AsyncMock(return_value=_bounds(races))
    # SQL-only: repo returns pre-stored data
    repo.get_pit_stops = AsyncMock(
        return_value=[
            {"driver_id": "HAM", "lap": 20, "stop_number": 1, "duration": 24.5},
            {"driver_id": "VER", "lap": 25, "stop_number": 1, "duration": 22.1},
        ]
    )
    update = _update()

    await pitstops_handler(update, _context(repo))

    call_kwargs = update.effective_message.reply_text.await_args.kwargs
    text = update.effective_message.reply_text.await_args.args[0]
    assert "HAM" in text
    assert "Lap 20" in text
    assert isinstance(call_kwargs.get("reply_markup"), InlineKeyboardMarkup)


async def test_pitstops_handler_no_stops_shows_no_data():
    """When Postgres has no pit stops for the round, shows no-data."""
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
        return_value=[{"driver_id": "NOR", "lap": 12, "stop_number": 1, "duration": 21.0}]
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
    repo.get_lap_timings = AsyncMock(
        return_value=[
            {"lap_number": 1, "driver_id": "HAM", "time": "1:32.456", "position": 1},
            {"lap_number": 1, "driver_id": "VER", "time": "1:32.789", "position": 2},
            {"lap_number": 2, "driver_id": "HAM", "time": "1:31.000", "position": 1},
            {"lap_number": 2, "driver_id": "VER", "time": "1:31.200", "position": 2},
        ]
    )
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
        return_value=[{"lap_number": 1, "driver_id": "LEC", "time": "1:33.100", "position": 3}]
    )
    update = _update()

    await laps_handler(update, _context(repo))

    text = update.effective_message.reply_text.await_args.args[0]
    assert "LEC" in text


async def test_laps_handler_shows_summary_with_lap_duration():
    """Verify that lap_duration is used when time is None."""
    races = [_race(5)]
    repo = MagicMock()
    repo.get_schedule = AsyncMock(return_value=races)
    repo.get_schedule_bounds = AsyncMock(return_value=_bounds(races))
    # OpenF1 style: time is None, lap_duration is set
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
    update = _update()

    await laps_handler(update, _context(repo))

    text = update.effective_message.reply_text.await_args.args[0]
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

    update = MagicMock()
    update.callback_query.data = "lap:5"
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()

    await _laps_callback(update, _context(repo))

    update.callback_query.answer.assert_called_once()
    call_args = update.callback_query.edit_message_text.await_args
    assert call_args is not None
    text = call_args.args[0]
    assert "HAM" in text
    assert "1:32.456" in text


async def test_laps_handler_resolves_driver_code():
    """Verify that driver numbers are resolved to codes in summary and details."""
    races = [_race(5)]
    repo = MagicMock()
    repo.get_schedule = AsyncMock(return_value=races)
    repo.get_schedule_bounds = AsyncMock(return_value=_bounds(races))

    # Mock drivers_map
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

    update = _update()
    await laps_handler(update, _context(repo))

    text = update.effective_message.reply_text.await_args.args[0]
    # Check that "HAM" and "PIA" are displayed instead of "44" and "81"
    assert "HAM" in text
    assert "PIA" in text
    assert "44" not in text
    assert "81" not in text


async def test_laps_handler_appends_placeholder_for_missing_active_driver():
    """Verify that placeholder laps are added for active but missing drivers."""
    races = [_race(5)]
    repo = MagicMock()
    repo.get_schedule = AsyncMock(return_value=races)
    repo.get_schedule_bounds = AsyncMock(return_value=_bounds(races))

    # HAM is active on lap 1 and lap 3. Lap 2 is missing for HAM.
    # VER is active on laps 1, 2, 3.
    repo.get_lap_timings = AsyncMock(
        return_value=[
            {"lap_number": 1, "driver_id": "HAM", "time": "1:30.000", "position": 1},
            {"lap_number": 1, "driver_id": "VER", "time": "1:30.500", "position": 2},
            # Lap 2 has no HAM in DB
            {"lap_number": 2, "driver_id": "VER", "time": "1:31.000", "position": 1},
            {"lap_number": 3, "driver_id": "HAM", "time": "1:30.200", "position": 1},
            {"lap_number": 3, "driver_id": "VER", "time": "1:30.800", "position": 2},
        ]
    )

    # We call the callback for Lap 2
    update = MagicMock()
    update.callback_query.data = "lap:5:l:2"
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()

    await _laps_callback(update, _context(repo))

    call_args = update.callback_query.edit_message_text.await_args
    assert call_args is not None
    text = call_args.args[0]

    # Check that VER has timing, and HAM has a placeholder with "—"
    assert "VER" in text
    assert "1:31.000" in text
    assert "HAM" in text
    # HAM should show "—" in timing table
    assert "—" in text


async def test_laps_handler_shows_formation_lap_note():
    """Verify that Lap 1 contains the formation lap notice."""
    races = [_race(5)]
    repo = MagicMock()
    repo.get_schedule = AsyncMock(return_value=races)
    repo.get_schedule_bounds = AsyncMock(return_value=_bounds(races))
    repo.get_lap_timings = AsyncMock(
        return_value=[
            {"lap_number": 1, "driver_id": "HAM", "time": "1:30.000", "position": 1},
        ]
    )

    update = MagicMock()
    update.callback_query.data = "lap:5:l:1"
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()

    await _laps_callback(update, _context(repo))

    call_args = update.callback_query.edit_message_text.await_args
    text = call_args.args[0]

    assert "standing start" in text


async def test_laps_driver_picker_keyboard_resolves_codes():
    """Verify that _laps_driver_picker_keyboard displays driver abbreviations while preserving driver numbers in callback_data."""
    from f1_bot.handlers.race_data import _laps_driver_picker_keyboard
    from f1_bot.models.driver import Driver

    drivers = {
        81: Driver(
            driver_id="piastri",
            permanent_number="81",
            code="PIA",
            given_name="Oscar",
            family_name="Piastri",
        ),
    }

    keyboard = _laps_driver_picker_keyboard(rnd=5, driver_ids=["81"], drivers=drivers)
    # The keyboard has columns. The first row has buttons for drivers.
    buttons = keyboard.inline_keyboard[0]
    button = buttons[0]

    assert button.text == "PIA"
    assert button.callback_data == "lap:5:d:81:0"


async def test_laps_callback_clamps_out_of_bounds_pages():
    """Verify that out-of-bounds page values in callbacks are clamped safely."""
    races = [_race(5)]
    repo = MagicMock()
    repo.get_schedule = AsyncMock(return_value=races)
    repo.get_schedule_bounds = AsyncMock(return_value=_bounds(races))
    # We mock 25 laps (meaning 2 pages: page 0 has 20 laps, page 1 has 5 laps)
    repo.get_lap_timings = AsyncMock(
        return_value=[
            {"lap_number": i, "driver_id": "HAM", "time": "1:30.000", "position": 1}
            for i in range(1, 26)
        ]
    )

    # Case A: Negative page (-1) -> should be clamped to page 0
    update_neg = MagicMock()
    update_neg.callback_query.data = "lap:5:d:HAM:-1"
    update_neg.callback_query.answer = AsyncMock()
    update_neg.callback_query.edit_message_text = AsyncMock()

    await _laps_callback(update_neg, _context(repo))
    text_neg = update_neg.callback_query.edit_message_text.await_args.args[0]
    assert "Page 1/2" in text_neg  # verify it shows page 0 (which prints Page 1/2)

    # Case B: Exceeding page (999) -> should be clamped to page 1 (which prints Page 2/2)
    update_pos = MagicMock()
    update_pos.callback_query.data = "lap:5:d:HAM:999"
    update_pos.callback_query.answer = AsyncMock()
    update_pos.callback_query.edit_message_text = AsyncMock()

    await _laps_callback(update_pos, _context(repo))
    text_pos = update_pos.callback_query.edit_message_text.await_args.args[0]
    assert "Page 2/2" in text_pos  # verify it shows page 1 (which prints Page 2/2)


async def test_laps_callback_handles_invalid_driver():
    """Verify that querying timings for a driver with no laps alerts the user and exits."""
    races = [_race(5)]
    repo = MagicMock()
    repo.get_schedule = AsyncMock(return_value=races)
    repo.get_schedule_bounds = AsyncMock(return_value=_bounds(races))
    repo.get_lap_timings = AsyncMock(
        return_value=[
            {"lap_number": 1, "driver_id": "HAM", "time": "1:30.000", "position": 1},
        ]
    )

    update = MagicMock()
    update.callback_query.data = "lap:5:d:INVALID:0"
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()

    await _laps_callback(update, _context(repo))

    assert update.callback_query.answer.call_count == 1
    update.callback_query.answer.assert_any_call(text="No data for driver INVALID", show_alert=True)
    update.callback_query.edit_message_text.assert_not_called()


async def test_laps_by_lap_handles_partial_null_sectors():
    """Verify that mixed None sector timings format correctly as '—' without crash."""
    from f1_bot.formatting.messages import format_laps_by_lap
    from f1_bot.models.results import LapTime

    # HAM has sector 1 timing, but sector 2 and 3 are missing
    laps = [
        LapTime(
            lap_number=1,
            driver_id="HAM",
            position=1,
            time="1:30.000",
            duration_sector_1=25.5,
            duration_sector_2=None,
            duration_sector_3=None,
            lap_duration=90.0,
        )
    ]

    text = format_laps_by_lap(race=_race(5), laps=laps, lap_number=1, total_laps=1)

    assert "HAM" in text
    assert "25.5" in text
    # Missing S2/S3 should format as '—'
    assert "—" in text


async def test_pitstops_callback_invalid_round_value_error():
    from f1_bot.handlers.race_data import _pitstops_callback

    update = MagicMock()
    update.callback_query.data = "pit:not_an_int"
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()

    ctx = _context(MagicMock())
    await _pitstops_callback(update, ctx)

    assert update.callback_query.answer.call_count == 1
    update.callback_query.answer.assert_called_with(text="Invalid selection", show_alert=True)
    update.callback_query.edit_message_text.assert_not_called()


async def test_laps_callback_invalid_round_value_error():
    from f1_bot.handlers.race_data import _laps_callback

    update = MagicMock()
    update.callback_query.data = "lap:not_an_int:s"
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()

    ctx = _context(MagicMock())
    await _laps_callback(update, ctx)

    assert update.callback_query.answer.call_count == 1
    update.callback_query.answer.assert_called_with(text="Invalid selection", show_alert=True)
    update.callback_query.edit_message_text.assert_not_called()


# --- Fix 7: Truncated callback data guards ---


async def test_laps_callback_truncated_lap_mode_data():
    """'lap:5:l' (missing lap_num) should show 'Invalid selection' alert."""
    from f1_bot.handlers.race_data import _laps_callback

    races = [_race(5)]
    repo = MagicMock()
    repo.get_schedule = AsyncMock(return_value=races)
    repo.get_schedule_bounds = AsyncMock(return_value=_bounds(races))
    repo.get_drivers_map = AsyncMock(return_value={})
    repo.get_lap_timings = AsyncMock(
        return_value=[{"driver_id": "ham", "lap_number": 1, "time": "1:30.0"}]
    )

    update = MagicMock()
    update.callback_query.data = "lap:5:l"  # missing lap number (parts[3])
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()

    ctx = _context(repo)
    await _laps_callback(update, ctx)

    update.callback_query.answer.assert_called_with(text="Invalid selection", show_alert=True)


async def test_laps_callback_non_integer_page():
    """'lap:5:d:VER:abc' (non-integer page) should show 'Invalid selection' alert."""
    from f1_bot.handlers.race_data import _laps_callback

    races = [_race(5)]
    repo = MagicMock()
    repo.get_schedule = AsyncMock(return_value=races)
    repo.get_schedule_bounds = AsyncMock(return_value=_bounds(races))
    repo.get_drivers_map = AsyncMock(return_value={})
    repo.get_lap_timings = AsyncMock(
        return_value=[{"driver_id": "VER", "lap_number": 1, "time": "1:30.0"}]
    )

    update = MagicMock()
    update.callback_query.data = "lap:5:d:VER:abc"  # non-integer page
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()

    ctx = _context(repo)
    await _laps_callback(update, ctx)

    update.callback_query.answer.assert_called_with(text="Invalid selection", show_alert=True)


# --- None bounds guard ---


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

    update = MagicMock()
    update.callback_query.data = "pit:5"
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()

    await _pitstops_callback(update, _context(repo))
    update.callback_query.answer.assert_called()


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

    update = MagicMock()
    update.callback_query.data = "lap:5:s"
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()

    await _laps_callback(update, _context(repo))
    update.callback_query.answer.assert_called()


# --- StopIteration guard ---


async def test_laps_handler_missing_round_in_schedule():
    """When resolve_default_round returns a round not in the schedule, show no-data gracefully."""
    races = [_race(5)]
    repo = MagicMock()
    repo.get_schedule = AsyncMock(return_value=races)
    bounds = _bounds(races)
    bounds["last_completed_round"] = 3
    repo.get_schedule_bounds = AsyncMock(return_value=bounds)
    repo.get_drivers_map = AsyncMock(return_value={})

    update = _update()
    await laps_handler(update, _context(repo))

    text = update.effective_message.reply_text.await_args.args[0]
    assert "no" in text.lower() or "⚠" in text
