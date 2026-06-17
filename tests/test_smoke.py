"""
Full-stack smoke test: Jolpica API → fetch job → SQLiteStore → Repository.

Uses real HTTP calls to api.jolpi.ca and real SQLite (tmp_path).
This exercises the actual persistence and schema logic.

Run with:
    uv run pytest tests/test_smoke.py -v
    uv run pytest -m integration -v      # run all integration tests
    uv run pytest -m "not integration"   # skip all integration tests (unit only)
"""

import datetime

import pytest
import pytest_asyncio

from f1_bot.api.jolpica import JolpicaClient
from f1_bot.scheduler.jobs import fetch_driver_standings, fetch_last_results, fetch_schedule
from f1_bot.storage.repository import Repository
from f1_bot.storage.sqlite_store import SQLiteStore
from f1_bot.utils.rate_limiter import RateLimiter

pytestmark = pytest.mark.integration


class _FakeContext:
    """Minimal stub that mimics python-telegram-bot's bot_data dict access."""

    def __init__(self, bot_data: dict) -> None:
        self.bot_data = bot_data


@pytest_asyncio.fixture
async def stack(tmp_path):
    """Set up Repository + JolpicaClient; tear down after the test."""
    sqlite = SQLiteStore(str(tmp_path / "smoke.db"))
    await sqlite.init()
    jolpica = JolpicaClient(
        base_url="https://api.jolpi.ca/ergast/f1",
        rate_limiter=RateLimiter(per_second=2.0),
    )
    repo = Repository(sqlite)
    ctx = _FakeContext({"jolpica": jolpica, "repo": repo})

    yield repo, ctx

    await jolpica.close()
    await sqlite.close()


async def test_schedule_flows_through_stack(stack):
    """fetch_schedule job writes to SQLite; Repository.get_schedule reads it back."""
    repo, ctx = stack
    season = datetime.date.today().year

    await fetch_schedule(ctx)

    races = await repo.get_schedule(season)
    assert len(races) > 0, "Expected at least one race in current season"
    assert all(r.season == season for r in races)
    assert all(r.name for r in races)


async def test_next_race_is_upcoming_or_none(stack):
    """After schedule is loaded, get_next_race returns a future date or None."""
    repo, ctx = stack
    season = datetime.date.today().year
    await fetch_schedule(ctx)

    next_race = await repo.get_next_race(season)
    if next_race is not None:
        assert next_race.date >= datetime.date.today()


async def test_driver_standings_flow_through_stack(stack):
    """fetch_driver_standings job writes standings; Repository reads them back."""
    repo, ctx = stack
    season = datetime.date.today().year

    await fetch_driver_standings(ctx)

    standings = await repo.get_driver_standings(season)
    assert len(standings) > 0, "Expected driver standings for current season"
    assert standings[0].position == 1
    assert standings[0].points > 0
    assert standings[0].driver.family_name


async def test_race_results_flow_through_stack(stack):
    """fetch_last_results job writes results; Repository reads them back."""
    repo, ctx = stack
    season = datetime.date.today().year

    # Need schedule first to know how many rounds to search
    await fetch_schedule(ctx)
    races = await repo.get_schedule(season)
    await fetch_last_results(ctx)

    found = None
    for round_num in range(len(races), 0, -1):
        results = await repo.get_race_results(season, round_num)
        if results:
            found = results
            break

    assert found is not None, "Expected at least one completed race with results"
    assert len(found) > 0
    assert found[0]["position"] == 1
    assert found[0]["driver"]["family_name"]
