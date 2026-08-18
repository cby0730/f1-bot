"""Shared fixtures for all test modules."""

import os  # noqa: I001
import re
import subprocess
from urllib.parse import urlparse

os.environ["PTB_TIMEDELTA"] = "1"

import pytest
import pytest_asyncio

from f1_bot.storage.postgres_store import PostgresStore
from f1_bot.storage.repository import Repository

# Separate from the bot's ``mango`` DB: fixtures TRUNCATE public tables after
# every test, which would empty /standings for a live process on the same DB.
TEST_DATABASE_URL = os.environ.get(
    "F1BOT_TEST_DATABASE_URL",
    "postgresql://mango:mango@localhost:31055/mango_test",
)
_ADMIN_URL = os.environ.get(
    "F1BOT_DATABASE_URL",
    "postgresql://mango:mango@localhost:31055/mango",
)
_DB_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _ensure_test_database() -> None:
    """CREATE DATABASE mango_test if needed. No-op when Postgres is down."""
    test = urlparse(TEST_DATABASE_URL)
    db_name = (test.path or "").lstrip("/")
    admin = urlparse(_ADMIN_URL)
    admin_db = (admin.path or "/mango").lstrip("/") or "mango"
    if not db_name or not _DB_NAME.fullmatch(db_name) or db_name == admin_db:
        return

    env = {**os.environ, "PGPASSWORD": admin.password or "mango"}
    psql = [
        "psql",
        "-h",
        admin.hostname or "localhost",
        "-p",
        str(admin.port or 5432),
        "-U",
        admin.username or "mango",
        "-d",
        admin_db,
    ]
    check = subprocess.run(  # noqa: S603
        [*psql, "-tAc", f"SELECT 1 FROM pg_database WHERE datname='{db_name}'"],  # noqa: S608
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if check.returncode != 0 or check.stdout.strip() == "1":
        return
    subprocess.run(  # noqa: S603
        [*psql, "-c", f'CREATE DATABASE "{db_name}" OWNER mango'],  # noqa: S608
        env=env,
        capture_output=True,
        check=False,
    )


def pytest_configure(config):
    _ensure_test_database()


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture
async def pg_store():
    """PostgresStore for tests — creates schema, yields, then drops all tables."""
    store = PostgresStore(TEST_DATABASE_URL, min_pool=2, max_pool=5)
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
