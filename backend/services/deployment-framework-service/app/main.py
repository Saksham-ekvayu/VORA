from contextlib import asynccontextmanager

from app.routers import deployment_framework as deployment_framework_router
from app.routers import framework_assignment as framework_assignment_router
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


app = create_vora_app(title="deployment-framework-service", lifespan=lifespan)
app.include_router(framework_assignment_router.router, prefix="/assignment-frameworks")
app.include_router(deployment_framework_router.router, prefix="/deployment-frameworks")
