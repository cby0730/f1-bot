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


# --- Missing required key handling (Fix 4) ---


async def test_get_meetings_skips_record_without_meeting_key(httpx_mock):
    """Records missing required 'meeting_key' should be skipped, not crash."""
    httpx_mock.add_response(
        json=[
            {"meeting_name": "Incomplete"},  # no meeting_key
            {
                "meeting_key": 200,
                "meeting_name": "Valid GP",
                "year": 2024,
            },
        ]
    )
    client = _client()
    meetings = await client.get_meetings(year=2024)
    await client.close()
    assert len(meetings) == 1
    assert meetings[0].meeting_key == 200


async def test_get_session_results_skips_record_without_driver_number(httpx_mock):
    """Records missing 'driver_number' should be skipped."""
    httpx_mock.add_response(
        json=[
            {"position": 1, "duration": 90.0},  # no driver_number
            {"driver_number": 44, "position": 2, "duration": 91.0},
        ]
    )
    client = _client()
    results = await client.get_session_results(session_key=9001)
    await client.close()
    assert len(results) == 1
    assert results[0].driver_number == 44


# --- Malformed record skipping ---


async def test_get_pit_skips_record_without_driver_number(httpx_mock):
    """Records missing 'driver_number' should be skipped."""
    httpx_mock.add_response(
        json=[
            {"lap_number": 10, "pit_duration": 24.0},
            {"driver_number": 44, "lap_number": 20, "pit_duration": 23.5},
        ]
    )
    client = _client()
    stops = await client.get_pit(session_key=9001)
    await client.close()
    assert len(stops) == 1
    assert stops[0].driver_id == "44"


async def test_get_laps_skips_record_without_driver_number(httpx_mock):
    """Records missing 'driver_number' should be skipped."""
    httpx_mock.add_response(
        json=[
            {"lap_number": 1, "lap_duration": 92.0},
            {"driver_number": 1, "lap_number": 1, "lap_duration": 91.5},
        ]
    )
    client = _client()
    laps = await client.get_laps(session_key=9001)
    await client.close()
    assert len(laps) == 1
    assert laps[0].driver_id == "1"
