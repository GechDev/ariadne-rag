"""Deterministic embedding provider.

Produces fixed-dimension, deterministic vectors from token hashing. Used for
tests and CI where downloading a real model is impractical. Vectors are
normalized so similarity scores behave like real embeddings.
"""

from __future__ import annotations

import hashlib
import math
import re

import numpy as np

from ariadne.embeddings.base import EmbeddingProvider

_TOKEN_RE = re.compile(r"[a-z0-9]+")


class DeterministicEmbeddingProvider(EmbeddingProvider):
    """Hashing-based embeddings for tests and offline development."""

    def __init__(self, dimension: int = 384, seed: int = 42) -> None:
        self._dimension = dimension
        self._seed = seed

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = [self._hash_vector(text) for text in texts]
        return [self._normalize(v) for v in vectors]

    def _hash_vector(self, text: str) -> list[float]:
        vector = np.zeros(self._dimension, dtype=float)
        tokens = _TOKEN_RE.findall(text.lower())
        for token in tokens:
            digest = hashlib.blake2b(
                token.encode(), digest_size=8, salt=f"{self._seed}".encode()
            ).digest()
            position = int.from_bytes(digest[:4], "big") % self._dimension
            magnitude = int.from_bytes(digest[4:], "big") / (2**32)
            vector[position] += 0.5 + magnitude
        return vector.tolist()

    @staticmethod
    def _normalize(vector: list[float]) -> list[float]:
        norm = math.sqrt(sum(v * v for v in vector))
        if norm == 0:
            return vector
        return [v / norm for v in vector]
