import os
from datetime import date, timedelta

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.routes.mlb import _classify_go_no_go


def test_classify_go_no_go_green() -> None:
    result = _classify_go_no_go(
        sample_size=180,
        calendar_days=20,
        last_game_date=date.today(),
        warning_alerts_24h=0,
        min_sample_size=120,
        min_calendar_days=14,
        max_last_game_age_days=3,
    )
    assert result["status"] == "green"
    assert result["checks"]["sample_size_ok"] is True
    assert result["checks"]["calendar_days_ok"] is True
    assert result["checks"]["freshness_ok"] is True
    assert result["checks"]["alerts_ok"] is True


def test_classify_go_no_go_yellow_on_recent_warning_alerts() -> None:
    result = _classify_go_no_go(
        sample_size=180,
        calendar_days=20,
        last_game_date=date.today(),
        warning_alerts_24h=2,
        min_sample_size=120,
        min_calendar_days=14,
        max_last_game_age_days=3,
    )
    assert result["status"] == "yellow"
    assert "recent_warning_alerts" in result["reasons"]


def test_classify_go_no_go_red_on_stale_and_low_coverage() -> None:
    result = _classify_go_no_go(
        sample_size=80,
        calendar_days=8,
        last_game_date=date.today() - timedelta(days=6),
        warning_alerts_24h=0,
        min_sample_size=120,
        min_calendar_days=14,
        max_last_game_age_days=3,
    )
    assert result["status"] == "red"
    assert "low_sample_size" in result["reasons"]
    assert "low_calendar_coverage" in result["reasons"]
    assert "stale_or_missing_outcomes" in result["reasons"]
