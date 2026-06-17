import asyncio
import time


class RateLimiter:
    """Token bucket rate limiter supporting per-second and per-period limits."""

    def __init__(
        self,
        per_second: float = 1.0,
        per_period: float | None = None,
        period: float = 3600.0,
    ) -> None:
        self._per_second = per_second
        self._min_interval = 1.0 / per_second
        self._last_call = 0.0

        self._per_period = per_period
        self._period = period
        self._period_calls: list[float] = []
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()

            # Per-second throttle
            elapsed = now - self._last_call
            if elapsed < self._min_interval:
                await asyncio.sleep(self._min_interval - elapsed)
            self._last_call = time.monotonic()

            # Per-period throttle (e.g. 500/hour or 30/minute)
            if self._per_period is not None:
                cutoff = time.monotonic() - self._period
                self._period_calls = [t for t in self._period_calls if t > cutoff]
                if len(self._period_calls) >= self._per_period:
                    sleep_for = self._period_calls[0] + self._period - time.monotonic()
                    if sleep_for > 0:
                        await asyncio.sleep(sleep_for)
                    self._period_calls = self._period_calls[1:]
                self._period_calls.append(time.monotonic())
