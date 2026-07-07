"""Tests for the knowledge graph store and traversal."""

from __future__ import annotations

import pytest

from ariadne.db.base import Base
from ariadne.db.session import get_engine, get_session_factory
from ariadne.graph.store import GraphStore
from ariadne.models import Chunk, Document, GraphEntity
from ariadne.models.document import DocumentStatus


@pytest.fixture()
def db_session():
    Base.metadata.create_all(get_engine())
    session = get_session_factory()()
    yield session
    session.close()


@pytest.fixture()
def seeded_graph(db_session):
    document = Document(
        filename="g.txt",
        content_type="text/plain",
        size_bytes=10,
        checksum="graph-doc",
        storage_path="graph-doc.bin",
        status=DocumentStatus.READY,
    )
    db_session.add(document)
    db_session.flush()

    chunks = [
        Chunk(
            document_id=document.id,
            index=0,
            text="ARIADNE uses Embedding Vectors.",
            page_numbers=[1],
        ),
        Chunk(
            document_id=document.id,
            index=1,
            text="Embedding Vectors connect to Neural Networks.",
            page_numbers=[2],
        ),
    ]
    db_session.add_all(chunks)
    db_session.flush()

    store = GraphStore()
    entities = [
        {"name": "ARIADNE", "entity_type": "technology", "chunk_ids": [chunks[0].id]},
        {
            "name": "Embedding Vectors",
            "entity_type": "technology",
            "chunk_ids": [chunks[0].id, chunks[1].id],
        },
        {"name": "Neural Networks", "entity_type": "concept", "chunk_ids": [chunks[1].id]},
    ]
    relationships = [
        {
            "source": "ARIADNE",
            "target": "Embedding Vectors",
            "relationship": "uses",
            "chunk_ids": [chunks[0].id],
        },
        {
            "source": "Embedding Vectors",
            "target": "Neural Networks",
            "relationship": "connects_to",
            "chunk_ids": [chunks[1].id],
        },
    ]
    store.save_document_graph(db_session, document.id, entities, relationships)
    db_session.flush()
    return document.id, chunks, store


def test_save_and_load_graph_roundtrip(db_session, seeded_graph):
    document_id, _, store = seeded_graph
    graph = store.get_document_graph(db_session, document_id)
    assert len(graph.nodes) == 3
    assert len(graph.edges) == 2


def test_nodes_carry_chunk_provenance(db_session, seeded_graph):
    document_id, chunks, store = seeded_graph
    nodes = store.get_document_nodes(db_session, document_id)
    vectors = {node.name: node for node in nodes}
    assert "Embedding Vectors" in vectors
    assert vectors["Embedding Vectors"].chunk_ids == [chunks[0].id, chunks[1].id]


def test_search_finds_chunks_for_query_entity(db_session, seeded_graph):
    document_id, chunks, store = seeded_graph
    matches = store.search(db_session, ["ARIADNE"])
    assert len(matches) >= 1
    assert matches[0].chunk_id == chunks[0].id
    assert matches[0].score >= 1.0


def test_search_expands_to_related_entities(db_session, seeded_graph):
    _, chunks, store = seeded_graph
    matches = store.search(db_session, ["Embedding Vectors"], depth=1)
    chunk_ids = {match.chunk_id for match in matches}
    assert chunks[0].id in chunk_ids
    assert chunks[1].id in chunk_ids


def test_search_returns_empty_for_unknown_entity(db_session, seeded_graph):
    _, _, store = seeded_graph
    assert store.search(db_session, ["DoesNotExist"]) == []


def test_delete_document_removes_graph(db_session, seeded_graph):
    document_id, _, store = seeded_graph
    store.delete_document(db_session, document_id)
    assert store.get_document_graph(db_session, document_id).number_of_nodes() == 0
    assert db_session.query(GraphEntity).filter(GraphEntity.document_id == document_id).count() == 0
