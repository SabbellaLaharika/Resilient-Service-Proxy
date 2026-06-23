import time
import asyncio
import logging
from enum import Enum

logger = logging.getLogger("circuit_breaker")

class CBState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

class CircuitBreakerOpenException(Exception):
    pass

class CircuitBreaker:
    def __init__(self, failure_threshold: int, reset_timeout_sec: int):
        self.state = CBState.CLOSED
        self.failures = 0
        self.failure_threshold = failure_threshold
        self.reset_timeout_sec = reset_timeout_sec
        self.last_failure_time = None
        self.half_open_attempts = 0
        self.lock = asyncio.Lock()
        logger.info(f"CircuitBreaker initialized: failure_threshold={failure_threshold}, reset_timeout_sec={reset_timeout_sec}")

    async def execute(self, external_call_func):
        async with self.lock:
            # Evaluate current state and timeouts (transition to HALF_OPEN if applicable)
            if self.state == CBState.OPEN:
                now = time.time()
                if self.last_failure_time and (now - self.last_failure_time >= self.reset_timeout_sec):
                    self.state = CBState.HALF_OPEN
                    self.half_open_attempts = 0
                    logger.info(f"[CIRCUIT BREAKER] State changed from OPEN to HALF_OPEN")
                else:
                    logger.warning("[CIRCUIT BREAKER] Request blocked: Circuit is OPEN")
                    raise CircuitBreakerOpenException("Circuit is open")

            # Check probe limits in HALF_OPEN
            if self.state == CBState.HALF_OPEN:
                self.half_open_attempts += 1
                if self.half_open_attempts > 1:
                    logger.warning("[CIRCUIT BREAKER] Request blocked: Circuit is HALF-OPEN (probe in progress)")
                    raise CircuitBreakerOpenException("Circuit is half-open (probe in progress)")

        # Attempt execution (outside evaluation lock)
        try:
            result = await external_call_func()
            
            # On success: reset counters, transition to CLOSED if HALF_OPEN
            async with self.lock:
                self.failures = 0
                if self.state == CBState.HALF_OPEN:
                    self.state = CBState.CLOSED
                    logger.info("[CIRCUIT BREAKER] State changed from HALF_OPEN to CLOSED")
                self.half_open_attempts = 0
            return result

        except Exception as e:
            # On failure: handle thresholds, transition to OPEN if necessary
            async with self.lock:
                if self.state == CBState.HALF_OPEN:
                    self.state = CBState.OPEN
                    self.last_failure_time = time.time()
                    self.failures = self.failure_threshold  # preserve failure state
                    self.half_open_attempts = 0
                    logger.warning(f"[CIRCUIT BREAKER] State changed from HALF_OPEN to OPEN (probe failed)")
                elif self.state == CBState.CLOSED:
                    self.failures += 1
                    logger.info(f"[CIRCUIT BREAKER] Failure recorded ({self.failures}/{self.failure_threshold})")
                    if self.failures >= self.failure_threshold:
                        self.state = CBState.OPEN
                        self.last_failure_time = time.time()
                        logger.warning(f"[CIRCUIT BREAKER] State changed from CLOSED to OPEN")
            raise e
