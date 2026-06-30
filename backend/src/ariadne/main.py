"""FastAPI application factory for ARIADNE."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ariadne.api.routers.health import router as health_router
from ariadne.config import get_settings
from ariadne.core.errors import AriadneError
from ariadne.db.init import init_db
from ariadne.logging import configure_logging, get_logger


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup/shutdown hooks for the application."""
    configure_logging()
    logger = get_logger("main")
    if get_settings().environment != "test":
        init_db()
        logger.info("startup complete")
    yield


def create_app() -> FastAPI:
    """Build and configure the ARIADNE FastAPI application."""
    settings = get_settings()
    app = FastAPI(
        title=settings.api.title,
        version=settings.api.version,
        description=settings.api.description,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors.origins,
        allow_credentials=settings.cors.allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)

    @app.exception_handler(AriadneError)
    async def ariadne_error_handler(request: Request, exc: AriadneError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "detail": exc.detail,
                }
            },
        )

    return app


app = create_app()
