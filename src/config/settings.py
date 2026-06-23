import os
import logging

logger = logging.getLogger("proxy")

class Settings:
    def __init__(self):
        # External Service
        self.EXTERNAL_SERVICE_URL = os.environ.get(
            "EXTERNAL_SERVICE_URL", 
            "http://localhost:5001/external-api/process"
        )
        
        # Rate Limiter
        self.RATE_LIMIT_WINDOW_SECONDS = int(os.environ.get("RATE_LIMIT_WINDOW_SECONDS", 60))
        self.RATE_LIMIT_MAX_REQUESTS = int(os.environ.get("RATE_LIMIT_MAX_REQUESTS", 10))
        
        # Circuit Breaker
        self.CB_FAILURE_THRESHOLD = int(os.environ.get("CB_FAILURE_THRESHOLD", 5))
        self.CB_RESET_TIMEOUT_SECONDS = int(os.environ.get("CB_RESET_TIMEOUT_SECONDS", 30))
        
        # Retry
        self.RETRY_MAX_ATTEMPTS = int(os.environ.get("RETRY_MAX_ATTEMPTS", 3))
        self.RETRY_INITIAL_DELAY_MS = int(os.environ.get("RETRY_INITIAL_DELAY_MS", 100))
        self.RETRY_BACKOFF_MULTIPLIER = float(os.environ.get("RETRY_BACKOFF_MULTIPLIER", 2.0))

        logger.info("Configuration loaded:")
        logger.info(f"  EXTERNAL_SERVICE_URL: {self.EXTERNAL_SERVICE_URL}")
        logger.info(f"  RATE_LIMIT_WINDOW_SECONDS: {self.RATE_LIMIT_WINDOW_SECONDS}")
        logger.info(f"  RATE_LIMIT_MAX_REQUESTS: {self.RATE_LIMIT_MAX_REQUESTS}")
        logger.info(f"  CB_FAILURE_THRESHOLD: {self.CB_FAILURE_THRESHOLD}")
        logger.info(f"  CB_RESET_TIMEOUT_SECONDS: {self.CB_RESET_TIMEOUT_SECONDS}")
        logger.info(f"  RETRY_MAX_ATTEMPTS: {self.RETRY_MAX_ATTEMPTS}")
        logger.info(f"  RETRY_INITIAL_DELAY_MS: {self.RETRY_INITIAL_DELAY_MS}")
        logger.info(f"  RETRY_BACKOFF_MULTIPLIER: {self.RETRY_BACKOFF_MULTIPLIER}")

settings = Settings()
