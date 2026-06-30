"""Tests for the health check endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient

from ariadne.main import app


def test_health_returns_ok():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["app"] == "ARIADNE"
    assert "database" in body
