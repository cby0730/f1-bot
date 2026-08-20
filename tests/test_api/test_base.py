"""Tests for BaseAPIClient — rate limiting, error handling, 429 retry."""

from unittest.mock import AsyncMock

import httpx
import pytest
from pytest_httpx import HTTPXMock

from f1_bot.api.base import (
    APIClientError,
    APIRateLimitError,
    APIServerError,
    BaseAPIClient,
    F1BotAPIError,
)
from f1_bot.utils.rate_limiter import RateLimiter


def _make_client(base_url="https://example.com") -> BaseAPIClient:
    limiter = RateLimiter(per_second=100, per_period=10000, period=3600)
    return BaseAPIClient(base_url, limiter)


async def test_user_agent_follows_installed_package_version(monkeypatch):
    """User-Agent must read the installed dist version, not a copied literal.

    WHY: pyproject.toml and this header previously drifted (the 0.3.0 bump
    missed the User-Agent). A hardcoded string stays green until the next
    bump; patching the metadata lookup fails immediately if the header is
    a literal again.
    """

    def fake_version(name: str) -> str:
        assert name == "f1-bot"
        return "9.9.9"

    monkeypatch.setattr("f1_bot.api.base.package_version", fake_version)
    client = _make_client()
    try:
        assert client._client.headers["user-agent"] == "f1-bot/9.9.9 (github.com/cby0730/f1-bot)"
    finally:
        await client.close()


async def test_successful_get(httpx_mock: HTTPXMock):
    """A 200 response returns parsed JSON."""
    httpx_mock.add_response(json={"ok": True})
    client = _make_client()
    result = await client.get("/test")
    assert result == {"ok": True}
    await client.close()


async def test_404_raises_api_client_error(httpx_mock: HTTPXMock):
    """4xx responses are caught and re-raised as APIClientError."""
    httpx_mock.add_response(status_code=404)
    client = _make_client()
    with pytest.raises(APIClientError):
        await client.get("/test")
    await client.close()


async def test_api_client_error_is_subclass_of_f1bot_api_error(httpx_mock: HTTPXMock):
    """APIClientError inherits from F1BotAPIError for unified exception handling."""
    httpx_mock.add_response(status_code=404)
    client = _make_client()
    with pytest.raises(F1BotAPIError):
        await client.get("/test")
    await client.close()


async def test_500_raises_api_server_error(httpx_mock: HTTPXMock):
    """5xx responses are caught before raise_for_status and re-raised as APIServerError."""
    httpx_mock.add_response(status_code=500)
    client = _make_client()
    with pytest.raises(APIServerError):
        await client.get("/test")
    await client.close()


async def test_with_query_params(httpx_mock: HTTPXMock):
    """Params are forwarded to the request."""
    httpx_mock.add_response(json=[1, 2, 3])
    client = _make_client()
    result = await client.get("/items", params={"limit": "10"})
    assert result == [1, 2, 3]
    await client.close()


async def test_429_single_retry_succeeds(httpx_mock: HTTPXMock):
    """A 429 followed by 200 should return the successful response."""
    httpx_mock.add_response(status_code=429, headers={"Retry-After": "0"})
    httpx_mock.add_response(json={"ok": True})
    client = _make_client()
    result = await client.get("/test")
    assert result == {"ok": True}
    await client.close()


async def test_429_double_raises_api_rate_limit_error(httpx_mock: HTTPXMock):
    """Two consecutive 429 responses must raise APIRateLimitError, not recurse infinitely."""
    httpx_mock.add_response(status_code=429, headers={"Retry-After": "0"})
    httpx_mock.add_response(status_code=429, headers={"Retry-After": "0"})
    client = _make_client()
    with pytest.raises(APIRateLimitError):
        await client.get("/test")
    await client.close()


async def test_429_retry_does_not_double_acquire_rate_limiter(httpx_mock: HTTPXMock):
    """On a 429→200 sequence, rate limiter acquire() must be called exactly once."""
    httpx_mock.add_response(status_code=429, headers={"Retry-After": "0"})
    httpx_mock.add_response(json={"ok": True})
    client = _make_client()
    client._rate_limiter.acquire = AsyncMock()
    await client.get("/test")
    assert client._rate_limiter.acquire.await_count == 1
    await client.close()


async def test_network_error_raises_api_connection_error(httpx_mock: HTTPXMock):
    """An httpx.RequestError (like ReadError or ProtocolError) raises APIConnectionError."""
    httpx_mock.add_exception(httpx.ReadError("connection reset"))
    client = _make_client()
    from f1_bot.api.base import APIConnectionError

    with pytest.raises(APIConnectionError):
        await client.get("/test")
    await client.close()


async def test_429_retry_after_http_date(httpx_mock: HTTPXMock):
    """A 429 with an HTTP-date Retry-After should fallback to 60s sleep and retry."""
    httpx_mock.add_response(
        status_code=429, headers={"Retry-After": "Wed, 21 Oct 2015 07:28:00 GMT"}
    )
    httpx_mock.add_response(json={"ok": True})
    client = _make_client()

    from unittest.mock import patch

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await client.get("/test")
        assert result == {"ok": True}
        mock_sleep.assert_awaited_once_with(60)
    await client.close()


async def test_429_retry_after_empty(httpx_mock: HTTPXMock):
    """A 429 with an empty Retry-After should fallback to 60s sleep and retry."""
    httpx_mock.add_response(status_code=429, headers={"Retry-After": ""})
    httpx_mock.add_response(json={"ok": True})
    client = _make_client()

    from unittest.mock import patch

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await client.get("/test")
        assert result == {"ok": True}
        mock_sleep.assert_awaited_once_with(60)
    await client.close()
