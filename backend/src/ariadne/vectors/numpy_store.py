"""NumPy-backed vector store persisted through SQLAlchemy.

Vectors are serialized as float32 buffers and stored in the ``vector_entries``
table. Search loads the (filtered) matrix into NumPy and computes cosine
similarity as a normalized dot product.
"""

from __future__ import annotations

import struct

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from ariadne.core.errors import VectorStoreError
from ariadne.logging import get_logger
from ariadne.models import VectorEntry
from ariadne.vectors.store import VectorMatch, VectorRecord, VectorStore

logger = get_logger("vectors.numpy")


def _pack(vector: list[float]) -> bytes:
    return struct.pack(f"{len(vector)}f", *vector)


def _unpack(payload: bytes) -> list[float]:
    count = len(payload) // 4
    return list(struct.unpack(f"{count}f", payload))


class NumpyVectorStore(VectorStore):
    """Vector store that computes similarity with NumPy."""

    def upsert(self, session: Session, records: list[VectorRecord]) -> int:
        if not records:
            return 0
        dimension = len(records[0].vector)
        session.query(VectorEntry).filter(
            VectorEntry.chunk_id.in_([r.chunk_id for r in records])
        ).delete(synchronize_session=False)

        for record in records:
            if len(record.vector) != dimension:
                raise VectorStoreError(
                    "inconsistent embedding dimensions within a batch",
                    detail={"expected": dimension, "received": len(record.vector)},
                )
            session.add(
                VectorEntry(
                    chunk_id=record.chunk_id,
                    document_id=record.document_id,
                    index=record.index,
                    vector=_pack(record.vector),
                    dimension=dimension,
                    page_numbers=record.page_numbers,
                    text=record.text,
                )
            )
        session.flush()
        return len(records)

    def search(
        self,
        session: Session,
        query_vector: list[float],
        *,
        top_k: int = 10,
        document_ids: list[str] | None = None,
    ) -> list[VectorMatch]:
        stmt = select(VectorEntry)
        if document_ids:
            stmt = stmt.where(VectorEntry.document_id.in_(document_ids))
        entries = list(session.scalars(stmt))
        if not entries:
            return []

        matrix = np.array([_unpack(entry.vector) for entry in entries], dtype=np.float32)
        query = np.asarray(query_vector, dtype=np.float32)
        norm = np.linalg.norm(query)
        if norm == 0:
            return []
        query = query / norm
        norms = np.linalg.norm(matrix, axis=1)
        norms[norms == 0] = 1.0
        similarities = (matrix @ query) / norms

        order = np.argsort(-similarities)[:top_k]
        matches: list[VectorMatch] = []
        for position in order:
            entry = entries[int(position)]
            matches.append(
                VectorMatch(
                    chunk_id=entry.chunk_id,
                    document_id=entry.document_id,
                    index=entry.index,
                    page_numbers=list(entry.page_numbers),
                    text=entry.text,
                    score=float(similarities[int(position)]),
                )
            )
        return matches

    def delete_document(self, session: Session, document_id: str) -> int:
        result = session.query(VectorEntry).filter(VectorEntry.document_id == document_id).delete(
            synchronize_session=False
        )
        session.flush()
        return result

    def count(self, session: Session) -> int:
        return session.query(VectorEntry).count()
