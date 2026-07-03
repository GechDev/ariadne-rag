"""Tests for the ingestion pipeline through the API."""

from __future__ import annotations


def _upload_and_ingest(client, content: str):
    upload = client.post(
        "/documents", files={"file": ("notes.txt", content.encode())}
    )
    assert upload.status_code == 201
    doc_id = upload.json()["document"]["id"]
    response = client.post(f"/documents/{doc_id}/ingest")
    assert response.status_code == 200
    return doc_id, response.json()


def test_ingest_creates_chunks_and_marks_document_ready(client):
    long_text = "Paragraph one about retrieval. " * 200
    doc_id, result = _upload_and_ingest(client, long_text)
    assert result["status"] == "ready"
    assert result["chunks"] > 1

    detail = client.get(f"/documents/{doc_id}").json()
    assert detail["status"] == "ready"
    assert detail["word_count"] is not None

    chunks = client.get(f"/documents/{doc_id}/chunks").json()
    assert len(chunks) == result["chunks"]
    assert all(chunk["document_id"] == doc_id for chunk in chunks)
    assert chunks[0]["index"] == 0


def test_ingest_short_text_produces_single_chunk(client):
    doc_id, result = _upload_and_ingest(client, "A very short note.")
    assert result["chunks"] == 1
    chunks = client.get(f"/documents/{doc_id}/chunks").json()
    assert chunks[0]["text"] == "A very short note."


def test_ingest_missing_document_returns_404(client):
    response = client.post("/documents/does-not-exist/ingest")
    assert response.status_code == 404


def test_reingest_replaces_previous_chunks(client):
    first, _ = _upload_and_ingest(client, "First version of the content. " * 50)
    upload2 = client.post(
        "/documents", files={"file": ("notes2.txt", b"Short replacement.")}
    )
    doc_id2 = upload2.json()["document"]["id"]
    client.post(f"/documents/{doc_id2}/ingest")

    chunks_after = client.get(f"/documents/{doc_id2}/chunks").json()
    assert len(chunks_after) == 1
    assert chunks_after[0]["text"] == "Short replacement."
