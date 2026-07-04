"""Vector indexing service.

Coordinates embedding generation and persistence so the ingestion pipeline
can emit chunks and have them indexed as vectors without knowing the
underlying store or model.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from ariadne.core.errors import EmbeddingProviderError
from ariadne.embeddings.base import EmbeddingProvider
from ariadne.embeddings.factory import get_embedding_provider
from ariadne.logging import get_logger
from ariadne.models import Chunk
from ariadne.vectors.numpy_store import NumpyVectorStore
from ariadne.vectors.store import VectorRecord, VectorStore

logger = get_logger("vectors.service")


class VectorIndexService:
    """Embed chunks and keep the vector store in sync with the corpus."""

    def __init__(
        self,
        provider: EmbeddingProvider | None = None,
        store: VectorStore | None = None,
    ) -> None:
        self.provider = provider or get_embedding_provider()
        self.store = store or NumpyVectorStore()

    def index_chunks(self, session: Session, chunks: list[Chunk]) -> int:
        """Embed the given chunks and upsert them into the vector store."""
        if not chunks:
            return 0
        texts = [chunk.text for chunk in chunks]
        try:
            vectors = self.provider.embed(texts)
        except EmbeddingProviderError:
            raise
        except Exception as exc:
            raise EmbeddingProviderError(f"embedding generation failed: {exc}") from exc

        records = [
            VectorRecord(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                index=chunk.index,
                vector=vector,
                page_numbers=list(chunk.page_numbers),
                text=chunk.text,
            )
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]
        count = self.store.upsert(session, records)
        logger.info(
            "indexed chunk vectors",
            extra={"document_id": chunks[0].document_id, "count": count},
        )
        return count

    def reindex_document(self, session: Session, document_id: str, chunks: list[Chunk]) -> int:
        """Replace the vector index for a document with fresh embeddings."""
        self.store.delete_document(session, document_id)
        return self.index_chunks(session, chunks)

    def delete_document(self, session: Session, document_id: str) -> int:
        return self.store.delete_document(session, document_id)
