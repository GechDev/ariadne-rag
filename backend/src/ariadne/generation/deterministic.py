"""Deterministic extractive generation provider.

Produces grounded answers without a model: query tokens are matched against
sentences in the provided context and the best-matching sentences are returned
verbatim. When nothing in the context matches the question, the provider
returns an explicit insufficient-evidence message instead of fabricating
content, mirroring the grounding constraint enforced by the prompt.
"""

from __future__ import annotations

import re
from collections.abc import Iterator

from ariadne.generation.base import LLMProvider
from ariadne.generation.prompts import ANSWER_HEADER, CONTEXT_HEADER, QUESTION_HEADER

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
_CHUNK_HEADER_RE = re.compile(r"^\[\d+\] \(chunk .*\)\s*$")
_QUERY_STOPWORDS = {"what", "when", "where", "which", "who", "how", "is", "the", "a", "an"}

INSUFFICIENT_EVIDENCE = (
    "The available sources do not contain enough information to answer this question."
)


class DeterministicLLMProvider(LLMProvider):
    """Extractive, reproducible answer provider for tests and offline use."""

    def generate(self, prompt: str) -> str:
        question = self._section(prompt, QUESTION_HEADER, ANSWER_HEADER)
        context = self._section(prompt, CONTEXT_HEADER, QUESTION_HEADER)
        query_tokens = {
            token for token in _TOKEN_RE.findall(question.lower()) if token not in _QUERY_STOPWORDS
        }
        sentences = [
            sentence.strip()
            for sentence in _SENTENCE_RE.split(context)
            if sentence.strip() and not _CHUNK_HEADER_RE.match(sentence.strip())
        ]
        if not query_tokens or not sentences:
            return INSUFFICIENT_EVIDENCE

        scored = [
            (sentence, len(query_tokens & set(_TOKEN_RE.findall(sentence.lower()))))
            for sentence in sentences
        ]
        supported = [sentence for sentence, count in scored if count > 0]
        if not supported:
            return INSUFFICIENT_EVIDENCE

        ordered = sorted(supported, key=len, reverse=True)[:3]
        return " ".join(ordered)

    def stream(self, prompt: str) -> Iterator[str]:
        answer = self.generate(prompt)
        for word in answer.split():
            yield word + " "

    @staticmethod
    def _section(prompt: str, header: str, next_header: str) -> str:
        start = prompt.find(header)
        if start == -1:
            return ""
        start += len(header)
        end = prompt.find(next_header, start)
        if end == -1:
            end = len(prompt)
        return prompt[start:end].strip()
