import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from src.routes import health, proxy

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("proxy")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Proxy server starting up...")
    yield
    logger.info("Proxy server shutting down...")

app = FastAPI(title="Resilient Service Proxy API", lifespan=lifespan)

# Register endpoints
app.include_router(health.router)
app.include_router(proxy.router)
