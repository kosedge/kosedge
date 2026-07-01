import os
from datetime import date

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src import tasks


def _good_holdout_profile() -> dict:
    return {
        "common_sample_size": 140,
        "bucket_count": 3,
        "dual_bucket_wins": 3,
        "worst_brier_improvement": 0.0014,
        "worst_mae_improvement": 0.06,
    }


def _weak_holdout_profile() -> dict:
    return {
        "common_sample_size": 60,
        "bucket_count": 3,
        "dual_bucket_wins": 1,
        "worst_brier_improvement": -0.0026,
        "worst_mae_improvement": -0.11,
    }


def test_decide_challenger_promotion_passes_with_clear_improvement(monkeypatch) -> None:
    today = date.today().isoformat()
    monkeypatch.setenv("MLB_PROMOTION_MIN_SAMPLE_SIZE", "100")
    monkeypatch.setenv("MLB_PROMOTION_MIN_CALENDAR_DAYS", "10")
    monkeypatch.setenv("MLB_PROMOTION_MAX_LAST_GAME_AGE_DAYS", "7")
    monkeypatch.setenv("MLB_PROMOTION_MIN_BRIER_IMPROVEMENT", "0.001")
    monkeypatch.setenv("MLB_PROMOTION_MIN_MAE_IMPROVEMENT", "0.05")
    monkeypatch.setenv("MLB_PROMOTION_MIN_TOTAL_CLV_IMPROVEMENT", "0.002")

    decision = tasks._decide_challenger_promotion(
        base_quality={
            "sample_size": 180,
            "brier_ml": 0.252,
            "mae_total_runs": 1.42,
            "avg_total_clv": 0.004,
            "calendar_days_covered": 16,
            "last_game_date": today,
        },
        challenger_quality={
            "sample_size": 185,
            "brier_ml": 0.247,
            "mae_total_runs": 1.31,
            "avg_total_clv": 0.009,
            "calendar_days_covered": 16,
            "last_game_date": today,
        },
        holdout_profile=_good_holdout_profile(),
    )
    assert decision["promote"] is True
    assert decision["checks"]["sample_size_ok"] is True
    assert decision["checks"]["calendar_days_ok"] is True
    assert decision["checks"]["freshness_ok"] is True
    assert decision["checks"]["brier_ok"] is True
    assert decision["checks"]["mae_ok"] is True
    assert decision["checks"]["clv_ok"] is True
    assert decision["checks"]["holdout_sample_ok"] is True
    assert decision["checks"]["holdout_consistency_ok"] is True
    assert decision["checks"]["holdout_regression_ok"] is True


def test_decide_challenger_promotion_blocks_on_sample_size(monkeypatch) -> None:
    today = date.today().isoformat()
    monkeypatch.setenv("MLB_PROMOTION_MIN_SAMPLE_SIZE", "300")
    monkeypatch.setenv("MLB_PROMOTION_MIN_CALENDAR_DAYS", "10")
    monkeypatch.setenv("MLB_PROMOTION_MAX_LAST_GAME_AGE_DAYS", "7")
    monkeypatch.setenv("MLB_PROMOTION_MIN_BRIER_IMPROVEMENT", "0.001")
    monkeypatch.setenv("MLB_PROMOTION_MIN_MAE_IMPROVEMENT", "0.05")
    monkeypatch.setenv("MLB_PROMOTION_MIN_TOTAL_CLV_IMPROVEMENT", "0.002")

    decision = tasks._decide_challenger_promotion(
        base_quality={
            "sample_size": 100,
            "brier_ml": 0.250,
            "mae_total_runs": 1.40,
            "avg_total_clv": 0.003,
            "calendar_days_covered": 14,
            "last_game_date": today,
        },
        challenger_quality={
            "sample_size": 95,
            "brier_ml": 0.240,
            "mae_total_runs": 1.30,
            "avg_total_clv": 0.010,
            "calendar_days_covered": 14,
            "last_game_date": today,
        },
        holdout_profile=_good_holdout_profile(),
    )
    assert decision["promote"] is False
    assert "insufficient_sample_size" in decision["reasons"]


def test_decide_challenger_promotion_blocks_on_calendar_coverage(monkeypatch) -> None:
    today = date.today().isoformat()
    monkeypatch.setenv("MLB_PROMOTION_MIN_SAMPLE_SIZE", "50")
    monkeypatch.setenv("MLB_PROMOTION_MIN_CALENDAR_DAYS", "20")
    monkeypatch.setenv("MLB_PROMOTION_MAX_LAST_GAME_AGE_DAYS", "7")
    monkeypatch.setenv("MLB_PROMOTION_MIN_BRIER_IMPROVEMENT", "0.001")
    monkeypatch.setenv("MLB_PROMOTION_MIN_MAE_IMPROVEMENT", "0.05")
    monkeypatch.setenv("MLB_PROMOTION_MIN_TOTAL_CLV_IMPROVEMENT", "0.002")

    decision = tasks._decide_challenger_promotion(
        base_quality={
            "sample_size": 180,
            "brier_ml": 0.252,
            "mae_total_runs": 1.42,
            "avg_total_clv": 0.004,
            "calendar_days_covered": 12,
            "last_game_date": today,
        },
        challenger_quality={
            "sample_size": 185,
            "brier_ml": 0.247,
            "mae_total_runs": 1.31,
            "avg_total_clv": 0.009,
            "calendar_days_covered": 12,
            "last_game_date": today,
        },
        holdout_profile=_good_holdout_profile(),
    )
    assert decision["promote"] is False
    assert "insufficient_calendar_days" in decision["reasons"]


def test_decide_challenger_promotion_blocks_on_holdout_profile(monkeypatch) -> None:
    today = date.today().isoformat()
    monkeypatch.setenv("MLB_PROMOTION_MIN_SAMPLE_SIZE", "50")
    monkeypatch.setenv("MLB_PROMOTION_MIN_CALENDAR_DAYS", "10")
    monkeypatch.setenv("MLB_PROMOTION_MAX_LAST_GAME_AGE_DAYS", "7")
    monkeypatch.setenv("MLB_PROMOTION_MIN_BRIER_IMPROVEMENT", "0.001")
    monkeypatch.setenv("MLB_PROMOTION_MIN_MAE_IMPROVEMENT", "0.05")
    monkeypatch.setenv("MLB_PROMOTION_MIN_TOTAL_CLV_IMPROVEMENT", "0.002")
    monkeypatch.setenv("MLB_PROMOTION_MIN_HOLDOUT_SAMPLE_SIZE", "90")
    monkeypatch.setenv("MLB_PROMOTION_MIN_HOLDOUT_BUCKET_WIN_RATE", "0.67")

    decision = tasks._decide_challenger_promotion(
        base_quality={
            "sample_size": 180,
            "brier_ml": 0.252,
            "mae_total_runs": 1.42,
            "avg_total_clv": 0.004,
            "calendar_days_covered": 16,
            "last_game_date": today,
        },
        challenger_quality={
            "sample_size": 185,
            "brier_ml": 0.247,
            "mae_total_runs": 1.31,
            "avg_total_clv": 0.009,
            "calendar_days_covered": 16,
            "last_game_date": today,
        },
        holdout_profile=_weak_holdout_profile(),
    )

    assert decision["promote"] is False
    assert decision["checks"]["holdout_sample_ok"] is False
    assert decision["checks"]["holdout_consistency_ok"] is False
    assert decision["checks"]["holdout_regression_ok"] is False
    assert "insufficient_holdout_sample" in decision["reasons"]
    assert "holdout_bucket_consistency_failed" in decision["reasons"]
    assert "holdout_bucket_regression_too_large" in decision["reasons"]


def test_compute_holdout_profile_aligns_common_games_and_buckets() -> None:
    base_points = [
        {
            "game_id": f"g{i}",
            "game_date": f"2026-04-0{i}",
            "fg_home_win_prob": 0.55,
            "fg_total_mean": 8.6,
            "home_team_won": i % 2 == 0,
            "final_total_runs": 8 + i,
        }
        for i in range(1, 7)
    ]
    challenger_points = [
        {
            "game_id": f"g{i}",
            "game_date": f"2026-04-0{i}",
            "fg_home_win_prob": 0.57 if i % 2 == 0 else 0.43,
            "fg_total_mean": 8.0 + i,
            "home_team_won": i % 2 == 0,
            "final_total_runs": 8 + i,
        }
        for i in range(1, 7)
    ] + [
        {
            "game_id": "g-extra",
            "game_date": "2026-04-09",
            "fg_home_win_prob": 0.52,
            "fg_total_mean": 8.8,
            "home_team_won": True,
            "final_total_runs": 9,
        }
    ]

    profile = tasks._compute_holdout_profile(
        base_points=base_points,
        challenger_points=challenger_points,
        bucket_count=3,
    )

    assert profile["common_sample_size"] == 6
    assert profile["bucket_count"] == 3
    assert profile["bucket_size_min"] == 2
    assert profile["bucket_size_max"] == 2
    assert len(profile["buckets"]) == 3
