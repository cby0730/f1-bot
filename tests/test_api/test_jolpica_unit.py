"""Unit tests for JolpicaClient parsing — all HTTP calls are mocked via pytest-httpx."""

from f1_bot.api.jolpica import JolpicaClient
from f1_bot.utils.rate_limiter import RateLimiter


def _client():
    return JolpicaClient("https://api.jolpi.ca/ergast/f1", RateLimiter(per_second=100))


def _mrdata_wrapper(table_name: str, subtable_name: str, rows: list) -> dict:
    return {"MRData": {table_name: {subtable_name: rows}}}


# --- _parse_circuit / _parse_driver (via get_drivers / get_circuits) ---


async def test_get_drivers_parses_minimal_driver(httpx_mock):
    httpx_mock.add_response(
        json={
            "MRData": {
                "DriverTable": {
                    "Drivers": [
                        {"driverId": "hamilton", "givenName": "Lewis", "familyName": "Hamilton"}
                    ]
                }
            }
        }
    )
    client = _client()
    drivers = await client.get_drivers()
    await client.close()
    assert len(drivers) == 1
    assert drivers[0].driver_id == "hamilton"
    assert drivers[0].given_name == "Lewis"


async def test_get_drivers_optional_fields_default_to_none(httpx_mock):
    httpx_mock.add_response(
        json={
            "MRData": {
                "DriverTable": {
                    "Drivers": [
                        {"driverId": "anon"}  # no givenName, familyName, etc.
                    ]
                }
            }
        }
    )
    client = _client()
    drivers = await client.get_drivers()
    await client.close()
    assert drivers[0].nationality is None
    assert drivers[0].code is None


async def test_get_circuits_parses_lat_lng(httpx_mock):
    httpx_mock.add_response(
        json={
            "MRData": {
                "CircuitTable": {
                    "Circuits": [
                        {
                            "circuitId": "monaco",
                            "circuitName": "Circuit de Monaco",
                            "Location": {
                                "locality": "Monte-Carlo",
                                "country": "Monaco",
                                "lat": "43.7347",
                                "long": "7.4205",
                            },
                        }
                    ]
                }
            }
        }
    )
    client = _client()
    circuits = await client.get_circuits()
    await client.close()
    assert circuits[0].circuit_id == "monaco"
    assert circuits[0].lat == 43.7347
    assert circuits[0].lng == 7.4205


async def test_get_circuits_missing_lat_lng_is_none(httpx_mock):
    httpx_mock.add_response(
        json={
            "MRData": {
                "CircuitTable": {
                    "Circuits": [
                        {
                            "circuitId": "test",
                            "circuitName": "Test",
                            "Location": {"locality": "X", "country": "Y"},
                        }
                    ]
                }
            }
        }
    )
    client = _client()
    circuits = await client.get_circuits()
    await client.close()
    assert circuits[0].lat is None
    assert circuits[0].lng is None


# --- get_driver_standings ---


async def test_get_driver_standings_empty_standings_lists(httpx_mock):
    httpx_mock.add_response(json={"MRData": {"StandingsTable": {"StandingsLists": []}}})
    client = _client()
    result = await client.get_driver_standings()
    await client.close()
    assert result == []


async def test_get_driver_standings_parses_position_and_points(httpx_mock):
    httpx_mock.add_response(
        json={
            "MRData": {
                "StandingsTable": {
                    "StandingsLists": [
                        {
                            "DriverStandings": [
                                {
                                    "position": "1",
                                    "points": "275",
                                    "wins": "7",
                                    "Driver": {
                                        "driverId": "hamilton",
                                        "givenName": "Lewis",
                                        "familyName": "Hamilton",
                                    },
                                    "Constructors": [
                                        {"constructorId": "mercedes", "name": "Mercedes"}
                                    ],
                                }
                            ]
                        }
                    ]
                }
            }
        }
    )
    client = _client()
    standings = await client.get_driver_standings()
    await client.close()
    assert standings[0].position == 1
    assert standings[0].points == 275.0
    assert standings[0].constructor_name == "Mercedes"


async def test_get_current_schedule_parses_all_session_slots(httpx_mock):
    """The schedule feeds /next, /results, notifications and the whole scheduler.

    Every optional session slot has its own Jolpica key, and the trailing ``Z`` on
    times must be stripped — a mis-parsed slot silently drops a session from every
    downstream view rather than failing loudly.
    """
    httpx_mock.add_response(
        json={
            "MRData": {
                "RaceTable": {
                    "Races": [
                        {
                            "season": "2026",
                            "round": "5",
                            "raceName": "Miami Grand Prix",
                            "url": "https://en.wikipedia.org/wiki/Miami",
                            "date": "2026-05-03",
                            "time": "20:00:00Z",
                            "Circuit": {
                                "circuitId": "miami",
                                "circuitName": "Miami International Autodrome",
                                "Location": {"locality": "Miami", "country": "USA"},
                            },
                            "FirstPractice": {"date": "2026-05-01", "time": "16:30:00Z"},
                            "SprintQualifying": {"date": "2026-05-01", "time": "20:30:00Z"},
                            "Sprint": {"date": "2026-05-02", "time": "16:00:00Z"},
                            "Qualifying": {"date": "2026-05-02", "time": "20:00:00Z"},
                        }
                    ]
                }
            }
        }
    )
    client = _client()
    races = await client.get_current_schedule()
    await client.close()

    race = races[0]
    assert race.season == 2026
    assert race.round == 5
    assert race.name == "Miami Grand Prix"
    assert race.circuit.locality == "Miami"
    assert str(race.time) == "20:00:00"  # trailing Z stripped
    assert str(race.fp1.time) == "16:30:00"
    assert race.sprint_qualifying is not None
    assert race.sprint is not None
    assert race.qualifying is not None
    # Absent slots stay None rather than becoming empty sessions
    assert race.fp2 is None
    assert race.fp3 is None


async def test_get_current_schedule_session_without_time_keeps_date(httpx_mock):
    """A session announced date-only must survive parsing, not be dropped."""
    httpx_mock.add_response(
        json={
            "MRData": {
                "RaceTable": {
                    "Races": [
                        {
                            "season": "2026",
                            "round": "1",
                            "raceName": "Test GP",
                            "date": "2026-03-08",
                            "Circuit": {
                                "circuitId": "test",
                                "circuitName": "Test Circuit",
                                "Location": {"locality": "Town", "country": "Nowhere"},
                            },
                            "FirstPractice": {"date": "2026-03-06"},
                        }
                    ]
                }
            }
        }
    )
    client = _client()
    races = await client.get_current_schedule()
    await client.close()

    assert races[0].time is None
    assert races[0].fp1 is not None
    assert str(races[0].fp1.date) == "2026-03-06"
    assert races[0].fp1.time is None


async def test_get_driver_standings_inner_key_missing_returns_empty(httpx_mock):
    """A structurally valid envelope with an empty entry must degrade, not raise.

    The malformed-response guard originally wrapped only the envelope lookup, so this
    payload raised KeyError past it and took down the whole /standings command.
    """
    httpx_mock.add_response(json={"MRData": {"StandingsTable": {"StandingsLists": [{}]}}})
    client = _client()
    result = await client.get_driver_standings()
    await client.close()
    assert result == []


# --- get_constructor_standings ---


async def test_get_constructor_standings_missing_standings_table_returns_empty(httpx_mock):
    httpx_mock.add_response(json={"MRData": {}})
    client = _client()
    result = await client.get_constructor_standings()
    await client.close()
    assert result == []


async def test_get_constructor_standings_empty_standings_lists(httpx_mock):
    httpx_mock.add_response(json={"MRData": {"StandingsTable": {"StandingsLists": []}}})
    client = _client()
    result = await client.get_constructor_standings()
    await client.close()
    assert result == []


async def test_get_constructor_standings_inner_key_missing_returns_empty(httpx_mock):
    """Same guard-scope defect as the driver-standings case above."""
    httpx_mock.add_response(json={"MRData": {"StandingsTable": {"StandingsLists": [{}]}}})
    client = _client()
    result = await client.get_constructor_standings()
    await client.close()
    assert result == []


async def test_get_constructor_standings_parses_position_and_points(httpx_mock):
    httpx_mock.add_response(
        json={
            "MRData": {
                "StandingsTable": {
                    "StandingsLists": [
                        {
                            "ConstructorStandings": [
                                {
                                    "position": "1",
                                    "points": "612",
                                    "wins": "12",
                                    "Constructor": {
                                        "constructorId": "mclaren",
                                        "name": "McLaren",
                                        "nationality": "British",
                                    },
                                }
                            ]
                        }
                    ]
                }
            }
        }
    )
    client = _client()
    standings = await client.get_constructor_standings()
    await client.close()
    assert standings[0].position == 1
    assert standings[0].points == 612.0
    assert standings[0].constructor.name == "McLaren"


# --- get_sprint_results ---


async def test_get_sprint_results_empty_races_returns_none(httpx_mock):
    httpx_mock.add_response(json={"MRData": {"RaceTable": {"Races": []}}})
    client = _client()
    race, results = await client.get_sprint_results()
    await client.close()
    assert race is None
    assert results == []


async def test_get_sprint_results_missing_race_table_returns_none(httpx_mock):
    """Rounds without a sprint still hit this endpoint; a missing table is routine."""
    httpx_mock.add_response(json={"MRData": {}})
    client = _client()
    race, results = await client.get_sprint_results()
    await client.close()
    assert race is None
    assert results == []


async def test_get_sprint_results_dnf_falls_back_to_status(httpx_mock):
    """A retired driver has no Time block; the row must show the status, never a blank.

    Sprint results feed /compare's head-to-head, which relies on status text to
    classify a DNF rather than scoring it as a finish.
    """
    httpx_mock.add_response(
        json={
            "MRData": {
                "RaceTable": {
                    "Races": [
                        {
                            "season": "2024",
                            "round": "5",
                            "raceName": "Chinese Grand Prix",
                            "date": "2024-04-20",
                            "Circuit": {
                                "circuitId": "shanghai",
                                "circuitName": "Shanghai International Circuit",
                                "Location": {"locality": "Shanghai", "country": "China"},
                            },
                            "SprintResults": [
                                {
                                    "position": "1",
                                    "grid": "1",
                                    "laps": "19",
                                    "status": "Finished",
                                    "points": "8",
                                    "Driver": {
                                        "driverId": "verstappen",
                                        "givenName": "Max",
                                        "familyName": "Verstappen",
                                    },
                                    "Constructor": {
                                        "constructorId": "red_bull",
                                        "name": "Red Bull",
                                    },
                                    "Time": {"time": "30:07.628"},
                                },
                                {
                                    "position": "20",
                                    "grid": "10",
                                    "laps": "3",
                                    "status": "Collision",
                                    "points": "0",
                                    "Driver": {
                                        "driverId": "sainz",
                                        "givenName": "Carlos",
                                        "familyName": "Sainz",
                                    },
                                    "Constructor": {"constructorId": "ferrari", "name": "Ferrari"},
                                },
                            ],
                        }
                    ]
                }
            }
        }
    )
    client = _client()
    race, results = await client.get_sprint_results()
    await client.close()
    assert race is not None
    assert race.round == 5
    assert results[0].time == "30:07.628"
    assert results[0].points == 8.0
    assert results[1].time == "Collision"
    assert results[1].status == "Collision"


# --- get_race_results ---


async def test_get_race_results_empty_races_returns_none(httpx_mock):
    httpx_mock.add_response(json={"MRData": {"RaceTable": {"Races": []}}})
    client = _client()
    race, results = await client.get_race_results("2024", "1")
    await client.close()
    assert race is None
    assert results == []


async def test_get_race_results_fastest_lap_rank_parsed(httpx_mock):
    httpx_mock.add_response(
        json={
            "MRData": {
                "RaceTable": {
                    "Races": [
                        {
                            "season": "2024",
                            "round": "1",
                            "raceName": "Bahrain GP",
                            "date": "2024-03-02",
                            "time": "15:00:00Z",
                            "Circuit": {
                                "circuitId": "bahrain",
                                "circuitName": "BIC",
                                "Location": {"locality": "Sakhir", "country": "Bahrain"},
                            },
                            "Results": [
                                {
                                    "position": "1",
                                    "grid": "1",
                                    "laps": "57",
                                    "status": "Finished",
                                    "points": "26",
                                    "Driver": {
                                        "driverId": "verstappen",
                                        "givenName": "Max",
                                        "familyName": "Verstappen",
                                    },
                                    "Constructor": {
                                        "constructorId": "red_bull",
                                        "name": "Red Bull",
                                    },
                                    "Time": {"time": "1:31:44.742"},
                                    "FastestLap": {"rank": "1", "Time": {"time": "1:31.447"}},
                                }
                            ],
                        }
                    ]
                }
            }
        }
    )
    client = _client()
    race, results = await client.get_race_results("2024", "1")
    await client.close()
    assert results[0].fastest_lap_rank == 1
    assert results[0].fastest_lap_time == "1:31.447"


# --- get_qualifying_results ---


async def test_get_qualifying_results_parses_q1_q2_q3(httpx_mock):
    httpx_mock.add_response(
        json={
            "MRData": {
                "RaceTable": {
                    "Races": [
                        {
                            "season": "2024",
                            "round": "1",
                            "raceName": "Bahrain GP",
                            "date": "2024-03-01",
                            "Circuit": {
                                "circuitId": "bahrain",
                                "circuitName": "BIC",
                                "Location": {"locality": "Sakhir", "country": "Bahrain"},
                            },
                            "QualifyingResults": [
                                {
                                    "position": "1",
                                    "Driver": {
                                        "driverId": "verstappen",
                                        "givenName": "Max",
                                        "familyName": "Verstappen",
                                    },
                                    "Constructor": {
                                        "constructorId": "red_bull",
                                        "name": "Red Bull",
                                    },
                                    "Q1": "1:32.0",
                                    "Q2": "1:30.5",
                                    "Q3": "1:29.1",
                                }
                            ],
                        }
                    ]
                }
            }
        }
    )
    client = _client()
    race, results = await client.get_qualifying_results("2024", "1")
    await client.close()
    assert results[0].q1 == "1:32.0"
    assert results[0].q2 == "1:30.5"
    assert results[0].q3 == "1:29.1"


# --- get_pit_stops ---


async def test_get_pit_stops_invalid_duration_handled(httpx_mock):
    """Non-numeric duration string (e.g. '1:01') should be stored as None."""
    httpx_mock.add_response(
        json={
            "MRData": {
                "RaceTable": {
                    "Races": [
                        {
                            "PitStops": [
                                {
                                    "driverId": "hamilton",
                                    "lap": "20",
                                    "stop": "1",
                                    "duration": "1:01.234",
                                }
                            ]
                        }
                    ]
                }
            }
        }
    )
    client = _client()
    stops = await client.get_pit_stops()
    await client.close()
    # "1:01.234" can't be parsed as float → duration is None
    assert stops[0].duration is None


async def test_get_pit_stops_numeric_duration_parsed(httpx_mock):
    httpx_mock.add_response(
        json={
            "MRData": {
                "RaceTable": {
                    "Races": [
                        {
                            "PitStops": [
                                {"driverId": "ham", "lap": "20", "stop": "1", "duration": "24.567"}
                            ]
                        }
                    ]
                }
            }
        }
    )
    client = _client()
    stops = await client.get_pit_stops()
    await client.close()
    assert stops[0].duration == 24.567


# --- get_lap_timings ---


async def test_get_lap_timings_multiple_timings_per_lap(httpx_mock):
    httpx_mock.add_response(
        json={
            "MRData": {
                "total": "2",
                "RaceTable": {
                    "Races": [
                        {
                            "Laps": [
                                {
                                    "number": "1",
                                    "Timings": [
                                        {"driverId": "hamilton", "position": "1", "time": "1:34.0"},
                                        {
                                            "driverId": "verstappen",
                                            "position": "2",
                                            "time": "1:34.5",
                                        },
                                    ],
                                }
                            ]
                        }
                    ]
                },
            }
        }
    )
    client = _client()
    laps = await client.get_lap_timings()
    await client.close()
    assert len(laps) == 2
    assert laps[0].driver_id == "hamilton"
    assert laps[1].driver_id == "verstappen"


async def test_get_lap_timings_empty_races_returns_empty(httpx_mock):
    httpx_mock.add_response(json={"MRData": {"total": "0", "RaceTable": {"Races": []}}})
    client = _client()
    laps = await client.get_lap_timings()
    await client.close()
    assert laps == []


# --- Malformed response handling (Fix 2 + Fix 3) ---


async def test_get_current_schedule_malformed_response_returns_empty(httpx_mock):
    """When API response has unexpected structure, return empty list instead of crashing."""
    httpx_mock.add_response(json={"MRData": {}})
    client = _client()
    races = await client.get_current_schedule()
    await client.close()
    assert races == []


async def test_get_race_results_missing_mrdata_returns_none(httpx_mock):
    """Completely missing MRData wrapper returns (None, [])."""
    httpx_mock.add_response(json={})
    client = _client()
    race, results = await client.get_race_results("2024", "1")
    await client.close()
    assert race is None
    assert results == []


async def test_parse_circuit_missing_circuit_id_uses_fallback(httpx_mock):
    """When circuitId is absent, parser uses 'unknown' fallback."""
    httpx_mock.add_response(
        json={
            "MRData": {
                "CircuitTable": {
                    "Circuits": [{"Location": {"locality": "Test", "country": "Testland"}}]
                }
            }
        }
    )
    client = _client()
    circuits = await client.get_circuits()
    await client.close()
    assert len(circuits) == 1
    assert circuits[0].circuit_id == "unknown"
    assert circuits[0].name == ""


# --- get_lap_timings malformed response ---


async def test_get_lap_timings_malformed_first_page_no_crash(httpx_mock):
    """When first page is malformed (missing MRData keys), return empty list without crash."""
    httpx_mock.add_response(json={"MRData": {}})
    client = _client()
    laps = await client.get_lap_timings()
    await client.close()
    assert laps == []
