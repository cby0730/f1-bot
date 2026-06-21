import asyncio

import httpx
import structlog

from f1_bot.utils.rate_limiter import RateLimiter

log = structlog.get_logger(__name__)


class F1BotAPIError(Exception):
    """Base exception for all API errors."""


class APITimeoutError(F1BotAPIError):
    pass


class APIConnectionError(F1BotAPIError):
    pass


class APIServerError(F1BotAPIError):
    pass


class APIRateLimitError(F1BotAPIError):
    pass


class BaseAPIClient:
    """Async HTTP client with rate limiting, 429 handling, and structured logging."""

    def __init__(self, base_url: str, rate_limiter: RateLimiter) -> None:
        self._base_url = base_url.rstrip("/")
        self._rate_limiter = rate_limiter
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(30.0, connect=10.0),
            headers={"User-Agent": "f1-bot/0.0.6 (github.com/billy/f1-bot)"},
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def get(
        self, path: str, params: dict | None = None, *, _retried: bool = False
    ) -> dict | list:
        if not _retried:
            await self._rate_limiter.acquire()
        try:
            response = await self._client.get(path, params=params)
        except httpx.TimeoutException as e:
            log.error("api_timeout", path=path, error=str(e))
            raise APITimeoutError(path) from e
        except httpx.RequestError as e:
            log.error("api_network_error", path=path, error=str(e))
            raise APIConnectionError(path) from e

        if response.status_code == 429:
            retry_after_raw = response.headers.get("Retry-After")
            try:
                retry_after = int(retry_after_raw) if retry_after_raw else 60
            except ValueError:
                retry_after = 60
            log.warning("api_rate_limited", path=path, retry_after=retry_after)
            if _retried:
                raise APIRateLimitError(f"{path} rate-limited after retry")
            await asyncio.sleep(retry_after)
            return await self.get(path, params, _retried=True)

        if response.status_code >= 500:
            log.error("api_server_error", path=path, status=response.status_code)
            raise APIServerError(f"{path} returned {response.status_code}")

        response.raise_for_status()
        return response.json()
