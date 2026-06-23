import os
import random
import asyncio
import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mock_service")

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/external-api/process")
async def process(request: Request):
    # Read environment variables on each request to allow dynamic overrides during testing
    fail_rate_str = os.environ.get("EXTERNAL_FAIL_RATE", "0.0")
    latency_ms_str = os.environ.get("EXTERNAL_LATENCY_MS", "0")
    
    try:
        fail_rate = float(fail_rate_str)
    except ValueError:
        fail_rate = 0.0
        
    try:
        latency_ms = int(latency_ms_str)
    except ValueError:
        latency_ms = 0

    logger.info(f"Received request. Configured fail_rate={fail_rate}, latency_ms={latency_ms}")

    # Inject artificial latency
    if latency_ms > 0:
        logger.info(f"Simulating latency of {latency_ms}ms")
        await asyncio.sleep(latency_ms / 1000.0)
        
    # Generate a random number to simulate failures
    if fail_rate > 0.0:
        rand_val = random.random()
        if rand_val < fail_rate:
            logger.warning(f"Simulated failure: random value {rand_val:.4f} < fail rate {fail_rate}")
            return JSONResponse(
                status_code=500,
                content={"message": "Internal Server Error"}
            )
            
    # Echo back the received JSON payload
    try:
        payload = await request.json()
    except Exception:
        payload = {}
        
    logger.info("Successfully processed request")
    return payload
