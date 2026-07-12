"""Tests for the cross-encoder reranker implementations."""

from __future__ import annotations

from ariadne.retrieval.fusion import RetrievedPassage
from ariadne.retrieval.rerank.lexical import LexicalOverlapReranker
from ariadne.retrieval.rerank.passthrough import PassthroughReranker


def _passage(chunk_id: str, text: str) -> RetrievedPassage:
    return RetrievedPassage(
        chunk_id=chunk_id,
        document_id="doc-1",
        index=0,
        page_numbers=[1],
        text=text,
        score=1.0,
    )


def test_lexical_reranker_ranks_matching_passage_first():
    reranker = LexicalOverlapReranker()
    passages = [
        _passage("a", "Unrelated content about farming and crops."),
        _passage("b", "ARIADNE combines vector search with knowledge graphs."),
    ]
    ranked = reranker.rerank("vector search knowledge graph", passages)
    assert ranked[0].chunk_id == "b"
    assert ranked[0].rerank_score is not None


def test_lexical_reranker_empty_query_scores_zero():
    reranker = LexicalOverlapReranker()
    scores = reranker.score("", ["Some text here."])
    assert scores == [0.0]


def test_lexical_reranker_empty_text_scores_zero():
    reranker = LexicalOverlapReranker()
    scores = reranker.score("query tokens", [""])
    assert scores == [0.0]


def test_passthrough_preserves_order():
    reranker = PassthroughReranker()
    passages = [_passage("a", "one"), _passage("b", "two")]
    ranked = reranker.rerank("anything", passages)
    assert [passage.chunk_id for passage in ranked] == ["a", "b"]


def test_rerank_honors_top_k():
    reranker = LexicalOverlapReranker()
    passages = [_passage(f"p{i}", f"token{i}") for i in range(5)]
    ranked = reranker.rerank("token", passages, top_k=2)
    assert len(ranked) == 2
