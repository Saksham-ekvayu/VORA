from contextlib import asynccontextmanager
from fastapi import FastAPI
from vora_shared.config import get_settings
from vora_shared.database import connect_db, disconnect_db
from vora_shared.server import create_vora_app
from app.routers import agent as agent_router

@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    await connect_db(settings.resolved_database_url())
    yield
    await disconnect_db()

app = create_vora_app(title="Compliance Agent Service", lifespan=lifespan)
app.include_router(agent_router.router, prefix="/api/compliance-agent")
