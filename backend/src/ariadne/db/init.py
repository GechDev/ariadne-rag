"""Database bootstrap helpers."""

from __future__ import annotations

from sqlalchemy import inspect

from ariadne.db.base import Base
from ariadne.db.session import get_engine
from ariadne.logging import get_logger

logger = get_logger("db")


def init_db() -> None:
    """Create all tables that do not yet exist."""
    from ariadne import models  # noqa: F401  (register models with the Base metadata)

    engine = get_engine()
    Base.metadata.create_all(engine)
    logger.info("database initialized")


def tables_exist() -> bool:
    """Return True if any ARIADNE table exists in the connected database."""
    engine = get_engine()
    inspector = inspect(engine)
    return bool(inspector.get_table_names())
