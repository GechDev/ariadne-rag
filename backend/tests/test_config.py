"""Tests for application configuration."""

from __future__ import annotations

from ariadne.config import get_settings


def test_default_settings_are_sensible():
    settings = get_settings()
    assert settings.app_name == "ARIADNE"
    assert settings.environment in {"development", "test", "production"}
    assert settings.api.title == "ARIADNE API"


def test_settings_load_from_environment(monkeypatch):
    monkeypatch.setenv("ARIADNE_APP_NAME", "custom-name")
    from ariadne.config import get_settings

    get_settings.cache_clear()
    assert get_settings().app_name == "custom-name"
    get_settings.cache_clear()
