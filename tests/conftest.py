"""Shared fixtures for all test modules."""

import os

import pytest
import pytest_asyncio

from f1_bot.storage.postgres_store import PostgresStore
from f1_bot.storage.repository import Repository

_TEST_DATABASE_URL = os.environ.get(
    "F1BOT_DATABASE_URL", "postgresql://mango:mango@localhost:31050/mango"
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture
async def pg_store():
    """PostgresStore for tests — creates schema, yields, then drops all tables."""
    store = PostgresStore(_TEST_DATABASE_URL, min_pool=2, max_pool=5)
    try:
        await store.init()
    except Exception:
        pytest.skip("Postgres not available")
    yield store
    # Clean all tables after each test
    async with store._pool.acquire() as conn:
        await conn.execute(
            """DO $$ DECLARE t TEXT;
            BEGIN FOR t IN
                SELECT tablename FROM pg_tables WHERE schemaname = 'public'
            LOOP EXECUTE 'TRUNCATE TABLE ' || quote_ident(t) || ' CASCADE';
            END LOOP; END $$;"""
        )
    await store.close()


@pytest_asyncio.fixture
async def repo(pg_store):
    return Repository(pg_store)


# --- Sample data fixtures ---


@pytest.fixture
def sample_race_dict():
    return {
        "season": 2024,
        "round": 5,
        "name": "Monaco Grand Prix",
        "url": None,
        "circuit": {
            "circuit_id": "monaco",
            "name": "Circuit de Monaco",
            "locality": "Monte-Carlo",
            "country": "Monaco",
            "lat": 43.7347,
            "lng": 7.4205,
            "url": None,
        },
        "date": "2024-05-26",
        "time": "13:00:00",
        "gmt_offset": None,
    }
