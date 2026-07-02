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


class CorsSettings(BaseSettings):
    """CORS policy for the HTTP API."""

    origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://localhost:3000"],
        description="Allowed browser origins",
    )
    allow_credentials: bool = Field(default=True)


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
    cors: CorsSettings = Field(default_factory=CorsSettings)


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings singleton."""
    return Settings()
