from contextlib import asynccontextmanager
import logging
import sys
import os

from app.routers import extract as extract_router
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
        logging.FileHandler("logs/extract-controls-service.log", mode="a"),
    ],
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    connect_db(settings.resolved_database_url())
    yield
    await disconnect_db()


app = create_vora_app(title="Extract Controls Service", lifespan=lifespan)
app.include_router(extract_router.router, prefix="/api/extract")
