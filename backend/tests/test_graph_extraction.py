"""Tests for knowledge graph extraction."""

from __future__ import annotations

from ariadne.graph.extraction import KnowledgeGraphExtractor


def test_extracts_capitalized_entities():
    extractor = KnowledgeGraphExtractor()
    entities = extractor.extract_entities(
        "ARIADNE combines vector search with knowledge graphs.", "chunk-1"
    )
    names = {entity.name for entity in entities}
    assert "ARIADNE" in names
    assert "vector" not in names  # lowercase tokens are not entities


def test_entity_types_are_classified():
    extractor = KnowledgeGraphExtractor()
    entities = extractor.extract_entities(
        "Stanford University built the Retrieval Engine.", "chunk-1"
    )
    types = {entity.name: entity.entity_type for entity in entities}
    assert types.get("Stanford University") == "organization"
    assert types.get("Retrieval Engine") == "technology"


def test_extracts_relationships_between_entities():
    extractor = KnowledgeGraphExtractor()
    relationships = extractor.extract_relationships(
        "ARIADNE uses Embedding Vectors for retrieval.", "chunk-1"
    )
    assert len(relationships) >= 1
    rel = relationships[0]
    assert rel.relationship == "uses"
    assert {rel.source, rel.target} == {"ARIADNE", "Embedding Vectors"}


def test_single_entity_produces_no_relationships():
    extractor = KnowledgeGraphExtractor()
    relationships = extractor.extract_relationships(
        "ARIADNE is a system.", "chunk-1"
    )
    assert relationships == []


def test_deduplicates_entities_within_chunk():
    extractor = KnowledgeGraphExtractor()
    entities = extractor.extract_entities(
        "ARIADNE is great. ARIADNE is fast.", "chunk-1"
    )
    assert len(entities) == 1


def test_query_entity_extraction_from_service():
    from ariadne.graph.service import GraphExtractionService

    service = GraphExtractionService()
    assert service.query_entities_from_text("Tell me about ARIADNE and Embedding Vectors") == [
        "ARIADNE",
        "Embedding Vectors",
    ]
