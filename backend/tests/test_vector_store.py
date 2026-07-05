"""Tests for the vector store."""

from __future__ import annotations

import pytest

from ariadne.core.errors import VectorStoreError
from ariadne.db.base import Base
from ariadne.db.session import get_engine, get_session_factory
from ariadne.models import Document
from ariadne.models.document import DocumentStatus
from ariadne.vectors.numpy_store import NumpyVectorStore
from ariadne.vectors.store import VectorRecord


@pytest.fixture()
def db_session():
    Base.metadata.create_all(get_engine())
    session = get_session_factory()()
    yield session
    session.close()


@pytest.fixture()
def seed_records():
    Document(
        filename="a.txt",
        content_type="text/plain",
        size_bytes=10,
        checksum="aa",
        storage_path="aa.bin",
        status=DocumentStatus.READY,
    )
    records = [
        VectorRecord(
            chunk_id=f"chunk-{i}",
            document_id="doc-1",
            index=i,
            vector=vector,
            page_numbers=[i],
            text=f"sample chunk {i}",
        )
        for i, vector in enumerate(
            [[1.0, 0.0, 0.0], [0.9, 0.1, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        )
    ]
    return records


def test_upsert_and_count(db_session, seed_records):
    store = NumpyVectorStore()
    assert store.upsert(db_session, seed_records) == 4
    assert store.count(db_session) == 4


def test_search_returns_most_similar_first(db_session, seed_records):
    store = NumpyVectorStore()
    store.upsert(db_session, seed_records)
    matches = store.search(db_session, [1.0, 0.0, 0.0], top_k=2)
    assert matches[0].chunk_id == "chunk-0"
    assert matches[1].chunk_id == "chunk-1"
    assert matches[0].score >= matches[1].score


def test_search_respects_top_k(db_session, seed_records):
    store = NumpyVectorStore()
    store.upsert(db_session, seed_records)
    matches = store.search(db_session, [1.0, 0.0, 0.0], top_k=1)
    assert len(matches) == 1


def test_search_respects_document_filter(db_session, seed_records):
    store = NumpyVectorStore()
    store.upsert(db_session, seed_records)
    matches = store.search(db_session, [0.0, 1.0, 0.0], document_ids=["other-doc"])
    assert matches == []


def test_delete_document_removes_only_its_vectors(db_session, seed_records):
    store = NumpyVectorStore()
    store.upsert(db_session, seed_records)
    store.upsert(
        db_session,
        [
            VectorRecord(
                chunk_id="chunk-other",
                document_id="doc-2",
                index=0,
                vector=[0.5, 0.5, 0.0],
                page_numbers=[1],
                text="other",
            )
        ],
    )
    assert store.delete_document(db_session, "doc-1") == 4
    assert store.count(db_session) == 1


def test_upsert_replaces_existing_chunk(db_session, seed_records):
    store = NumpyVectorStore()
    store.upsert(db_session, seed_records)
    replacement = [
        VectorRecord(
            chunk_id="chunk-0",
            document_id="doc-1",
            index=0,
            vector=[0.0, 0.0, 1.0],
            page_numbers=[1],
            text="replaced",
        )
    ]
    store.upsert(db_session, replacement)
    assert store.count(db_session) == 4
    matches = store.search(db_session, [0.0, 0.0, 1.0], top_k=1)
    assert matches[0].chunk_id == "chunk-0"
    assert matches[0].text == "replaced"


def test_mixed_dimension_batch_raises(db_session, seed_records):
    store = NumpyVectorStore()
    bad = seed_records + [
        VectorRecord(
            chunk_id="chunk-bad",
            document_id="doc-1",
            index=99,
            vector=[1.0, 2.0],
            page_numbers=[1],
            text="bad",
        )
    ]
    with pytest.raises(VectorStoreError):
        store.upsert(db_session, bad)
