from contextlib import asynccontextmanager
import logging
import sys
import os

from app.routers import comparison as comparison_router
from app.routers import config as config_router
from app.routers import gap as gap_router
from fastapi import FastAPI
from vora_shared.config import get_settings
from vora_shared.database import connect_db, disconnect_db
from vora_shared.server import create_vora_app


# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/ai-analysis-service.log", mode="a"),
    ],
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    connect_db(settings.resolved_database_url())
    logger.info("AI Analysis Service started")
    logger.info(f"Using model: {settings.sentence_transformer_model}")
    logger.info(f"Thresholds - High: {settings.similarity_threshold_high}, Medium: {settings.similarity_threshold_medium}")
    yield
    await disconnect_db()
    logger.info("AI Analysis Service stopped")


app = create_vora_app(title="AI Analysis Service", lifespan=lifespan)
app.include_router(comparison_router.router, prefix="/api/comparison")
app.include_router(gap_router.router, prefix="/api/deployment-gap")
app.include_router(config_router.router, prefix="/api/config")
