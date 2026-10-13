import asyncio
import pytest
from src.core.rate_limiter.sliding_window import RateLimiter

@pytest.mark.asyncio
async def test_rate_limiter_allowed_under_quota():
    limiter = RateLimiter(window_seconds=10, max_requests=3)
    assert await limiter.check_limit("client-1") is True
    assert await limiter.check_limit("client-1") is True
    assert await limiter.check_limit("client-1") is True

@pytest.mark.asyncio
async def test_rate_limiter_blocked_over_quota():
    limiter = RateLimiter(window_seconds=10, max_requests=2)
    assert await limiter.check_limit("client-2") is True
    assert await limiter.check_limit("client-2") is True
    assert await limiter.check_limit("client-2") is False

@pytest.mark.asyncio
async def test_rate_limiter_window_slide():
    limiter = RateLimiter(window_seconds=1, max_requests=1)
    assert await limiter.check_limit("client-3") is True
    assert await limiter.check_limit("client-3") is False
    # Wait for window to slide
    await asyncio.sleep(1.1)
    assert await limiter.check_limit("client-3") is True

@pytest.mark.asyncio
async def test_rate_limiter_evicts_expired_clients():
    limiter = RateLimiter(window_seconds=1, max_requests=2)
    assert await limiter.check_limit("client-temp") is True
    assert "client-temp" in limiter.store
    # After window expiration, calling evict_expired cleans inactive keys from memory
    await asyncio.sleep(1.1)
    evicted_count = limiter.evict_expired()
    assert evicted_count == 1
    assert "client-temp" not in limiter.store
