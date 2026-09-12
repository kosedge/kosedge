"""Locks for additive scoring architecture. No coefficient writes."""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.cfb_season_engine.priors import (
    LEAGUE_TEAM_PPG,
    MATCHUP_RESPONSE,
    overlay_score_components,
    score_component_overlay,
)
from src.services.cfb_season_engine.team_features import CFB_EDGE_BOARD_PUBLIC_ENABLED
from src.services.cfb_season_engine.team_projection import (
    expected_team_points,
    project_game,
)
from src.services.cfb_season_engine.types import (
    EfficiencyProfile,
    EngineUniverse,
    TeamProjectionState,
)
from src.services.cfb_warehouse.additive_scoring_architecture import (
    A1_A4_MAX_ABS_DIFF,
    CANDIDATES,
    DISPERSION_FLOOR,
    HALF_INDEX_SLOPE,
    RANGE_DROP,
    decide,
)
from src.services.cfb_warehouse.frozen_140_scoring import refuse_sealed_or_confirm
from src.services.cfb_warehouse.matchup_architecture_holdout import PROTOCOL_SPLITS

ROOT = Path(__file__).resolve().parents[3]
ART = ROOT / "data/ops/cfb-additive-scoring-architecture-20260912.json"


def _state(team: str, off: float, deff: float, *, pace: float = 1.0) -> TeamProjectionState:
    return TeamProjectionState(
        team=team,
        offense_index=1.0,
        defense_index=1.0,
        pace_factor=pace,
        efficiency=EfficiencyProfile(team=team, off_eff=off, def_eff=deff),
    )


def test_production_and_kill_switch_frozen() -> None:
    assert MATCHUP_RESPONSE == 1.40
    assert abs(LEAGUE_TEAM_PPG - 25.9) < 1e-9
    assert CFB_EDGE_BOARD_PUBLIC_ENABLED is False
    with overlay_score_components({"matchup_mode": "point_additive_half"}):
        assert score_component_overlay()["matchup_mode"] == "point_additive_half"
        assert MATCHUP_RESPONSE == 1.40
    assert score_component_overlay() == {}


def test_candidates_are_predeclared() -> None:
    ids = [c["id"] for c in CANDIDATES]
    assert ids[0] == "E3_ref"
    assert "C2_ref" in ids
    assert "A1_point_half" in ids
    assert "A2_point_units" in ids
    assert "A3_point_full" in ids
    assert "A4_point_poss" in ids
    assert "A5_c2_unclamped" in ids
    assert RANGE_DROP == 8.0
    assert DISPERSION_FLOOR == 0.50
    assert PROTOCOL_SPLITS["val_1"]["seasons"] == (2024,)
    roles = {c["id"]: c["role"] for c in CANDIDATES}
    assert roles["C2_ref"] == "reference"
    assert roles["A1_point_half"] == "candidate"
    assert roles["A4_point_poss"] == "identity_check"


def test_half_slope_is_documented_identity() -> None:
    assert abs(HALF_INDEX_SLOPE - (25.9 / 136.0)) < 1e-12


def test_a1_hand_calculation_and_a4_identity() -> None:
    off = _state("OFF", 70.0, 50.0, pace=1.10)
    deff = _state("DEF", 50.0, 30.0, pace=1.10)
    pace = 1.10
    expected = pace * (25.9 + (25.9 / 136.0) * (70.0 - 50.0) + (25.9 / 136.0) * (50.0 - 30.0))
    with overlay_score_components(
        {"matchup_mode": "point_additive_half", "disable_clamp": True, "zero_hfa": True, "zero_coaching": True}
    ):
        a1, diag = expected_team_points(off, deff, home=False, week=8)
        assert diag["matchup_mode"] == "point_additive_half"
        assert abs(a1 - expected) < 1e-9
        assert abs(float(diag["additive_alpha"]) - (25.9 / 136.0)) < 1e-6
    with overlay_score_components(
        {"matchup_mode": "point_additive_poss", "disable_clamp": True, "zero_hfa": True, "zero_coaching": True}
    ):
        a4, _ = expected_team_points(off, deff, home=False, week=8)
    assert abs(a1 - a4) < 1e-9


def test_project_game_algebraic_identity() -> None:
    home = _state("HOME", 62.0, 48.0, pace=1.05)
    away = _state("AWAY", 44.0, 58.0, pace=0.97)
    universe = EngineUniverse(season=2024, schedule=[], teams={"HOME": home, "AWAY": away})
    with overlay_score_components(
        {"matchup_mode": "point_additive_half", "disable_clamp": True}
    ):
        proj = project_game(
            universe, home_team="HOME", away_team="AWAY", week=6, season=2024
        )
    assert abs(
        (proj.expected_home_score + proj.expected_away_score) - proj.expected_total
    ) < 1e-9
    assert abs(
        (proj.expected_away_score - proj.expected_home_score) - proj.spread_home
    ) < 1e-9


def test_default_path_is_still_power_ratio() -> None:
    off = _state("OFF", 70.0, 50.0)
    off.offense_index = 1.20
    deff = _state("DEF", 50.0, 30.0)
    deff.defense_index = 0.85
    pts, diag = expected_team_points(off, deff, home=False, week=8)
    assert diag["matchup_mode"] == "power"
    assert MATCHUP_RESPONSE == 1.40
    assert pts > 25.9 + 1.0


def test_refuses_2025_and_2026() -> None:
    try:
        refuse_sealed_or_confirm([2025])
        raise AssertionError("2025 must stay sealed")
    except Exception as exc:
        assert "2025" in str(exc) or "sealed" in str(exc).lower()
    try:
        refuse_sealed_or_confirm([2026])
        raise AssertionError("2026 must stay out of the loss")
    except Exception as exc:
        assert "2026" in str(exc) or "confirm" in str(exc).lower()


def test_decision_never_ships() -> None:
    empty = decide([], a1_a4_ok=None)
    assert empty["ship"] is False
    assert empty["winner"] is None
    broken = decide(
        [{"id": "E3_ref", "eval": {}, "role": "reference"}],
        a1_a4_ok=False,
    )
    assert broken["ship"] is False
    assert broken["decision"] == "IMPLEMENTATION_INCONSISTENT_DO_NOT_SHIP"


def test_artifact_if_present_does_not_ship() -> None:
    if not ART.is_file():
        return
    payload = json.loads(ART.read_text(encoding="utf-8"))
    assert payload["wrote_production_coefficient"] is False
    assert payload["used_2026_for_fitting"] is False
    assert payload["opened_2025"] is False
    assert payload["do_not_fit_c2_weights"] is True
    assert payload["kill_switch"] == "OFF"
    assert payload["decision"]["ship"] is False
    assert payload["decision"]["winner"] is None
    assert abs(float(payload["matchup_response_frozen"]) - 1.40) < 1e-9
    assert abs(float(payload["league_team_ppg_frozen"]) - 25.9) < 1e-9
    assert A1_A4_MAX_ABS_DIFF == 0.02
