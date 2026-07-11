"""Lexical overlap reranker.

A deterministic cross-encoder substitute that scores a (query, passage) pair by
lexical overlap: the fraction of query tokens appearing in the passage, with a
small boost for query token density. It needs no model weights, runs offline,
and keeps hybrid retrieval testable and reproducible. A model-backed cross-
encoder can be swapped in behind the same interface.
"""

from __future__ import annotations

import re

from ariadne.retrieval.rerank.base import CrossEncoderReranker

_TOKEN_RE = re.compile(r"[a-z0-9]+")


class LexicalOverlapReranker(CrossEncoderReranker):
    """Score passages by normalized query-token overlap."""

    def score(self, query: str, texts: list[str]) -> list[float]:
        query_tokens = set(_TOKEN_RE.findall(query.lower()))
        if not query_tokens:
            return [0.0 for _ in texts]
        scores: list[float] = []
        for text in texts:
            passage_tokens = set(_TOKEN_RE.findall(text.lower()))
            if not passage_tokens:
                scores.append(0.0)
                continue
            overlap = len(query_tokens & passage_tokens)
            coverage = overlap / len(query_tokens)
            density = overlap / len(passage_tokens)
            scores.append(coverage + 0.25 * density)
        return scores
