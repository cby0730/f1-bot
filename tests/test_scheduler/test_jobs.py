"""Tests for scheduler jobs — verify each job calls the right API methods and saves to repo."""

from datetime import date, time
from unittest.mock import AsyncMock, MagicMock

from f1_bot.models.constructor import Constructor, ConstructorStanding
from f1_bot.models.driver import Driver, DriverStanding
from f1_bot.models.race import Circuit, Race
from f1_bot.models.results import QualifyingResult, RaceResult
from f1_bot.scheduler.jobs import (
    fetch_constructor_standings,
    fetch_driver_standings,
    fetch_last_qualifying,
    fetch_last_results,
    fetch_schedule,
)


def _make_context(jolpica, repo):
    """Build a minimal telegram ContextTypes mock with bot_data."""
    ctx = MagicMock()
    ctx.bot_data = {"jolpica": jolpica, "repo": repo}
    return ctx


def _sample_race():
    circuit = Circuit(
        circuit_id="monza", name="Autodromo Nazionale Monza", locality="Monza", country="Italy"
    )
    return Race(
        season=2024,
        round=3,
        name="Italian Grand Prix",
        circuit=circuit,
        date=date(2024, 9, 1),
        time=time(13, 0, 0),
    )


def _sample_driver_standings():
    driver = Driver(
        driver_id="hamilton", given_name="Lewis", family_name="Hamilton", nationality="British"
    )
    return [
        DriverStanding(position=1, points=100, wins=2, driver=driver, constructor_name="Mercedes")
    ]


def _sample_constructor_standings():
    constructor = Constructor(constructor_id="mercedes", name="Mercedes", nationality="German")
    return [ConstructorStanding(position=1, points=200, wins=4, constructor=constructor)]


def _sample_race_results():
    driver = Driver(
        driver_id="hamilton", given_name="Lewis", family_name="Hamilton", nationality="British"
    )
    constructor = Constructor(constructor_id="mercedes", name="Mercedes", nationality="German")
    return [
        RaceResult(
            position=1,
            grid=1,
            laps=53,
            status="Finished",
            points=25.0,
            driver=driver,
            constructor=constructor,
        )
    ]


def _sample_qualifying_results():
    driver = Driver(
        driver_id="hamilton", given_name="Lewis", family_name="Hamilton", nationality="British"
    )
    constructor = Constructor(constructor_id="mercedes", name="Mercedes", nationality="German")
    return [
        QualifyingResult(
            position=1,
            driver=driver,
            constructor=constructor,
            q1="1:20.0",
            q2="1:19.5",
            q3="1:18.9",
        )
    ]


# --- fetch_schedule ---


async def test_fetch_schedule_saves_races():
    race = _sample_race()
    jolpica = MagicMock()
    jolpica.get_current_schedule = AsyncMock(return_value=[race])
    repo = MagicMock()
    repo.save_schedule = AsyncMock()

    await fetch_schedule(_make_context(jolpica, repo))

    jolpica.get_current_schedule.assert_awaited_once()
    repo.save_schedule.assert_awaited_once_with(2024, [race])


async def test_fetch_schedule_skips_on_empty_response():
    jolpica = MagicMock()
    jolpica.get_current_schedule = AsyncMock(return_value=[])
    repo = MagicMock()
    repo.save_schedule = AsyncMock()

    await fetch_schedule(_make_context(jolpica, repo))

    repo.save_schedule.assert_not_awaited()


async def test_fetch_schedule_does_not_raise_on_api_error():
    jolpica = MagicMock()
    jolpica.get_current_schedule = AsyncMock(side_effect=Exception("network error"))
    repo = MagicMock()
    repo.save_schedule = AsyncMock()

    # Should not raise — jobs must be resilient
    await fetch_schedule(_make_context(jolpica, repo))
    repo.save_schedule.assert_not_awaited()


# --- fetch_driver_standings ---


async def test_fetch_driver_standings_saves_standings():
    standings = _sample_driver_standings()
    jolpica = MagicMock()
    jolpica.get_driver_standings = AsyncMock(return_value=standings)
    repo = MagicMock()
    repo.save_driver_standings = AsyncMock()

    await fetch_driver_standings(_make_context(jolpica, repo))

    jolpica.get_driver_standings.assert_awaited_once()
    repo.save_driver_standings.assert_awaited_once()
    # Verify the standings list was passed correctly
    call_args = repo.save_driver_standings.call_args
    assert call_args[0][1] == standings


async def test_fetch_driver_standings_survives_exception():
    jolpica = MagicMock()
    jolpica.get_driver_standings = AsyncMock(side_effect=RuntimeError("timeout"))
    repo = MagicMock()
    repo.save_driver_standings = AsyncMock()

    await fetch_driver_standings(_make_context(jolpica, repo))
    repo.save_driver_standings.assert_not_awaited()


# --- fetch_constructor_standings ---


async def test_fetch_constructor_standings_saves_standings():
    standings = _sample_constructor_standings()
    jolpica = MagicMock()
    jolpica.get_constructor_standings = AsyncMock(return_value=standings)
    repo = MagicMock()
    repo.save_constructor_standings = AsyncMock()

    await fetch_constructor_standings(_make_context(jolpica, repo))

    jolpica.get_constructor_standings.assert_awaited_once()
    repo.save_constructor_standings.assert_awaited_once()
    call_args = repo.save_constructor_standings.call_args
    assert call_args[0][1] == standings


async def test_fetch_constructor_standings_survives_exception():
    jolpica = MagicMock()
    jolpica.get_constructor_standings = AsyncMock(side_effect=ConnectionError("refused"))
    repo = MagicMock()
    repo.save_constructor_standings = AsyncMock()

    await fetch_constructor_standings(_make_context(jolpica, repo))
    repo.save_constructor_standings.assert_not_awaited()


# --- fetch_last_results ---


async def test_fetch_last_results_saves_results():
    race = _sample_race()
    results = _sample_race_results()
    jolpica = MagicMock()
    jolpica.get_race_results = AsyncMock(return_value=(race, results))
    repo = MagicMock()
    repo.save_race_results = AsyncMock()

    await fetch_last_results(_make_context(jolpica, repo))

    jolpica.get_race_results.assert_awaited_once()
    repo.save_race_results.assert_awaited_once_with(2024, 3, results)


async def test_fetch_last_results_skips_when_none():
    jolpica = MagicMock()
    jolpica.get_race_results = AsyncMock(return_value=(None, None))
    repo = MagicMock()
    repo.save_race_results = AsyncMock()

    await fetch_last_results(_make_context(jolpica, repo))
    repo.save_race_results.assert_not_awaited()


# --- fetch_last_qualifying ---


async def test_fetch_last_qualifying_saves_results():
    race = _sample_race()
    results = _sample_qualifying_results()
    jolpica = MagicMock()
    jolpica.get_qualifying_results = AsyncMock(return_value=(race, results))
    repo = MagicMock()
    repo.save_qualifying_results = AsyncMock()

    await fetch_last_qualifying(_make_context(jolpica, repo))

    jolpica.get_qualifying_results.assert_awaited_once()
    repo.save_qualifying_results.assert_awaited_once_with(2024, 3, results)


async def test_fetch_last_qualifying_survives_exception():
    jolpica = MagicMock()
    jolpica.get_qualifying_results = AsyncMock(side_effect=Exception("500"))
    repo = MagicMock()
    repo.save_qualifying_results = AsyncMock()

    await fetch_last_qualifying(_make_context(jolpica, repo))
    repo.save_qualifying_results.assert_not_awaited()
