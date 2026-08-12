import sys
from pathlib import Path
from contextlib import asynccontextmanager

# ------------------------------------------------
# Add backend/shared to PYTHONPATH FIRST
# ------------------------------------------------
shared_path = Path(__file__).resolve().parents[2] / "shared"
sys.path.insert(0, str(shared_path))

from fastapi import FastAPI

from mcp_server.router import router
from middlewares.cors_middleware import setup_cors
from vora_shared.config import get_settings
from vora_shared.database import connect_db, disconnect_db


# ------------------------------------------------
# Shared database connection for all services
# ------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    # Connect to shared PostgreSQL database
    connect_db(settings.resolved_database_url())

    yield

    await disconnect_db()


# ------------------------------------------------
# FastAPI app
# ------------------------------------------------
app = FastAPI(
    title="MCP Monitoring System",
    lifespan=lifespan,
)

setup_cors(app)

app.include_router(router)


@app.get("/")
async def home():
    return {
        "message": "MCP Monitoring System Running"
    }