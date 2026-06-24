import pytest
import httpx
import time
from unittest.mock import Mock, AsyncMock
from src.core.retry.backoff import with_retry

@pytest.mark.asyncio
async def test_retry_success_first_time():
    action = AsyncMock(return_value="success")
    result = await with_retry(action, max_attempts=3, initial_delay_ms=10, backoff_multiplier=2)
    assert result == "success"
    assert action.call_count == 1

@pytest.mark.asyncio
async def test_retry_transient_error_then_success():
    calls = []
    
    async def action():
        calls.append(time.time())
        if len(calls) < 3:
            # Raise transient HTTPStatusError (500)
            request = httpx.Request("POST", "http://test")
            response = httpx.Response(500, request=request)
            raise httpx.HTTPStatusError("Transient Error", request=request, response=response)
        return "success"

    start_time = time.time()
    result = await with_retry(action, max_attempts=3, initial_delay_ms=50, backoff_multiplier=2)
    duration = time.time() - start_time
    
    assert result == "success"
    assert len(calls) == 3
    # First retry delay (attempt index 0): 50ms * 2^0 = 50ms
    # Second retry delay (attempt index 1): 50ms * 2^1 = 100ms
    # Total delay should be around 150ms (0.15s)
    assert duration >= 0.14

@pytest.mark.asyncio
async def test_retry_permanent_error_no_retry():
    calls = []
    
    async def action():
        calls.append(time.time())
        # Raise permanent HTTPStatusError (400)
        request = httpx.Request("POST", "http://test")
        response = httpx.Response(400, request=request)
        raise httpx.HTTPStatusError("Permanent Error", request=request, response=response)

    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await with_retry(action, max_attempts=3, initial_delay_ms=50, backoff_multiplier=2)
        
    assert exc_info.value.response.status_code == 400
    assert len(calls) == 1

@pytest.mark.asyncio
async def test_retry_network_error_exhausted():
    calls = []
    
    async def action():
        calls.append(time.time())
        request = httpx.Request("POST", "http://test")
        raise httpx.ConnectError("Connection failed", request=request)

    with pytest.raises(httpx.ConnectError):
        await with_retry(action, max_attempts=3, initial_delay_ms=10, backoff_multiplier=2)
        
    assert len(calls) == 3
