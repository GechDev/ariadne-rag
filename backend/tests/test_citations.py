"""Tests for citation resolution and persistence."""

from __future__ import annotations

import pytest

from ariadne.citations.service import CitationService
from ariadne.db.base import Base
from ariadne.db.session import get_engine, get_session_factory
from ariadne.models import Citation, Document, Message
from ariadne.models.document import DocumentStatus
from ariadne.retrieval.fusion import RetrievedPassage


@pytest.fixture()
def db_session():
    Base.metadata.create_all(get_engine())
    session = get_session_factory()()
    yield session
    session.close()


@pytest.fixture()
def seeded(db_session):
    document = Document(
        filename="report.pdf",
        content_type="application/pdf",
        size_bytes=10,
        checksum="cit-doc",
        storage_path="cit-doc.bin",
        status=DocumentStatus.READY,
        title="Annual Report",
    )
    db_session.add(document)
    db_session.flush()
    message = Message(conversation_id="conv-1", role="assistant", content="answer")
    db_session.add(message)
    db_session.flush()
    return document, message


def _passage(chunk_id: str, document_id: str, page: int) -> RetrievedPassage:
    return RetrievedPassage(
        chunk_id=chunk_id,
        document_id=document_id,
        index=3,
        page_numbers=[page],
        text="Some supporting text.",
        score=0.8,
    )


def test_resolve_attaches_document_metadata(db_session, seeded):
    document, _ = seeded
    passages = [_passage("chunk-a", document.id, 7)]
    references = CitationService().resolve(db_session, passages)
    assert len(references) == 1
    reference = references[0]
    assert reference.chunk_id == "chunk-a"
    assert reference.document_id == document.id
    assert reference.document_title == "report.pdf"
    assert reference.page_numbers == [7]
    assert reference.rank == 1


def test_resolve_orders_by_passage_rank(db_session, seeded):
    document, _ = seeded
    passages = [_passage("first", document.id, 1), _passage("second", document.id, 2)]
    references = CitationService().resolve(db_session, passages)
    assert [reference.rank for reference in references] == [1, 2]
    assert references[0].chunk_id == "first"


def test_resolve_empty_passages(db_session, seeded):
    assert CitationService().resolve(db_session, []) == []


def test_persist_writes_citation_rows(db_session, seeded):
    document, message = seeded
    service = CitationService()
    references = service.resolve(db_session, [_passage("chunk-a", document.id, 7)])
    count = service.persist(db_session, message.id, references)
    assert count == 1
    row = db_session.query(Citation).filter(Citation.message_id == message.id).one()
    assert row.chunk_id == "chunk-a"
    assert row.document_id == document.id
    assert row.rank == 1
