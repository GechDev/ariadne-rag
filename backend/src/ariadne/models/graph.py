"""Knowledge graph persistence models."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ariadne.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class GraphEntity(Base):
    """A named entity extracted from a document."""

    __tablename__ = "graph_entities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(512), index=True)
    entity_type: Mapped[str] = mapped_column(String(128), default="unknown")
    frequency: Mapped[int] = mapped_column(Integer, default=1)
    chunk_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<GraphEntity name={self.name!r} type={self.entity_type!r}>"


class GraphRelationship(Base):
    """A typed edge between two entities in a document."""

    __tablename__ = "graph_relationships"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    source_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("graph_entities.id", ondelete="CASCADE"), index=True
    )
    target_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("graph_entities.id", ondelete="CASCADE"), index=True
    )
    relationship: Mapped[str] = mapped_column(String(256))
    weight: Mapped[float] = mapped_column(Integer, default=1)
    chunk_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<GraphRelationship {self.source_id} -{self.relationship}-> {self.target_id}>"
