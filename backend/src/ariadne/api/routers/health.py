"""Health check endpoint."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from sqlalchemy import text

from ariadne.config import get_settings
from ariadne.db.session import get_engine
from ariadne.logging import get_logger

router = APIRouter(tags=["health"])
logger = get_logger("health")


def _database_status() -> dict[str, Any]:
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as exc:  # pragma: no cover - depends on runtime infra
        logger.warning("database health probe failed", extra={"error": str(exc)})
        return {"status": "error", "detail": str(exc)}


@router.get("/health", summary="Liveness and readiness probe")
def health() -> dict[str, Any]:
    """Report application and dependency health."""
    settings = get_settings()
    db = _database_status()
    healthy = db["status"] == "ok"
    return {
        "status": "ok" if healthy else "degraded",
        "app": settings.app_name,
        "environment": settings.environment,
        "version": settings.api.version,
        "database": db,
    }
