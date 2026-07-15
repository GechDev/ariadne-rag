"""Grounded answer generation package."""

from __future__ import annotations

from ariadne.generation.context import format_context, truncate_to_budget
from ariadne.generation.prompts import build_prompt
from ariadne.generation.service import GenerationResult, GenerationService

__all__ = [
    "GenerationResult",
    "GenerationService",
    "build_prompt",
    "format_context",
    "truncate_to_budget",
]
