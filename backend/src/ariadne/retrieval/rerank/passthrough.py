"""No-op reranker that preserves the fused ordering."""

from __future__ import annotations

from ariadne.retrieval.rerank.base import CrossEncoderReranker


class PassthroughReranker(CrossEncoderReranker):
    """Keep candidates in the fused order without rescoring."""

    def score(self, query: str, texts: list[str]) -> list[float]:
        return [0.0 for _ in texts]
