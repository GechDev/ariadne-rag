"""Grounded generation service.

Builds the prompt from retrieved passages, delegates to the configured LLM
provider and reports whether the produced answer is supported by the supplied
evidence. Answers that lack supporting context are flagged so citation and
streaming layers can treat them accordingly.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field

from ariadne.config import GenerationSettings, get_settings
from ariadne.generation.base import LLMProvider
from ariadne.generation.deterministic import INSUFFICIENT_EVIDENCE
from ariadne.generation.factory import get_llm_provider
from ariadne.generation.prompts import build_prompt
from ariadne.logging import get_logger
from ariadne.retrieval.fusion import RetrievedPassage

logger = get_logger("generation.service")


@dataclass(slots=True)
class GenerationResult:
    """A generated answer with its grounding evidence."""

    query: str
    answer: str
    grounded: bool
    used_chunk_ids: list[str] = field(default_factory=list)
    prompt: str = ""


class GenerationService:
    """Coordinate prompt construction and answer generation."""

    def __init__(
        self,
        provider: LLMProvider | None = None,
        settings: GenerationSettings | None = None,
    ) -> None:
        self.provider = provider or get_llm_provider()
        self.settings = settings or get_settings().generation

    def generate(self, query: str, passages: list[RetrievedPassage]) -> GenerationResult:
        """Generate a grounded answer for ``query`` over ``passages``."""
        prompt = build_prompt(
            query,
            passages,
            max_context_chars=self.settings.max_context_chars,
            max_passages=self.settings.max_passages,
        )
        answer = self.provider.generate(prompt).strip()
        used = [passage.chunk_id for passage in passages]
        grounded = bool(passages) and answer != INSUFFICIENT_EVIDENCE
        logger.info(
            "answer generated",
            extra={"grounded": grounded, "passages": len(passages), "chars": len(answer)},
        )
        return GenerationResult(
            query=query,
            answer=answer,
            grounded=grounded,
            used_chunk_ids=used,
            prompt=prompt,
        )

    def stream(self, query: str, passages: list[RetrievedPassage]) -> Iterator[str]:
        """Yield answer token chunks for streaming endpoints."""
        prompt = build_prompt(
            query,
            passages,
            max_context_chars=self.settings.max_context_chars,
            max_passages=self.settings.max_passages,
        )
        yield from self.provider.stream(prompt)
