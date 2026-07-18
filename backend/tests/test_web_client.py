"""Tests for the bundled web client serving.

The web client is a single-page application shipped inside the package and
mounted at the application root. API routes must keep precedence over the
static mount so the SPA never shadows backend endpoints.
"""

from __future__ import annotations

from ariadne.web import WEB_STATIC_DIR, web_static_app


def test_web_static_app_points_at_bundled_assets():
    assets = web_static_app()
    assert assets.directory == WEB_STATIC_DIR
    assert WEB_STATIC_DIR.is_dir()


def test_bundled_static_assets_exist():
    for name in ("index.html", "app.js", "style.css"):
        assert (WEB_STATIC_DIR / name).is_file(), f"missing bundled asset {name}"


def test_web_root_serves_the_spa(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "ARIADNE" in response.text


def test_static_assets_are_served(client):
    expected = {"/style.css": "text/css", "/app.js": "javascript"}
    for path, ctype in expected.items():
        response = client.get(path)
        assert response.status_code == 200
        assert ctype in response.headers.get("content-type", "")


def test_spa_does_not_shadow_api_routes(client):
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["app"] == "ARIADNE"
