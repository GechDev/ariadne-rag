"""Tests for the SSE streaming endpoint."""

from __future__ import annotations

import json


def _ingest(client, content: str) -> str:
    upload = client.post("/documents", files={"file": ("notes.txt", content.encode())})
    assert upload.status_code == 201
    doc_id = upload.json()["document"]["id"]
    assert client.post(f"/documents/{doc_id}/ingest").status_code == 200
    return doc_id


def _read_stream(response):
    events: list[tuple[str, dict]] = []
    for line in response.iter_lines():
        if line.startswith("event: "):
            events.append((line[len("event: ") :], None))
        elif line.startswith("data: "):
            events[-1] = (events[-1][0], json.loads(line[len("data: ") :]))
    return events


def test_stream_emits_full_lifecycle(client):
    _ingest(client, "ARIADNE is a local-first RAG platform for document intelligence.\n" * 30)
    with client.stream(
        "POST", "/query/stream", json={"question": "What is ARIADNE?"}
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        events = _read_stream(response)

    names = [name for name, _ in events]
    assert names[0] == "retrieval_started"
    assert "retrieval_completed" in names
    assert "sources_found" in names
    assert "generation_started" in names
    assert "token" in names
    assert names[-2] == "generation_completed"
    assert names[-1] == "done"

    completion = dict(events)["generation_completed"]
    assert completion["answer"]
    assert completion["grounded"] is True
    assert completion["message_id"]
    assert completion["conversation_id"]
    assert completion["citations"]

    sources = dict(events)["sources_found"]
    assert sources["sources"]
    assert sources["sources"][0]["document_title"] == "notes.txt"

    tokens = "".join(data["token"] for name, data in events if name == "token")
    assert "local-first" in tokens


def test_stream_persists_conversation(client):
    _ingest(client, "ARIADNE is a local-first RAG platform.\n" * 30)
    with client.stream(
        "POST", "/query/stream", json={"question": "What is ARIADNE?"}
    ) as response:
        events = _read_stream(response)
    completion = dict(events)["generation_completed"]

    detail = client.get(f"/conversations/{completion['conversation_id']}").json()
    assert len(detail["messages"]) == 2
    assert detail["messages"][0]["role"] == "user"
    assert detail["messages"][1]["role"] == "assistant"


def test_stream_reports_unknown_conversation(client):
    with client.stream(
        "POST", "/query/stream", json={"question": "hi", "conversation_id": "missing"}
    ) as response:
        events = _read_stream(response)
    names = dict(events)
    assert "error" in names
    assert names["error"]["code"] == "not_found"


def test_stream_rejects_empty_question(client):
    response = client.post("/query/stream", json={"question": ""})
    assert response.status_code == 422
