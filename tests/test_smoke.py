"""
Full-stack smoke test: Jolpica API → sync function → PostgresStore → Repository.

Uses real HTTP calls to api.jolpi.ca and real Postgres (mango_pg container).
This exercises the actual persistence and schema logic.

Run with:
    uv run pytest tests/test_smoke.py -v
    uv run pytest -m integration -v      # run all integration tests
    uv run pytest -m "not integration"   # skip all integration tests (unit only)
"""

import datetime
import os

import pytest
import pytest_asyncio

from f1_bot.api.jolpica import JolpicaClient
from f1_bot.scheduler.jobs import sync_results_window, sync_schedule, sync_standings
from f1_bot.storage.postgres_store import PostgresStore
from f1_bot.storage.repository import Repository
from f1_bot.utils.rate_limiter import RateLimiter

pytestmark = pytest.mark.integration

_TEST_DATABASE_URL = os.environ.get(
    "F1BOT_DATABASE_URL", "postgresql://mango:mango@localhost:31055/mango"
)


@pytest_asyncio.fixture
async def stack():
    """Set up Repository + JolpicaClient; tear down after the test."""
    store = PostgresStore(_TEST_DATABASE_URL, min_pool=2, max_pool=5)
    try:
        await store.init()
    except Exception:
        pytest.skip("Postgres not available")
    jolpica = JolpicaClient(
        base_url="https://api.jolpi.ca/ergast/f1",
        rate_limiter=RateLimiter(per_second=2.0),
    )
    repo = Repository(store)

    yield repo, jolpica

    await jolpica.close()
    # Clean all tables
    async with store._pool.acquire() as conn:
        await conn.execute(
            """DO $$ DECLARE t TEXT;
            BEGIN FOR t IN
                SELECT tablename FROM pg_tables WHERE schemaname = 'public'
            LOOP EXECUTE 'TRUNCATE TABLE ' || quote_ident(t) || ' CASCADE';
            END LOOP; END $$;"""
        )
    await store.close()


async def test_schedule_flows_through_stack(stack):
    """sync_schedule writes to Postgres; Repository.get_schedule reads it back."""
    repo, jolpica = stack
    season = datetime.date.today().year

    races = await sync_schedule(jolpica, repo)

    assert len(races) > 0, "Expected at least one race in current season"
    stored_races = await repo.get_schedule(season)
    assert len(stored_races) > 0
    assert all(r.season == season for r in stored_races)
    assert all(r.name for r in stored_races)


async def test_next_race_is_upcoming_or_none(stack):
    """After schedule is loaded, get_next_race returns a future date or None."""
    repo, jolpica = stack
    season = datetime.date.today().year
    await sync_schedule(jolpica, repo)

    next_race = await repo.get_next_race(season)
    if next_race is not None:
        assert next_race.date >= datetime.date.today()


async def test_driver_standings_flow_through_stack(stack):
    """sync_standings writes standings; Repository reads them back."""
    repo, jolpica = stack
    season = datetime.date.today().year

    # Need schedule first for round_after
    await sync_schedule(jolpica, repo)
    await sync_standings(jolpica, repo)

    standings = await repo.get_driver_standings(season)
    assert len(standings) > 0, "Expected driver standings for current season"
    assert standings[0].position == 1
    assert standings[0].points > 0
    assert standings[0].driver.family_name


async def test_race_results_flow_through_stack(stack):
    """sync_results_window writes results; Repository reads them back."""
    repo, jolpica = stack
    season = datetime.date.today().year

    races = await sync_schedule(jolpica, repo)
    await sync_results_window(jolpica, repo, races, full=True)

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
