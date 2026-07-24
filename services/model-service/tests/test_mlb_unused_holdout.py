import os
from datetime import datetime, timedelta, timezone

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.mlb_unused_holdout import (
    clear_unused_holdout_cache,
    filter_points_excluding_unused_holdout,
    filter_points_in_unused_holdout,
    is_unused_holdout_date,
    load_unused_holdout_registry,
    unused_holdout_date_set,
    unused_holdout_summary,
)
from src.tasks import _walkforward_backtest


def test_unused_holdout_registry_loads_frozen_windows() -> None:
    clear_unused_holdout_cache()
    registry = load_unused_holdout_registry()
    assert registry.get("status") == "frozen_unused"
    windows = registry.get("windows") or []
    assert any(w.get("id") == "late_july_2026_frozen" for w in windows)
    assert any(w.get("id") == "post_july_2026_reserved" for w in windows)
    assert registry.get("stake_policy", {}).get("props_play_stake_eligible") is False


def test_unused_holdout_dates_include_late_july() -> None:
    clear_unused_holdout_cache()
    dates = unused_holdout_date_set()
    assert "2026-07-18" in dates
    assert "2026-07-23" in dates
    assert "2026-08-01" in dates
    assert "2026-06-01" not in dates
    assert is_unused_holdout_date("2026-07-20")
    assert not is_unused_holdout_date("2026-06-10")


def test_filter_points_excludes_unused_from_train() -> None:
    clear_unused_holdout_cache()
    points = [
        {"game_id": "a", "game_date": "2026-06-10", "fg_home_win_prob": 0.5},
        {"game_id": "b", "game_date": "2026-07-20", "fg_home_win_prob": 0.5},
        {"game_id": "c", "game_date": "2026-08-01", "fg_home_win_prob": 0.5},
    ]
    train = filter_points_excluding_unused_holdout(points)
    # Eval filter defaults to unused_evaluation role only (not reserved_future).
    unused_eval = filter_points_in_unused_holdout(points)
    unused_all = filter_points_in_unused_holdout(
        points, roles=("unused_evaluation", "reserved_future")
    )
    assert [p["game_id"] for p in train] == ["a"]
    assert {p["game_id"] for p in unused_eval} == {"b"}
    assert {p["game_id"] for p in unused_all} == {"b", "c"}


def test_walkforward_skips_unused_dates_in_train() -> None:
    clear_unused_holdout_cache()
    points = []
    # Dense May–mid-June train/test regime + late-July unused slice.
    # Walkforward requires ≥20 train / ≥5 test points per fold.
    for d in range(0, 55):
        day = datetime(2026, 5, 20, tzinfo=timezone.utc) + timedelta(days=d)
        for g in range(3):
            points.append(
                {
                    "game_id": f"g-{d}-{g}",
                    "game_date": day.date().isoformat(),
                    "fg_home_win_prob": 0.55 if (d + g) % 2 == 0 else 0.45,
                    "fg_total_mean": 8.5,
                    "home_team_won": (d + g) % 2 == 0,
                    "final_total_runs": 9,
                }
            )
    for d in range(0, 6):
        day = datetime(2026, 7, 18, tzinfo=timezone.utc) + timedelta(days=d)
        for g in range(3):
            points.append(
                {
                    "game_id": f"hold-{d}-{g}",
                    "game_date": day.date().isoformat(),
                    "fg_home_win_prob": 0.52,
                    "fg_total_mean": 8.2,
                    "home_team_won": True,
                    "final_total_runs": 8,
                }
            )
    out = _walkforward_backtest(
        points=points,
        training_days=10,
        step_days=3,
        apply_calibration=True,
        exclude_unused_holdout_from_train=True,
    )
    assert out["unused_holdout_excluded_from_train"] is True
    assert out["unused_holdout"]["props_play_stake_eligible"] is False
    assert out["unused_holdout_eval_points_available"] == 18
    assert out["fold_count"] > 0


def test_unused_holdout_summary_stake_gate() -> None:
    clear_unused_holdout_cache()
    summary = unused_holdout_summary()
    assert summary["stake_marketing_requires_unused_pass"] is True
    assert summary["props_play_stake_eligible"] is False
    assert summary["date_count"] > 0
