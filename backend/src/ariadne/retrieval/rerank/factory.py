"""Reranker selection based on application configuration."""

from __future__ import annotations

from functools import lru_cache

from ariadne.config import get_settings
from ariadne.core.errors import RerankerUnavailableError
from ariadne.retrieval.rerank.base import CrossEncoderReranker
from ariadne.retrieval.rerank.lexical import LexicalOverlapReranker


@lru_cache
def get_reranker() -> CrossEncoderReranker:
    """Return the configured cross-encoder reranker."""
    name = get_settings().retrieval.reranker.lower()
    if name == "lexical":
        return LexicalOverlapReranker()
    if name == "none":
        from ariadne.retrieval.rerank.passthrough import PassthroughReranker

        return PassthroughReranker()
    raise RerankerUnavailableError(f"unknown reranker configured: {name!r}")
