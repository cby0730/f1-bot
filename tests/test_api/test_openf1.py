"""Integration tests that hit the real OpenF1 API.

Uses a known historical session (2024 Monaco GP Race, session_key=9522)
to get stable, reproducible data. Requires network access.
"""

import pytest
from f1_bot.api.openf1 import OpenF1Client
from f1_bot.models.live import LivePosition, RaceControlMessage, WeatherData
from f1_bot.models.race import Meeting
from f1_bot.models.results import LapTime, PitStop
from f1_bot.utils.rate_limiter import RateLimiter

pytestmark = pytest.mark.integration

# Abu Dhabi 2024 Race — stable reference session (Monaco 2024 data was pruned from API)
ABU_DHABI_2024_MEETING = 1252
ABU_DHABI_2024_RACE_SESSION = 9662


@pytest.fixture
def client():
    limiter = RateLimiter(per_second=2.0, per_period=10, period=60)
    return OpenF1Client("https://api.openf1.org/v1", limiter)


# --- Meetings ---


async def test_get_meeting_abu_dhabi_2024(client):
    meetings = await client.get_meetings(year=2024, meeting_key=ABU_DHABI_2024_MEETING)
    assert len(meetings) == 1
    m = meetings[0]
    assert isinstance(m, Meeting)
    assert "Abu Dhabi" in m.meeting_name
    assert m.gmt_offset == "04:00:00"
    assert m.year == 2024


# --- Sessions ---


async def test_get_sessions_abu_dhabi_2024(client):
    sessions = await client.get_sessions(meeting_key=ABU_DHABI_2024_MEETING)
    assert len(sessions) > 0
    session_types = {s.session_type for s in sessions}
    assert "Race" in session_types or "race" in session_types


# --- Positions (race start, limited) ---


async def test_get_positions_abu_dhabi_race(client):
    positions = await client.get_positions(session_key=ABU_DHABI_2024_RACE_SESSION, driver_number=1)
    assert len(positions) > 0
    p = positions[0]
    assert isinstance(p, LivePosition)
    assert p.session_key == ABU_DHABI_2024_RACE_SESSION
    assert p.driver_number == 1
    assert 1 <= p.position <= 20


# --- Pit stops ---


async def test_get_pit_stops_abu_dhabi_race(client):
    stops = await client.get_pit(session_key=ABU_DHABI_2024_RACE_SESSION)
    assert len(stops) > 0
    s = stops[0]
    assert isinstance(s, PitStop)
    assert s.driver_id
    assert s.lap >= 1


# --- Lap times (single driver to stay within rate limits) ---


async def test_get_laps_abu_dhabi_race_single_driver(client):
    laps = await client.get_laps(
        session_key=ABU_DHABI_2024_RACE_SESSION, driver_number=1, lap_number=1
    )
    assert len(laps) >= 1
    lap = laps[0]
    assert isinstance(lap, LapTime)
    assert lap.lap_number == 1
    assert lap.driver_id == "1"


# --- Weather ---


async def test_get_weather_abu_dhabi_race(client):
    weather = await client.get_weather(session_key=ABU_DHABI_2024_RACE_SESSION)
    assert len(weather) > 0
    w = weather[0]
    assert isinstance(w, WeatherData)
    assert w.session_key == ABU_DHABI_2024_RACE_SESSION
    assert w.air_temperature is not None


# --- Race control messages ---


async def test_get_race_control_abu_dhabi(client):
    messages = await client.get_race_control(session_key=ABU_DHABI_2024_RACE_SESSION)
    assert len(messages) > 0
    m = messages[0]
    assert isinstance(m, RaceControlMessage)
    assert m.message
