"""Hybrid retrieval orchestration.

Combines dense vector search with knowledge-graph traversal, fuses and
deduplicates candidates, and applies a configurable cross-encoder reranker.
"""

from __future__ import annotations

from ariadne.retrieval.fusion import RetrievedPassage, fuse_candidates, normalize_query
from ariadne.retrieval.orchestrator import HybridRetrievalService

__all__ = ["HybridRetrievalService", "RetrievedPassage", "fuse_candidates", "normalize_query"]
