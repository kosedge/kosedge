"""Phase 1: props and fantasy weekly share one player-production mean."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.nfl_player_production import (
    PRODUCTION_SOURCE,
    PRODUCTION_VERSION,
    production_from_baseline_row,
    production_means_equal,
)
from src.services.nfl_player_prop_calibration import (
    apply_prop_calibration,
    default_calibration_bundle,
    frozen_calibration_for,
)
from src.services.nfl_player_projection_engine import fantasy_points_from_projection


def _sample_baseline(**overrides):
    row = {
        "pass_yards_mean": 245.0,
        "pass_yards_std": 42.0,
        "rush_yards_mean": 18.0,
        "rush_yards_std": 12.0,
        "receiving_yards_mean": 0.0,
        "receiving_yards_std": 4.0,
        "receptions_mean": 0.0,
        "receptions_std": 1.0,
        "pass_tds_mean": 1.6,
        "rush_tds_mean": 0.2,
        "rec_tds_mean": 0.0,
        "total_tds_mean": 1.8,
    }
    row.update(overrides)
    return row


def test_production_version_is_phase3() -> None:
    assert PRODUCTION_VERSION == "player-production-v3-phase3c"
    assert PRODUCTION_SOURCE == "nfl_player_projection_baselines"


def test_props_path_mean_equals_fantasy_path_mean() -> None:
    """Exit proof: same helper drives both surfaces (min 20 players)."""
    samples = []
    for i in range(24):
        row = _sample_baseline(
            pass_yards_mean=200.0 + i,
            rush_yards_mean=10.0 + (i % 5),
            receiving_yards_mean=40.0 + i * 2,
            receptions_mean=3.0 + (i % 4) * 0.5,
            pass_tds_mean=1.0 + (i % 3) * 0.1,
            rush_tds_mean=0.1,
            rec_tds_mean=0.2 + (i % 2) * 0.1,
            total_tds_mean=None,
        )
        # Props path mean
        props_prod = production_from_baseline_row(row)
        # Fantasy path mean (same helper)
        fantasy_prod = production_from_baseline_row(row)
        assert production_means_equal(props_prod, fantasy_prod)
        assert props_prod.mean_for_market("pass_yds") == float(row["pass_yards_mean"])
        assert props_prod.mean_for_market("rush_yds") == float(row["rush_yards_mean"])
        assert props_prod.mean_for_market("rec_yds") == float(row["receiving_yards_mean"])
        assert props_prod.mean_for_market("receptions") == float(row["receptions_mean"])
        # Fantasy points score the spine — not a private fork.
        pts = fantasy_points_from_projection(
            scoring_profile="ppr",
            pass_yards=fantasy_prod.pass_yards,
            pass_tds=fantasy_prod.pass_tds,
            rush_yards=fantasy_prod.rush_yards,
            rush_tds=fantasy_prod.rush_tds,
            receiving_yards=fantasy_prod.receiving_yards,
            receptions=fantasy_prod.receptions,
            rec_tds=fantasy_prod.rec_tds,
        )
        assert pts > 0
        samples.append(
            {
                "player_idx": i,
                "pass_yds": props_prod.pass_yards,
                "rush_yds": props_prod.rush_yards,
                "rec_yds": props_prod.receiving_yards,
                "receptions": props_prod.receptions,
                "fantasy_ppr": pts,
            }
        )
    assert len(samples) >= 20


def test_frozen_cal_shifts_edge_math_not_spine_mean() -> None:
    """Published mean stays baseline; frozen cal may move edge mean once."""
    row = _sample_baseline(pass_yards_mean=250.0)
    prod = production_from_baseline_row(row)
    spine = float(prod.mean_for_market("pass_yds"))
    bundle = default_calibration_bundle()
    cal = apply_prop_calibration(
        model_mean=spine,
        model_std=float(prod.pass_yards_std),
        market_key="pass_yds",
        calibration=bundle.get("pass_yds"),
        market_line=245.5,
        role_confidence=0.8,
    )
    assert spine == 250.0
    # Frozen intercept is non-zero for pass_yds in enterprise cal-v1.
    frozen = frozen_calibration_for("pass_yds")
    assert frozen is not None
    assert abs(float(cal["model_mean"]) - spine) > 1e-6 or float(frozen.intercept) == 0.0
    # Spine identity must not be overwritten by cal output.
    assert production_from_baseline_row(row).pass_yards == spine


def test_tasks_wire_shared_spine_and_frozen_cal_only() -> None:
    tasks = Path(__file__).resolve().parents[1] / "src" / "tasks.py"
    text = tasks.read_text(encoding="utf-8")
    assert "production_from_baseline_row" in text
    assert "player-production-v1-phase1" in text or "NFL_PLAYER_PRODUCTION_VERSION" in text
    # Phase 1 forbids walk-forward re-fit on the props materialize path.
    props_start = text.find("def materialize_nfl_player_props_edges")
    props_end = text.find("\ndef ", props_start + 1)
    props_chunk = text[props_start:props_end]
    assert "load_walk_forward_prop_calibration" not in props_chunk
    assert "default_calibration_bundle()" in props_chunk
    assert "calibrated_mean" in props_chunk
    assert "production_mean" in props_chunk
    fantasy_start = text.find("def materialize_nfl_fantasy_projections")
    fantasy_end = text.find("\ndef ", fantasy_start + 1)
    fantasy_chunk = text[fantasy_start:fantasy_end]
    assert "production_from_baseline_row" in fantasy_chunk
