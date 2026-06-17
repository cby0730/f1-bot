"""Tests for Settings: env_prefix, aliases, defaults."""

import pytest
from pydantic import ValidationError

from f1_bot.config import Settings


def test_settings_defaults(monkeypatch):
    """All non-required fields have usable defaults."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    s = Settings()
    assert s.telegram_bot_token == "test-token"
    assert s.sqlite_path == "f1bot.db"
    assert s.log_level == "INFO"
    assert s.log_format == "auto"


def test_settings_prefixed_fields(monkeypatch):
    """F1BOT_ prefix is applied to non-aliased fields."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.setenv("F1BOT_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("F1BOT_LOG_FORMAT", "json")
    monkeypatch.setenv("F1BOT_SQLITE_PATH", "/tmp/test.db")
    s = Settings()
    assert s.log_level == "DEBUG"
    assert s.log_format == "json"
    assert s.sqlite_path == "/tmp/test.db"


def test_settings_missing_token_raises(monkeypatch):
    """Missing TELEGRAM_BOT_TOKEN must fail validation."""
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    with pytest.raises((ValidationError, Exception)):
        Settings(_env_file=None)
