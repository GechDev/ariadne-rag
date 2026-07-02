"""FastAPI dependency providers."""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import Request
from sqlalchemy.orm import Session

from ariadne.db.session import get_session_factory
from ariadne.logging import get_logger


def get_db(request: Request) -> Iterator[Session]:
    """Provide a request-scoped database session that commits on success."""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_request_logger(request: Request):
    """Provide a logger bound to the current request."""
    logger = get_logger("api")
    return logger
