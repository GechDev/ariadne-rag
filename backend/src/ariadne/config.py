"""Application configuration for ARIADNE.

Settings are loaded from environment variables and an optional ``.env`` file.
Every option documented here is available through the ``settings`` singleton.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

AppEnv = Literal["development", "test", "production"]


class DatabaseSettings(BaseSettings):
    """SQLAlchemy database connection settings."""

    url: str = Field(default="sqlite:///./ariadne.db", description="SQLAlchemy database URL")
    pool_pre_ping: bool = Field(default=True, description="Verify connections before use")
    connect_args: dict = Field(default={"check_same_thread": False})


class StorageSettings(BaseSettings):
    """Local file storage settings for uploaded documents."""

    upload_dir: Path = Field(
        default=Path("storage/uploads"), description="Where uploaded files are kept"
    )


class EmbeddingSettings(BaseSettings):
    """Embedding model settings."""

    provider: str = Field(
        default="deterministic",
        description="Embedding provider: 'deterministic' or 'local'",
    )
    model: str = Field(default="all-MiniLM-L6-v2", description="Local model name")
    dimension: int = Field(default=384, description="Deterministic provider dimension")


class CorsSettings(BaseSettings):
    """CORS policy for the HTTP API."""

    origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://localhost:3000"],
        description="Allowed browser origins",
    )
    allow_credentials: bool = Field(default=True)


class RetrievalSettings(BaseSettings):
    """Hybrid retrieval configuration."""

    top_k: int = Field(default=10, description="Final number of passages returned")
    vector_top_k: int = Field(default=20, description="Candidates fetched from the vector store")
    graph_top_k: int = Field(default=10, description="Candidates fetched from the knowledge graph")
    graph_depth: int = Field(default=1, description="Graph traversal hops around seed entities")
    vector_weight: float = Field(default=1.0, description="Weight applied to vector scores")
    graph_weight: float = Field(default=0.6, description="Weight applied to graph scores")
    reranker: str = Field(default="lexical", description="Reranker: 'lexical' or 'none'")
    rerank_top_k: int = Field(default=10, description="Passages passed through the reranker")


class GenerationSettings(BaseSettings):
    """Grounded answer generation configuration."""

    provider: str = Field(
        default="deterministic",
        description="LLM provider: 'deterministic' or 'local'",
    )
    model: str = Field(
        default="HuggingFaceH4/zephyr-7b-beta", description="Local model name"
    )
    max_tokens: int = Field(default=512, description="Maximum generated tokens")
    temperature: float = Field(default=0.2, description="Sampling temperature")
    max_context_chars: int = Field(
        default=8000, description="Context budget supplied to the model"
    )
    max_passages: int = Field(default=6, description="Passages included in the prompt")


class APISettings(BaseSettings):
    """HTTP API behaviour settings."""

    title: str = Field(default="ARIADNE API")
    version: str = Field(default="0.1.0")
    description: str = Field(
        default="Adaptive Retrieval & Intelligent Answering over Document Networks with Embeddings."
    )


class Settings(BaseSettings):
    """Root application settings."""

    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="ARIADNE_", env_nested_delimiter="__", extra="ignore"
    )

    app_name: str = Field(default="ARIADNE", description="Human readable application name")
    environment: AppEnv = Field(default="development", description="Runtime environment")
    debug: bool = Field(default=True, description="Enable debug logging and reload")
    log_level: str = Field(default="INFO", description="Root logging level")
    api: APISettings = Field(default_factory=APISettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    embeddings: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    retrieval: RetrievalSettings = Field(default_factory=RetrievalSettings)
    generation: GenerationSettings = Field(default_factory=GenerationSettings)
    cors: CorsSettings = Field(default_factory=CorsSettings)


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings singleton."""
    return Settings()
