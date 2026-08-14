import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# ------------------------------------------------
# Add backend/shared to PYTHONPATH FIRST
# ------------------------------------------------
shared_path = Path(__file__).resolve().parents[3] / "shared"
sys.path.insert(0, str(shared_path))

from app.mcp_server.router import router
from fastapi import FastAPI
from vora_shared.config import get_settings
from vora_shared.database import connect_db, disconnect_db
from vora_shared.server import create_vora_app

# ------------------------------------------------
# Logging
# ------------------------------------------------
os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/mcp-boto3-server.log", mode="a"),
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
app = create_vora_app(
    title="MCP Monitoring System",
    lifespan=lifespan,
)

app.include_router(router, prefix="/mcp")
