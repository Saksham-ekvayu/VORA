import logging
import os
import sys
from contextlib import asynccontextmanager

from app.routers import framework
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
        logging.FileHandler("logs/framework-service.log", mode="a"),
    ],
)

logger = logging.getLogger(__name__)


# ------------------------------------------------
# Shared PostgreSQL connection for all services
# ------------------------------------------------
@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    connect_db(settings.resolved_database_url())
    yield
    await disconnect_db()


# ------------------------------------------------
# FastAPI app
# ------------------------------------------------
app = create_vora_app(title="framework-service", lifespan=lifespan)

app.include_router(framework.router, prefix="/framework")
