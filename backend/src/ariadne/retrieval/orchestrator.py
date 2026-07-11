"""Hybrid retrieval orchestration.

The orchestrator runs the full retrieval pipeline for a query:

    Query -> Normalization -> Embedding -> Vector retrieval
          -> Entity extraction -> Graph traversal
          -> Fusion -> Deduplication -> Reranking -> Passages

Each stage is isolated so the pipeline can be observed and tested piece by
piece. Provider and store failures are surfaced as domain errors.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from ariadne.config import RetrievalSettings, get_settings
from ariadne.core.errors import EmbeddingProviderError
from ariadne.embeddings.base import EmbeddingProvider
from ariadne.embeddings.factory import get_embedding_provider
from ariadne.graph.service import GraphExtractionService
from ariadne.graph.store import GraphStore
from ariadne.logging import get_logger
from ariadne.retrieval.fusion import RetrievedPassage, fuse_candidates, normalize_query
from ariadne.retrieval.rerank.base import CrossEncoderReranker
from ariadne.retrieval.rerank.factory import get_reranker
from ariadne.vectors.numpy_store import NumpyVectorStore
from ariadne.vectors.store import VectorStore

logger = get_logger("retrieval.orchestrator")


class HybridRetrievalService:
    """Fuse vector and knowledge-graph retrieval into ranked passages."""

    def __init__(
        self,
        *,
        provider: EmbeddingProvider | None = None,
        vector_store: VectorStore | None = None,
        graph_service: GraphExtractionService | None = None,
        reranker: CrossEncoderReranker | None = None,
        settings: RetrievalSettings | None = None,
    ) -> None:
        self.provider = provider or get_embedding_provider()
        self.vector_store = vector_store or NumpyVectorStore()
        self.graph_service = graph_service or GraphExtractionService(store=GraphStore())
        self.reranker = reranker or get_reranker()
        self.settings = settings or get_settings().retrieval

    def retrieve(
        self,
        session: Session,
        query: str,
        *,
        top_k: int | None = None,
        document_ids: list[str] | None = None,
    ) -> list[RetrievedPassage]:
        """Retrieve, fuse and rank passages relevant to ``query``."""
        normalized = normalize_query(query)
        if not normalized:
            return []

        top_k = top_k or self.settings.top_k

        vector_matches = self._vector_retrieval(session, normalized, document_ids)
        graph_matches = self._graph_retrieval(session, normalized, document_ids)

        fused = fuse_candidates(
            vector_matches,
            graph_matches,
            vector_weight=self.settings.vector_weight,
            graph_weight=self.settings.graph_weight,
        )

        rerank_pool = fused[: self.settings.rerank_top_k]
        reranked = self.reranker.rerank(normalized, rerank_pool, top_k=top_k)
        logger.info(
            "hybrid retrieval completed",
            extra={
                "query": normalized,
                "vector_candidates": len(vector_matches),
                "graph_candidates": len(graph_matches),
                "fused": len(fused),
                "returned": len(reranked),
            },
        )
        return reranked

    def _vector_retrieval(
        self,
        session: Session,
        query: str,
        document_ids: list[str] | None,
    ) -> list:
        try:
            query_vector = self.provider.embed_one(query)
        except EmbeddingProviderError:
            raise
        except Exception as exc:
            raise EmbeddingProviderError(f"query embedding failed: {exc}") from exc
        return self.vector_store.search(
            session,
            query_vector,
            top_k=self.settings.vector_top_k,
            document_ids=document_ids,
        )

    def _graph_retrieval(
        self,
        session: Session,
        query: str,
        document_ids: list[str] | None,
    ) -> list:
        entities = self.graph_service.query_entities_from_text(query)
        return self.graph_service.store.search(
            session,
            entities,
            document_ids=document_ids,
            depth=self.settings.graph_depth,
            top_k=self.settings.graph_top_k,
        )
