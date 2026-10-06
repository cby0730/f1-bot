"""Tests for unified /next and /results two-state handlers."""

from datetime import UTC, date, datetime, time, timedelta
from unittest.mock import AsyncMock, MagicMock

from telegram import InlineKeyboardMarkup

from f1_bot.handlers.results import results_handler
from f1_bot.handlers.schedule import (
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
    update = _update()

    await next_handler(update, _context(repo=repo))

    markup = update.effective_message.reply_text.await_args.kwargs["reply_markup"]
    # FP1 button callback_data
    fp1_btn = markup.inline_keyboard[0][0]
    assert fp1_btn.callback_data == "next:filtered:fp1:10"


# ---------------------------------------------------------------------------
# /results — State A (overview)
# ---------------------------------------------------------------------------


async def test_results_handler_shows_latest_round_with_results():
    """Both rounds have stored race results → open the newer one, ◀ pages to the older."""
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
    repo.get_result_sessions_by_round = AsyncMock(return_value={14: {"race"}, 15: {"race"}})
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
    # Overview keyboard has 4 rows: pager + 2 filter rows + Pit/Laps (completed rounds > 1)
    assert len(markup.inline_keyboard) == 4
    # Check the pager row
    pager_row = markup.inline_keyboard[0]
    assert len(pager_row) == 2  # Prev (◀) and current label
    assert pager_row[0].text == "◀"
    assert pager_row[0].callback_data == "res:back:_:14"
    assert pager_row[1].text == "R15/15"
    assert pager_row[1].callback_data == "rpk:rb:15"


async def test_results_handler_no_completed_round_shows_no_data():
    """When no race is completed, shows no-data message."""
    repo = MagicMock()
    repo.get_schedule = AsyncMock(return_value=[_race()])  # future race only
    repo.get_schedule_bounds = AsyncMock(return_value=_bounds([_race()]))
    repo.get_result_sessions_by_round = AsyncMock(return_value={})
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
    repo.get_result_sessions_by_round = AsyncMock(return_value={15: {"race"}})
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
# /schedule
# ---------------------------------------------------------------------------


async def test_schedule_handler_shows_all_races():
    repo = MagicMock()
    races = [_race(), _past_race()]
    repo.get_schedule = AsyncMock(return_value=races)
    repo.get_schedule_bounds = AsyncMock(return_value=_bounds(races))
    update = _update()

    await schedule_handler(update, _context(repo=repo))

    text = update.effective_message.reply_text.await_args.args[0]
    assert "Italian Grand Prix" in text


async def test_format_all_results_dynamic_truncation(monkeypatch):
    """Verify Stage 1, Stage 2, and Stage 3 truncation rules in _format_all_results."""
    from f1_bot.formatting.context import RenderContext
    from f1_bot.handlers.results import _format_all_results

    ctx = RenderContext()

    mock_results = {
        "fp1": "FP1: Max",
        "fp2": "FP2: Max",
        "fp3": "FP3: Max",
        "sprint_qualifying": "SQ: Max",
        "sprint": "Sprint: Max",
        "qualifying": "Q: Max",
        "race": "Race: Max",
    }

    async def mock_format_session(repo, season, rnd, race, key, drivers_map, ctx, top_n=None):
        val = mock_results.get(key)
        if val and top_n is not None:
            return val + f" (top {top_n})"
        return val

    monkeypatch.setattr("f1_bot.handlers.results._format_results_for_session", mock_format_session)

    repo = MagicMock()
    race = MagicMock()
    drivers_map = {}

    # Case 1: Short message (<= 4096)
    text = await _format_all_results(repo, 2026, 1, race, drivers_map, ctx)
    assert text is not None
    assert "FP1: Max" in text
    assert "Race: Max" in text
    assert "omitted" not in text

    # Case 2: Long message (> 4096) -> Drop practice
    mock_results["fp1"] = "A" * 4100
    text_long = await _format_all_results(repo, 2026, 1, race, drivers_map, ctx)
    assert text_long is not None
    assert "FP2: Max" not in text_long
    assert "FP1: Max" not in text_long
    assert "SQ: Max" in text_long
    assert "Race: Max" in text_long
    assert "omitted to fit Telegram character limits" in text_long
    assert "top 10" not in text_long

    # Case 3: Extremely long message even without practice -> Truncate to top 10
    mock_results["fp1"] = "A" * 4100
    mock_results["race"] = "B" * 4100
    text_extreme = await _format_all_results(repo, 2026, 1, race, drivers_map, ctx)
    assert text_extreme is not None
    assert "FP2: Max" not in text_extreme
    assert "SQ: Max (top 10)" in text_extreme
    assert "B" * 4100 + " (top 10)" in text_extreme
    assert "truncated to top 10" in text_extreme


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
    repo.get_result_sessions_by_round = AsyncMock(return_value={})

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
    repo.get_result_sessions_by_round = AsyncMock(return_value={7: {"sprint"}})

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
    repo.get_result_sessions_by_round = AsyncMock(return_value={})

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
    from f1_bot.formatting.context import RenderContext
    from f1_bot.handlers.results import _format_all_results

    repo = MagicMock()
    c = Circuit(circuit_id="test", name="Test", locality="Test", country="Test")
    race = Race(season=2026, round=5, name="Test GP", circuit=c, date=date(2026, 5, 1))

    call_count = 0

    async def mock_format(r, s, rnd, rc, key, dm, ctx, top_n=None):
        nonlocal call_count
        call_count += 1
        if key == "race":
            return "Race results text"
        if key == "qualifying":
            return "Qualifying results text"
        return None

    monkeypatch.setattr("f1_bot.handlers.results._format_results_for_session", mock_format)

    result = await _format_all_results(repo, 2026, 5, race, {}, RenderContext())
    assert result is not None
    assert "Race results text" in result
    assert "Qualifying results text" in result
    # With pre-fetch, only 7 calls (one per session key), not 7+4=11
    assert call_count == 7


async def test_next_callback_invalid_filter_value_error():
    import pytest

    from f1_bot.handlers.schedule import _next_callback

    update = MagicMock()
    update.callback_query.data = "next:filtered:invalid_filter:5"
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()

    r1 = _race()
    repo = MagicMock()
    repo.get_schedule = AsyncMock(return_value=[r1])
    repo.get_schedule_bounds = AsyncMock(return_value=_bounds([r1]))
    ctx = _context(repo=repo)

    with pytest.raises(ValueError, match="Unknown session group or key: invalid_filter"):
        await _next_callback(update, ctx)


# ---------------------------------------------------------------------------
# /results follows stored data, never the clock
#
# Incident 2026-10-03 (R16): FP1–FP3 results were synced, qualifying had
# started but Jolpica had not published it yet. /results opened on R15 (the
# clock said R16's race had not started), and paging to R16 picked qualifying
# (the clock said it had started) and showed "no data". Data arrives hours
# after the clock moves, so every /results decision must come from what is in
# the results table: `repo.get_result_sessions_by_round(season)`.
# ---------------------------------------------------------------------------

_VER_RACE_ROW = {
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

_LEC_QUALI_ROW = {
    "position": 1,
    "driver": {
        "driver_id": "leclerc",
        "given_name": "Charles",
        "family_name": "Leclerc",
        "code": "LEC",
    },
    "constructor": {"constructor_id": "ferrari", "name": "Ferrari"},
    "q3": "1:19.000",
}

# OpenF1 practice results stored for R16; the driver number identifies the session.
_R16_PRACTICE_TYPES = ["session:fp1:9001", "session:fp2:9002", "session:fp3:9003"]
_PRACTICE_DRIVER = {"session:fp1:9001": 1, "session:fp2:9002": 16, "session:fp3:9003": 81}


def _session_at(name: str, hours_from_now: float) -> RaceSession:
    """A session relative to the real clock, so "already started" is true at test time."""
    dt = datetime.now(UTC) + timedelta(hours=hours_from_now)
    return RaceSession(name=name, date=dt.date(), time=dt.time().replace(microsecond=0))


def _done_weekend(rnd: int, days_ago: int, name: str = "Dutch Grand Prix") -> Race:
    """A fully finished, conventional weekend."""
    return Race(
        season=date.today().year,
        round=rnd,
        name=name,
        circuit=_circuit(),
        date=_past_date(days_ago),
        time=time(13, 0),
        fp1=RaceSession(name="FP1", date=_past_date(days_ago + 2), time=time(11, 30)),
        fp2=RaceSession(name="FP2", date=_past_date(days_ago + 2), time=time(15, 0)),
        fp3=RaceSession(name="FP3", date=_past_date(days_ago + 1), time=time(10, 30)),
        qualifying=RaceSession(name="Qualifying", date=_past_date(days_ago + 1), time=time(14, 0)),
    )


def _r16_qualifying_saturday() -> Race:
    """R16 mid-weekend: FP1–FP3 over, qualifying started an hour ago, race in two days."""
    race_session = _session_at("Race", 48)
    return Race(
        season=date.today().year,
        round=16,
        name="Italian Grand Prix",
        circuit=_circuit(),
        date=race_session.date,
        time=race_session.time,
        fp1=_session_at("FP1", -27),
        fp2=_session_at("FP2", -23),
        fp3=_session_at("FP3", -4),
        qualifying=_session_at("Qualifying", -1),
    )


def _results_repo(races: list, sessions_by_round: dict[int, set[str]]) -> MagicMock:
    """Repo whose result reads agree with ``sessions_by_round``.

    Race/qualifying rows exist exactly for the rounds listed with those keys;
    R16's practice sessions are served through the OpenF1 ``session:`` types.
    """
    repo = MagicMock()
    repo.get_schedule = AsyncMock(return_value=races)
    repo.get_schedule_bounds = AsyncMock(return_value=_bounds(races))
    repo.get_drivers_by_id_map = AsyncMock(return_value={})
    repo.get_result_sessions_by_round = AsyncMock(return_value=sessions_by_round)

    def _has(rnd: int, key: str) -> bool:
        return key in sessions_by_round.get(rnd, set())

    repo.get_race_results = AsyncMock(
        side_effect=lambda season, rnd: [_VER_RACE_ROW] if _has(rnd, "race") else None
    )
    repo.get_qualifying_results = AsyncMock(
        side_effect=lambda season, rnd: [_LEC_QUALI_ROW] if _has(rnd, "qualifying") else None
    )
    repo.get_sprint_results = AsyncMock(return_value=None)
    repo.get_all_result_types = AsyncMock(
        side_effect=lambda season, rnd: [
            t for t in _R16_PRACTICE_TYPES if _has(rnd, t.split(":")[1])
        ]
    )
    repo.get_results_by_type = AsyncMock(
        side_effect=lambda season, rnd, rtype: [
            {"position": 1, "driver_number": _PRACTICE_DRIVER[rtype], "duration": 80.123}
        ]
    )
    return repo


def _callback_update(data: str) -> MagicMock:
    update = MagicMock()
    update.callback_query.data = data
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    return update


def _buttons(markup: InlineKeyboardMarkup) -> list:
    return [btn for row in markup.inline_keyboard for btn in row]


async def test_results_handler_opens_latest_round_with_data():
    """/results opens the newest round that HAS results, not the last race the clock finished.

    The 2026-10-03 R16 state: bounds say R15 is the last completed round (R16's
    race is in the future), and R16's qualifying has started but has no results.
    The user must land on R16 FP3 — the latest session actually stored.
    """
    races = [_done_weekend(15, 8), _r16_qualifying_saturday()]
    repo = _results_repo(races, {15: {"race"}, 16: {"fp1", "fp2", "fp3"}})
    update = _update()

    await results_handler(update, _context(repo=repo))

    text = update.effective_message.reply_text.await_args.args[0]
    assert "#81" in text, f"expected R16 FP3 results, got: {text!r}"
    markup = update.effective_message.reply_text.await_args.kwargs["reply_markup"]
    labels = [btn.text for btn in _buttons(markup)]
    assert "·FP3·" in labels
    pager = markup.inline_keyboard[0]
    assert pager[0].callback_data == "res:back:_:15"
    assert pager[1].callback_data == "rpk:rb:16"


async def test_results_back_skips_session_without_data():
    """Returning to R16's overview picks FP3 (has data), not qualifying (started, no data yet).

    The clock-based default picked qualifying because it had started, which
    rendered "no data" even though three practice sessions were stored.
    """
    from f1_bot.handlers.results import _results_callback

    races = [_done_weekend(15, 8), _r16_qualifying_saturday()]
    repo = _results_repo(races, {15: {"race"}, 16: {"fp1", "fp2", "fp3"}})
    update = _callback_update("res:back:_:16")

    await _results_callback(update, _context(repo=repo))

    args, kwargs = update.callback_query.edit_message_text.await_args
    assert "#81" in args[0], f"expected R16 FP3 results, got: {args[0]!r}"
    labels = [btn.text for btn in _buttons(kwargs["reply_markup"])]
    assert "·FP3·" in labels
    assert "·Q·" not in labels


async def test_results_default_prefers_race_when_present():
    """Once the race result is stored it stays the default — it is the weekend's last session."""
    races = [_done_weekend(15, 8), _race()]  # R16 entirely in the future
    repo = _results_repo(races, {15: {"fp1", "qualifying", "race"}})
    update = _update()

    await results_handler(update, _context(repo=repo))

    text = update.effective_message.reply_text.await_args.args[0]
    assert "Verstappen" in text
    markup = update.effective_message.reply_text.await_args.kwargs["reply_markup"]
    assert "·Race·" in [btn.text for btn in _buttons(markup)]


async def test_results_without_any_data_shows_no_data_without_keyboard():
    """No stored results this season → plain "no data", no buttons.

    Every button would lead to another empty page: the clock says R15 is done,
    but nothing has been synced, so there is nothing to navigate to.
    """
    races = [_done_weekend(15, 8)]
    repo = _results_repo(races, {})
    update = _update()

    await results_handler(update, _context(repo=repo))

    args, kwargs = update.effective_message.reply_text.await_args
    assert "⚠️" in args[0]
    assert kwargs.get("reply_markup") is None


async def test_results_pager_lists_only_rounds_with_data():
    """R17's FP1 has started but nothing is stored yet → the pager must not offer ▶ R17.

    The clock-based list included R17 as soon as FP1 began; tapping it showed
    an empty page for the 3.5–4.5h before the first OpenF1 sync.
    """
    r17 = _r16_qualifying_saturday()
    r17.round = 17
    r17.fp2 = r17.fp3 = r17.qualifying = None
    r17.fp1 = _session_at("FP1", -1)
    races = [_done_weekend(15, 15), _done_weekend(16, 6, "Italian Grand Prix"), r17]
    repo = _results_repo(races, {15: {"race"}, 16: {"race"}})
    update = _update()

    await results_handler(update, _context(repo=repo))

    markup = update.effective_message.reply_text.await_args.kwargs["reply_markup"]
    pager = markup.inline_keyboard[0]
    assert [btn.text for btn in pager] == ["◀", "R16/16"]
    assert "res:back:_:17" not in [btn.callback_data for btn in _buttons(markup)]


async def test_results_filtered_rounds_follow_session_data():
    """Filtered Q view navigates only rounds with stored Q results.

    R16's qualifying has started but Jolpica has not published it, so R16 must
    not be reachable from the Q view (it would render "no data").
    """
    from f1_bot.handlers.results import _results_callback

    races = [_done_weekend(14, 15), _done_weekend(15, 8), _r16_qualifying_saturday()]
    repo = _results_repo(
        races,
        {
            14: {"qualifying", "race"},
            15: {"qualifying", "race"},
            16: {"fp1", "fp2", "fp3"},
        },
    )
    update = _callback_update("res:filtered:qualifying:15")

    await _results_callback(update, _context(repo=repo))

    args, kwargs = update.callback_query.edit_message_text.await_args
    assert "Leclerc" in args[0]
    nav_row = kwargs["reply_markup"].inline_keyboard[0]
    assert [btn.callback_data for btn in nav_row] == [
        "res:filtered:qualifying:14",
        "rpk:rf:qualifying:15",
    ]


def _fixed_weekend(rnd: int, **sessions: RaceSession) -> Race:
    return Race(
        season=2026,
        round=rnd,
        name=f"GP {rnd}",
        circuit=_circuit(),
        date=date(2026, 3, rnd + 2),
        time=time(13, 0),
        **sessions,
    )


def _conventional(rnd: int) -> Race:
    d = date(2026, 3, rnd)
    return _fixed_weekend(
        rnd,
        fp1=RaceSession(name="FP1", date=d, time=time(11, 30)),
        fp2=RaceSession(name="FP2", date=d, time=time(15, 0)),
        fp3=RaceSession(name="FP3", date=d + timedelta(days=1), time=time(10, 30)),
        qualifying=RaceSession(name="Q", date=d + timedelta(days=1), time=time(14, 0)),
    )


def test_displayable_sessions_is_stored_and_scheduled_in_schedule_order():
    """Only sessions that have results AND exist in the schedule can render a page.

    The last element is the /results default, so the order must be the
    weekend's chronological order.
    """
    from f1_bot.handlers.pagination import displayable_sessions

    race = _conventional(1)

    assert displayable_sessions(race, {"fp3", "fp1", "fp2"}) == ["fp1", "fp2", "fp3"]
    assert displayable_sessions(race, {"race", "qualifying", "fp1"}) == [
        "fp1",
        "qualifying",
        "race",
    ]
    # "sprint" has results but this weekend has no sprint → nothing to render it with
    assert displayable_sessions(race, {"fp1", "sprint"}) == ["fp1"]
    assert displayable_sessions(race, set()) == []


def test_displayable_sessions_follows_schedule_time_not_a_fixed_key_order():
    """2023-format sprint weekend: qualifying (Fri) precedes the sprint (Sat).

    The default must be the sprint — the latest session that happened — so the
    order comes from the schedule's start times, not a hard-coded key list.
    """
    from f1_bot.handlers.pagination import displayable_sessions

    fri, sat = date(2023, 4, 28), date(2023, 4, 29)
    race = _fixed_weekend(
        4,
        fp1=RaceSession(name="FP1", date=fri, time=time(9, 30)),
        qualifying=RaceSession(name="Q", date=fri, time=time(13, 0)),
        sprint_qualifying=RaceSession(name="SQ", date=sat, time=time(8, 30)),
        sprint=RaceSession(name="Sprint", date=sat, time=time(13, 30)),
    )

    assert displayable_sessions(race, {"sprint", "qualifying"}) == ["qualifying", "sprint"]


def test_displayable_sessions_ignores_the_clock():
    """A stored result is shown even if the schedule says the session is in the future.

    Data is the authority: a rescheduled session whose results exist must not
    be hidden by its (stale) start time.
    """
    from f1_bot.handlers.pagination import displayable_sessions

    race = _race()  # every session in the future

    assert displayable_sessions(race, {"fp1"}) == ["fp1"]


def test_rounds_with_results_all_and_single_key():
    """The round list is exactly the rounds with something displayable, sorted."""
    from f1_bot.handlers.pagination import rounds_with_results

    races = [_conventional(1), _conventional(2), _conventional(3)]
    sessions_by_round = {3: {"fp1"}, 1: {"qualifying", "race"}}

    assert rounds_with_results(sessions_by_round, races, "all") == [1, 3]
    assert rounds_with_results(sessions_by_round, races, "qualifying") == [1]
    assert rounds_with_results(sessions_by_round, races, "fp1") == [3]


def test_rounds_with_results_excludes_rounds_missing_from_schedule():
    """Leftover rows for a round no longer in the schedule (upsert never deletes) are ignored."""
    from f1_bot.handlers.pagination import rounds_with_results

    races = [_conventional(1)]

    assert rounds_with_results({1: {"race"}, 99: {"race"}}, races, "all") == [1]
    assert rounds_with_results({99: {"race"}}, races, "race") == []


def test_rounds_with_results_excludes_sessions_missing_from_schedule():
    """A round whose only results are for a session not in its schedule is not listed.

    Otherwise the "all" list would contain a round whose default session cannot
    be rendered — the list and the default share one rule.
    """
    from f1_bot.handlers.pagination import rounds_with_results

    races = [_conventional(1), _conventional(2)]  # no sprint in either
    sessions_by_round = {1: {"race"}, 2: {"sprint"}}

    assert rounds_with_results(sessions_by_round, races, "all") == [1]
    assert rounds_with_results(sessions_by_round, races, "sprint") == []


def test_rounds_with_results_empty():
    from f1_bot.handlers.pagination import rounds_with_results

    assert rounds_with_results({}, [_conventional(1)], "all") == []


def test_results_overview_keyboard_current_round_not_in_list_pages_by_value():
    """Current R16 has no data yet (list [14, 15]) → ◀ goes to R15, the nearest earlier round.

    Index-based fallback treated R16 as list[-1] and sent ◀ to R14, skipping R15.
    This is the normal Saturday path once lists follow data (R16 has FP, not Q).
    """
    from f1_bot.handlers.pagination import results_overview_keyboard

    markup = results_overview_keyboard(16, completed_rounds=[14, 15])

    pager = markup.inline_keyboard[0]
    assert pager[0].text == "◀"
    assert pager[0].callback_data == "res:back:_:15"
    assert "▶" not in [btn.text for btn in pager]


def test_results_filtered_keyboard_current_round_not_in_list_pages_by_value():
    """Same value-based paging for the filtered view: R16 Q not stored, list [14, 15] → ◀ R15."""
    from f1_bot.handlers.pagination import results_filtered_keyboard

    markup = results_filtered_keyboard(16, [14, 15], "qualifying")

    nav_row = markup.inline_keyboard[0]
    assert nav_row[0].text == "◀"
    assert nav_row[0].callback_data == "res:filtered:qualifying:15"
    assert "▶" not in [btn.text for btn in nav_row]
