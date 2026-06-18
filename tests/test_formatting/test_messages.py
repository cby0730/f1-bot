"""Tests for message formatters — verify key content appears in output."""

from datetime import date, time

from f1_bot.formatting.messages import (
    _esc,
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


def _driver(driver_id="hamilton", given="Lewis", family="Hamilton", nat="British"):
    return Driver(driver_id=driver_id, given_name=given, family_name=family, nationality=nat)


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
    assert "Hamilton" in text
    assert "1:23:45" in text


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
    assert "⚡" in text


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


def test_format_laps_by_lap_shows_position():
    laps = [LapTime(lap_number=1, driver_id="NOR", time="1:30.000", position=3)]
    text = format_laps_by_lap(_race(), laps, 1, 52)
    assert "P3" in text


def test_format_laps_by_lap_empty_lap():
    laps = [LapTime(lap_number=1, driver_id="HAM", time="1:32.000", position=1)]
    text = format_laps_by_lap(_race(), laps, 99, 52)
    assert "No data" in text


# --- format_laps_by_driver ---


def test_format_laps_by_driver_shows_driver_laps():
    laps = [
        LapTime(lap_number=i, driver_id="VER", time=f"1:3{i}.000") for i in range(1, 6)
    ]
    text = format_laps_by_driver(_race(), laps, "VER", page=0)
    assert "VER" in text
    for i in range(1, 6):
        # format_laps_by_driver uses {:>3} padding: single-digit laps get 2 leading spaces
        assert f"Lap {i:>3}" in text


def test_format_laps_by_driver_paginates():
    laps = [
        LapTime(lap_number=i, driver_id="HAM", time="1:30.000") for i in range(1, 25)
    ]
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
