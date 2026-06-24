import asyncio
import socket
import pytest
import httpx

PROXY_URL = "http://localhost:8000"

def is_proxy_running():
    try:
        # Check if port 8000 is open on localhost
        with socket.create_connection(("localhost", 8000), timeout=0.5):
            return True
    except OSError:
        return False

# Skip integration tests if the proxy-service container is not running
pytestmark = pytest.mark.skipif(
    not is_proxy_running(),
    reason="Integration tests require the proxy service to be running on localhost:8000 (docker-compose up)"
)

@pytest.mark.asyncio
async def test_integration_rate_limiting():
    """
    Fire 20 concurrent requests and assert that rate limiting (429) is triggered
    for requests exceeding the configured limit.
    """
    async def send_request(i):
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{PROXY_URL}/api/proxy/data", 
                    json={"test": i, "fail_rate": 0.0},
                    timeout=5.0
                )
                return response.status_code
            except Exception as e:
                return str(e)
                
    tasks = [send_request(i) for i in range(20)]
    results = await asyncio.gather(*tasks)
    
    success_count = sum(1 for status in results if status == 200)
    rate_limited_count = sum(1 for status in results if status == 429)
    
    # Out of 20 concurrent requests:
    # Up to 10 (RATE_LIMIT_MAX_REQUESTS) should succeed, and the rest should return 429
    assert success_count <= 10
    assert rate_limited_count >= 10

@pytest.mark.asyncio
async def test_integration_circuit_breaker_and_recovery():
    """
    Send failing requests to trip the circuit breaker and assert 503 response.
    """
    async with httpx.AsyncClient() as client:
        # We need to send CB_FAILURE_THRESHOLD (5) requests that return 5xx errors.
        # We do this by passing fail_rate=1.0 in the payload.
        failures = 0
        for i in range(5):
            try:
                response = await client.post(
                    f"{PROXY_URL}/api/proxy/data",
                    json={"test": f"fail-{i}", "fail_rate": 1.0},
                    timeout=5.0
                )
                if response.status_code == 500:
                    failures += 1
                elif response.status_code == 429:
                    # If rate limited, sleep briefly and retry
                    await asyncio.sleep(1.0)
                    response = await client.post(
                        f"{PROXY_URL}/api/proxy/data",
                        json={"test": f"fail-{i}-retry", "fail_rate": 1.0},
                        timeout=5.0
                    )
                    if response.status_code == 500:
                        failures += 1
            except Exception:
                failures += 1
                
        # Now the circuit breaker state should be OPEN.
        # The next request should immediately fail-fast with a 503 status code.
        response = await client.post(
            f"{PROXY_URL}/api/proxy/data",
            json={"test": "probe-open", "fail_rate": 0.0},
            timeout=5.0
        )
        assert response.status_code == 503
        data = response.json()
        assert "message" in data
        assert "circuit open" in data["message"].lower()
