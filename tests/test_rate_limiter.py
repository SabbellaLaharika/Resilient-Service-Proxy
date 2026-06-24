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
