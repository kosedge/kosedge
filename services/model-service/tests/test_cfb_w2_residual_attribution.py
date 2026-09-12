"""Measure-only locks for W2 residual attribution. No coefficient changes."""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.cfb_season_engine.priors import (  # noqa: E402
    LEAGUE_TEAM_PPG,
    MATCHUP_RESPONSE,
    matchup_response_for_week,
)
from src.services.cfb_season_engine.team_features import (  # noqa: E402
    CFB_EDGE_BOARD_PUBLIC_ENABLED,
)

ROOT = Path(__file__).resolve().parents[3]
LEDGER = ROOT / "data/ops/cfb-w2-residual-attribution-20260912.json"


def _report() -> dict:
    assert LEDGER.is_file(), f"missing attribution ledger {LEDGER}"
    return json.loads(LEDGER.read_text(encoding="utf-8"))


def test_no_tuning_and_kill_switch_stays_off() -> None:
    assert MATCHUP_RESPONSE == 1.40
    assert abs(LEAGUE_TEAM_PPG - 25.9) < 1e-9
    assert abs(matchup_response_for_week(2) - 1.302) < 1e-3
    assert CFB_EDGE_BOARD_PUBLIC_ENABLED is False
    rep = _report()
    assert rep["role"] == "diagnosis_only"
    assert rep["do_not_tune"] is True
    assert rep["kill_switch"] == "OFF"
    assert rep["merge_532"] is False
    assert rep["diagnosis"]["do_not_subtract_10"] is True
    assert rep["diagnosis"]["calibration_recommendation"] == "FAIL"


def test_comparison_layer_is_not_the_plus_10() -> None:
    cmp_ = _report()["comparison_layer"]
    assert cmp_["joined_n"] == 47
    assert cmp_["unjoined"] == []
    assert cmp_["duplicate_pairs"] == []
    assert cmp_["neutral_site_joined"] == []
    assert cmp_["kei_total_equals_model"] is True
    assert cmp_["rut_bc_in_snapshot"] is True
    assert (cmp_["pack_vs_reproject_max_abs_total"] or 0) <= 0.3


def test_totals_shape_is_not_market_plus_10() -> None:
    tot = _report()["totals"]
    assert tot["n"] == 47
    assert abs(tot["mean_residual"] - 9.976) < 0.05
    assert tot["overs"] == 45
    assert tot["unders"] == 2
    ols = tot["ols_model_on_market"]
    assert 0.80 <= float(ols["slope"]) <= 0.92
    assert float(ols["r2"]) < 0.45
    const = tot["constant_plus_10_hypothesis"]
    assert const["share_within_3_of_mean"] < 0.50
    cf = tot["counterfactual_mean_gap_vs_market"]
    assert cf["matchup_ratio_1"]["delta_from_actual"] < -8.0
    assert cf["two_times_league_ppg"]["mean_gap"] < 0.0
    assert "explicit possessions / plays" in tot["absent_from_score_path"]


def test_favorite_flips_and_rut_bc_forensic() -> None:
    rep = _report()
    assert rep["flips"]["n"] == 10
    pairs = {row["pair"]: row for row in rep["flips"]["pairs"]}
    assert "RUT@BC" in pairs
    assert "UNLV@UNT" in pairs
    rut = rep["rut_bc"]
    assert rut["joined"] is True
    assert rut["market_spread_home"] == -3.0
    assert rut["market_total"] == 53.5
    assert rut["favorite_flip"] is True
    assert rut["counterfactual_total"]["matchup_ratio_1"] == 53.316
    assert rut["counterfactual_spread"]["matchup_ratio_1"] == -1.402
    # Without the matchup term the model is a 1-point home favorite, not RUT -12.
    assert rut["counterfactual_spread"]["actual"] > 10
    assert rut["counterfactual_spread"]["matchup_ratio_1"] < 0
