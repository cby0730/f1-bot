"""Tests for Repository — verifies PostgreSQL data storage operations.

All tests use real Postgres (no mocks for storage layer).
"""

from datetime import date, time

from f1_bot.models.constructor import Constructor, ConstructorStanding
from f1_bot.models.driver import Driver, DriverStanding
from f1_bot.models.race import Circuit, Race, RaceSession
from f1_bot.models.results import QualifyingResult, RaceResult, SessionResult, SprintResult


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


async def test_save_and_get_schedule(repo):
    """save_schedule writes to DB; subsequent get_schedule reads from DB."""
    races = [_race(round_num=5)]
    await repo.save_schedule(2024, races)
    result = await repo.get_schedule(2024)
    assert len(result) == 1
    assert result[0].round == 5
    assert result[0].name == "Monaco Grand Prix"


async def test_get_schedule_from_store(repo, pg_store):
    """get_schedule falls back to reading store directly."""
    races = [_race(round_num=7)]
    races_json = [r.model_dump(mode="json") for r in races]
    await pg_store.save_races(2024, races_json)

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
    """save/get driver standings via Repository."""
    standings = [_driver_standing(1), _driver_standing(2)]
    await repo.save_driver_standings(2024, standings)
    result = await repo.get_driver_standings(2024)
    assert len(result) == 2
    assert result[0].position == 1
    assert result[0].driver.driver_id == "hamilton"


async def test_get_driver_standings_from_store(repo, pg_store):
    """falls back to reading driver standings from store directly."""
    standings = [_driver_standing(1)]
    data = [s.model_dump(mode="json") for s in standings]
    await pg_store.save_driver_standings(2024, 0, data)

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
    """Race results: save and re-read from DB."""
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
    results = [
        SessionResult(
            position=1, driver_number=44, driver_id="openf1_44_hamilton", duration="1:20.123"
        )
    ]
    await repo.save_session_results(2024, 5, session_key=9001, results=results)
    cached = await repo.get_session_results(2024, 5, session_key=9001)
    assert cached is not None
    assert cached[0]["driver_number"] == 44
    assert cached[0]["driver_id"] == "openf1_44_hamilton"


async def test_get_session_results_miss_returns_none(repo):
    result = await repo.get_session_results(2024, 5, session_key=9999)
    assert result is None


async def test_save_and_get_drivers_by_id_map(repo):
    from f1_bot.models.driver import Driver

    driver = Driver(
        driver_id="hamilton",
        permanent_number="44",
        given_name="Lewis",
        family_name="Hamilton",
        nationality="British",
    )
    await repo.save_drivers(2024, [driver])

    drivers_map = await repo.get_drivers_by_id_map(2024)
    assert "hamilton" in drivers_map
    assert drivers_map["hamilton"].family_name == "Hamilton"
    assert drivers_map["hamilton"].permanent_number == "44"
    assert "44" in drivers_map
    assert 44 in drivers_map
    assert drivers_map["44"] == drivers_map["hamilton"]
    assert drivers_map[44] == drivers_map["hamilton"]


async def test_driver_maps_merge_openf1_and_jolpica(repo):
    """Test get_drivers_by_id_map and get_drivers_map properly merge OpenF1 and Jolpica profiles."""
    from f1_bot.models.driver import Driver

    # 1. Save a Jolpica driver (with nationality)
    jolpica_driver = Driver(
        driver_id="russell",
        permanent_number="63",
        given_name="George",
        family_name="Russell",
        nationality="British",
    )

    # 2. Save an OpenF1 driver sharing the same permanent number (without nationality)
    openf1_driver = Driver(
        driver_id="openf1_63_russell",
        permanent_number="63",
        given_name="George",
        family_name="Russell",
        nationality="",
    )

    # 3. Save a junior OpenF1 driver with no matching Jolpica driver
    junior_driver = Driver(
        driver_id="openf1_97_aron",
        permanent_number="97",
        given_name="Paul",
        family_name="Aron",
        nationality="",
    )

    await repo.save_drivers(2026, [jolpica_driver, openf1_driver, junior_driver])

    # Verify get_drivers_by_id_map
    by_id_map = await repo.get_drivers_by_id_map(2026)

    # OpenF1 Russell key maps to Jolpica profile
    assert "openf1_63_russell" in by_id_map
    assert by_id_map["openf1_63_russell"].driver_id == "russell"
    assert by_id_map["openf1_63_russell"].nationality == "British"

    # Jolpica Russell key maps to Jolpica profile
    assert "russell" in by_id_map
    assert by_id_map["russell"].nationality == "British"

    # Junior driver falls back to OpenF1 profile
    assert "openf1_97_aron" in by_id_map
    assert by_id_map["openf1_97_aron"].driver_id == "openf1_97_aron"
    assert by_id_map["openf1_97_aron"].nationality == ""

    # Verify get_drivers_map
    by_number_map = await repo.get_drivers_map(2026)

    # Key 63 points to Jolpica profile
    assert 63 in by_number_map
    assert by_number_map[63].nationality == "British"

    # Key 97 points to OpenF1 profile
    assert 97 in by_number_map
    assert by_number_map[97].nationality == ""


# --- User preference / timezone tests ---


async def test_get_user_timezone_default(repo):
    """Unknown user → default timezone is 'UTC'."""
    tz = await repo.get_user_timezone(telegram_id=99999)
    assert tz == "UTC"


async def test_set_and_get_user_timezone(repo):
    """set_user_timezone writes the timezone; get_user_timezone reads it back.

    Replaces the removed whole-object repo.upsert_user_preference (spec 005).
    """
    await repo.set_user_timezone(12345, "Asia/Taipei")
    tz = await repo.get_user_timezone(telegram_id=12345)
    assert tz == "Asia/Taipei"


async def test_set_user_timezone_overwrite(repo):
    """Setting a different timezone overwrites the previous value."""
    await repo.set_user_timezone(100, "UTC")
    await repo.set_user_timezone(100, "Europe/London")
    tz = await repo.get_user_timezone(telegram_id=100)
    assert tz == "Europe/London"


async def test_get_user_language_stored_and_default(repo):
    """get_user_language returns the stored language, or 'en' when no row exists.

    This is the language-only lookup the notification sender uses on a background
    job (no Update to resolve a full RenderContext from), so its default must match
    the platform default.
    """
    # No row yet → default
    assert await repo.get_user_language(telegram_id=77777) == "en"

    # After setting a language → stored value
    await repo.set_user_language(77777, "zh-Hant")
    assert await repo.get_user_language(telegram_id=77777) == "zh-Hant"


# --- get_schedule_bounds edge cases ---


async def test_schedule_bounds_empty_schedule(repo):
    """Empty schedule returns zeroes and Nones."""
    bounds = await repo.get_schedule_bounds(2099)
    assert bounds["total_rounds"] == 0
    assert bounds["completed_rounds"] == 0
    assert bounds["upcoming_rounds"] == 0
    assert bounds["last_completed_round"] is None
    assert bounds["next_upcoming_round"] is None
    assert bounds["sprint_rounds"] == []
    assert bounds["completed_sprint_rounds"] == []


async def test_schedule_bounds_all_completed(repo, pg_store):
    """When all races are in the past, next_upcoming_round is None."""
    from datetime import date, time

    from f1_bot.models.race import Circuit, Race

    circuit = Circuit(circuit_id="test", name="Test", locality="Test", country="Test")
    races = [
        Race(
            season=2024,
            round=1,
            name="R1",
            circuit=circuit,
            date=date(2024, 1, 15),
            time=time(13, 0),
        ),
        Race(
            season=2024,
            round=2,
            name="R2",
            circuit=circuit,
            date=date(2024, 2, 15),
            time=time(13, 0),
        ),
    ]
    await repo.save_schedule(2024, races)

    # Reference time well after both races
    from datetime import UTC, datetime

    ref = datetime(2024, 12, 31, 23, 59, tzinfo=UTC)
    bounds = await repo.get_schedule_bounds(2024, reference_dt=ref)

    assert bounds["completed_rounds"] == 2
    assert bounds["upcoming_rounds"] == 0
    assert bounds["last_completed_round"] == 2
    assert bounds["next_upcoming_round"] is None


async def test_schedule_bounds_all_upcoming(repo, pg_store):
    """When all races are in the future, last_completed_round is None."""
    from datetime import UTC, date, datetime, time

    from f1_bot.models.race import Circuit, Race

    circuit = Circuit(circuit_id="test", name="Test", locality="Test", country="Test")
    races = [
        Race(
            season=2099,
            round=1,
            name="R1",
            circuit=circuit,
            date=date(2099, 6, 15),
            time=time(13, 0),
        ),
        Race(
            season=2099,
            round=2,
            name="R2",
            circuit=circuit,
            date=date(2099, 7, 15),
            time=time(13, 0),
        ),
    ]
    await repo.save_schedule(2099, races)

    ref = datetime(2099, 1, 1, 0, 0, tzinfo=UTC)
    bounds = await repo.get_schedule_bounds(2099, reference_dt=ref)

    assert bounds["completed_rounds"] == 0
    assert bounds["upcoming_rounds"] == 2
    assert bounds["last_completed_round"] is None
    assert bounds["next_upcoming_round"] == 1


async def test_schedule_bounds_sprint_classification(repo, pg_store):
    """Sprint weekends are tracked in sprint_rounds and completed_sprint_rounds."""
    from datetime import UTC, date, datetime, time

    from f1_bot.models.race import Circuit, Race, RaceSession

    circuit = Circuit(circuit_id="test", name="Test", locality="Test", country="Test")
    sprint_race = Race(
        season=2024,
        round=4,
        name="Sprint GP",
        circuit=circuit,
        date=date(2024, 4, 20),
        time=time(13, 0),
        sprint=RaceSession(name="Sprint", date=date(2024, 4, 19), time=time(10, 0)),
    )
    normal_race = Race(
        season=2024,
        round=5,
        name="Normal GP",
        circuit=circuit,
        date=date(2024, 5, 10),
        time=time(13, 0),
    )
    await repo.save_schedule(2024, [sprint_race, normal_race])

    ref = datetime(2024, 12, 31, 23, 59, tzinfo=UTC)
    bounds = await repo.get_schedule_bounds(2024, reference_dt=ref)

    assert 4 in bounds["sprint_rounds"]
    assert 5 not in bounds["sprint_rounds"]
    assert 4 in bounds["completed_sprint_rounds"]


async def test_schedule_bounds_naive_reference_dt_treated_as_utc(repo, pg_store):
    """Naive datetime reference_dt is treated as UTC."""
    from datetime import date, datetime, time

    from f1_bot.models.race import Circuit, Race

    circuit = Circuit(circuit_id="test", name="Test", locality="Test", country="Test")
    race = Race(
        season=2024, round=1, name="R1", circuit=circuit, date=date(2024, 3, 10), time=time(13, 0)
    )
    await repo.save_schedule(2024, [race])

    # Naive datetime after race
    naive_ref = datetime(2024, 6, 1, 0, 0)  # no tzinfo
    bounds = await repo.get_schedule_bounds(2024, reference_dt=naive_ref)

    assert bounds["completed_rounds"] == 1
    assert bounds["last_completed_round"] == 1


async def test_schedule_bounds_aware_non_utc_reference_dt(repo, pg_store):
    """Timezone-aware non-UTC reference_dt is compared correctly."""
    from datetime import date, datetime, time, timedelta, timezone

    from f1_bot.models.race import Circuit, Race

    circuit = Circuit(circuit_id="test", name="Test", locality="Test", country="Test")
    # Race at 2024-03-10 13:00 UTC
    race = Race(
        season=2024, round=1, name="R1", circuit=circuit, date=date(2024, 3, 10), time=time(13, 0)
    )
    await repo.save_schedule(2024, [race])

    # Reference in UTC+8: 2024-03-10 20:30 (= 12:30 UTC, which is BEFORE the race at 13:00 UTC)
    tz_plus8 = timezone(timedelta(hours=8))
    ref = datetime(2024, 3, 10, 20, 30, tzinfo=tz_plus8)
    bounds = await repo.get_schedule_bounds(2024, reference_dt=ref)

    assert bounds["completed_rounds"] == 0
    assert bounds["next_upcoming_round"] == 1


async def test_get_lap_timings_cached_and_save_clears_cache(repo, pg_store):
    """Verify in-memory caching of lap timings and that save_lap_timings invalidates the cache."""
    from f1_bot.models.results import LapTime

    timings = [
        LapTime(
            driver_id="hamilton",
            lap_number=1,
            lap_time=90.5,
            sector_1=30.0,
            sector_2=30.0,
            sector_3=30.5,
        ),
        LapTime(
            driver_id="verstappen",
            lap_number=1,
            lap_time=91.0,
            sector_1=30.2,
            sector_2=30.1,
            sector_3=30.7,
        ),
    ]
    await repo.save_lap_timings(2024, 5, timings)

    # Spy store.get_lap_timings
    original_get = pg_store.get_lap_timings
    call_count = 0

    async def spy_get(season, round_num):
        nonlocal call_count
        call_count += 1
        return await original_get(season, round_num)

    pg_store.get_lap_timings = spy_get

    # First fetch: should call database and return LapTime list
    res1 = await repo.get_lap_timings(2024, 5)
    assert len(res1) == 2
    assert call_count == 1
    assert isinstance(res1[0], LapTime)

    # Second fetch: should hit memory cache (no database call)
    res2 = await repo.get_lap_timings(2024, 5)
    assert len(res2) == 2
    assert call_count == 1
    assert isinstance(res2[0], LapTime)

    # Save timings: should clear the cache
    await repo.save_lap_timings(2024, 5, timings)

    # Third fetch: should query database again
    res3 = await repo.get_lap_timings(2024, 5)
    assert len(res3) == 2
    assert call_count == 2


async def test_get_schedule_bounds_with_preloaded_races(repo):
    """Verify get_schedule_bounds avoids calling get_schedule if preloaded races are provided."""
    from unittest.mock import AsyncMock

    # Spy repo.get_schedule
    repo.get_schedule = AsyncMock(return_value=[])

    races = [_race(round_num=1)]

    # Calling get_schedule_bounds with races=races
    bounds = await repo.get_schedule_bounds(2024, races=races)
    assert bounds["total_rounds"] == 1
    # verify repo.get_schedule was NOT called
    repo.get_schedule.assert_not_called()

    # Calling get_schedule_bounds WITHOUT races
    await repo.get_schedule_bounds(2024)
    # verify repo.get_schedule WAS called
    repo.get_schedule.assert_awaited_once_with(2024)


# --- Fix 12: LRU cache eviction ---


async def test_laps_cache_evicts_oldest_when_exceeding_max(repo, pg_store):
    """When cache exceeds _MAX_LAPS_CACHE, the oldest entry is evicted."""
    from f1_bot.models.results import LapTime
    from f1_bot.storage.repository import _MAX_LAPS_CACHE

    timing = LapTime(driver_id="hamilton", lap_number=1)

    # Fill cache to max + 1
    for i in range(1, _MAX_LAPS_CACHE + 2):
        await repo.save_lap_timings(2024, i, [timing])
        await repo.get_lap_timings(2024, i)

    # Cache should have exactly _MAX_LAPS_CACHE entries
    assert len(repo._laps_cache) == _MAX_LAPS_CACHE

    # The first entry (round 1) should have been evicted
    assert (2024, 1) not in repo._laps_cache
    # The last entry should still be cached
    assert (2024, _MAX_LAPS_CACHE + 1) in repo._laps_cache


async def test_laps_cache_move_to_end_on_hit(repo, pg_store):
    """Accessing a cached entry moves it to the end (prevents eviction)."""
    from f1_bot.models.results import LapTime
    from f1_bot.storage.repository import _MAX_LAPS_CACHE

    timing = LapTime(driver_id="hamilton", lap_number=1)

    # Insert entries 1 through MAX
    for i in range(1, _MAX_LAPS_CACHE + 1):
        await repo.save_lap_timings(2024, i, [timing])
        await repo.get_lap_timings(2024, i)

    # Access round 1 (oldest) — moves it to end
    await repo.get_lap_timings(2024, 1)

    # Insert one more to trigger eviction
    await repo.save_lap_timings(2024, _MAX_LAPS_CACHE + 1, [timing])
    await repo.get_lap_timings(2024, _MAX_LAPS_CACHE + 1)

    # Round 1 should still be cached (was moved to end)
    assert (2024, 1) in repo._laps_cache
    # Round 2 should have been evicted (was oldest after round 1 was moved)
    assert (2024, 2) not in repo._laps_cache
