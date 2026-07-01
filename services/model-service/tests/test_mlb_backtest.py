import os
from datetime import datetime, timedelta, timezone

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.tasks import (
    _apply_prob_calibrator,
    _build_prob_calibrator,
    _count_leakage_violations,
    _walkforward_backtest,
)


def _make_point(day_offset: int, prob: float, won: bool) -> dict:
    base_date = datetime(2026, 4, 1, tzinfo=timezone.utc) + timedelta(days=day_offset)
    return {
        "game_id": f"g-{day_offset}-{prob}",
        "game_date": base_date.date().isoformat(),
        "fg_home_win_prob": prob,
        "fg_total_mean": 8.6,
        "home_team_won": won,
        "final_total_runs": 9,
    }


def test_prob_calibrator_shrinks_bins_and_applies() -> None:
    points = []
    for i in range(60):
        p = 0.2 if i < 30 else 0.8
        won = i >= 30
        points.append(_make_point(i, p, won))
    calibrator = _build_prob_calibrator(points, bins=10, prior_strength=6.0)
    out_low = _apply_prob_calibrator(0.2, calibrator)
    out_high = _apply_prob_calibrator(0.8, calibrator)
    assert 0.01 <= out_low <= 0.99
    assert 0.01 <= out_high <= 0.99
    assert out_high > out_low


def test_count_leakage_violations_detects_projection_after_outcome() -> None:
    done = datetime(2026, 4, 5, 3, 0, tzinfo=timezone.utc)
    points = [
        {"projection_created_at": done - timedelta(hours=2), "outcome_completed_at": done},
        {"projection_created_at": done + timedelta(minutes=5), "outcome_completed_at": done},
    ]
    assert _count_leakage_violations(points) == 1


def test_walkforward_backtest_returns_fold_metrics() -> None:
    points = []
    for d in range(140):
        p = 0.58 if d % 2 == 0 else 0.42
        won = d % 2 == 0
        points.append(_make_point(d, p, won))
    out = _walkforward_backtest(
        points=points,
        training_days=30,
        step_days=7,
        apply_calibration=True,
    )
    assert out["fold_count"] > 0
    assert out["sample_size"] > 0
    assert out["base_brier_ml"] is not None
    assert out["calibrated_brier_ml"] is not None
