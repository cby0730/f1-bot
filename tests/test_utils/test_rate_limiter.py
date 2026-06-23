import asyncio
import time

import pytest

from f1_bot.utils.rate_limiter import RateLimiter


@pytest.mark.asyncio
async def test_acquire_returns_immediately_with_generous_limits():
    rl = RateLimiter(per_second=100.0)
    start = time.monotonic()
    await rl.acquire()
    assert time.monotonic() - start < 0.1


@pytest.mark.asyncio
async def test_per_second_throttle_spaces_calls():
    rl = RateLimiter(per_second=10.0)  # min_interval = 0.1s
    await rl.acquire()
    start = time.monotonic()
    await rl.acquire()
    elapsed = time.monotonic() - start
    assert elapsed >= 0.08  # allow small clock jitter


@pytest.mark.asyncio
async def test_concurrent_acquires_do_not_serialise_behind_per_period_sleep():
    """Key regression test: two concurrent callers must not each wait a full period.
    With the old lock-during-sleep implementation, the second caller would block
    for the full sleep_for duration held by the first."""
    rl = RateLimiter(per_second=1000.0, per_period=1, period=0.2)

    # Exhaust the per-period bucket (1 call allowed per 0.2s)
    await rl.acquire()

    start = time.monotonic()
    # Two concurrent calls — the lock must be released during the sleep
    results = await asyncio.gather(
        rl.acquire(),
        rl.acquire(),
        return_exceptions=True,
    )
    elapsed = time.monotonic() - start

    assert all(r is None for r in results), f"Unexpected errors: {results}"
    # If the lock were held during sleep, elapsed would be ~2 * 0.2 = 0.4s.
    # With the fix, both callers sleep concurrently so elapsed ≈ 0.2–0.3s.
    assert elapsed < 0.45, f"Callers appeared to serialise: elapsed={elapsed:.3f}s"


@pytest.mark.asyncio
async def test_per_period_throttle_blocks_after_limit():
    rl = RateLimiter(per_second=1000.0, per_period=2, period=0.3)
    await rl.acquire()
    await rl.acquire()
    # Third call must wait until the period window slides
    start = time.monotonic()
    await rl.acquire()
    elapsed = time.monotonic() - start
    assert elapsed >= 0.25


@pytest.mark.asyncio
async def test_no_per_period_limit_is_respected():
    rl = RateLimiter(per_second=1000.0)  # no per_period
    for _ in range(10):
        await rl.acquire()  # should not raise or block meaningfully
