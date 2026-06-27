"""Tests for Settings: env_prefix, aliases, defaults."""

import pytest
from pydantic import ValidationError

from f1_bot.config import Settings


def test_settings_defaults(monkeypatch):
    """All non-required fields have usable defaults."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    s = Settings()
    assert s.telegram_bot_token == "test-token"
    assert s.database_url == "postgresql://mango:mango@localhost:31050/mango"
    assert s.log_level == "INFO"
    assert s.log_format == "auto"


def test_settings_prefixed_fields(monkeypatch):
    """F1BOT_ prefix is applied to non-aliased fields."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.setenv("F1BOT_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("F1BOT_LOG_FORMAT", "json")
    monkeypatch.setenv("F1BOT_DATABASE_URL", "postgresql://test:test@localhost:5432/test")
    s = Settings()
    assert s.log_level == "DEBUG"
    assert s.log_format == "json"
    assert s.database_url == "postgresql://test:test@localhost:5432/test"


def test_settings_missing_token_raises(monkeypatch):
    """Missing TELEGRAM_BOT_TOKEN must fail validation."""
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    with pytest.raises((ValidationError, Exception)):
        Settings(_env_file=None)


def test_settings_telegram_network(monkeypatch):
    """Test defaults and environment variable overrides for Telegram network settings."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")

    # Defaults
    s1 = Settings()
    assert s1.telegram_proxy is None
    assert s1.telegram_connect_timeout == 20.0
    assert s1.telegram_read_timeout == 20.0

    # Overrides
    monkeypatch.setenv("TELEGRAM_PROXY", "socks5://127.0.0.1:1080")
    monkeypatch.setenv("TELEGRAM_CONNECT_TIMEOUT", "15.5")
    monkeypatch.setenv("TELEGRAM_READ_TIMEOUT", "30.0")

    s2 = Settings()
    assert s2.telegram_proxy == "socks5://127.0.0.1:1080"
    assert s2.telegram_connect_timeout == 15.5
    assert s2.telegram_read_timeout == 30.0
