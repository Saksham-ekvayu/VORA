from typing import Any, Callable

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from vora_shared.config import get_settings
from vora_shared.responses import http_exception_handler, request_validation_exception_handler


def create_vora_app(title: str, lifespan: Callable[[FastAPI], Any] = None) -> FastAPI:
    from contextlib import asynccontextmanager
    import sys
    import logging

    @asynccontextmanager
    async def custom_lifespan(app_instance: FastAPI):
        port = 8000
        if "--port" in sys.argv:
            try:
                port = int(sys.argv[sys.argv.index("--port") + 1])
            except (ValueError, IndexError):
                pass
        
        logger = logging.getLogger("uvicorn.error")
        logger.info(f"Service URL: http://localhost:{port}")
        logger.info(f"Docs URL: http://localhost:{port}/docs")
        
        if lifespan:
            # We call the user's lifespan context manager
            async with lifespan(app_instance):
                yield
        else:
            yield

    settings = get_settings()
    app = FastAPI(
        title=title,
        lifespan=custom_lifespan,
        swagger_ui_parameters={"persistAuthorization": True},
    )

    origins = [o.strip() for o in settings.cors_origin.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "x-tenant-id"],
    )

    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, request_validation_exception_handler)

    @app.get("/")
    async def root():
        return {"success": True, "message": f"Welcome to {app.title}"}

    @app.get("/health")
    async def health():
        return {
            "success": True,
            "service": title.lower().replace(" ", "-"),
            "status": "healthy",
        }

    return app
