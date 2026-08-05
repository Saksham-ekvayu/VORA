from contextlib import asynccontextmanager

from app.routers import framework, framework_access
from fastapi import FastAPI
from vora_shared.config import get_settings
from vora_shared.database import connect_db, disconnect_db
from vora_shared.server import create_vora_app


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    await connect_db(settings.resolved_database_url())
    yield
    await disconnect_db()


app = create_vora_app(title="framework-service", lifespan=lifespan)

app.include_router(framework_access.router, prefix="/framework-access")
app.include_router(framework.router, prefix="/framework")
