"""Tests for get_standings_round — the per-table cutoff read (needs dev DB).

Auto-skips when the container is down (via the pg_store fixture's Postgres guard).
"""

from f1_bot.models.constructor import Constructor, ConstructorStanding
from f1_bot.models.driver import Driver, DriverStanding


def _driver_standing():
    return DriverStanding(
        position=1,
        points=100.0,
        wins=3,
        driver=Driver(driver_id="max", given_name="Max", family_name="Verstappen"),
        constructor_name="Red Bull",
    )


def _constructor_standing():
    return ConstructorStanding(
        position=1,
        points=200.0,
        wins=5,
        constructor=Constructor(constructor_id="redbull", name="Red Bull"),
    )


async def test_get_standings_round_reflects_saved_round(repo):
    await repo.save_driver_standings(2026, [_driver_standing()], round_after=7)
    assert await repo.get_standings_round(2026, "drivers") == 7


async def test_get_standings_round_per_table_independence(repo):
    """The partial-sync guard: drivers at 15, constructors at 14 → distinct cutoffs."""
    await repo.save_driver_standings(2026, [_driver_standing()], round_after=15)
    await repo.save_constructor_standings(2026, [_constructor_standing()], round_after=14)

    assert await repo.get_standings_round(2026, "drivers") == 15
    assert await repo.get_standings_round(2026, "constructors") == 14


async def test_get_standings_round_empty_table_returns_none(repo):
    assert await repo.get_standings_round(2026, "drivers") is None
    assert await repo.get_standings_round(2026, "constructors") is None


async def test_get_standings_round_matches_latest_snapshot(repo):
    """Reads the SAME snapshot get_driver_standings returns (ORDER BY round_after DESC).

    Save round 5 then round 8; the cutoff must be 8, matching the standings list the
    read returns (both take the latest round_after).
    """
    early = _driver_standing()
    late = DriverStanding(
        position=1,
        points=180.0,
        wins=6,
        driver=Driver(driver_id="max", given_name="Max", family_name="Verstappen"),
        constructor_name="Red Bull",
    )
    await repo.save_driver_standings(2026, [early], round_after=5)
    await repo.save_driver_standings(2026, [late], round_after=8)

    assert await repo.get_standings_round(2026, "drivers") == 8
    standings = await repo.get_driver_standings(2026)
    # The returned snapshot is the round-8 one (180 pts), aligned with the cutoff.
    assert standings[0].points == 180.0
