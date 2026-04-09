import os

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.main import _parse_cors_origins, _resolve_cors_settings


def test_parse_cors_origins_splits_and_trims() -> None:
    raw = " https://a.com,https://b.com ,  "
    assert _parse_cors_origins(raw) == ["https://a.com", "https://b.com"]


def test_resolve_cors_defaults_to_localhost_in_dev(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    monkeypatch.setenv("ENV", "development")

    origins, allow_credentials = _resolve_cors_settings()
    assert "http://localhost:3000" in origins
    assert allow_credentials is True


def test_resolve_cors_requires_origins_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    monkeypatch.setenv("ENV", "production")

    with pytest.raises(RuntimeError, match="CORS_ORIGINS must be set in production"):
        _resolve_cors_settings()


def test_resolve_cors_disallows_wildcard_mix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("CORS_ORIGINS", "*,https://app.example.com")

    with pytest.raises(RuntimeError, match="cannot mix '\\*' with explicit origins"):
        _resolve_cors_settings()


def test_resolve_cors_wildcard_disables_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "development")
    monkeypatch.setenv("CORS_ORIGINS", "*")

    origins, allow_credentials = _resolve_cors_settings()
    assert origins == ["*"]
    assert allow_credentials is False

