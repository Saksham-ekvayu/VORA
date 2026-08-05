from contextlib import asynccontextmanager

from fastapi import FastAPI

from vora_shared.config import get_settings
from vora_shared.database import connect_db, disconnect_db
from vora_shared.server import create_vora_app

from app.routers import admin as admin_router
from app.routers import expert as expert_router
from app.routers import customer_admin as customer_admin_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    await connect_db(settings.resolved_database_url())
    yield
    await disconnect_db()


app = create_vora_app(title="dashboard-service", lifespan=lifespan)
app.include_router(admin_router.router, prefix="/dashboard/admin")
app.include_router(expert_router.router, prefix="/dashboard/expert")
app.include_router(customer_admin_router.router, prefix="/dashboard/customer-admin")
