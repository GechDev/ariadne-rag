"""LLM provider factory."""

from __future__ import annotations

from functools import lru_cache

from ariadne.config import get_settings
from ariadne.generation.base import LLMProvider
from ariadne.generation.deterministic import DeterministicLLMProvider
from ariadne.generation.local import LocalLLMProvider


@lru_cache
def get_llm_provider() -> LLMProvider:
    """Build the configured LLM provider (cached per process)."""
    settings = get_settings().generation
    if settings.provider == "deterministic":
        return DeterministicLLMProvider()
    if settings.provider == "local":
        return LocalLLMProvider(
            settings.model,
            max_new_tokens=settings.max_tokens,
            temperature=settings.temperature,
        )
    raise ValueError(f"unknown LLM provider: {settings.provider!r}")
