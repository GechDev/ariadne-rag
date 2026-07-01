"""SQLAlchemy ORM models for ARIADNE.

Importing this package registers every model on the shared metadata so that
``Base.metadata.create_all`` knows about the full schema.
"""

from __future__ import annotations

from ariadne.models.document import Document, DocumentStatus

__all__ = ["Document", "DocumentStatus"]
