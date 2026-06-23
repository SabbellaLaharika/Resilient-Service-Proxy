import time
import asyncio
import logging
from typing import Dict, List

logger = logging.getLogger("rate_limiter")

class RateLimiter:
    def __init__(self, window_seconds: int, max_requests: int):
        self.window_seconds = window_seconds
        self.max_requests = max_requests
        self.store: Dict[str, List[float]] = {}
        self.lock = asyncio.Lock()
        logger.info(f"RateLimiter initialized: window_seconds={window_seconds}, max_requests={max_requests}")

    async def check_limit(self, client_id: str) -> bool:
        """
        Evaluate the current request for a given client_id.
        Returns True if the request is allowed (within quota), False if rate-limited.
        """
        async with self.lock:
            now = time.time()
            cutoff = now - self.window_seconds
            
            # Clean up old timestamps
            if client_id in self.store:
                # Keep timestamps inside the window
                self.store[client_id] = [t for t in self.store[client_id] if t > cutoff]
            else:
                self.store[client_id] = []
                
            current_requests = len(self.store[client_id])
            
            if current_requests < self.max_requests:
                self.store[client_id].append(now)
                logger.info(f"RateLimiter: client={client_id} allowed ({current_requests + 1}/{self.max_requests})")
                return True
            else:
                logger.warning(f"RateLimiter: client={client_id} rate-limited ({current_requests}/{self.max_requests})")
                return False
