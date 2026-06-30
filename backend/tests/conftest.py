"""Shared pytest fixtures for ARIADNE tests."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("ARIADNE_ENVIRONMENT", "test")
os.environ.setdefault("ARIADNE_DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("ARIADNE_LOG_LEVEL", "ERROR")

from ariadne.config import get_settings  # noqa: E402


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
