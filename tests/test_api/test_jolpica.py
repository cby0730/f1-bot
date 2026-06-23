"""Integration tests that hit the real Jolpica API.

These tests verify that our parser correctly handles live API responses.
They require network access; skip them with -m "not integration" if offline.
"""

import pytest

from f1_bot.api.jolpica import JolpicaClient
from f1_bot.models.constructor import ConstructorStanding
from f1_bot.models.driver import DriverStanding
from f1_bot.models.race import Race
from f1_bot.models.results import LapTime, PitStop, QualifyingResult, RaceResult
from f1_bot.utils.rate_limiter import RateLimiter

pytestmark = pytest.mark.integration


@pytest.fixture
def client():
    limiter = RateLimiter(per_second=2.0, per_period=10, period=60)
    return JolpicaClient("https://api.jolpi.ca/ergast/f1", limiter)


# --- Schedule ---


async def test_get_current_schedule_returns_races(client):
    races = await client.get_current_schedule()
    assert len(races) > 0
    race = races[0]
    assert isinstance(race, Race)
    assert race.season >= 2024
    assert race.round >= 1
    assert race.circuit.circuit_id


async def test_schedule_race_has_date(client):
    races = await client.get_current_schedule()
    for race in races:
        assert race.date is not None


# --- Standings ---


async def test_get_driver_standings_returns_list(client):
    standings = await client.get_driver_standings()
    assert len(standings) > 0
    s = standings[0]
    assert isinstance(s, DriverStanding)
    assert s.position == 1
    assert s.points >= 0
    assert s.driver.family_name


async def test_get_constructor_standings_returns_list(client):
    standings = await client.get_constructor_standings()
    assert len(standings) > 0
    s = standings[0]
    assert isinstance(s, ConstructorStanding)
    assert s.position == 1
    assert s.constructor.name


# --- Race results (2024 R1 Bahrain — stable historical data) ---


async def test_get_race_results_2024_r1(client):
    race, results = await client.get_race_results("2024", "1")
    assert race is not None
    assert race.name == "Bahrain Grand Prix"
    assert race.season == 2024
    assert race.round == 1
    assert len(results) > 0
    winner = results[0]
    assert isinstance(winner, RaceResult)
    assert winner.position == 1
    assert winner.driver.family_name == "Verstappen"
    assert winner.points >= 25.0  # 25 race pts + 1 fastest lap bonus = 26


async def test_race_results_have_constructor(client):
    _, results = await client.get_race_results("2024", "1")
    for r in results:
        assert r.constructor.name


# --- Qualifying results (2024 R1) ---


async def test_get_qualifying_results_2024_r1(client):
    race, results = await client.get_qualifying_results("2024", "1")
    assert race is not None
    assert len(results) > 0
    pole = results[0]
    assert isinstance(pole, QualifyingResult)
    assert pole.position == 1
    assert pole.q1 is not None


# --- Pit stops (2024 R1) ---


async def test_get_pit_stops_2024_r1(client):
    stops = await client.get_pit_stops("2024", "1")
    assert len(stops) > 0
    s = stops[0]
    assert isinstance(s, PitStop)
    assert s.driver_id
    assert s.lap >= 1
    assert s.stop_number >= 1


async def test_pit_stop_duration_is_float_or_none(client):
    stops = await client.get_pit_stops("2024", "1")
    for s in stops:
        assert s.duration is None or isinstance(s.duration, float)


# --- Lap times (2024 R1, limited) ---


async def test_get_lap_timings_2024_r1(client):
    laps = await client.get_lap_timings("2024", "1")
    assert len(laps) > 0
    lap = laps[0]
    assert isinstance(lap, LapTime)
    assert lap.lap_number >= 1
    assert lap.driver_id


# --- Empty / missing round graceful handling ---


async def test_missing_sprint_returns_empty(client):
    # Bahrain 2024 had no sprint — should return empty list gracefully
    race, results = await client.get_sprint_results("2024", "1")
    assert race is None
    assert results == []
