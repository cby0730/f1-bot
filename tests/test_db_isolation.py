"""Tests must never run against a database anyone else owns.

Origin: commit ``ede12bf`` fixed a real incident where the pytest fixtures'
TRUNCATE emptied the *bot's* database, so a running bot answered /standings
with "no data". The original guard compared two module constants in conftest.

Those constants are gone -- the test database is now a throwaway container --
but the guard still earns its place, for a reason the original version could
not cover: it asserts against the URL the ``pg_url`` fixture *actually hands
out*. ``tests/test_e2e.py`` used to carry its own ``_TEST_DATABASE_URL`` and
TRUNCATE the whole database through it, completely bypassing conftest. A guard
that only reads conftest's constants cannot see a bypass like that; one that
reads the fixture can.
"""

from urllib.parse import urlparse

from conftest import PG_IMAGE

# Ports a human would plausibly point at a database they care about: the
# PostgreSQL default, and this project's dev container (docker-compose.dev.yml).
_OWNED_PORTS = {5432, 31055}


def test_pg_url_is_a_throwaway_container(pg_url):
    """The DB under test must be container-assigned, not a host anyone owns."""
    parsed = urlparse(pg_url)

    assert parsed.scheme == "postgresql", (
        f"asyncpg needs a bare postgresql:// URL, got {parsed.scheme!r} -- "
        "pass driver=None to get_connection_url()"
    )
    assert parsed.hostname in {"localhost", "127.0.0.1"}, (
        f"test database is on a remote host {parsed.hostname!r}: {pg_url!r}"
    )
    assert parsed.port not in _OWNED_PORTS, (
        f"test database is on port {parsed.port}, which belongs to a real "
        f"database, not a throwaway container: {pg_url!r}. The fixtures "
        "TRUNCATE every public table after each test."
    )


def test_every_db_test_shares_the_one_fixture(pg_store, pg_url):
    """No test may reach a database except through ``pg_url``.

    ``pg_store`` is built from ``pg_url``; asserting they agree is what makes
    a second, hardcoded URL elsewhere in the suite impossible to hide.
    """
    assert pg_store._database_url == pg_url, (
        f"pg_store connected to {pg_store._database_url!r} but the fixture "
        f"hands out {pg_url!r} -- something is building its own connection string"
    )


def test_container_image_is_pinned():
    """An unpinned image would silently change the PostgreSQL major version."""
    assert ":" in PG_IMAGE and not PG_IMAGE.endswith(":latest"), (
        f"pin the postgres image to a major version, got {PG_IMAGE!r}"
    )
