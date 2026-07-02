"""Shared pytest fixtures for ARIADNE tests."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("ARIADNE_ENVIRONMENT", "test")
os.environ.setdefault("ARIADNE_DATABASE__URL", "sqlite:///:memory:")
os.environ.setdefault("ARIADNE_LOG_LEVEL", "ERROR")

from fastapi.testclient import TestClient  # noqa: E402

from ariadne.config import get_settings  # noqa: E402
from ariadne.db.base import Base  # noqa: E402
from ariadne.db.session import dispose_engine, get_engine  # noqa: E402
from ariadne.main import create_app  # noqa: E402
from ariadne.models import Document  # noqa: F401, E402


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
    dispose_engine()


@pytest.fixture()
def app():
    Base.metadata.create_all(get_engine())
    yield create_app()
    dispose_engine()


@pytest.fixture()
def client(app):
    with TestClient(app) as test_client:
        yield test_client
