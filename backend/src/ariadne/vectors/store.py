"""Vector store abstraction.

A vector store persists chunk embeddings and returns the most similar
chunks for a query vector, optionally restricted by metadata filters. The
store is the single point where similarity search happens; retrieval
orchestration builds on top of it.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from sqlalchemy.orm import Session


@dataclass(slots=True)
class VectorRecord:
    """A chunk paired with its dense embedding and provenance metadata."""

    chunk_id: str
    document_id: str
    index: int
    vector: list[float]
    page_numbers: list[int]
    text: str


@dataclass(slots=True)
class VectorMatch:
    """A retrieval result with its similarity score."""

    chunk_id: str
    document_id: str
    index: int
    page_numbers: list[int]
    text: str
    score: float


class VectorStore(ABC):
    """Interface implemented by concrete vector stores."""

    @abstractmethod
    def upsert(self, session: Session, records: list[VectorRecord]) -> int:
        """Persist or replace the given vector records. Returns count."""
        raise NotImplementedError

    @abstractmethod
    def search(
        self,
        session: Session,
        query_vector: list[float],
        *,
        top_k: int = 10,
        document_ids: list[str] | None = None,
    ) -> list[VectorMatch]:
        """Return the most similar records to ``query_vector``."""
        raise NotImplementedError

    @abstractmethod
    def delete_document(self, session: Session, document_id: str) -> int:
        """Remove every vector for a document. Returns count removed."""
        raise NotImplementedError

    @abstractmethod
    def count(self, session: Session) -> int:
        """Return the total number of stored vectors."""
        raise NotImplementedError
