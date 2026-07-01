import os
from datetime import date, timedelta

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.main import _classify_mlb_readiness, _parse_cors_origins, _resolve_cors_settings
from src.main import _readiness_ok_flag
from src.main import _classify_nfl_readiness


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


def test_classify_mlb_readiness_green() -> None:
    out = _classify_mlb_readiness(
        sample_size=180,
        calendar_days=20,
        last_game_date=date.today(),
        warning_alerts_24h=0,
        min_sample_size=120,
        min_calendar_days=14,
        max_last_game_age_days=3,
    )
    assert out["status"] == "green"
    assert out["checks"]["sample_size_ok"] is True
    assert out["checks"]["calendar_days_ok"] is True
    assert out["checks"]["freshness_ok"] is True
    assert out["checks"]["alerts_ok"] is True


def test_classify_mlb_readiness_red_for_stale_data() -> None:
    out = _classify_mlb_readiness(
        sample_size=180,
        calendar_days=20,
        last_game_date=date.today() - timedelta(days=10),
        warning_alerts_24h=0,
        min_sample_size=120,
        min_calendar_days=14,
        max_last_game_age_days=3,
    )
    assert out["status"] == "red"
    assert "stale_or_missing_outcomes" in out["reasons"]


def test_readiness_ok_flag_mapping() -> None:
    assert _readiness_ok_flag("green") == 1
    assert _readiness_ok_flag("yellow") == 1
    assert _readiness_ok_flag("red") == 0
    assert _readiness_ok_flag("unknown") == 0


def test_classify_nfl_readiness_go() -> None:
    out = _classify_nfl_readiness(
        sample_size=220,
        calendar_days=21,
        last_game_date=date.today(),
        moneyline_brier=0.226,
        total_mae=5.2,
        clv_avg=0.012,
        min_sample_size=100,
        min_calendar_days=14,
        max_last_game_age_days=8,
        max_moneyline_brier=0.255,
        max_total_mae=6.0,
        min_clv_avg=0.0,
    )
    assert out["status"] == "go"
    assert out["checks"]["sample_size_ok"] is True
    assert out["checks"]["moneyline_brier_ok"] is True
    assert out["checks"]["clv_ok"] is True


def test_classify_nfl_readiness_no_go_for_stale_and_error() -> None:
    out = _classify_nfl_readiness(
        sample_size=80,
        calendar_days=9,
        last_game_date=date.today() - timedelta(days=20),
        moneyline_brier=0.29,
        total_mae=7.1,
        clv_avg=-0.015,
        min_sample_size=100,
        min_calendar_days=14,
        max_last_game_age_days=8,
        max_moneyline_brier=0.255,
        max_total_mae=6.0,
        min_clv_avg=0.0,
    )
    assert out["status"] == "no-go"
    assert "sample_size_ok" in out["reasons"]
    assert "freshness_ok" in out["reasons"]
    assert "moneyline_brier_ok" in out["reasons"]

