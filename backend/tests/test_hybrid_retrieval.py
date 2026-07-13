"""Integration tests for hybrid retrieval through the API."""

from __future__ import annotations


def _upload_and_ingest(client, content: str):
    upload = client.post("/documents", files={"file": ("notes.txt", content.encode())})
    assert upload.status_code == 201
    doc_id = upload.json()["document"]["id"]
    response = client.post(f"/documents/{doc_id}/ingest")
    assert response.status_code == 200
    return doc_id


def test_hybrid_search_returns_ranked_hits(client):
    content = (
        "ARIADNE combines vector search with Embedding Vectors.\n"
        "Embedding Vectors connect to Neural Networks.\n"
        "The Graph Store traverses entity relationships for retrieval.\n"
    ) * 30
    doc_id = _upload_and_ingest(client, content)

    response = client.get("/retrieval/hybrid/search", params={"q": "ARIADNE vector search"})
    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "ARIADNE vector search"
    assert body["hits"]
    assert all(hit["document_id"] == doc_id for hit in body["hits"])
    assert all(hit["score"] >= 0 for hit in body["hits"])
    assert any("vector" in hit["sources"] for hit in body["hits"])


def test_hybrid_search_surfaces_graph_sources(client):
    content = (
        "Stanford University develops Retrieval Systems.\n"
        "Retrieval Systems depend on Knowledge Graphs.\n"
    ) * 30
    _upload_and_ingest(client, content)

    response = client.get(
        "/retrieval/hybrid/search", params={"q": "What does Stanford University develop?"}
    )
    assert response.status_code == 200
    hits = response.json()["hits"]
    assert hits
    assert any("graph" in hit["sources"] for hit in hits)


def test_hybrid_search_supports_document_filter(client):
    _upload_and_ingest(client, "ARIADNE uses Embedding Vectors for retrieval.\n" * 40)
    other = _upload_and_ingest(client, "Completely unrelated agriculture notes.\n" * 40)

    response = client.get(
        "/retrieval/hybrid/search",
        params={"q": "ARIADNE embedding", "document_ids": other},
    )
    assert response.status_code == 200
    hits = response.json()["hits"]
    if hits:
        assert all(hit["document_id"] == other for hit in hits)


def test_hybrid_search_rejects_empty_query(client):
    response = client.get("/retrieval/hybrid/search", params={"q": ""})
    assert response.status_code == 422
