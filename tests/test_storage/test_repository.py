"""Tests for Repository — verifies Redis-first / SQLite-fallback two-layer caching.

All tests use real fakeredis + in-memory SQLite (no mocks for storage layer).
This exercises the actual caching logic, not just the interface.
"""

from datetime import date, time

from f1_bot.models.constructor import Constructor, ConstructorStanding
from f1_bot.models.driver import Driver, DriverStanding
from f1_bot.models.race import Circuit, Race, RaceSession
from f1_bot.models.results import QualifyingResult, RaceResult, SessionResult, SprintResult
from f1_bot.models.user import UserPreference


def _driver(driver_id: str = "hamilton") -> Driver:
    return Driver(
        driver_id=driver_id,
        given_name="Lewis",
        family_name="Hamilton",
        nationality="British",
    )


def _constructor(constructor_id: str = "mercedes") -> Constructor:
    return Constructor(constructor_id=constructor_id, name="Mercedes")


def _circuit() -> Circuit:
    return Circuit(
        circuit_id="monaco", name="Circuit de Monaco", locality="Monte-Carlo", country="Monaco"
    )


def _race(round_num: int = 5, days_ahead: int = 10) -> Race:
    from datetime import timedelta

    future = date.today() + timedelta(days=days_ahead)
    return Race(
        season=2024,
        round=round_num,
        name="Monaco Grand Prix",
        circuit=_circuit(),
        date=future,
        time=time(13, 0),
        fp1=RaceSession(name="FP1", date=future - timedelta(days=2), time=time(11, 30)),
    )


def _driver_standing(position: int = 1) -> DriverStanding:
    return DriverStanding(
        position=position,
        points=100.0,
        wins=3,
        driver=_driver(),
        constructor_name="Mercedes",
    )


def _constructor_standing(position: int = 1) -> ConstructorStanding:
    return ConstructorStanding(
        position=position,
        points=200.0,
        wins=5,
        constructor=_constructor(),
    )


# --- Schedule tests ---


async def test_save_and_get_schedule_redis_hit(repo):
    """save_schedule writes to Redis; subsequent get_schedule reads from Redis (hot path)."""
    races = [_race(round_num=5)]
    await repo.save_schedule(2024, races)
    result = await repo.get_schedule(2024)
    assert len(result) == 1
    assert result[0].round == 5
    assert result[0].name == "Monaco Grand Prix"


async def test_get_schedule_sqlite_fallback(repo, sqlite_store):
    """When Redis is empty, get_schedule falls back to SQLite."""
    races = [_race(round_num=7)]
    races_json = [r.model_dump(mode="json") for r in races]
    await sqlite_store.save_races(2024, races_json)

    result = await repo.get_schedule(2024)
    assert len(result) == 1
    assert result[0].round == 7


async def test_get_schedule_empty_returns_empty_list(repo):
    """Both storages empty → get_schedule returns []."""
    result = await repo.get_schedule(2099)
    assert result == []


async def test_get_next_race_returns_upcoming(repo):
    """get_next_race returns the first race that hasn't happened yet."""
    past_race = _race(round_num=1, days_ahead=-5)  # already past
    future_race = _race(round_num=2, days_ahead=10)  # upcoming
    await repo.save_schedule(2024, [past_race, future_race])
    result = await repo.get_next_race(2024)
    assert result is not None
    assert result.round == 2


async def test_get_next_race_all_past_returns_none(repo):
    """If all races are in the past, get_next_race returns None."""
    past_race = _race(round_num=1, days_ahead=-5)
    await repo.save_schedule(2024, [past_race])
    result = await repo.get_next_race(2024)
    assert result is None


# --- Driver standings tests ---


async def test_save_and_get_driver_standings(repo):
    """save/get driver standings via Redis-first path."""
    standings = [_driver_standing(1), _driver_standing(2)]
    await repo.save_driver_standings(2024, standings)
    result = await repo.get_driver_standings(2024)
    assert len(result) == 2
    assert result[0].position == 1
    assert result[0].driver.driver_id == "hamilton"


async def test_get_driver_standings_sqlite_fallback(repo, sqlite_store):
    """When Redis is empty, falls back to SQLite for driver standings."""
    standings = [_driver_standing(1)]
    data = [s.model_dump(mode="json") for s in standings]
    await sqlite_store.save_driver_standings(2024, 0, data)

    result = await repo.get_driver_standings(2024)
    assert len(result) == 1
    assert result[0].points == 100.0


async def test_get_driver_standings_empty(repo):
    result = await repo.get_driver_standings(2099)
    assert result == []


# --- Constructor standings tests ---


async def test_save_and_get_constructor_standings(repo):
    standings = [_constructor_standing(1)]
    await repo.save_constructor_standings(2024, standings)
    result = await repo.get_constructor_standings(2024)
    assert len(result) == 1
    assert result[0].constructor.name == "Mercedes"
    assert result[0].wins == 5


async def test_get_constructor_standings_empty(repo):
    result = await repo.get_constructor_standings(2099)
    assert result == []


# --- Race results tests ---


async def test_save_and_get_race_results(repo):
    """Race results: save → Redis hit on re-read."""
    results = [
        RaceResult(
            position=1,
            grid=1,
            laps=78,
            status="Finished",
            points=25.0,
            driver=_driver(),
            constructor=_constructor(),
            time="1:30:00",
        )
    ]
    await repo.save_race_results(2024, 5, results)
    cached = await repo.get_race_results(2024, 5)
    assert cached is not None
    assert len(cached) == 1
    assert cached[0]["position"] == 1


async def test_get_race_results_miss_returns_none(repo):
    """Cache miss on race results returns None (handler must fetch from API)."""
    result = await repo.get_race_results(2024, 99)
    assert result is None


# --- Qualifying results tests ---


async def test_save_and_get_qualifying_results(repo):
    results = [
        QualifyingResult(
            position=1,
            driver=_driver(),
            constructor=_constructor(),
            q1="1:12.000",
            q2="1:11.500",
            q3="1:10.900",
        )
    ]
    await repo.save_qualifying_results(2024, 5, results)
    cached = await repo.get_qualifying_results(2024, 5)
    assert cached is not None
    assert cached[0]["q3"] == "1:10.900"


# --- Sprint results tests ---


async def test_save_and_get_sprint_results(repo):
    results = [
        SprintResult(
            position=1,
            grid=2,
            laps=24,
            status="Finished",
            points=8.0,
            driver=_driver(),
            constructor=_constructor(),
            time="30:00.000",
        )
    ]
    await repo.save_sprint_results(2024, 5, results)
    cached = await repo.get_sprint_results(2024, 5)
    assert cached is not None
    assert cached[0]["position"] == 1


# --- Session results tests ---


async def test_save_and_get_session_results(repo):
    results = [SessionResult(position=1, driver_number=44, duration="1:20.123")]
    await repo.save_session_results(2024, 5, session_key=9001, results=results)
    cached = await repo.get_session_results(2024, 5, session_key=9001)
    assert cached is not None
    assert cached[0]["driver_number"] == 44


async def test_get_session_results_miss_returns_none(repo):
    result = await repo.get_session_results(2024, 5, session_key=9999)
    assert result is None


# --- User preference / timezone tests ---


async def test_get_user_timezone_default(repo):
    """Unknown user → default timezone is 'UTC'."""
    tz = await repo.get_user_timezone(telegram_id=99999)
    assert tz == "UTC"


async def test_upsert_and_get_user_timezone(repo):
    pref = UserPreference(telegram_id=12345, timezone="Asia/Taipei")
    await repo.upsert_user_preference(pref)
    tz = await repo.get_user_timezone(telegram_id=12345)
    assert tz == "Asia/Taipei"


async def test_upsert_user_timezone_overwrite(repo):
    """Upserting with a different timezone overwrites the previous value."""
    await repo.upsert_user_preference(UserPreference(telegram_id=100, timezone="UTC"))
    await repo.upsert_user_preference(UserPreference(telegram_id=100, timezone="Europe/London"))
    tz = await repo.get_user_timezone(telegram_id=100)
    assert tz == "Europe/London"
