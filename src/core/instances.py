from src.config.settings import settings
from src.core.rate_limiter import RateLimiter
from src.core.circuit_breaker import CircuitBreaker

rate_limiter = RateLimiter(
    window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
    max_requests=settings.RATE_LIMIT_MAX_REQUESTS
)

circuit_breaker = CircuitBreaker(
    failure_threshold=settings.CB_FAILURE_THRESHOLD,
    reset_timeout_sec=settings.CB_RESET_TIMEOUT_SECONDS
)
