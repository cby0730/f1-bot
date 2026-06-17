from datetime import date, time, timedelta
from unittest.mock import AsyncMock, MagicMock

from f1_bot.handlers.results import (
    results_handler,
    session_result_handler,
    sprint_handler,
)
from f1_bot.handlers.schedule import (
    next_handler,
    next_practice_handler,
    next_session_handler,
)
from f1_bot.models.race import Circuit, Race, RaceSession
from f1_bot.models.results import SessionResult


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
    """Race whose sessions are in the past — for find_recent_completed_session tests."""
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


async def test_next_session_handler_shows_upcoming_session():
    repo = MagicMock()
    repo.get_schedule = AsyncMock(return_value=[_race()])
    repo.get_user_timezone = AsyncMock(return_value="UTC")
    update = _update()

    await next_session_handler(update, _context(repo=repo))

    assert update.effective_message.reply_text.await_count == 1
    assert "Next FP1" in update.effective_message.reply_text.await_args.args[0]
    assert "Italian Grand Prix" in update.effective_message.reply_text.await_args.args[0]


async def test_next_practice_handler_targets_practice_sessions():
    repo = MagicMock()
    repo.get_schedule = AsyncMock(return_value=[_race()])
    repo.get_user_timezone = AsyncMock(return_value="UTC")
    update = _update()

    await next_practice_handler(update, _context(repo=repo))

    assert update.effective_message.reply_text.await_count == 1
    assert "FP1" in update.effective_message.reply_text.await_args.args[0]


async def test_session_result_handler_fetches_openf1_result():
    past_race = _past_race()
    fp1_date = past_race.fp1.date  # e.g. today - 3 days
    openf1_date_start = f"{fp1_date.isoformat()}T11:30:00+00:00"

    repo = MagicMock()
    repo.get_schedule = AsyncMock(return_value=[past_race])
    repo.get_session_results = AsyncMock(return_value=None)
    repo.save_session_results = AsyncMock()
    openf1 = MagicMock()
    openf1.get_sessions = AsyncMock(
        return_value=[
            MagicMock(
                session_key=777,
                session_name="Practice 1",
                session_type="Practice",
                meeting_key=99,
                date_start=openf1_date_start,
                date_end=None,
                year=date.today().year,
            )
        ]
    )
    openf1.get_session_results = AsyncMock(
        return_value=[
            SessionResult(
                position=1,
                driver_number=4,
                duration="1:12.345",
            )
        ]
    )
    update = _update()
    ctx = _context(repo=repo, openf1=openf1)
    ctx.args = ["fp1"]

    await session_result_handler(update, ctx)

    assert openf1.get_sessions.await_count == 1
    assert openf1.get_session_results.await_count == 1
    assert repo.save_session_results.await_count == 1
    assert "FP1 Result" in update.effective_message.reply_text.await_args.args[0]
    assert "#4" in update.effective_message.reply_text.await_args.args[0]


async def test_results_handler_with_limit():
    repo = MagicMock()
    r1 = _past_race()
    r1.round = 15
    r2 = _past_race()
    r2.round = 16
    repo.get_schedule = AsyncMock(return_value=[r1, r2])
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

    jolpica = MagicMock()
    ctx = _context(repo=repo, jolpica=jolpica)
    ctx.args = ["2"]
    update = _update()

    await results_handler(update, ctx)

    assert update.effective_message.reply_text.await_count == 1
    reply_text = update.effective_message.reply_text.await_args.args[0]
    assert "---" in reply_text
    assert reply_text.count("Verstappen") == 2


async def test_sprint_handler_rejects_non_sprint_weekend():
    repo = MagicMock()
    r = _past_race()
    r.round = 5
    repo.get_schedule = AsyncMock(return_value=[r])
    jolpica = MagicMock()
    ctx = _context(repo=repo, jolpica=jolpica)
    ctx.args = ["r5"]
    update = _update()

    await sprint_handler(update, ctx)

    assert update.effective_message.reply_text.await_count == 1
    reply_text = update.effective_message.reply_text.await_args.args[0]
    assert "not a sprint weekend" in reply_text


async def test_sprint_handler_rejects_invalid_round():
    repo = MagicMock()
    r = _past_race()
    r.round = 5
    repo.get_schedule = AsyncMock(return_value=[r])
    jolpica = MagicMock()
    ctx = _context(repo=repo, jolpica=jolpica)
    ctx.args = ["r99"]
    update = _update()

    await sprint_handler(update, ctx)

    assert update.effective_message.reply_text.await_count == 1
    reply_text = update.effective_message.reply_text.await_args.args[0]
    assert "Invalid round number" in reply_text


async def test_next_handler_with_limit():
    repo = MagicMock()
    r1 = _race()
    r1.round = 17
    r2 = _race()
    r2.round = 18
    repo.get_schedule = AsyncMock(return_value=[r1, r2])
    repo.get_user_timezone = AsyncMock(return_value="UTC")
    jolpica = MagicMock()
    ctx = _context(repo=repo, jolpica=jolpica)
    ctx.args = ["2"]
    update = _update()

    await next_handler(update, ctx)

    assert update.effective_message.reply_text.await_count == 1
    reply_text = update.effective_message.reply_text.await_args.args[0]
    assert "---" in reply_text
    assert reply_text.count("Next Race") == 2
