from __future__ import annotations

import pytest

from data_platform_nfl.inseason_weekly_update import (
    build_inseason_weekly_update_plan,
    summarize_inseason_weekly_update,
)


def test_build_plan_includes_core_dp_and_model_steps() -> None:
    plan = build_inseason_weekly_update_plan(season=2026, week=5)
    ids = [step["id"] for step in plan]
    assert ids[0] == "ingest_launch_hardening"
    assert "refresh_rolling_player_usage" in ids
    assert "materialize_player_projection_features" in ids
    assert "materialize_player_baselines" in ids
    assert "materialize_box_score_sims" in ids
    assert "materialize_prop_edges" in ids
    assert "materialize_fantasy_weekly" in ids
    assert "materialize_award_projections" in ids


def test_build_plan_skip_flags_trim_optional_steps() -> None:
    plan = build_inseason_weekly_update_plan(
        season=2026,
        week=3,
        skip_ingest=True,
        skip_fantasy=True,
        skip_awards=True,
        rematerialize_remaining_weeks=False,
    )
    ids = [step["id"] for step in plan]
    assert "ingest_launch_hardening" not in ids
    assert "materialize_fantasy_weekly" not in ids
    assert "materialize_award_projections" not in ids
    feature_step = next(s for s in plan if s["id"] == "materialize_player_projection_features")
    assert "--week 3" in feature_step["cli"]


def test_build_plan_rejects_invalid_week() -> None:
    with pytest.raises(ValueError, match="week must be 1-25"):
        build_inseason_weekly_update_plan(season=2026, week=0)


def test_summarize_counts_statuses() -> None:
    summary = summarize_inseason_weekly_update(
        season=2026,
        week=4,
        step_results=[
            {"id": "a", "status": "ok"},
            {"id": "b", "status": "skipped"},
            {"id": "c", "status": "dry_run"},
            {"id": "d", "status": "failed"},
        ],
    )
    assert summary["steps_total"] == 4
    assert summary["steps_ok"] == 1
    assert summary["steps_skipped"] == 1
    assert summary["steps_dry_run"] == 1
    assert summary["steps_failed"] == 1
    assert summary["status"] == "failed"
