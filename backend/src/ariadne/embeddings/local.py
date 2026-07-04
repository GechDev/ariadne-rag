"""Local embedding provider backed by sentence-transformers.

The heavy model is imported lazily so that a cold start without the model
installed still lets the rest of the application load. Use
``pip install ariadne[embedding]`` to enable this provider.
"""

from __future__ import annotations

from ariadne.core.errors import EmbeddingProviderError
from ariadne.embeddings.base import EmbeddingProvider
from ariadne.logging import get_logger

logger = get_logger("embeddings.local")


class LocalEmbeddingProvider(EmbeddingProvider):
    """sentence-transformers embeddings running on the local machine."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self.model_name = model_name
        self._model = None
        self._dimension: int | None = None

    def _load(self) -> object:
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise EmbeddingProviderError(
                    "sentence-transformers is not installed; add the 'embedding' extra",
                    detail={"model": self.model_name},
                ) from exc
            logger.info("loading embedding model", extra={"model": self.model_name})
            self._model = SentenceTransformer(self.model_name)
            self._dimension = self._model.get_sentence_embedding_dimension()
        return self._model

    @property
    def dimension(self) -> int:
        self._load()
        assert self._dimension is not None
        return self._dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        model = self._load()
        if not texts:
            return []
        try:
            vectors = model.encode(texts, normalize_embeddings=True)
            return [vector.tolist() for vector in vectors]
        except Exception as exc:
            logger.error("local embedding failed", extra={"error": str(exc)})
            raise EmbeddingProviderError(f"embedding generation failed: {exc}") from exc
