from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.nfl_decomposition_drift import summarize_decomposition_drift
from src.services.nfl_framework_tuning import build_tuning_candidates, evaluate_tuning_grid
from src.services.nfl_handicapping_framework import get_nfl_handicapping_config


def _build_point(day_offset: int, *, leaked: bool = False) -> dict:
    game_date = date(2026, 9, 1) + timedelta(days=day_offset)
    outcome_at = datetime(2026, 9, 1, 22, 0, tzinfo=timezone.utc) + timedelta(days=day_offset)
    projection_at = outcome_at + timedelta(hours=2) if leaked else outcome_at - timedelta(hours=5)
    return {
        "game_id": f"g-{day_offset}",
        "game_date": game_date.isoformat(),
        "home_win_prob": 0.64 if day_offset % 2 == 0 else 0.36,
        "total_mean": 45.0 + float(day_offset % 4),
        "home_team_won": day_offset % 2 == 0,
        "final_total_points": 45.5 + float((day_offset + 1) % 5),
        "projection_created_at": projection_at,
        "outcome_completed_at": outcome_at,
        "clv_avg": 0.012 if day_offset % 3 == 0 else 0.003,
        "projection": {
            "decomposition": {
                "confidence_score": 0.71,
                "factor_coverage": 0.72,
                "uncertainty_penalties": {"total_penalty": 0.11},
                "factor_contributions": {
                    "base_efficiency": {"margin_points": 2.1, "total_points": 1.4},
                    "injuries_depth": {"margin_points": 0.4, "total_points": -0.3},
                    "regression_luck": {"margin_points": 0.25, "total_points": 0.0},
                },
            }
        },
    }


def test_tuning_pipeline_deterministic_recommendation() -> None:
    points = [_build_point(i) for i in range(70)]
    base_cfg = get_nfl_handicapping_config()
    candidates = build_tuning_candidates(
        base_guardrails=base_cfg["guardrails"],
        max_candidates=24,
    )
    first = evaluate_tuning_grid(
        points=points,
        candidates=candidates,
        training_days=28,
        step_days=8,
    )
    second = evaluate_tuning_grid(
        points=points,
        candidates=candidates,
        training_days=28,
        step_days=8,
    )
    assert first["status"] == "ok"
    assert second["status"] == "ok"
    assert first["recommended_candidate"]["rank"] == 1
    assert first["recommended_candidate"]["score"] == second["recommended_candidate"]["score"]
    assert first["recommended_candidate"]["metrics"] == second["recommended_candidate"]["metrics"]


def test_tuning_pipeline_rejects_leakage() -> None:
    points = [_build_point(i, leaked=(i == 8)) for i in range(42)]
    base_cfg = get_nfl_handicapping_config()
    candidates = build_tuning_candidates(
        base_guardrails=base_cfg["guardrails"],
        max_candidates=16,
    )
    out = evaluate_tuning_grid(
        points=points,
        candidates=candidates,
        training_days=21,
        step_days=7,
    )
    assert out["status"] == "rejected"
    assert out["reason"] == "leakage_detected"
    assert out["leakage_violations"] >= 1


def test_decomposition_drift_thresholding_flags_shift() -> None:
    rows = []
    for i in range(20):
        rows.append(
            {
                "week_bucket": f"2026-09-{(i % 7) + 1:02d}",
                "projection": {
                    "decomposition": {
                        "factor_contributions": {
                            "base_efficiency": {"margin_points": 1.5, "total_points": 1.0},
                            "travel_schedule": {"margin_points": 0.2, "total_points": 0.1},
                        }
                    }
                },
            }
        )
    for i in range(8):
        rows.append(
            {
                "week_bucket": "2026-10-20",
                "projection": {
                    "decomposition": {
                        "factor_contributions": {
                            "base_efficiency": {"margin_points": 0.3, "total_points": 0.2},
                            "travel_schedule": {"margin_points": 1.9, "total_points": 1.5},
                        }
                    }
                },
            }
        )
    out = summarize_decomposition_drift(rows=rows, baseline_weeks=3, warn_threshold=0.15, critical_threshold=0.25)
    assert out["status"] in {"warning", "critical"}
    assert out["latest_week"] == "2026-10-20"
    assert len(out["top_shifts"]) > 0
    assert out["top_shifts"][0]["relative_shift"] > 0.15
