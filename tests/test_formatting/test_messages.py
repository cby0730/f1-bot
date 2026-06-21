"""Tests for message formatters — verify key content appears in output."""

from datetime import date, time

from f1_bot.formatting.messages import (
    _esc,
    _format_result_value,
    _parse_lap_time_ms,
    format_constructor_standings,
    format_driver_standings,
    format_laps_by_driver,
    format_laps_by_lap,
    format_laps_driver_picker,
    format_laps_summary,
    format_next_race,
    format_pitstops,
    format_qualifying_results,
    format_race_results,
    format_schedule,
    format_session_results,
)
from f1_bot.models.constructor import Constructor, ConstructorStanding
from f1_bot.models.driver import Driver, DriverStanding
from f1_bot.models.race import Circuit, Race, RaceSession
from f1_bot.models.results import LapTime, PitStop, QualifyingResult, RaceResult, SessionResult
from f1_bot.utils.sessions import find_race_session


def _circuit():
    return Circuit(
        circuit_id="monaco", name="Circuit de Monaco", locality="Monte-Carlo", country="Monaco"
    )


def _race(round_num=5, r_date=date(2024, 5, 26), r_time=time(13, 0, 0)):
    return Race(
        season=2024,
        round=round_num,
        name="Monaco Grand Prix",
        circuit=_circuit(),
        date=r_date,
        time=r_time,
    )


def _driver(driver_id="hamilton", given="Lewis", family="Hamilton", nat="British", perm_num="44"):
    return Driver(
        driver_id=driver_id,
        given_name=given,
        family_name=family,
        nationality=nat,
        permanent_number=perm_num,
    )


def _constructor(cid="mercedes", name="Mercedes"):
    return Constructor(constructor_id=cid, name=name, nationality="German")


# --- format_next_race ---


def test_format_next_race_contains_name():
    race = _race()
    text = format_next_race(race, "UTC")
    assert "Monaco Grand Prix" in text


def test_format_next_race_shows_race_time():
    race = _race()
    text = format_next_race(race, "UTC")
    assert "13:00" in text


def test_format_next_race_timezone_converted():
    race = _race()
    text = format_next_race(race, "Asia/Taipei")
    # 13:00 UTC = 21:00 Taipei (UTC+8)
    assert "21:00" in text


def test_format_next_race_shows_circuit_location():
    race = _race()
    text = format_next_race(race, "UTC")
    assert "Monte-Carlo" in text


def test_format_next_race_includes_session_times_when_present():
    qualifying = RaceSession(name="Qualifying", date=date(2024, 5, 25), time=time(15, 0, 0))
    race = Race(
        season=2024,
        round=5,
        name="Monaco Grand Prix",
        circuit=_circuit(),
        date=date(2024, 5, 26),
        qualifying=qualifying,
    )
    text = format_next_race(race, "UTC")
    assert "Quali" in text
    assert "15:00" in text


# --- format_schedule ---


def test_format_schedule_lists_all_rounds():
    races = [_race(r, date(2024, 3 + r, 1)) for r in range(1, 4)]
    text = format_schedule(races, "UTC")
    assert "R01" in text and "R02" in text and "R03" in text


def test_format_schedule_marks_past_races():
    past_race = _race(1, date(2020, 1, 1))
    future_race = _race(2, date(2099, 1, 1))
    text = format_schedule([past_race, future_race], "UTC")
    assert "✅" in text


# --- format_driver_standings ---


def test_format_driver_standings_shows_top_drivers():
    standings = [
        DriverStanding(
            position=1, points=100, wins=3, driver=_driver(), constructor_name="Mercedes"
        ),
        DriverStanding(
            position=2,
            points=80,
            wins=1,
            driver=_driver("max_verstappen", "Max", "Verstappen", "Dutch"),
            constructor_name="Red Bull",
        ),
    ]
    text = format_driver_standings(standings, 2024)
    assert "Hamilton" in text
    assert "Verstappen" in text
    assert "100" in text


def test_format_driver_standings_shows_season():
    standings = [
        DriverStanding(position=1, points=50, wins=1, driver=_driver(), constructor_name="Merc")
    ]
    text = format_driver_standings(standings, 2024)
    assert "2024" in text


# --- format_constructor_standings ---


def test_format_constructor_standings_shows_teams():
    standings = [
        ConstructorStanding(position=1, points=200, wins=4, constructor=_constructor()),
        ConstructorStanding(
            position=2, points=150, wins=2, constructor=_constructor("ferrari", "Ferrari")
        ),
    ]
    text = format_constructor_standings(standings, 2024)
    assert "Mercedes" in text
    assert "Ferrari" in text


# --- format_race_results ---


def test_format_race_results_shows_winner():
    results = [
        RaceResult(
            position=1,
            grid=1,
            laps=78,
            status="Finished",
            points=25.0,
            driver=_driver(),
            constructor=_constructor(),
            time="1:23:45.678",
        ),
    ]
    text = format_race_results(_race(), results)
    assert "Hamilton (#44) — ⏱ 1:23:45.678" in text
    assert "🇬🇧" in text


def test_format_race_results_fastest_lap_marker():
    results = [
        RaceResult(
            position=1,
            grid=1,
            laps=78,
            status="Finished",
            points=25.0,
            driver=_driver(),
            constructor=_constructor(),
            time="1:23:45",
            fastest_lap_rank=1,
        ),
    ]
    text = format_race_results(_race(), results)
    assert "Hamilton (#44) ⚡ — ⏱ 1:23:45" in text


def test_format_race_results_gap_time():
    results = [
        RaceResult(
            position=1,
            grid=1,
            laps=78,
            status="Finished",
            points=25.0,
            driver=_driver(driver_id="hamilton", given="Lewis", family="Hamilton", perm_num="44"),
            constructor=_constructor(),
            time="1:23:45.678",
        ),
        RaceResult(
            position=2,
            grid=2,
            laps=78,
            status="Finished",
            points=18.0,
            driver=_driver(driver_id="bottas", given="Valtteri", family="Bottas", perm_num="77"),
            constructor=_constructor(),
            time="+3.264",
        ),
    ]
    text = format_race_results(_race(), results)
    assert "Lewis Hamilton (#44) — ⏱ 1:23:45.678" in text
    assert "Valtteri Bottas (#77) — +3.264" in text


# --- format_qualifying_results ---


def test_format_qualifying_shows_q3_time():
    results = [
        QualifyingResult(
            position=1,
            driver=_driver(),
            constructor=_constructor(),
            q1="1:11.0",
            q2="1:10.5",
            q3="1:09.8",
        ),
    ]
    text = format_qualifying_results(_race(), results)
    assert "1:09.8" in text
    assert "#44" in text
    assert "🇬🇧" in text


def test_format_session_results_shows_session_and_duration():
    race = _race()
    race = race.model_copy(
        update={"fp1": RaceSession(name="FP1", date=date(2024, 5, 24), time=time(11, 30))}
    )
    entry = find_race_session([race], 5, "fp1")
    results = [SessionResult(position=1, driver_number=4, duration="1:12.345")]

    text = format_session_results(entry, results)

    assert "FP1 Result" in text
    assert "#4" in text
    assert "1:12.345" in text


def test_format_session_results_with_driver_mappings():
    race = _race()
    race = race.model_copy(
        update={"fp1": RaceSession(name="FP1", date=date(2024, 5, 24), time=time(11, 30))}
    )
    entry = find_race_session([race], 5, "fp1")

    # 1. Test lookup via driver_id
    results_id = [
        SessionResult(position=1, driver_number=44, driver_id="hamilton", duration="1:12.345")
    ]
    drivers_dict = {"hamilton": _driver(driver_id="hamilton", nat="British")}
    text_id = format_session_results(entry, results_id, drivers_dict)
    assert "🇬🇧 #44 Lewis Hamilton" in text_id

    # 2. Test fallback lookup via driver_number (legacy compatibility)
    results_num = [SessionResult(position=1, driver_number=44, duration="1:12.345")]
    drivers_dict_legacy = {44: _driver(driver_id="hamilton", nat="British")}
    text_legacy = format_session_results(entry, results_num, drivers_dict_legacy)
    assert "🇬🇧 #44 Lewis Hamilton" in text_legacy

    # 3. Test dynamic flag generation for uncommon countries
    results_uncommon = [
        SessionResult(position=1, driver_number=88, driver_id="rookie", duration="1:12.345")
    ]
    drivers_dict_uncommon = {
        "rookie": _driver(
            driver_id="rookie", given="Arvid", family="Lindblad", nat="EST", perm_num="88"
        )
    }
    text_uncommon = format_session_results(entry, results_uncommon, drivers_dict_uncommon)
    assert "🇪🇪 #88 Arvid Lindblad" in text_uncommon


# --- format_pitstops ---


def test_format_pitstops_shows_driver_and_lap():
    stops = [
        PitStop(driver_id="HAM", lap=20, stop_number=1, duration=24.5),
    ]
    text = format_pitstops(_race(), stops, 5)
    assert "HAM" in text
    assert "Lap 20" in text
    assert "24.5s" in text


def test_format_pitstops_groups_multiple_stops_per_driver():
    stops = [
        PitStop(driver_id="VER", lap=15, stop_number=1, duration=22.1),
        PitStop(driver_id="VER", lap=40, stop_number=2, duration=23.8),
    ]
    text = format_pitstops(_race(), stops, 5)
    # Both stops should appear on a single driver row
    assert "Lap 15" in text
    assert "Lap 40" in text
    assert text.count("VER") == 1


def test_format_pitstops_none_duration_shows_dash():
    stops = [PitStop(driver_id="LEC", lap=30, stop_number=1, duration=None)]
    text = format_pitstops(_race(), stops, 5)
    assert "—" in text


def test_format_pitstops_no_race_uses_round_number():
    stops = [PitStop(driver_id="NOR", lap=10, stop_number=1, duration=21.0)]
    text = format_pitstops(None, stops, 7)
    assert "Round 7" in text


# --- format_laps_summary ---


def test_format_laps_summary_shows_drivers():
    laps = [
        LapTime(lap_number=1, driver_id="HAM", time="1:32.456", position=1),
        LapTime(lap_number=2, driver_id="HAM", time="1:31.999", position=1),
        LapTime(lap_number=1, driver_id="VER", time="1:32.789", position=2),
    ]
    text = format_laps_summary(_race(), laps)
    assert "HAM" in text
    assert "VER" in text
    assert "Best" in text
    assert "Avg" in text


def test_format_laps_summary_no_race():
    laps = [LapTime(lap_number=1, driver_id="LEC", time="1:33.111")]
    text = format_laps_summary(None, laps)
    assert "LEC" in text


# --- format_laps_by_lap ---


def test_format_laps_by_lap_shows_all_drivers_for_lap():
    laps = [
        LapTime(lap_number=3, driver_id="VER", time="1:31.999", position=1),
        LapTime(lap_number=3, driver_id="HAM", time="1:32.456", position=2),
        LapTime(lap_number=4, driver_id="VER", time="1:31.800", position=1),
    ]
    text = format_laps_by_lap(_race(), laps, 3, 10)
    assert "VER" in text
    assert "HAM" in text
    # Lap 4 drivers should not appear
    assert "1:31.800" not in text
    assert "Timing data from live feeds may occasionally be incomplete." in text


def test_format_laps_by_lap_shows_position():
    laps = [LapTime(lap_number=1, driver_id="NOR", time="1:30.000", position=3)]
    text = format_laps_by_lap(_race(), laps, 1, 52)
    assert "P3" in text
    assert "standing start lap" in text
    assert "Timing data from live feeds may occasionally be incomplete." not in text


def test_format_laps_by_lap_empty_lap():
    laps = [LapTime(lap_number=1, driver_id="HAM", time="1:32.000", position=1)]
    text = format_laps_by_lap(_race(), laps, 99, 52)
    assert "No data" in text


# --- format_laps_by_driver ---


def test_format_laps_by_driver_shows_driver_laps():
    laps = [LapTime(lap_number=i, driver_id="VER", time=f"1:3{i}.000") for i in range(1, 6)]
    text = format_laps_by_driver(_race(), laps, "VER", page=0)
    assert "VER" in text
    for i in range(1, 6):
        # format_laps_by_driver uses {:>3} padding: single-digit laps get 2 leading spaces
        assert f"Lap {i:>3}" in text
    assert "Timing data from live feeds may occasionally be incomplete." in text


def test_format_laps_by_driver_paginates():
    laps = [LapTime(lap_number=i, driver_id="HAM", time="1:30.000") for i in range(1, 25)]
    text_p0 = format_laps_by_driver(_race(), laps, "HAM", page=0)
    text_p1 = format_laps_by_driver(_race(), laps, "HAM", page=1)
    # Page 0: laps 1-20; page 1: laps 21-24
    assert "Lap  1" in text_p0 or "Lap 1" in text_p0
    assert "Lap 21" in text_p1 or "21" in text_p1
    assert "Page 1/2" in text_p0
    assert "Page 2/2" in text_p1


# --- format_laps_driver_picker ---


def test_format_laps_driver_picker_header():
    text = format_laps_driver_picker(_race())
    assert "Select" in text
    assert "Driver" in text
    assert "Monaco Grand Prix" in text


# --- _esc ---


def test_esc_underscores():
    assert _esc("max_verstappen") == r"max\_verstappen"


def test_esc_asterisk():
    assert _esc("*bold*") == r"\*bold\*"


def test_esc_backtick():
    assert _esc("`code`") == r"\`code\`"


def test_esc_square_bracket():
    assert _esc("[link]") == r"\[link]"


def test_esc_plain_text_unchanged():
    assert _esc("Hamilton") == "Hamilton"


def test_esc_combined():
    assert _esc("PIT_LANE_*OPEN*") == r"PIT\_LANE\_\*OPEN\*"


def test_format_pitstops_escapes_underscored_driver_id():
    stops = [PitStop(driver_id="de_vries", lap=10, stop_number=1, duration=22.0)]
    text = format_pitstops(_race(), stops, 5)
    assert r"de\_vries" in text


# ---------------------------------------------------------------------------
# _parse_lap_time_ms — private but complex parsing logic
# ---------------------------------------------------------------------------


def test_parse_lap_time_ms_valid_with_colon():
    """Standard format M:SS.mmm → milliseconds."""
    assert _parse_lap_time_ms("1:23.456") == 83456


def test_parse_lap_time_ms_sub_minute():
    """0:SS.mmm format."""
    assert _parse_lap_time_ms("0:59.999") == 59999


def test_parse_lap_time_ms_none_returns_none():
    assert _parse_lap_time_ms(None) is None


def test_parse_lap_time_ms_empty_string_returns_none():
    assert _parse_lap_time_ms("") is None


def test_parse_lap_time_ms_malformed_returns_none():
    assert _parse_lap_time_ms("abc") is None


def test_parse_lap_time_ms_no_colon_treated_as_seconds():
    """A plain number without colon is treated as seconds."""
    result = _parse_lap_time_ms("23.456")
    assert result == 23456


# ---------------------------------------------------------------------------
# _format_result_value — recursive formatter
# ---------------------------------------------------------------------------


def test_format_result_value_none():
    assert _format_result_value(None) is None


def test_format_result_value_string():
    assert _format_result_value("1:23.456") == "1:23.456"


def test_format_result_value_float():
    assert _format_result_value(1.234) == "1.234"


def test_format_result_value_list_of_strings():
    """List of sector times joined with ' / '."""
    assert _format_result_value(["23.1", "24.2", "25.3"]) == "23.1 / 24.2 / 25.3"


def test_format_result_value_list_with_none():
    """None items in list are filtered out."""
    assert _format_result_value(["23.1", None, "25.3"]) == "23.1 / 25.3"


def test_format_result_value_list_all_none():
    """All-None list returns None."""
    assert _format_result_value([None, None]) is None


def test_format_result_value_empty_list():
    assert _format_result_value([]) is None


def test_format_schedule_timezone_marker(monkeypatch):
    """It checks that the 'today' marker in format_schedule is timezone-aware."""
    from datetime import date, datetime, time

    from f1_bot.formatting.messages import format_schedule
    from f1_bot.models.race import Circuit, Race

    class MockDatetime:
        @classmethod
        def now(cls, tz=None):
            from datetime import UTC

            # Saturday June 20, 2026, 18:00 UTC (Taipei is Sunday June 21, 02:00, London is Saturday June 20, 19:00)
            utc_dt = datetime(2026, 6, 20, 18, 0, 0, tzinfo=UTC)
            if tz is not None:
                return utc_dt.astimezone(tz)
            return utc_dt

    monkeypatch.setattr("f1_bot.formatting.messages.datetime", MockDatetime)

    race = Race(
        season=2026,
        round=1,
        name="Test GP",
        circuit=Circuit(circuit_id="test", name="Test", locality="Test", country="Test"),
        date=date(2026, 6, 21),
        time=time(13, 0),
    )

    # Taipei user: race is on Sunday June 21, which matches today in Taipei -> show 🔜
    text_taipei = format_schedule([race], "Asia/Taipei")
    assert "🔜" in text_taipei

    # London user: race is on Sunday June 21, but today in London is Saturday June 20 -> do not show 🔜
    text_london = format_schedule([race], "Europe/London")
    assert "🔜" not in text_london
