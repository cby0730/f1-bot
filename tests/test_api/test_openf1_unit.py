"""Unit tests for OpenF1Client response parsing — all HTTP calls mocked via pytest-httpx."""

from f1_bot.api.openf1 import OpenF1Client
from f1_bot.utils.rate_limiter import RateLimiter


def _client():
    return OpenF1Client("https://api.openf1.org/v1", RateLimiter(per_second=100))


# --- get_sessions ---


async def test_get_sessions_parses_correctly(httpx_mock):
    httpx_mock.add_response(
        json=[
            {
                "session_key": 9001,
                "session_name": "Practice 1",
                "session_type": "Practice",
                "meeting_key": 100,
                "date_start": "2024-05-23T11:30:00+00:00",
                "date_end": "2024-05-23T12:30:00+00:00",
                "gmt_offset": "02:00:00",
                "year": 2024,
            }
        ]
    )
    client = _client()
    sessions = await client.get_sessions(year=2024)
    await client.close()
    assert len(sessions) == 1
    assert sessions[0].session_key == 9001
    assert sessions[0].session_name == "Practice 1"
    assert sessions[0].gmt_offset == "02:00:00"


async def test_get_sessions_optional_fields_default(httpx_mock):
    httpx_mock.add_response(
        json=[
            {
                "session_key": 9002,
            }
        ]
    )
    client = _client()
    sessions = await client.get_sessions()
    await client.close()
    assert sessions[0].session_name == ""
    assert sessions[0].date_start is None


# --- get_positions ---


async def test_get_positions_parses_position_and_driver(httpx_mock):
    httpx_mock.add_response(
        json=[
            {"session_key": 9001, "driver_number": 1, "position": 1, "date": "2024-05-26T13:00:00"},
            {
                "session_key": 9001,
                "driver_number": 44,
                "position": 2,
                "date": "2024-05-26T13:00:00",
            },
        ]
    )
    client = _client()
    positions = await client.get_positions(session_key=9001)
    await client.close()
    assert len(positions) == 2
    assert positions[0].driver_number == 1
    assert positions[0].position == 1
    assert positions[1].driver_number == 44


# --- get_intervals ---


async def test_get_intervals_none_gap_handled(httpx_mock):
    """gap_to_leader=None (leader) and interval=None should produce None fields."""
    httpx_mock.add_response(
        json=[
            {"session_key": 9001, "driver_number": 1, "gap_to_leader": None, "interval": None},
            {"session_key": 9001, "driver_number": 44, "gap_to_leader": 3.456, "interval": 1.234},
        ]
    )
    client = _client()
    intervals = await client.get_intervals(session_key=9001)
    await client.close()
    assert intervals[0].gap_to_leader is None
    assert intervals[0].interval is None
    assert intervals[1].gap_to_leader == "3.456"
    assert intervals[1].interval == "1.234"


# --- get_race_control ---


async def test_get_race_control_parses_messages(httpx_mock):
    httpx_mock.add_response(
        json=[
            {
                "session_key": 9001,
                "category": "Flag",
                "flag": "YELLOW",
                "scope": "Track",
                "sector": 1,
                "driver_number": None,
                "message": "YELLOW FLAG IN SECTOR 1",
                "date": "2024-05-26T13:05:00",
            }
        ]
    )
    client = _client()
    messages = await client.get_race_control(session_key=9001)
    await client.close()
    assert messages[0].category == "Flag"
    assert messages[0].flag == "YELLOW"
    assert messages[0].message == "YELLOW FLAG IN SECTOR 1"


# --- get_weather ---


async def test_get_weather_parses_all_fields(httpx_mock):
    httpx_mock.add_response(
        json=[
            {
                "session_key": 9001,
                "air_temperature": 28.5,
                "track_temperature": 42.1,
                "humidity": 65.0,
                "pressure": 1013.25,
                "wind_speed": 3.2,
                "wind_direction": 180,
                "rainfall": False,
                "date": "2024-05-26T13:10:00",
            }
        ]
    )
    client = _client()
    weather = await client.get_weather(session_key=9001)
    await client.close()
    assert weather[0].air_temperature == 28.5
    assert weather[0].rainfall is False


# --- get_session_results ---


async def test_get_session_results_dsq_flag(httpx_mock):
    httpx_mock.add_response(
        json=[
            {
                "position": None,
                "driver_number": 16,
                "duration": None,
                "gap_to_leader": None,
                "number_of_laps": 0,
                "dnf": False,
                "dns": False,
                "dsq": True,
            }
        ]
    )
    client = _client()
    results = await client.get_session_results(session_key=9001)
    await client.close()
    assert results[0].dsq is True
    assert results[0].driver_number == 16
    assert results[0].position is None


async def test_get_pit_parses_duration(httpx_mock):
    httpx_mock.add_response(
        json=[
            {
                "driver_number": 44,
                "lap_number": 20,
                "stop_number": 1,
                "pit_duration": 24.5,
                "date": "2024-05-26T14:00:00",
            }
        ]
    )
    client = _client()
    stops = await client.get_pit(session_key=9001)
    await client.close()
    assert stops[0].driver_id == "44"
    assert stops[0].lap == 20
    assert stops[0].duration == 24.5


async def test_get_meetings_parses_gmt_offset(httpx_mock):
    httpx_mock.add_response(
        json=[
            {
                "meeting_key": 100,
                "meeting_name": "Monaco Grand Prix",
                "meeting_official_name": "Formula 1 Grand Prix de Monaco 2024",
                "location": "Monte-Carlo",
                "country_name": "Monaco",
                "circuit_short_name": "Monaco",
                "date_start": "2024-05-23",
                "gmt_offset": "02:00:00",
                "year": 2024,
            }
        ]
    )
    client = _client()
    meetings = await client.get_meetings(year=2024)
    await client.close()
    assert meetings[0].meeting_key == 100
    assert meetings[0].gmt_offset == "02:00:00"
