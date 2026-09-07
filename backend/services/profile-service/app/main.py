import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from app.routers import admin as admin_router
from app.routers import user as user_router
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from vora_shared.config import get_settings
from vora_shared.database import connect_db, disconnect_db
from vora_shared.server import create_vora_app

UPLOADS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "shared" / "uploads"


# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/profile-service.log", mode="a"),
    ],
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    connect_db(settings.resolved_database_url())
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    yield
    await disconnect_db()


app = create_vora_app(title="Profile Service", lifespan=lifespan)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")
app.include_router(user_router.router, prefix="/user")
app.include_router(admin_router.router, prefix="/admin")
