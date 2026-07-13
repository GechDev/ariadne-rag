"""LLM provider abstraction.

Providers translate a complete prompt into generated text. ARIADNE treats the
language model as a swappable dependency: a deterministic extractive provider
for tests and CI, a local transformers pipeline for offline production.
Streaming yields token-level chunks so SSE endpoints can forward them live.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator


class LLMProvider(ABC):
    """Interface for grounded text generation."""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Return the full generated answer for ``prompt``."""
        raise NotImplementedError

    def stream(self, prompt: str) -> Iterator[str]:
        """Yield generated token chunks for ``prompt``."""
        yield self.generate(prompt)
