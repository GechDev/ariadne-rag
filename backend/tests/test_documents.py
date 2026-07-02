"""Tests for the document lifecycle API."""

from __future__ import annotations


def _upload(
    client, *, filename: str = "sample.txt", content="Hello ARIADNE", declared: str | None = None
):
    payload = content.encode() if isinstance(content, str) else content
    files = {"file": (filename, payload)}
    data = {"content_type": declared} if declared else None
    return client.post("/documents", files=files, data=data)


def test_upload_and_retrieve_document(client):
    response = _upload(client, content="The quick brown fox.")
    assert response.status_code == 201
    body = response.json()["document"]
    assert body["filename"] == "sample.txt"
    assert body["content_type"] == "text/plain"
    assert body["status"] == "uploaded"

    doc_id = body["id"]
    fetched = client.get(f"/documents/{doc_id}")
    assert fetched.status_code == 200
    assert fetched.json()["filename"] == "sample.txt"


def test_list_documents_returns_all(client):
    _upload(client, filename="a.txt", content="first")
    _upload(client, filename="b.txt", content="second")
    listing = client.get("/documents")
    assert listing.status_code == 200
    assert len(listing.json()) == 2


def test_duplicate_content_is_rejected(client):
    _upload(client, filename="a.txt", content="same bytes")
    duplicate = _upload(client, filename="b.txt", content="same bytes")
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "conflict"


def test_unsupported_file_type_is_rejected(client):
    response = _upload(client, filename="evil.exe", content=b"MZ")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "unsupported_document_type"


def test_missing_document_returns_404(client):
    response = client.get("/documents/nonexistent-id")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_update_document_title(client):
    doc_id = _upload(client).json()["document"]["id"]
    response = client.patch(f"/documents/{doc_id}", json={"title": "My Notes"})
    assert response.status_code == 200
    assert response.json()["title"] == "My Notes"


def test_delete_document(client):
    doc_id = _upload(client).json()["document"]["id"]
    response = client.delete(f"/documents/{doc_id}")
    assert response.status_code == 200
    assert response.json()["deleted"] is True
    assert client.get(f"/documents/{doc_id}").status_code == 404
