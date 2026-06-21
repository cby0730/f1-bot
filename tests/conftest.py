"""Shared fixtures for all test modules."""

import pytest
import pytest_asyncio
from f1_bot.storage.repository import Repository
from f1_bot.storage.sqlite_store import SQLiteStore


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture
async def sqlite_store(tmp_path):
    """In-memory SQLite store using a temp file."""
    store = SQLiteStore(str(tmp_path / "test.db"))
    await store.init()
    yield store
    await store.close()


@pytest_asyncio.fixture
async def repo(sqlite_store):
    return Repository(sqlite_store)


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
