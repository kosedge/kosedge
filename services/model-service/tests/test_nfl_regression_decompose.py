"""NFL regression track — decompose + scoring lock + W-L vs EPA.

Investigation only. Does not rematerialize or change coefficients.
"""

from __future__ import annotations

from pathlib import Path

from src.services.nfl_handicapping_framework import NFL_HANDICAPPING_FRAMEWORK_VERSION
from src.services.nfl_regression_diagnose import (
    LOCKED_SCORING,
    classify_strength_source,
    load_packaged_epa_priors,
    locked_scoring_snapshot,
    looks_like_week1_record_bucket,
    record_indices,
    replay_focus_matchups,
)

ROUTES_NFL = Path(__file__).resolve().parents[1] / "src" / "routes" / "nfl.py"
ADHOC_SENTINEL = "NFL_REGRESSION_20260915"


def test_scoring_equation_not_silently_retuned() -> None:
    live = locked_scoring_snapshot()
    assert live["framework_version"] == LOCKED_SCORING["framework_version"]
    assert live["framework_version"] == NFL_HANDICAPPING_FRAMEWORK_VERSION
    assert live["base_total_points"] == LOCKED_SCORING["base_total_points"]
    assert live["home_field_points"] == LOCKED_SCORING["home_field_points"]
    assert live["base_efficiency_max_total_points"] == LOCKED_SCORING["base_efficiency_max_total_points"]
    assert live["base_efficiency_max_margin_points"] == LOCKED_SCORING["base_efficiency_max_margin_points"]
    assert live["hfa_margin_points"] == LOCKED_SCORING["home_field_points"]


def test_week1_record_buckets_match_live_context_shape() -> None:
    # Railway /nfl/games after Week 1: 1-0 → 1.12/1.12, 0-1 → 0.90/0.92.
    assert record_indices("1-0") == (1.12, 1.12)
    assert record_indices("0-1") == (0.90, 0.92)
    assert looks_like_week1_record_bucket(
        offense_index=1.12, defense_index=1.12, record_summary="1-0"
    )
    assert looks_like_week1_record_bucket(
        offense_index=0.90, defense_index=0.92, record_summary="0-1"
    )
    assert classify_strength_source(
        offense_index=1.12, defense_index=1.12, record_summary="1-0"
    ) == "espn_win_loss_record"


def test_packaged_epa_is_not_the_week1_record_bucket() -> None:
    priors = load_packaged_epa_priors()
    assert set(priors) >= {"DET", "BUF", "CAR", "ATL", "CHI", "PIT"}
    for team in ("DET", "BUF", "ATL", "PIT"):
        row = priors[team]
        assert classify_strength_source(
            offense_index=float(row["offense_index"]),
            defense_index=float(row["defense_index"]),
            record_summary="1-0",
            epa=row,
        ) == "packaged_epa_prior"


def test_epa_vs_record_replay_differs_on_more_than_one_matchup() -> None:
    rows = replay_focus_matchups()
    keys = {row["key"] for row in rows}
    assert {"DET@BUF", "CAR@ATL", "ATL@PIT", "CHI@CAR"} <= keys
    material = []
    for row in rows:
        delta = row["deltas"]["record_spread_minus_epa_spread"]
        assert delta is not None
        if abs(float(delta)) >= 0.75:
            material.append(row["key"])
        # Personnel / injury stay off on this probe (season_too_early analogue).
        for src in ("epa", "record"):
            comps = row[src]["components"]
            assert comps["injuries_depth"]["margin_points"] == 0.0
            assert comps["personnel_efficiency"]["margin_points"] == 0.0
    # Failure must reproduce on ≥2 matchups, not a one-game special case.
    assert "ATL@PIT" in material
    assert "CHI@CAR" in material
    assert len(material) >= 2


def test_car_atl_july31_model_tracks_epa_not_record() -> None:
    """Last-good July-31 CAR@ATL model (−2.77) is EPA+HFA, not W-L."""
    row = next(r for r in replay_focus_matchups() if r["key"] == "CAR@ATL")
    epa_spread = float(row["epa"]["spread_home"])
    rec_spread = float(row["record"]["spread_home"])
    live = float(row["live"]["model_spread_home"])
    assert abs(epa_spread - live) < abs(rec_spread - live)
    assert abs(epa_spread - live) <= 0.35


def test_chi_car_actual_is_outside_equation_band_not_a_retune_license() -> None:
    """CHI@CAR actual 96 vs model ~44 is a residual, not a scoring-equation bug."""
    row = next(r for r in replay_focus_matchups() if r["key"] == "CHI@CAR")
    live_total = float(row["live"]["model_total"])
    epa_total = float(row["epa"]["predicted_total"])
    actual_total = float(row["actual"]["total"])
    assert 40.0 <= live_total <= 50.5
    assert 40.0 <= epa_total <= 50.5
    assert actual_total == 96.0
    # Equation clamp: prior 45.3 ± 5 efficiency. Do not raise the prior here.
    assert abs(epa_total - 45.3) <= 5.5


def test_adhoc_simulation_route_uses_epa_or_refuse() -> None:
    """NFL #564: POST /simulations/{id} must resolve packaged EPA or refuse persist."""
    src = ROUTES_NFL.read_text(encoding="utf-8")
    assert ADHOC_SENTINEL in src
    start = src.index("def run_nfl_simulation")
    end = src.index("\ndef _nfl_web_launch_bundle_candidates", start)
    fn = src[start:end]
    code_only = "\n".join(
        line for line in fn.splitlines() if not line.lstrip().startswith("#")
    )
    assert "resolve_adhoc_simulation_strength" in code_only
    assert "NflWlPersistRefused" in code_only
    assert "nfl_wl_persist_refused" in code_only
    assert "INSERT INTO nfl_market_projections" in code_only
