"""Tests for embedding providers."""

from __future__ import annotations

from ariadne.embeddings.base import EmbeddingProvider
from ariadne.embeddings.deterministic import DeterministicEmbeddingProvider


def test_deterministic_provider_produces_expected_dimension():
    provider = DeterministicEmbeddingProvider(dimension=128)
    assert provider.dimension == 128
    vectors = provider.embed(["hello", "world"])
    assert len(vectors) == 2
    assert all(len(vector) == 128 for vector in vectors)


def test_deterministic_provider_is_consistent():
    provider = DeterministicEmbeddingProvider()
    first = provider.embed(["the quick brown fox"])
    second = provider.embed(["the quick brown fox"])
    assert first == second


def test_vectors_are_normalized():
    provider = DeterministicEmbeddingProvider(dimension=64)
    vector = provider.embed_one("a b c d e f g")
    magnitude = sum(value * value for value in vector) ** 0.5
    assert abs(magnitude - 1.0) < 1e-6


def test_semantically_similar_texts_are_closer():
    provider = DeterministicEmbeddingProvider()
    base = provider.embed_one("retrieval augmented generation")
    related = provider.embed_one("retrieval augmented generation systems")
    unrelated = provider.embed_one("the weather in paris is rainy today")
    dot_related = sum(a * b for a, b in zip(base, related, strict=False))
    dot_unrelated = sum(a * b for a, b in zip(base, unrelated, strict=False))
    assert dot_related > dot_unrelated


def test_empty_text_returns_zero_vector():
    provider = DeterministicEmbeddingProvider(dimension=32)
    vector = provider.embed_one("")
    assert all(value == 0.0 for value in vector)


def test_provider_is_embedding_protocol():
    assert isinstance(DeterministicEmbeddingProvider(), EmbeddingProvider)
