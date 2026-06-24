import asyncio
import pytest
from src.core.circuit_breaker.state_machine import CircuitBreaker, CircuitBreakerOpenException, CBState

@pytest.mark.asyncio
async def test_circuit_breaker_transitions_to_open():
    cb = CircuitBreaker(failure_threshold=3, reset_timeout_sec=1)
    
    async def failing_action():
        raise ValueError("Error")
        
    async def successful_action():
        return "OK"

    # Consecutive failures
    with pytest.raises(ValueError):
        await cb.execute(failing_action)
    assert cb.state == CBState.CLOSED
    
    with pytest.raises(ValueError):
        await cb.execute(failing_action)
    assert cb.state == CBState.CLOSED

    # Third failure trips the circuit
    with pytest.raises(ValueError):
        await cb.execute(failing_action)
    assert cb.state == CBState.OPEN

    # Subsequent requests fail fast immediately
    with pytest.raises(CircuitBreakerOpenException):
        await cb.execute(successful_action)

@pytest.mark.asyncio
async def test_circuit_breaker_recovery_via_half_open():
    cb = CircuitBreaker(failure_threshold=2, reset_timeout_sec=1)
    
    async def failing_action():
        raise ValueError("Error")
        
    async def successful_action():
        return "OK"

    # Trip the circuit
    with pytest.raises(ValueError):
        await cb.execute(failing_action)
    with pytest.raises(ValueError):
        await cb.execute(failing_action)
    assert cb.state == CBState.OPEN

    # Wait for the reset timeout to expire
    await asyncio.sleep(1.1)

    # Next call should transition to HALF_OPEN and succeed, resetting to CLOSED
    result = await cb.execute(successful_action)
    assert result == "OK"
    assert cb.state == CBState.CLOSED

@pytest.mark.asyncio
async def test_circuit_breaker_half_open_failure_trips_back():
    cb = CircuitBreaker(failure_threshold=2, reset_timeout_sec=1)
    
    async def failing_action():
        raise ValueError("Error")

    # Trip the circuit
    with pytest.raises(ValueError):
        await cb.execute(failing_action)
    with pytest.raises(ValueError):
        await cb.execute(failing_action)
    assert cb.state == CBState.OPEN

    # Wait for the reset timeout to expire
    await asyncio.sleep(1.1)

    # Next call (probe) fails, should trip immediately back to OPEN
    with pytest.raises(ValueError):
        await cb.execute(failing_action)
    assert cb.state == CBState.OPEN

@pytest.mark.asyncio
async def test_circuit_breaker_limits_half_open_probes():
    cb = CircuitBreaker(failure_threshold=2, reset_timeout_sec=2)
    
    async def failing_action():
        raise ValueError("Error")

    # Trip the circuit
    with pytest.raises(ValueError):
        await cb.execute(failing_action)
    with pytest.raises(ValueError):
        await cb.execute(failing_action)
    assert cb.state == CBState.OPEN

    # Wait for the reset timeout to expire
    await asyncio.sleep(2.1)

    # We start a probe request that is slow
    async def slow_successful_action():
        await asyncio.sleep(0.5)
        return "OK"

    # Start the slow probe in the background
    probe_task = asyncio.create_task(cb.execute(slow_successful_action))
    
    # Wait a tiny bit to make sure it started and entered HALF_OPEN state
    await asyncio.sleep(0.1)
    assert cb.state == CBState.HALF_OPEN
    assert cb.half_open_attempts == 1

    # Attempt a second concurrent execution, which should be rejected
    with pytest.raises(CircuitBreakerOpenException):
        await cb.execute(slow_successful_action)

    # Wait for the probe to finish
    res = await probe_task
    assert res == "OK"
    assert cb.state == CBState.CLOSED
