from contextlib import asynccontextmanager

from fastapi import FastAPI

from vora_shared.config import get_settings
from vora_shared.database import connect_db, disconnect_db
from vora_shared.server import create_vora_app

from app.routers import deployment_document as deployment_document_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    await connect_db(settings.resolved_database_url())
    yield
    await disconnect_db()


app = create_vora_app(title="deployment-document-service", lifespan=lifespan)
app.include_router(deployment_document_router.router, prefix="/deployment-documents")
