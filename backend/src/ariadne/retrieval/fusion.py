"""Candidate fusion for hybrid retrieval.

Vector and knowledge-graph retrieval produce heterogeneous scores (cosine
similarities vs. aggregate graph proximity). Fusion normalizes each stream
independently, merges candidates by chunk, applies the configured weights,
and returns a single deduplicated list of passages.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ariadne.graph.store import GraphMatch
from ariadne.vectors.store import VectorMatch

_WS_RE = re.compile(r"\s+")


@dataclass(slots=True)
class RetrievedPassage:
    """A single retrieval hit with scores and provenance metadata."""

    chunk_id: str
    document_id: str
    index: int
    page_numbers: list[int]
    text: str
    vector_score: float | None = None
    graph_score: float | None = None
    score: float = 0.0
    rerank_score: float | None = None
    sources: list[str] = field(default_factory=list)


def normalize_query(query: str) -> str:
    """Collapse whitespace and trim the raw query string."""
    return _WS_RE.sub(" ", query).strip()


def _normalize_scores(values: list[float]) -> list[float]:
    """Scale scores to the [0, 1] range using min-max normalization."""
    if not values:
        return []
    maximum = max(values)
    if maximum <= 0:
        return [0.0 for _ in values]
    minimum = min(values)
    span = maximum - minimum
    if span <= 0:
        return [value / maximum for value in values]
    return [(value - minimum) / span for value in values]


def fuse_candidates(
    vector_matches: list[VectorMatch],
    graph_matches: list[GraphMatch],
    *,
    vector_weight: float,
    graph_weight: float,
) -> list[RetrievedPassage]:
    """Merge vector and graph matches into deduplicated, weighted passages."""
    merged: dict[str, RetrievedPassage] = {}

    vector_scores = _normalize_scores([match.score for match in vector_matches])
    for match, normalized in zip(vector_matches, vector_scores, strict=True):
        merged[match.chunk_id] = RetrievedPassage(
            chunk_id=match.chunk_id,
            document_id=match.document_id,
            index=match.index,
            page_numbers=list(match.page_numbers),
            text=match.text,
            vector_score=normalized,
            sources=["vector"],
        )

    graph_scores = _normalize_scores([match.score for match in graph_matches])
    for graph_match, normalized in zip(graph_matches, graph_scores, strict=True):
        passage = merged.get(graph_match.chunk_id)
        if passage is None:
            merged[graph_match.chunk_id] = RetrievedPassage(
                chunk_id=graph_match.chunk_id,
                document_id=graph_match.document_id,
                index=0,
                page_numbers=[],
                text="",
                graph_score=normalized,
                sources=["graph"],
            )
        else:
            passage.graph_score = normalized
            if "graph" not in passage.sources:
                passage.sources.append("graph")
    for passage in merged.values():
        vector = passage.vector_score or 0.0
        graph = passage.graph_score or 0.0
        passage.score = vector_weight * vector + graph_weight * graph

    return sorted(merged.values(), key=lambda passage: passage.score, reverse=True)
