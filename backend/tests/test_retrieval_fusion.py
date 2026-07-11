"""Tests for hybrid retrieval candidate fusion."""

from __future__ import annotations

from ariadne.graph.store import GraphMatch
from ariadne.retrieval.fusion import fuse_candidates, normalize_query
from ariadne.vectors.store import VectorMatch


def _vector_match(chunk_id: str, score: float) -> VectorMatch:
    return VectorMatch(
        chunk_id=chunk_id,
        document_id="doc-1",
        index=0,
        page_numbers=[1],
        text=chunk_id,
        score=score,
    )


def _graph_match(chunk_id: str, score: float) -> GraphMatch:
    return GraphMatch(chunk_id=chunk_id, document_id="doc-1", entities=["ARIADNE"], score=score)


def test_normalize_query_collapses_whitespace():
    assert normalize_query("  hello   world \t") == "hello world"
    assert normalize_query("   ") == ""


def test_fusion_merges_vector_and_graph_candidates():
    vector = [_vector_match("a", 0.9), _vector_match("b", 0.5)]
    graph = [_graph_match("b", 4.0), _graph_match("c", 2.0)]
    fused = fuse_candidates(vector, graph, vector_weight=1.0, graph_weight=0.5)

    ids = {passage.chunk_id for passage in fused}
    assert ids == {"a", "b", "c"}
    by_id = {passage.chunk_id: passage for passage in fused}
    assert by_id["b"].sources == ["vector", "graph"]
    assert by_id["a"].sources == ["vector"]
    assert by_id["c"].sources == ["graph"]


def test_fusion_deduplicates_shared_chunks():
    vector = [_vector_match("a", 0.8)]
    graph = [_graph_match("a", 3.0)]
    fused = fuse_candidates(vector, graph, vector_weight=1.0, graph_weight=0.5)
    assert len(fused) == 1
    passage = fused[0]
    assert passage.vector_score is not None
    assert passage.graph_score is not None
    assert passage.score > passage.vector_score  # graph contribution increases the total


def test_fusion_scores_are_weighted_and_ordered():
    vector = [_vector_match("a", 1.0), _vector_match("b", 0.0)]
    fused = fuse_candidates(vector, [], vector_weight=1.0, graph_weight=0.5)
    assert fused[0].chunk_id == "a"
    assert fused[0].score == 1.0
    assert fused[1].score == 0.0


def test_fusion_with_empty_candidates():
    assert fuse_candidates([], [], vector_weight=1.0, graph_weight=0.5) == []
    fused = fuse_candidates([_vector_match("a", 0.7)], [], vector_weight=1.0, graph_weight=0.5)
    assert [passage.chunk_id for passage in fused] == ["a"]
