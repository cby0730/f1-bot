"""Tests must not share the bot's database — pytest TRUNCATEs after every test.

Sharing the bot's database empties live data (e.g. /standings replies "no data").
"""

from urllib.parse import urlparse

from conftest import _ADMIN_URL, TEST_DATABASE_URL

_PG_DEFAULT_PORT = 5432


def _database_identity(url: str) -> tuple[str | None, int, str]:
    """Return (host, port, database name) for a PostgreSQL URL."""
    parsed = urlparse(url)
    port = parsed.port if parsed.port is not None else _PG_DEFAULT_PORT
    db_name = (parsed.path or "").rstrip("/").lstrip("/")
    return parsed.hostname, port, db_name


def test_test_database_is_not_the_bot_database():
    """Sharing the bot DB with pytest lets TRUNCATE empty /standings for a live process."""
    test_id = _database_identity(TEST_DATABASE_URL)
    admin_id = _database_identity(_ADMIN_URL)
    _, _, test_db = test_id
    assert test_db, (
        f"test database name is empty: {TEST_DATABASE_URL!r} vs bot/admin {_ADMIN_URL!r}"
    )
    assert test_id != admin_id, (
        f"test database {TEST_DATABASE_URL!r} collides with bot/admin {_ADMIN_URL!r}"
    )
