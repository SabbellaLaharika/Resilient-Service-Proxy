import asyncio
import logging
import httpx

logger = logging.getLogger("retry")

async def with_retry(
    action_func, 
    max_attempts: int, 
    initial_delay_ms: int, 
    backoff_multiplier: float
):
    """
    Executes the action_func in a loop, retrying up to max_attempts times on transient errors
    with exponential backoff.
    """
    attempts = 0
    while True:
        attempts += 1
        try:
            # Attempt the external API call
            return await action_func()
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            # Retry only on transient 5xx errors
            if status_code >= 500:
                if attempts < max_attempts:
                    # Delay = Initial_Delay * (Multiplier ^ Attempt)
                    # Here, attempt index is 0-based for the delay duration calculation.
                    attempt_index = attempts - 1
                    delay_sec = (initial_delay_ms / 1000.0) * (backoff_multiplier ** attempt_index)
                    logger.warning(
                        f"Transient HTTP status {status_code} on attempt {attempts}/{max_attempts}. "
                        f"Retrying in {delay_sec:.3f}s..."
                    )
                    await asyncio.sleep(delay_sec)
                    continue
            logger.error(f"Permanent HTTP status {status_code} or retries exhausted after {attempts} attempts.")
            raise exc
        except (httpx.RequestError, asyncio.TimeoutError) as exc:
            # Network connection and timeout exceptions are transient
            if attempts < max_attempts:
                attempt_index = attempts - 1
                delay_sec = (initial_delay_ms / 1000.0) * (backoff_multiplier ** attempt_index)
                logger.warning(
                    f"Transient network error on attempt {attempts}/{max_attempts}: {exc}. "
                    f"Retrying in {delay_sec:.3f}s..."
                )
                await asyncio.sleep(delay_sec)
                continue
            logger.error(f"Network error or retries exhausted after {attempts} attempts: {exc}")
            raise exc
