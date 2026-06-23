from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
import httpx
import logging
import asyncio
from src.config.settings import settings
from src.core.instances import rate_limiter, circuit_breaker
from src.core.circuit_breaker import CircuitBreakerOpenException
from src.core.retry import with_retry

logger = logging.getLogger("proxy")
router = APIRouter()

@router.post("/api/proxy/data")
async def proxy_data(request: Request):
    # Step 1: Extract client identifier and check Rate Limiter
    client_ip = request.client.host if request.client else "127.0.0.1"
    
    allowed = await rate_limiter.check_limit(client_ip)
    if not allowed:
        return JSONResponse(
            status_code=429,
            content={"message": "Rate limit exceeded. Please try again later."}
        )

    # Read payload to forward
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    # Step 2 & 3: Wrap request in Retry Strategy and Circuit Breaker
    async def retry_action():
        # We use a new client or shared client. A context manager ensures connection cleanup.
        async with httpx.AsyncClient(timeout=10.0) as client:
            logger.info(f"Forwarding request to downstream: {settings.EXTERNAL_SERVICE_URL}")
            response = await client.post(settings.EXTERNAL_SERVICE_URL, json=payload)
            # Raise status error so with_retry can inspect it and trigger retries
            response.raise_for_status()
            return response

    async def cb_action():
        return await with_retry(
            action_func=retry_action,
            max_attempts=settings.RETRY_MAX_ATTEMPTS,
            initial_delay_ms=settings.RETRY_INITIAL_DELAY_MS,
            backoff_multiplier=settings.RETRY_BACKOFF_MULTIPLIER
        )

    try:
        response = await circuit_breaker.execute(cb_action)
        
        # Try to parse JSON body from the upstream response
        try:
            resp_body = response.json()
        except Exception:
            resp_body = response.text

        return JSONResponse(
            status_code=response.status_code,
            content=resp_body
        )

    except CircuitBreakerOpenException as exc:
        logger.warning(f"Circuit Breaker open: {exc}")
        return JSONResponse(
            status_code=503,
            content={"message": "External service is currently unavailable (circuit open)."}
        )

    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code
        logger.error(f"HTTPStatusError from upstream: status_code={status_code}")
        # Map 5xx upstream failures (after retries exhausted) to 500 Internal Server Error
        if status_code >= 500:
            return JSONResponse(
                status_code=500,
                content={"message": "Upstream service failure. After maximum retry attempts, the service remains unhealthy."}
            )
        # Client errors (4xx) are returned as-is
        try:
            content = exc.response.json()
        except Exception:
            content = {"message": exc.response.text}
        return JSONResponse(status_code=status_code, content=content)

    except Exception as exc:
        logger.error(f"Unexpected connection or network error: {exc}")
        # Any other failure (like connection failures after retries are exhausted) maps to 500
        return JSONResponse(
            status_code=500,
            content={"message": f"Upstream service failure. Connection error: {str(exc)}"}
        )
