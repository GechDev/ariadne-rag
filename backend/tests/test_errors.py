"""Tests for the application error contract."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from ariadne.core.errors import NotFoundError


def test_error_handler_exposes_stable_payload():
    app = FastAPI()

    from ariadne.core.errors import AriadneError

    @app.exception_handler(AriadneError)
    async def handler(request, exc):  # type: ignore[no-untyped-def]
        content = {"error": {"code": exc.code, "message": exc.message}}
        return JSONResponse(status_code=exc.status_code, content=content)

    @app.get("/missing")
    def missing():
        raise NotFoundError("no such resource")

    with TestClient(app) as client:
        response = client.get("/missing")
    assert response.status_code == 404
    assert response.json() == {"error": {"code": "not_found", "message": "no such resource"}}
