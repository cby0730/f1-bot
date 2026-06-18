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
        while True:
            sleep_for = 0.0
            async with self._lock:
                now = time.monotonic()

                # Per-second throttle
                elapsed = now - self._last_call
                if elapsed < self._min_interval:
                    sleep_for = self._min_interval - elapsed
                elif self._per_period is not None:
                    # Per-period throttle (e.g. 500/hour or 30/minute)
                    cutoff = now - self._period
                    self._period_calls = [t for t in self._period_calls if t > cutoff]
                    if len(self._period_calls) >= self._per_period:
                        sleep_for = self._period_calls[0] + self._period - now
                        if sleep_for <= 0:
                            self._period_calls = self._period_calls[1:]
                            sleep_for = 0.0

                if sleep_for <= 0:
                    # All clear — record and return while still holding the lock
                    self._last_call = time.monotonic()
                    if self._per_period is not None:
                        self._period_calls.append(time.monotonic())
                    return

            # Lock released; sleep outside the lock then re-check state
            await asyncio.sleep(sleep_for)
