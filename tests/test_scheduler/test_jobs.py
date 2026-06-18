"""Tests for scheduler sync functions — verify each sync function calls the right API methods and saves to repo."""

from datetime import date, time
from unittest.mock import AsyncMock, MagicMock

from f1_bot.models.constructor import Constructor, ConstructorStanding
from f1_bot.models.driver import Driver, DriverStanding
from f1_bot.models.race import Circuit, Race
from f1_bot.scheduler.jobs import (
    sync_drivers_and_circuits,
    sync_schedule,
    sync_standings,
)


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


# --- sync_schedule ---


async def test_sync_schedule_saves_races():
    race = _sample_race()
    jolpica = MagicMock()
    jolpica.get_current_schedule = AsyncMock(return_value=[race])
    repo = MagicMock()
    repo.save_schedule = AsyncMock()
    repo.set_sync_metadata = AsyncMock()

    result = await sync_schedule(jolpica, repo)

    jolpica.get_current_schedule.assert_awaited_once()
    # race.season=2024, today().year=2026 — saved under both keys
    assert repo.save_schedule.await_count == 2
    repo.save_schedule.assert_any_await(2024, [race])
    assert len(result) == 1


async def test_sync_schedule_returns_empty_on_failure():
    jolpica = MagicMock()
    jolpica.get_current_schedule = AsyncMock(side_effect=Exception("network error"))
    repo = MagicMock()
    repo.save_schedule = AsyncMock()

    result = await sync_schedule(jolpica, repo)

    assert result == []
    repo.save_schedule.assert_not_awaited()


# --- sync_standings ---


async def test_sync_standings_saves_both():
    standings = _sample_driver_standings()
    c_standings = _sample_constructor_standings()
    jolpica = MagicMock()
    jolpica.get_driver_standings = AsyncMock(return_value=standings)
    jolpica.get_constructor_standings = AsyncMock(return_value=c_standings)
    repo = MagicMock()
    repo.save_driver_standings = AsyncMock()
    repo.save_constructor_standings = AsyncMock()
    repo.get_schedule_bounds = AsyncMock(return_value={"last_completed_round": 3})

    await sync_standings(jolpica, repo)

    jolpica.get_driver_standings.assert_awaited_once()
    repo.save_driver_standings.assert_awaited_once()
    jolpica.get_constructor_standings.assert_awaited_once()
    repo.save_constructor_standings.assert_awaited_once()


async def test_sync_standings_survives_exception():
    jolpica = MagicMock()
    jolpica.get_driver_standings = AsyncMock(side_effect=RuntimeError("timeout"))
    jolpica.get_constructor_standings = AsyncMock(side_effect=RuntimeError("timeout"))
    repo = MagicMock()
    repo.save_driver_standings = AsyncMock()
    repo.save_constructor_standings = AsyncMock()

    # Should not raise
    await sync_standings(jolpica, repo)
    repo.save_driver_standings.assert_not_awaited()
    repo.save_constructor_standings.assert_not_awaited()


# --- sync_drivers_and_circuits ---


async def test_sync_drivers_saves_drivers():
    driver = Driver(driver_id="ham", given_name="Lewis", family_name="Hamilton")
    jolpica = MagicMock()
    jolpica.get_drivers = AsyncMock(return_value=[driver])
    jolpica.get_circuits = AsyncMock(return_value=[])
    repo = MagicMock()
    repo.save_drivers = AsyncMock()
    repo.save_circuits = AsyncMock()

    await sync_drivers_and_circuits(jolpica, repo)

    repo.save_drivers.assert_awaited_once()
