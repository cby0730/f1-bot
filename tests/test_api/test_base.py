"""Tests for BaseAPIClient — rate limiting, error handling, 429 retry."""

import httpx
import pytest
from pytest_httpx import HTTPXMock

from f1_bot.api.base import (
    APIRateLimitError,
    APIServerError,
    BaseAPIClient,
)
from f1_bot.utils.rate_limiter import RateLimiter


def _make_client(base_url="https://example.com") -> BaseAPIClient:
    limiter = RateLimiter(per_second=100, per_period=10000, period=3600)
    return BaseAPIClient(base_url, limiter)


async def test_successful_get(httpx_mock: HTTPXMock):
    """A 200 response returns parsed JSON."""
    httpx_mock.add_response(json={"ok": True})
    client = _make_client()
    result = await client.get("/test")
    assert result == {"ok": True}
    await client.close()


async def test_404_raises_http_status_error(httpx_mock: HTTPXMock):
    """4xx responses surface as httpx.HTTPStatusError via raise_for_status()."""
    httpx_mock.add_response(status_code=404)
    client = _make_client()
    with pytest.raises(httpx.HTTPStatusError):
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
