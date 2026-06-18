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
        date=_past_date(1),
        time=time(13, 0),
        fp1=RaceSession(name="FP1", date=_past_date(3), time=time(11, 30)),
        fp2=RaceSession(name="FP2", date=_past_date(3), time=time(15, 0)),
        fp3=RaceSession(name="FP3", date=_past_date(2), time=time(10, 30)),
        qualifying=RaceSession(name="Qualifying", date=_past_date(2), time=time(14, 0)),
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
    # State A keyboard has 2 rows (practice + competitive)
    assert len(markup.inline_keyboard) == 2
    # First row: FP1, FP2, FP3, Q
    labels = [btn.text for btn in markup.inline_keyboard[0]]
    assert labels == ["FP1", "FP2", "FP3", "Q"]
    # Second row: SQ, SPR, Race, All
    labels = [btn.text for btn in markup.inline_keyboard[1]]
    assert labels == ["SQ", "SPR", "Race", "All"]


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
    # All button callback_data
    all_btn = markup.inline_keyboard[1][3]
    assert all_btn.callback_data == "next:filtered:all:10"


# ---------------------------------------------------------------------------
# /results — State A (overview)
# ---------------------------------------------------------------------------


async def test_results_handler_shows_last_completed_round():
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
                "constructor": {"constructor_id": "red_bull", "name": "Red Bull"},
            }
        ]
    )
    repo.get_last_result_round = AsyncMock(return_value=15)
    repo.get_drivers_map = AsyncMock(return_value={})
    ctx = _context(repo=repo)
    update = _update()

    await results_handler(update, ctx)

    assert update.effective_message.reply_text.await_count == 1
    reply_text = update.effective_message.reply_text.await_args.args[0]
    assert "Verstappen" in reply_text
    # Should have two-state keyboard with session filter buttons
    markup = update.effective_message.reply_text.await_args.kwargs.get("reply_markup")
    assert isinstance(markup, InlineKeyboardMarkup)
    # Overview keyboard has 2 rows
    assert len(markup.inline_keyboard) == 2


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
    repo.get_race_results = AsyncMock(return_value=[{"position": 1, "grid": 1, "laps": 50,
        "status": "Finished", "points": 25,
        "driver": {"driver_id": "ver", "given_name": "Max", "family_name": "Verstappen", "code": "VER"},
        "constructor": {"constructor_id": "rb", "name": "Red Bull"}}])
    repo.get_last_result_round = AsyncMock(return_value=15)
    repo.get_drivers_map = AsyncMock(return_value={})

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
