"""Tests must not share the bot's database — pytest TRUNCATEs after every test."""

import os
from urllib.parse import urlparse

_TEST_DATABASE_URL = os.environ.get(
    "F1BOT_TEST_DATABASE_URL", "postgresql://mango:mango@localhost:31055/mango_test"
)


def test_test_database_is_not_the_bot_database():
    """Sharing ``mango`` with the bot lets pytest empty /standings for a live process."""
    path = urlparse(_TEST_DATABASE_URL).path.rstrip("/")
    assert path not in {"", "/mango"}
