"""Tests for unified /next and /results two-state handlers."""

from datetime import date, time, timedelta
from unittest.mock import AsyncMock, MagicMock

from telegram import InlineKeyboardMarkup

from f1_bot.handlers.results import results_handler
from f1_bot.handlers.schedule import (
    countdown_handler,
    next_handler,
    schedule_handler,
)
from f1_bot.models.race import Circuit, Race, RaceSession


def _circuit():
    return Circuit(circuit_id="monza", name="Monza", locality="Monza", country="Italy")


def _future_date(days_ahead: int) -> date:
    return date.today() + timedelta(days=days_ahead)


def _past_date(days_ago: int) -> date:
    return date.today() - timedelta(days=days_ago)


def _race():
    return Race(
        season=date.today().year,
        round=16,
        name="Italian Grand Prix",
        circuit=_circuit(),
        date=_future_date(10),
        time=time(13, 0),
        fp1=RaceSession(name="FP1", date=_future_date(8), time=time(11, 30)),
        fp2=RaceSession(name="FP2", date=_future_date(8), time=time(15, 0)),
        fp3=RaceSession(name="FP3", date=_future_date(9), time=time(10, 30)),
        qualifying=RaceSession(name="Qualifying", date=_future_date(9), time=time(14, 0)),
    )


def _past_race():
    """Race whose sessions are in the past — for completed-session tests."""
    return Race(
        season=date.today().year,
        round=15,
        name="Italian Grand Prix",
        circuit=_circuit(),
        date=_past_date(5),
        time=time(13, 0),
        fp1=RaceSession(name="FP1", date=_past_date(7), time=time(11, 30)),
        fp2=RaceSession(name="FP2", date=_past_date(7), time=time(15, 0)),
        fp3=RaceSession(name="FP3", date=_past_date(6), time=time(10, 30)),
        qualifying=RaceSession(name="Qualifying", date=_past_date(6), time=time(14, 0)),
    )


def _bounds(races: list | None = None) -> dict:
    """Produce the dict shape returned by Repository.get_schedule_bounds."""
    races = races or []
    today = date.today()
    completed = [r for r in races if r.date <= today]
    upcoming = [r for r in races if r.date > today]
    sprint_rounds = [r.round for r in races if getattr(r, "sprint", None) is not None]
    completed_sprint_rounds = [
        r.round for r in races if getattr(r, "sprint", None) is not None and r.date <= today
    ]
    return {
        "total_rounds": max((r.round for r in races), default=0),
        "completed_rounds": len(completed),
        "upcoming_rounds": len(upcoming),
        "last_completed_round": completed[-1].round if completed else None,
        "next_upcoming_round": upcoming[0].round if upcoming else None,
        "sprint_rounds": sprint_rounds,
        "completed_sprint_rounds": completed_sprint_rounds,
    }


def _context(repo=None, openf1=None, jolpica=None):
    ctx = MagicMock()
    ctx.bot_data = {
        "repo": repo or MagicMock(),
        "openf1": openf1 or MagicMock(),
        "jolpica": jolpica or MagicMock(),
    }
    ctx.args = []
    return ctx


def _update():
    update = MagicMock()
    update.effective_user.id = 123
    update.effective_message.reply_text = AsyncMock()
    return update


# ---------------------------------------------------------------------------
# /next — State A (overview)
# ---------------------------------------------------------------------------


async def test_next_handler_shows_next_upcoming_race():
    repo = MagicMock()
    r1 = _race()
    r1.round = 17
    races = [r1]
    repo.get_schedule = AsyncMock(return_value=races)
    repo.get_schedule_bounds = AsyncMock(return_value=_bounds(races))
    repo.get_user_timezone = AsyncMock(return_value="UTC")
    ctx = _context(repo=repo)
    update = _update()

    await next_handler(update, ctx)

    assert update.effective_message.reply_text.await_count == 1
    reply_text = update.effective_message.reply_text.await_args.args[0]
    assert "Next Race" in reply_text
    assert "Italian Grand Prix" in reply_text
    # Should have two-state keyboard with session filter buttons
    markup = update.effective_message.reply_text.await_args.kwargs.get("reply_markup")
    assert isinstance(markup, InlineKeyboardMarkup)
    # State A keyboard has 3 rows (practice + competitive + bell)
    assert len(markup.inline_keyboard) == 3
    # First row: FP1, FP2, FP3, Q
    labels = [btn.text for btn in markup.inline_keyboard[0]]
    assert labels == ["FP1", "FP2", "FP3", "Q"]
    # Second row: SQ, SPR, Race (All is excluded)
    labels = [btn.text for btn in markup.inline_keyboard[1]]
    assert labels == ["SQ", "SPR", "Race"]


async def test_next_handler_no_upcoming_races():
    """When all races are in the past, shows no-data message."""
    repo = MagicMock()
    r = _past_race()
    repo.get_schedule = AsyncMock(return_value=[r])
    repo.get_schedule_bounds = AsyncMock(return_value=_bounds([r]))
    repo.get_user_timezone = AsyncMock(return_value="UTC")
    update = _update()

    await next_handler(update, _context(repo=repo))

    text = update.effective_message.reply_text.await_args.args[0]
    assert "⚠️" in text


async def test_next_handler_callback_data_format():
    """Verify callback_data in /next keyboard uses new format next:filtered:{filter}:{round}."""
    repo = MagicMock()
    r = _race()
    r.round = 10
    repo.get_schedule = AsyncMock(return_value=[r])
    repo.get_schedule_bounds = AsyncMock(return_value=_bounds([r]))
    repo.get_user_timezone = AsyncMock(return_value="UTC")
    update = _update()

    await next_handler(update, _context(repo=repo))

    markup = update.effective_message.reply_text.await_args.kwargs["reply_markup"]
    # FP1 button callback_data
    fp1_btn = markup.inline_keyboard[0][0]
    assert fp1_btn.callback_data == "next:filtered:fp1:10"


# ---------------------------------------------------------------------------
# /results — State A (overview)
# ---------------------------------------------------------------------------


async def test_results_handler_shows_last_completed_round():
    r_prev = Race(
        season=date.today().year,
        round=14,
        name="Dutch Grand Prix",
        circuit=_circuit(),
        date=_past_date(20),
        time=time(13, 0),
        fp1=RaceSession(name="FP1", date=_past_date(22), time=time(11, 30)),
        qualifying=RaceSession(name="Qualifying", date=_past_date(21), time=time(14, 0)),
    )
    r1 = _past_race()
    r1.round = 15
    repo = MagicMock()
    repo.get_schedule = AsyncMock(return_value=[r_prev, r1])
    repo.get_schedule_bounds = AsyncMock(return_value=_bounds([r_prev, r1]))
    repo.get_race_results = AsyncMock(
        return_value=[
            {
                "position": 1,
                "grid": 1,
                "laps": 50,
                "status": "Finished",
                "points": 25,
                "driver": {
                    "driver_id": "ver",
                    "given_name": "Max",
                    "family_name": "Verstappen",
                    "code": "VER",
                },
                "constructor": {"constructor_id": "red_bull", "name": "Red Bull"},
            }
        ]
    )
    repo.get_last_result_round = AsyncMock(return_value=15)
    repo.get_drivers_by_id_map = AsyncMock(return_value={})
    ctx = _context(repo=repo)
    update = _update()

    await results_handler(update, ctx)

    assert update.effective_message.reply_text.await_count == 1
    reply_text = update.effective_message.reply_text.await_args.args[0]
    assert "Verstappen" in reply_text
    # Should have two-state keyboard with session filter buttons
    markup = update.effective_message.reply_text.await_args.kwargs.get("reply_markup")
    assert isinstance(markup, InlineKeyboardMarkup)
    # Overview keyboard now has 3 rows (pager row + 2 filter rows) because completed rounds > 1
    assert len(markup.inline_keyboard) == 3
    # Check the pager row
    pager_row = markup.inline_keyboard[0]
    assert len(pager_row) == 2  # Prev (◀) and current label
    assert pager_row[0].text == "◀"
    assert pager_row[0].callback_data == "res:back:_:14"
    assert pager_row[1].text == "R15/15"
    assert pager_row[1].callback_data == "res:back:_:15"


async def test_results_handler_no_completed_round_shows_no_data():
    """When no race is completed, shows no-data message."""
    repo = MagicMock()
    repo.get_schedule = AsyncMock(return_value=[_race()])  # future race only
    repo.get_schedule_bounds = AsyncMock(return_value=_bounds([_race()]))
    repo.get_last_result_round = AsyncMock(return_value=None)
    update = _update()

    await results_handler(update, _context(repo=repo))

    text = update.effective_message.reply_text.await_args.args[0]
    assert "⚠️" in text


async def test_results_handler_sql_only_no_api_calls():
    """Verify /results handler does NOT call jolpica or openf1 directly."""
    r1 = _past_race()
    r1.round = 15
    repo = MagicMock()
    repo.get_schedule = AsyncMock(return_value=[r1])
    repo.get_schedule_bounds = AsyncMock(return_value=_bounds([r1]))
    repo.get_race_results = AsyncMock(
        return_value=[
            {
                "position": 1,
                "grid": 1,
                "laps": 50,
                "status": "Finished",
                "points": 25,
                "driver": {
                    "driver_id": "ver",
                    "given_name": "Max",
                    "family_name": "Verstappen",
                    "code": "VER",
                },
                "constructor": {"constructor_id": "rb", "name": "Red Bull"},
            }
        ]
    )
    repo.get_last_result_round = AsyncMock(return_value=15)
    repo.get_drivers_by_id_map = AsyncMock(return_value={})

    jolpica = MagicMock()
    openf1 = MagicMock()
    ctx = _context(repo=repo, jolpica=jolpica, openf1=openf1)
    update = _update()

    await results_handler(update, ctx)

    # No API calls should have been made
    assert jolpica.get_race_results.call_count == 0
    assert jolpica.get_qualifying_results.call_count == 0
    assert openf1.get_sessions.call_count == 0
    assert openf1.get_session_results.call_count == 0


# ---------------------------------------------------------------------------
# /schedule and /countdown (unchanged)
# ---------------------------------------------------------------------------


async def test_schedule_handler_shows_all_races():
    repo = MagicMock()
    races = [_race(), _past_race()]
    repo.get_schedule = AsyncMock(return_value=races)
    repo.get_schedule_bounds = AsyncMock(return_value=_bounds(races))
    repo.get_user_timezone = AsyncMock(return_value="UTC")
    update = _update()

    await schedule_handler(update, _context(repo=repo))

    text = update.effective_message.reply_text.await_args.args[0]
    assert "Italian Grand Prix" in text


async def test_countdown_handler_shows_countdown():
    repo = MagicMock()
    repo.get_next_race = AsyncMock(return_value=_race())
    repo.get_user_timezone = AsyncMock(return_value="UTC")
    update = _update()

    await countdown_handler(update, _context(repo=repo))

    text = update.effective_message.reply_text.await_args.args[0]
    assert "Countdown" in text


async def test_get_next_race_utc_alignment(repo, monkeypatch):
    """It uses UTC date for scheduling checks to avoid local time zone delta shifts."""
    from datetime import UTC, date, datetime, time

    from f1_bot.models.race import Circuit, Race

    class MockDatetime:
        @classmethod
        def now(cls, tz=None):
            # Return UTC time: Saturday June 20, 2026, 23:00 UTC (Taipei is Sunday June 21, 07:00)
            return datetime(2026, 6, 20, 23, 0, 0, tzinfo=UTC)

    monkeypatch.setattr("f1_bot.storage.repository.datetime", MockDatetime)

    race = Race(
        season=2026,
        round=1,
        name="Test Grand Prix",
        circuit=Circuit(circuit_id="test", name="Test", locality="Test", country="Test"),
        date=date(2026, 6, 20),
        time=time(13, 0),
    )

    await repo.save_schedule(2026, [race])
    next_race = await repo.get_next_race(2026)
    assert next_race is not None
    assert next_race.name == "Test Grand Prix"


async def test_format_all_results_dynamic_truncation(monkeypatch):
    """Verify Stage 1, Stage 2, and Stage 3 truncation rules in _format_all_results."""
    from f1_bot.handlers.results import _format_all_results

    mock_results = {
        "fp1": "FP1: Max",
        "fp2": "FP2: Max",
        "fp3": "FP3: Max",
        "sprint_qualifying": "SQ: Max",
        "sprint": "Sprint: Max",
        "qualifying": "Q: Max",
        "race": "Race: Max",
    }

    async def mock_format_session(repo, season, rnd, race, key, drivers_map, top_n=None):
        val = mock_results.get(key)
        if val and top_n is not None:
            return val + f" (top {top_n})"
        return val

    monkeypatch.setattr("f1_bot.handlers.results._format_results_for_session", mock_format_session)

    repo = MagicMock()
    race = MagicMock()
    drivers_map = {}

    # Case 1: Short message (<= 4096)
    text = await _format_all_results(repo, 2026, 1, race, drivers_map)
    assert "FP1: Max" in text
    assert "Race: Max" in text
    assert "omitted" not in text

    # Case 2: Long message (> 4096) -> Drop practice
    mock_results["fp1"] = "A" * 4100
    text_long = await _format_all_results(repo, 2026, 1, race, drivers_map)
    assert "FP2: Max" not in text_long
    assert "FP1: Max" not in text_long
    assert "SQ: Max" in text_long
    assert "Race: Max" in text_long
    assert "omitted to fit Telegram character limits" in text_long
    assert "top 10" not in text_long

    # Case 3: Extremely long message even without practice -> Truncate to top 10
    mock_results["fp1"] = "A" * 4100
    mock_results["race"] = "B" * 4100
    text_extreme = await _format_all_results(repo, 2026, 1, race, drivers_map)
    assert "FP2: Max" not in text_extreme
    assert "SQ: Max (top 10)" in text_extreme
    assert "B" * 4100 + " (top 10)" in text_extreme
    assert "truncated to top 10" in text_extreme


async def test_get_completed_rounds_for_session():
    from f1_bot.handlers.results import _get_completed_rounds_for_session

    c = Circuit(circuit_id="test", name="Test", locality="Test", country="Test")
    r1 = Race(
        season=2026,
        round=1,
        name="Race 1",
        circuit=c,
        date=date(2026, 3, 1),
        time=time(13, 0),
        fp1=RaceSession(name="FP1", date=date(2026, 2, 27), time=time(11, 30)),
        fp2=RaceSession(name="FP2", date=date(2026, 2, 27), time=time(15, 0)),
        fp3=RaceSession(name="FP3", date=date(2026, 2, 28), time=time(10, 30)),
        qualifying=RaceSession(name="Qualifying", date=date(2026, 2, 28), time=time(14, 0)),
    )
    r2 = Race(
        season=2026,
        round=2,
        name="Race 2",
        circuit=c,
        date=date(2026, 3, 15),
        time=time(13, 0),
        fp1=RaceSession(name="FP1", date=date(2026, 3, 13), time=time(11, 30)),
        sprint_qualifying=RaceSession(name="SQ", date=date(2026, 3, 13), time=time(15, 0)),
        sprint=RaceSession(name="Sprint", date=date(2026, 3, 14), time=time(10, 30)),
        qualifying=RaceSession(name="Qualifying", date=date(2026, 3, 14), time=time(14, 0)),
    )
    r3 = Race(
        season=2026,
        round=3,
        name="Race 3",
        circuit=c,
        date=date(2026, 4, 1),
        time=time(13, 0),
        fp1=RaceSession(name="FP1", date=date(2026, 3, 30), time=time(11, 30)),
        fp2=RaceSession(name="FP2", date=date(2026, 3, 30), time=time(15, 0)),
        fp3=RaceSession(name="FP3", date=date(2026, 3, 31), time=time(10, 30)),
        qualifying=RaceSession(name="Qualifying", date=date(2026, 3, 31), time=time(14, 0)),
    )
    races = [r1, r2, r3]

    assert _get_completed_rounds_for_session(races, "fp3") == [1, 3]
    assert _get_completed_rounds_for_session(races, "sprint") == [2]
    assert _get_completed_rounds_for_session(races, "race") == [1, 2, 3]


async def test_get_completed_rounds_qualifying_before_race():
    """Round with completed qualifying but pending race is navigable."""
    from f1_bot.handlers.results import _get_completed_rounds_for_session

    c = Circuit(circuit_id="test", name="Test", locality="Test", country="Test")
    today = date.today()
    # R1: fully completed (past)
    r1 = Race(
        season=2026,
        round=1,
        name="Race 1",
        circuit=c,
        date=today - timedelta(days=14),
        time=time(13, 0),
        fp1=RaceSession(name="FP1", date=today - timedelta(days=16), time=time(11, 30)),
        qualifying=RaceSession(name="Q", date=today - timedelta(days=15), time=time(14, 0)),
    )
    # R2: qualifying done yesterday, race tomorrow
    r2 = Race(
        season=2026,
        round=2,
        name="Race 2",
        circuit=c,
        date=today + timedelta(days=1),
        time=time(13, 0),
        fp1=RaceSession(name="FP1", date=today - timedelta(days=2), time=time(11, 30)),
        qualifying=RaceSession(name="Q", date=today - timedelta(days=1), time=time(14, 0)),
    )
    races = [r1, r2]

    # qualifying completed for both rounds
    assert _get_completed_rounds_for_session(races, "qualifying") == [1, 2]
    # "all" includes R2 because FP1 and Q are completed
    assert _get_completed_rounds_for_session(races, "all") == [1, 2]
    # race only completed for R1
    assert _get_completed_rounds_for_session(races, "race") == [1]


def test_results_filtered_keyboard_custom_denominator():
    from f1_bot.handlers.pagination import results_filtered_keyboard

    navigable = [1, 2, 3, 5, 6]
    markup = results_filtered_keyboard(
        current_round=5, navigable_rounds=navigable, session_key="fp3", last_completed_round=7
    )

    nav_row = markup.inline_keyboard[0]
    assert len(nav_row) == 3
    assert nav_row[0].text == "◀"
    assert nav_row[0].callback_data == "res:filtered:fp3:3"
    assert nav_row[1].text == "R5/7"
    assert nav_row[2].text == "▶"
    assert nav_row[2].callback_data == "res:filtered:fp3:6"


async def test_results_callback_duplicate_answer_guard(monkeypatch):
    from f1_bot.handlers.results import _results_callback

    c = Circuit(circuit_id="test", name="Test", locality="Test", country="Test")
    r = Race(
        season=2026,
        round=8,
        name="Monaco",
        circuit=c,
        date=date(2026, 5, 24),
        time=time(13, 0),
        fp1=RaceSession(name="FP1", date=date(2026, 5, 22), time=time(11, 30)),
        fp2=RaceSession(name="FP2", date=date(2026, 5, 22), time=time(15, 0)),
        fp3=RaceSession(name="FP3", date=date(2026, 5, 23), time=time(10, 30)),
        qualifying=RaceSession(name="Qualifying", date=date(2026, 5, 23), time=time(14, 0)),
    )

    repo = MagicMock()
    repo.get_schedule = AsyncMock(return_value=[r])
    repo.get_schedule_bounds = AsyncMock(return_value={"last_completed_round": 8})
    repo.get_drivers_by_id_map = AsyncMock(return_value={})

    update = MagicMock()
    update.callback_query.data = "res:filtered:sprint:8"
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()

    # Mock inline keyboard to extract current round
    btn_mock = MagicMock()
    btn_mock.callback_data = "res:filtered:fp3:8"
    update.callback_query.message.reply_markup.inline_keyboard = [[btn_mock]]

    ctx = _context(repo=repo)
    await _results_callback(update, ctx)

    assert update.callback_query.answer.call_count == 1
    update.callback_query.answer.assert_called_with(
        text="No Sprint data yet this season", show_alert=True
    )
    update.callback_query.edit_message_text.assert_not_called()


async def test_results_callback_auto_jump_session(monkeypatch):
    from f1_bot.handlers.results import _results_callback

    c = Circuit(circuit_id="test", name="Test", locality="Test", country="Test")
    r7 = Race(
        season=2026,
        round=7,
        name="China",
        circuit=c,
        date=date(2026, 4, 19),
        time=time(15, 0),
        fp1=RaceSession(name="FP1", date=date(2026, 4, 17), time=time(11, 30)),
        sprint_qualifying=RaceSession(
            name="Sprint Qualifying", date=date(2026, 4, 17), time=time(15, 30)
        ),
        sprint=RaceSession(name="Sprint", date=date(2026, 4, 18), time=time(11, 0)),
        qualifying=RaceSession(name="Qualifying", date=date(2026, 4, 18), time=time(15, 0)),
    )
    r8 = Race(
        season=2026,
        round=8,
        name="Monaco",
        circuit=c,
        date=date(2026, 5, 24),
        time=time(13, 0),
        fp1=RaceSession(name="FP1", date=date(2026, 5, 22), time=time(11, 30)),
        fp2=RaceSession(name="FP2", date=date(2026, 5, 22), time=time(15, 0)),
        fp3=RaceSession(name="FP3", date=date(2026, 5, 23), time=time(10, 30)),
        qualifying=RaceSession(name="Qualifying", date=date(2026, 5, 23), time=time(14, 0)),
    )

    repo = MagicMock()
    repo.get_schedule = AsyncMock(return_value=[r7, r8])
    repo.get_schedule_bounds = AsyncMock(return_value={"last_completed_round": 8})
    repo.get_drivers_by_id_map = AsyncMock(return_value={})
    repo.get_sprint_results = AsyncMock(return_value=[])

    update = MagicMock()
    update.callback_query.data = "res:filtered:sprint:8"
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()

    # Mock inline keyboard to extract current round
    btn_mock = MagicMock()
    btn_mock.callback_data = "res:filtered:fp3:8"
    update.callback_query.message.reply_markup.inline_keyboard = [[btn_mock]]

    ctx = _context(repo=repo)
    await _results_callback(update, ctx)

    assert update.callback_query.answer.call_count == 1
    update.callback_query.answer.assert_called_with()
    assert update.callback_query.edit_message_text.call_count == 1
    args, kwargs = update.callback_query.edit_message_text.call_args
    markup = kwargs["reply_markup"]
    nav_row = markup.inline_keyboard[0]
    assert nav_row[0].text == "R7/7"


async def test_results_callback_fp2_fallback_routing():
    from f1_bot.handlers.results import _results_callback

    c = Circuit(circuit_id="test", name="Test", locality="Test", country="Test")
    # r7 is a sprint weekend and does not have fp2
    r7 = Race(
        season=2026,
        round=7,
        name="China",
        circuit=c,
        date=date(2026, 4, 19),
        time=time(15, 0),
        fp1=RaceSession(name="FP1", date=date(2026, 4, 17), time=time(11, 30)),
        sprint_qualifying=RaceSession(
            name="Sprint Qualifying", date=date(2026, 4, 17), time=time(15, 30)
        ),
        sprint=RaceSession(name="Sprint", date=date(2026, 4, 18), time=time(11, 0)),
        qualifying=RaceSession(name="Qualifying", date=date(2026, 4, 18), time=time(15, 0)),
    )

    repo = MagicMock()
    repo.get_schedule = AsyncMock(return_value=[r7])
    repo.get_schedule_bounds = AsyncMock(return_value={"last_completed_round": 7})
    repo.get_drivers_by_id_map = AsyncMock(return_value={})

    update = MagicMock()
    update.callback_query.data = "res:filtered:fp2:7"
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()

    # Mock inline keyboard to extract current round
    btn_mock = MagicMock()
    btn_mock.callback_data = "res:filtered:fp1:7"
    update.callback_query.message.reply_markup.inline_keyboard = [[btn_mock]]

    ctx = _context(repo=repo)
    await _results_callback(update, ctx)

    assert update.callback_query.answer.call_count == 1
    update.callback_query.answer.assert_called_with(
        text="No FP2 data yet this season", show_alert=True
    )
    update.callback_query.edit_message_text.assert_not_called()


async def test_results_callback_invalid_round_value_error():
    from f1_bot.handlers.results import _results_callback

    update = MagicMock()
    update.callback_query.data = "res:filtered:fp1:not_an_int"
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()

    ctx = _context()
    await _results_callback(update, ctx)

    assert update.callback_query.answer.call_count == 1
    update.callback_query.answer.assert_called_with(text="Invalid selection", show_alert=True)
    update.callback_query.edit_message_text.assert_not_called()


async def test_schedule_callback_invalid_round_value_error():
    from f1_bot.handlers.schedule import _next_callback

    update = MagicMock()
    update.callback_query.data = "next:filtered:race:not_an_int"
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()

    ctx = _context()
    await _next_callback(update, ctx)

    assert update.callback_query.answer.call_count == 1
    update.callback_query.answer.assert_called_with(text="Invalid selection", show_alert=True)
    update.callback_query.edit_message_text.assert_not_called()


# --- Fix 10: Nonexistent round in _results_callback ---


async def test_results_callback_nonexistent_round():
    """Callback with a round number that doesn't exist in schedule should show alert."""
    from f1_bot.handlers.results import _results_callback

    c = Circuit(circuit_id="test", name="Test", locality="Test", country="Test")
    r1 = Race(season=2026, round=1, name="Test GP", circuit=c, date=date(2026, 3, 1))

    repo = MagicMock()
    repo.get_schedule = AsyncMock(return_value=[r1])
    repo.get_schedule_bounds = AsyncMock(return_value={"last_completed_round": 1})

    update = MagicMock()
    update.callback_query.data = "res:filtered:race:99"  # round 99 doesn't exist
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()

    ctx = _context(repo=repo)
    await _results_callback(update, ctx)

    update.callback_query.answer.assert_called_with(text="Round not found", show_alert=True)
    update.callback_query.edit_message_text.assert_not_called()


async def test_format_all_results_prefetch_no_regression(monkeypatch):
    """_format_all_results with short combined text returns it directly (Stage 1)."""
    from f1_bot.handlers.results import _format_all_results

    repo = MagicMock()
    c = Circuit(circuit_id="test", name="Test", locality="Test", country="Test")
    race = Race(season=2026, round=5, name="Test GP", circuit=c, date=date(2026, 5, 1))

    call_count = 0

    async def mock_format(r, s, rnd, rc, key, dm, top_n=None):
        nonlocal call_count
        call_count += 1
        if key == "race":
            return "Race results text"
        if key == "qualifying":
            return "Qualifying results text"
        return None

    monkeypatch.setattr("f1_bot.handlers.results._format_results_for_session", mock_format)

    result = await _format_all_results(repo, 2026, 5, race, {})
    assert result is not None
    assert "Race results text" in result
    assert "Qualifying results text" in result
    # With pre-fetch, only 7 calls (one per session key), not 7+4=11
    assert call_count == 7
