"""Application error hierarchy for ARIADNE.

Domain errors inherit from :class:`AriadneError` and carry an HTTP status
code plus a stable machine-readable ``code`` that API clients can rely on.
"""

from __future__ import annotations


class AriadneError(Exception):
    """Base class for all domain errors raised by the application."""

    status_code: int = 500
    code: str = "internal_error"

    def __init__(self, message: str, *, detail: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail or {}


class NotFoundError(AriadneError):
    status_code = 404
    code = "not_found"


class ValidationError(AriadneError):
    status_code = 422
    code = "validation_error"


class ConflictError(AriadneError):
    status_code = 409
    code = "conflict"


class UnsupportedDocumentTypeError(ValidationError):
    code = "unsupported_document_type"


class IngestionError(AriadneError):
    status_code = 500
    code = "ingestion_failed"


class ProviderUnavailableError(AriadneError):
    status_code = 503
    code = "provider_unavailable"


class RerankerUnavailableError(ProviderUnavailableError):
    code = "reranker_unavailable"


class EmbeddingProviderError(ProviderUnavailableError):
    code = "embedding_provider_error"


class LLMProviderError(ProviderUnavailableError):
    code = "llm_provider_error"


class VectorStoreError(AriadneError):
    status_code = 500
    code = "vector_store_error"


class GraphStoreError(AriadneError):
    status_code = 500
    code = "graph_store_error"
