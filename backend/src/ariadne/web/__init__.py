"""Bundled web client for ARIADNE.

A single-page application served directly by the backend so the whole platform
runs from one process. Static assets live in ``static/`` and ship inside the
installed package alongside the API modules.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.staticfiles import StaticFiles

WEB_STATIC_DIR = Path(__file__).parent / "static"


def web_static_app() -> StaticFiles:
    """Return a ``StaticFiles`` app serving the bundled web client."""
    return StaticFiles(directory=WEB_STATIC_DIR, html=True)
