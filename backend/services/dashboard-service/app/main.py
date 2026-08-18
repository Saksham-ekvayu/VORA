import logging
import os
import sys
from contextlib import asynccontextmanager

from app.routers import admin as admin_router
from app.routers import auditor as auditor_router
from app.routers import customer_admin as customer_admin_router
from app.routers import expert as expert_router
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
        logging.FileHandler("logs/dashboard-service.log", mode="a"),
    ],
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    connect_db(settings.resolved_database_url())
    yield
    await disconnect_db()


app = create_vora_app(title="dashboard-service", lifespan=lifespan)
app.include_router(admin_router.router, prefix="/dashboard/admin")
app.include_router(expert_router.router, prefix="/dashboard/expert")
app.include_router(customer_admin_router.router, prefix="/dashboard/customer-admin")
app.include_router(auditor_router.router, prefix="/dashboard/auditor")
