"""Component attribution: score-time only, one family, no production writes."""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.cfb_season_engine.priors import (
    LEAGUE_TEAM_PPG,
    MATCHUP_RESPONSE,
    overlay_score_components,
    overlaid_float,
    score_component_overlay,
)
from src.services.cfb_season_engine.qb_feature_contract import QB_FEATURE_CONTRACT_VERSION
from src.services.cfb_season_engine.team_projection import expected_team_points
from src.services.cfb_season_engine.types import EngineUniverse, TeamProjectionState
from src.services.cfb_warehouse.component_attribution import (
    AUTHORIZED_FLOOR,
    FAMILIES,
    decide_attribution,
    totals_equation_doc,
    transform_universe,
)
from src.services.cfb_warehouse.frozen_140_scoring import (
    FrozenScoringError,
    assert_frozen_priors,
    refuse_sealed_or_confirm,
)
from src.services.cfb_warehouse.matchup_response_sweep import sanity_check_frozen_140


def test_production_constants_stay_frozen_under_overlay() -> None:
    assert MATCHUP_RESPONSE == 1.40
    assert abs(LEAGUE_TEAM_PPG - 25.9) < 1e-9
    assert QB_FEATURE_CONTRACT_VERSION == "cfb-qb-feature-v1"
    assert AUTHORIZED_FLOOR == 0.70
    assert_frozen_priors()
    with overlay_score_components(
        {"LEAGUE_TEAM_PPG": 24.0, "matchup_mode": "identity", "zero_hfa": True}
    ):
        assert MATCHUP_RESPONSE == 1.40
        assert abs(LEAGUE_TEAM_PPG - 25.9) < 1e-9
        assert abs(overlaid_float("LEAGUE_TEAM_PPG", LEAGUE_TEAM_PPG) - 24.0) < 1e-9
        assert score_component_overlay()["matchup_mode"] == "identity"
    assert abs(overlaid_float("LEAGUE_TEAM_PPG", LEAGUE_TEAM_PPG) - 25.9) < 1e-9
    assert score_component_overlay() == {}


def test_refuses_2025_and_2026() -> None:
    try:
        refuse_sealed_or_confirm([2025])
        raise AssertionError("2025 should be sealed")
    except FrozenScoringError:
        pass
    try:
        refuse_sealed_or_confirm([2026])
        raise AssertionError("2026 should stay out")
    except FrozenScoringError:
        pass


def test_one_family_at_a_time() -> None:
    ids = [f["id"] for f in FAMILIES]
    assert len(ids) == len(set(ids))
    assert "multiplicative_matchup" in ids
    assert "nonlinear_exponent" in ids
    # Families do not stack overlays with each other in the runner.
    for fam in FAMILIES:
        ov = fam["score_overlay"]
        if fam["id"] == "clipping":
            assert set(ov) <= {"disable_clamp", "disable_ratio_clamp"}
        elif fam["id"] == "nonlinear_exponent":
            assert ov == {"matchup_mode": "linear"}
        elif fam["id"] == "multiplicative_matchup":
            assert ov == {"matchup_mode": "identity"}
        elif ov:
            assert len(ov) == 1


def test_equation_lists_every_moving_term() -> None:
    doc = totals_equation_doc()
    blob = " ".join(doc["terms_that_can_move_the_total"]).lower()
    for needle in (
        "league_team_ppg",
        "matchup_response",
        "pace",
        "hfa",
        "qb",
        "efficiency",
        "clamp",
        "double",
        "ratio",
    ):
        assert needle in blob
    assert "expected_team_points" in doc
    assert "compose" in doc
    assert "qb_layer" in doc


def test_linear_matchup_is_softer_than_power_when_ratio_gt_one() -> None:
    off = TeamProjectionState(team="AAA", offense_index=1.30, defense_index=1.00, pace_factor=1.0)
    deff = TeamProjectionState(team="BBB", offense_index=1.00, defense_index=0.80, pace_factor=1.0)
    power, power_diag = expected_team_points(off, deff, home=False, week=10)
    with overlay_score_components({"matchup_mode": "linear"}):
        linear, linear_diag = expected_team_points(off, deff, home=False, week=10)
    with overlay_score_components({"matchup_mode": "identity"}):
        ident, ident_diag = expected_team_points(off, deff, home=False, week=10)
    assert power_diag["matchup_mode"] == "power"
    assert linear_diag["matchup_mode"] == "linear"
    assert ident_diag["matchup_mult"] == 1.0
    assert power > linear > ident
    assert abs(LEAGUE_TEAM_PPG - 25.9) < 1e-9
    assert MATCHUP_RESPONSE == 1.40


def test_index_recenter_forces_unit_means() -> None:
    uni = EngineUniverse(
        season=2024,
        schedule=[],
        teams={
            "AAA": TeamProjectionState(team="AAA", offense_index=1.20, defense_index=0.90),
            "BBB": TeamProjectionState(team="BBB", offense_index=1.00, defense_index=0.70),
        },
    )
    out = transform_universe(uni, "recenter_indices")
    offs = [t.offense_index for t in out.teams.values()]
    defs = [t.defense_index for t in out.teams.values()]
    assert abs(sum(offs) / 2.0 - 1.0) < 1e-6
    assert abs(sum(defs) / 2.0 - 1.0) < 1e-6
    assert uni.teams["AAA"].offense_index == 1.20


def _ref_card(**overrides):
    base = {
        "n": 717,
        "mae_vs_actual": 16.651,
        "rmse_vs_actual": 20.429,
        "bias_vs_actual": 10.100,
        "medae_vs_actual": 14.350,
        "mean_model_total": 63.838,
        "std_model_total": 8.0,
        "mean_abs_disagree_total": 12.177,
        "bias_vs_close": 11.340,
        "high_tail_n": 217,
        "high_tail_bias_vs_actual": 17.906,
        "high_tail_bias_vs_close": 17.791,
        "margin_mae_vs_actual": 14.804,
        "ats_hit_rate": 0.487,
        "mean_actual_total": 53.738,
        "mean_close_total": 52.499,
        "moments": {"mean_off_minus_def": 0.08},
        "error_type": {"primary": "MULTIPLE", "flags": ["LOCATION", "NONLINEARITY"]},
        "projected_total_buckets": {},
    }
    base.update(overrides)
    return base


def _rec(family_id: str, val1, panel="ablate"):
    return {
        "family_id": family_id,
        "panel": panel,
        "splits": {
            "train_0": {"n": 712, **val1},
            "val_0": {"n": 710, **val1},
            "val_1": val1,
        },
    }


def test_multivariate_when_centering_and_qb_both_move() -> None:
    ref140 = _rec("frozen_140", _ref_card(), panel="reference_140")
    ref070 = _rec(
        "floor_070",
        _ref_card(
            mae_vs_actual=13.987,
            bias_vs_actual=4.619,
            high_tail_n=5,
            mean_model_total=58.356,
            mean_abs_disagree_total=7.370,
        ),
        panel="reference_070",
    )
    panel_140 = [ref140]
    panel_070 = [ref070]
    for fam in FAMILIES:
        if fam["id"] == "od_strength_centering":
            v140 = _ref_card(bias_vs_actual=7.5, mae_vs_actual=15.2, high_tail_n=140)
            v070 = _ref_card(bias_vs_actual=3.2, mae_vs_actual=13.4, high_tail_n=4)
        elif fam["id"] == "qb_talent_scale":
            v140 = _ref_card(bias_vs_actual=8.4, mae_vs_actual=15.6, high_tail_n=160)
            v070 = _ref_card(bias_vs_actual=3.8, mae_vs_actual=13.6, high_tail_n=5)
        else:
            v140 = _ref_card()
            v070 = _ref_card(bias_vs_actual=4.619, mae_vs_actual=13.987, high_tail_n=5)
        panel_140.append(_rec(fam["id"], v140))
        panel_070.append(_rec(fam["id"], v070))
    memo = decide_attribution(
        lake_mounted=True,
        sanity=sanity_check_frozen_140(_ref_card()),
        panel_140=panel_140,
        panel_070=panel_070,
    )
    assert memo["recommendation"] == "MULTIVARIATE RECALIBRATION"
    assert "od_strength_centering" in memo["material_families"]
    assert "qb_talent_scale" in memo["material_families"]


def test_insufficient_when_lake_missing() -> None:
    memo = decide_attribution(
        lake_mounted=False,
        sanity={"ok": False},
        panel_140=[],
        panel_070=[],
    )
    assert memo["recommendation"] == "INSUFFICIENT EVIDENCE"
