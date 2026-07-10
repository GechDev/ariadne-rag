"""Cross-encoder reranker abstraction.

A cross-encoder scores each (query, passage) pair jointly, in contrast to the
bi-encoder retrieval step that embeds query and passages separately. This
produces finer-grained relevance scores at the cost of one forward pass per
candidate, so reranking is applied only to the top candidates.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ariadne.retrieval.fusion import RetrievedPassage


class CrossEncoderReranker(ABC):
    """Interface implemented by concrete rerankers."""

    @abstractmethod
    def score(self, query: str, texts: list[str]) -> list[float]:
        """Return a relevance score per (query, text) pair."""
        raise NotImplementedError

    def rerank(
        self, query: str, passages: list[RetrievedPassage], *, top_k: int | None = None
    ) -> list[RetrievedPassage]:
        """Return ``passages`` reordered by joint relevance to ``query``."""
        if not passages:
            return []
        texts = [passage.text or "" for passage in passages]
        scores = self.score(query, texts)
        for passage, rerank_score in zip(passages, scores, strict=True):
            passage.rerank_score = rerank_score
        ordered = sorted(passages, key=lambda passage: passage.rerank_score or 0.0, reverse=True)
        if top_k is not None:
            ordered = ordered[:top_k]
        return ordered
