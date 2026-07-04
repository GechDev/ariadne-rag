"""Embedding provider abstraction.

Providers translate text into dense vectors. ARIADNE treats the embedding
model as a swappable dependency: local sentence-transformers for production,
deterministic providers for tests and CI. Providers must return normalized
vectors so that cosine similarity reduces to a dot product.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """Interface for text embedding models."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Length of vectors produced by this provider."""
        raise NotImplementedError

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one dense vector per input text."""
        raise NotImplementedError

    def embed_one(self, text: str) -> list[float]:
        """Convenience wrapper returning a single vector."""
        return self.embed([text])[0]
