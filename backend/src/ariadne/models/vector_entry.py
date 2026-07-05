"""Vector entry persistence model.

Stores one dense vector per chunk alongside the provenance metadata needed
for retrieval filters and citation support.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from ariadne.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class VectorEntry(Base):
    """A chunk embedded as a dense vector."""

    __tablename__ = "vector_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    chunk_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("chunks.id", ondelete="CASCADE"), unique=True, index=True
    )
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    index: Mapped[int] = mapped_column(Integer)
    vector: Mapped[bytes] = mapped_column(LargeBinary)
    dimension: Mapped[int] = mapped_column(Integer)
    page_numbers: Mapped[list[int]] = mapped_column(JSON, default=list)
    text: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<VectorEntry id={self.id} chunk={self.chunk_id} dim={self.dimension}>"
