"""Shared fixtures for all test modules."""

import os  # noqa: I001

os.environ["PTB_TIMEDELTA"] = "1"

import pytest
import pytest_asyncio

from f1_bot.storage.postgres_store import PostgresStore
from f1_bot.storage.repository import Repository

# Keep in step with docker-compose.yml (production). They are allowed to differ
# briefly during a major upgrade -- production needs a dump/restore, this does
# not -- but a lasting gap means tests stop covering the server the bot runs on.
PG_IMAGE = "postgres:18-alpine"


@pytest.fixture(scope="session")
def pg_url():
    """A throwaway PostgreSQL container, shared by every test that needs a DB.

    Session-scoped so the ~9s startup is paid once, but *lazily* started:
    pytest only builds a fixture when a test actually requests it, so the
    DB-free suites (``tests/test_i18n/``, most of ``tests/test_handlers/``)
    never launch a container. Nothing may request this at collection time.

    Replaces the old ``F1BOT_TEST_DATABASE_URL`` + ``_ensure_test_database()``
    pair, which required a postgres client on the host and a DB listening on a
    fixed port 31055.
    """
    from testcontainers.community.postgres import PostgresContainer

    with PostgresContainer(PG_IMAGE) as pg:
        # The default returns a SQLAlchemy URL (``postgresql+psycopg2://``),
        # which asyncpg rejects. ``driver=None`` yields bare ``postgresql://``.
        yield pg.get_connection_url(driver=None)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture
async def pg_store(pg_url):
    """PostgresStore for tests — creates schema, yields, then truncates.

    Function-scoped on purpose, even though the container is not: each test
    gets a fresh ``PostgresStore`` (and via ``repo``, a fresh
    ``Repository._laps_cache``). Only ``pg_url`` is shared.
    """
    store = PostgresStore(pg_url, min_pool=2, max_pool=5)
    await store.init()
    yield store
    # Clean all tables after each test. RESTART IDENTITY matters now that the
    # container outlives the test: the two SERIAL keys (schedule_audit_log.id,
    # notification_subscriptions.id) would otherwise climb across the session.
    async with store._pool.acquire() as conn:
        await conn.execute(
            """DO $$ DECLARE t TEXT;
            BEGIN FOR t IN
                SELECT tablename FROM pg_tables WHERE schemaname = 'public'
            LOOP EXECUTE 'TRUNCATE TABLE ' || quote_ident(t) || ' RESTART IDENTITY CASCADE';
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
