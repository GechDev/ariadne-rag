"""Tests for the vector search API endpoint."""

from __future__ import annotations


def _seed_document(client, content: str) -> str:
    upload = client.post("/documents", files={"file": ("doc.txt", content.encode())})
    doc_id = upload.json()["document"]["id"]
    ingest = client.post(f"/documents/{doc_id}/ingest")
    assert ingest.status_code == 200
    return doc_id


def test_vector_search_returns_matching_chunks(client):
    _seed_document(client, "The capital of France is Paris. " * 200)
    response = client.get("/retrieval/vector/search", params={"q": "capital of France", "top_k": 5})
    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "capital of France"
    assert len(body["hits"]) > 0
    assert body["hits"][0]["score"] >= 0.0
    assert "document_id" in body["hits"][0]
    assert "page_numbers" in body["hits"][0]


def test_vector_search_requires_query(client):
    response = client.get("/retrieval/vector/search")
    assert response.status_code == 422


def test_vector_search_returns_empty_for_empty_index(client):
    response = client.get("/retrieval/vector/search", params={"q": "anything"})
    assert response.status_code == 200
    assert response.json()["hits"] == []


def test_vector_search_filters_by_document(client):
    doc_id = _seed_document(client, "Bananas are yellow fruits. " * 100)
    response = client.get(
        "/retrieval/vector/search", params={"q": "bananas", "document_ids": [doc_id]}
    )
    assert response.status_code == 200
    hits = response.json()["hits"]
    assert len(hits) > 0
    assert all(hit["document_id"] == doc_id for hit in hits)
