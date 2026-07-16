"""Tests for the grounded query API and conversation history."""

from __future__ import annotations


def _ingest_grounded_doc(client, content: str) -> str:
    upload = client.post("/documents", files={"file": ("notes.txt", content.encode())})
    assert upload.status_code == 201
    doc_id = upload.json()["document"]["id"]
    assert client.post(f"/documents/{doc_id}/ingest").status_code == 200
    return doc_id


def test_query_returns_grounded_answer_with_citations(client):
    _ingest_grounded_doc(
        client,
        "ARIADNE is a local-first RAG platform for private document intelligence.\n" * 30,
    )
    response = client.post(
        "/query",
        json={"question": "What is ARIADNE?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["answer"]
    assert body["grounded"] is True
    assert body["conversation_id"]
    assert body["message_id"]
    assert body["citations"]
    citation = body["citations"][0]
    assert citation["document_title"] == "notes.txt"
    assert citation["rank"] == 1


def test_query_with_unsupported_question_reports_ungrounded(client):
    _ingest_grounded_doc(client, "The ocean is full of fish.\n" * 30)
    response = client.post(
        "/query",
        json={"question": "Who founded ARIADNE?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["grounded"] is False
    assert "not contain enough information" in body["answer"]


def test_query_requires_question(client):
    response = client.post("/query", json={"question": ""})
    assert response.status_code == 422


def test_conversation_history_roundtrip(client):
    _ingest_grounded_doc(client, "ARIADNE is a local-first RAG platform.\n" * 30)
    first = client.post("/query", json={"question": "What is ARIADNE?"}).json()

    second = client.post(
        "/query",
        json={"question": "Where is it based?", "conversation_id": first["conversation_id"]},
    )
    assert second.status_code == 200
    assert second.json()["conversation_id"] == first["conversation_id"]

    detail = client.get(f"/conversations/{first['conversation_id']}").json()
    assert len(detail["messages"]) == 4  # user+assistant for each question
    assert detail["messages"][0]["role"] == "user"
    assert detail["messages"][1]["role"] == "assistant"

    listings = client.get("/conversations").json()
    assert any(item["id"] == first["conversation_id"] for item in listings)


def test_message_citations_are_retrievable(client):
    _ingest_grounded_doc(client, "ARIADNE is a local-first RAG platform.\n" * 30)
    query = client.post("/query", json={"question": "What is ARIADNE?"}).json()

    response = client.get(
        f"/conversations/{query['conversation_id']}/messages/{query['message_id']}/citations"
    )
    assert response.status_code == 200
    assert response.json()
    assert response.json()[0]["document_title"] == "notes.txt"


def test_unknown_conversation_returns_404(client):
    response = client.get("/conversations/does-not-exist")
    assert response.status_code == 404
