"""Embedding provider factory."""

from __future__ import annotations

from functools import lru_cache

from ariadne.config import get_settings
from ariadne.embeddings.base import EmbeddingProvider
from ariadne.embeddings.deterministic import DeterministicEmbeddingProvider
from ariadne.embeddings.local import LocalEmbeddingProvider
from ariadne.logging import get_logger

logger = get_logger("embeddings.factory")


@lru_cache
def get_embedding_provider(
    provider: str | None = None, model: str | None = None
) -> EmbeddingProvider:
    """Build the configured embedding provider (cached per arguments)."""
    settings = get_settings()
    provider = provider or settings.embeddings.provider
    model = model or settings.embeddings.model
    if provider == "deterministic":
        return DeterministicEmbeddingProvider(dimension=settings.embeddings.dimension)
    if provider == "local":
        return LocalEmbeddingProvider(model_name=model)
    raise ValueError(f"unknown embedding provider: {provider!r}")
