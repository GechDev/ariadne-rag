"""Grounded prompt construction.

Prompts carry explicit instructions to answer only from the supplied context
and to acknowledge when the evidence is insufficient, which is the core
anti-hallucination constraint of ARIADNE.
"""

from __future__ import annotations

from ariadne.generation.context import format_context
from ariadne.retrieval.fusion import RetrievedPassage

SYSTEM_PROMPT = (
    "You are ARIADNE, a grounded question-answering assistant. "
    "Answer strictly using the context passages below. "
    "Do not use outside knowledge. If the passages do not contain enough "
    "information to answer the question, state that the available sources do "
    "not support an answer instead of guessing. Keep the answer concise."
)

CONTEXT_HEADER = "Context passages:"
QUESTION_HEADER = "Question:"
ANSWER_HEADER = "Answer:"


def build_prompt(
    query: str,
    passages: list[RetrievedPassage],
    *,
    max_context_chars: int,
    max_passages: int,
) -> str:
    """Assemble the full generation prompt from query and retrieved passages."""
    context = format_context(
        passages, max_chars=max_context_chars, max_passages=max_passages
    )
    return "\n\n".join(
        [
            SYSTEM_PROMPT,
            f"{CONTEXT_HEADER}\n{context or '(no passages retrieved)'}",
            f"{QUESTION_HEADER}\n{query}",
            f"{ANSWER_HEADER}\n",
        ]
    )
