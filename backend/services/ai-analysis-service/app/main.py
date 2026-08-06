from contextlib import asynccontextmanager

from app.routers import comparison as comparison_router
from app.routers import gap as gap_router
from fastapi import FastAPI
from vora_shared.config import get_settings
from vora_shared.database import connect_db, disconnect_db
from vora_shared.server import create_vora_app


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    connect_db(settings.resolved_database_url())
    yield
    await disconnect_db()


app = create_vora_app(title="AI Analysis Service", lifespan=lifespan)
app.include_router(comparison_router.router, prefix="/api/comparison")
app.include_router(gap_router.router, prefix="/api/deployment-gap")
