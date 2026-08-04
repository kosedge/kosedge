"""Tests for the hierarchical CFB season engine (roster + QB deepened)."""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from fastapi.testclient import TestClient

from src.services.cfb_season_engine import (
    DEFAULT_SEASON_ENGINE_VERSION,
    build_packaged_universe,
    engine_status_payload,
    project_game_preview,
    simulate_full_season,
)
from src.services.cfb_season_engine.qb_situation import (
    build_qb_situation,
    classify_qb_situation,
    compute_qb_situation_index,
)
from src.services.cfb_season_engine.roster_construction import (
    build_roster_construction,
    compute_roster_strength,
)
from src.services.cfb_season_engine.team_projection import compose_team_projection
from src.services.cfb_season_engine.position_groups import build_position_groups
from src.services.cfb_season_engine.priors import early_season_uncertainty
from src.services.cfb_season_engine.types import EngineUniverse, TeamProjectionState


def test_engine_version_string() -> None:
    assert DEFAULT_SEASON_ENGINE_VERSION == "cfb-season-engine-v0.2-roster-qb"


def test_qb_situation_classification() -> None:
    assert classify_qb_situation(qb_class="incumbent") == "incumbent"
    assert classify_qb_situation(is_portal=True) == "portal"
    assert classify_qb_situation(qb_class="portal_starter") == "portal"
    assert classify_qb_situation(open_competition=True) == "open_competition"
    assert classify_qb_situation(is_true_freshman=True) == "true_freshman"
    assert classify_qb_situation(experience_starts=12) == "incumbent"
    # Priority: true freshman beats portal flag
    assert (
        classify_qb_situation(is_true_freshman=True, is_portal=True) == "true_freshman"
    )


def test_roster_strength_components_inspectable() -> None:
    roster = build_roster_construction(
        "UGA",
        {
            "returning_snap_share": 0.56,
            "returning_start_share": 0.60,
            "portal_in_value": 62,
            "portal_out_value": 48,
            "recruiting_class_score": 96,
            "experience_index": 62,
        },
    )
    assert roster.roster_strength > 60
    assert 0.0 < roster.returning_snap_share <= 1.0
    assert roster.portal_net > 40
    strength, breakdown = compute_roster_strength(
        returning_production=roster.returning_production,
        portal_net=roster.portal_net,
        recruiting_class_score=roster.recruiting_class_score,
        experience_index=roster.experience_index,
    )
    assert abs(strength - roster.roster_strength) < 0.01
    assert "returning_production" in breakdown
    assert "weights" in breakdown


def test_roster_strength_ranks_blue_bloods_above_mid_rebuilds() -> None:
    universe = build_packaged_universe(2026)
    strengths = {
        code: state.roster.roster_strength
        for code, state in universe.teams.items()
        if state.roster
    }
    blue = ["UGA", "ALA", "TEX", "OSU", "ND"]
    mid = ["BALL", "EMU", "NMSU", "WAKE"]
    for b in blue:
        assert b in strengths
    for m in mid:
        assert m in strengths
    blue_mean = sum(strengths[b] for b in blue) / len(blue)
    mid_mean = sum(strengths[m] for m in mid) / len(mid)
    assert blue_mean > mid_mean + 8.0
    assert strengths["UGA"] > strengths["BALL"]
    assert strengths["TEX"] > strengths["EMU"]


def test_qb_class_materially_moves_offense_index() -> None:
    """Holding roster/groups fixed, QB class must move offense sharply."""
    roster = build_roster_construction(
        "TEST",
        {
            "returning_production": 55,
            "portal_in_value": 55,
            "portal_out_value": 50,
            "recruiting_class_score": 70,
            "experience_index": 55,
        },
    )
    groups = build_position_groups(
        "TEST",
        {"ol": 70, "skill": 70, "front_seven": 65, "secondary": 65},
        roster=roster,
    )
    indexes = {}
    for qb_class in ("incumbent", "portal", "open_competition", "true_freshman"):
        qb = build_qb_situation(
            "TEST",
            {
                "qb_class": qb_class,
                "qb_talent": 75,
                "ol_support": 70,
                "weapons_support": 70,
                "experience_starts": 8 if qb_class == "incumbent" else 0,
            },
        )
        state = compose_team_projection("TEST", roster, qb, groups)
        indexes[qb_class] = state.offense_index

    assert indexes["incumbent"] > indexes["portal"]
    assert indexes["portal"] > indexes["open_competition"]
    assert indexes["open_competition"] > indexes["true_freshman"]
    # Material — not a tiny unused field.
    assert indexes["incumbent"] - indexes["true_freshman"] >= 0.10


def test_incumbent_good_cast_beats_true_freshman_weak_cast() -> None:
    roster = build_roster_construction(
        "TEST",
        {
            "returning_production": 50,
            "portal_in_value": 50,
            "portal_out_value": 50,
            "recruiting_class_score": 60,
            "experience_index": 50,
        },
    )
    groups = build_position_groups(
        "TEST",
        {"ol": 55, "skill": 55, "front_seven": 55, "secondary": 55},
        roster=roster,
    )
    good = build_qb_situation(
        "TEST",
        {
            "qb_class": "incumbent",
            "qb_talent": 78,
            "ol_support": 88,
            "weapons_support": 90,
            "experience_starts": 12,
        },
    )
    weak = build_qb_situation(
        "TEST",
        {
            "qb_class": "true_freshman",
            "qb_talent": 78,  # equal talent — class + cast drive gap
            "ol_support": 45,
            "weapons_support": 42,
            "is_true_freshman": True,
        },
    )
    good_state = compose_team_projection("TEST", roster, good, groups)
    weak_state = compose_team_projection("TEST", roster, weak, groups)
    assert good.qb_situation_index > weak.qb_situation_index + 0.15
    assert good_state.offense_index > weak_state.offense_index + 0.12
    assert good_state.early_season_uncertainty < weak_state.early_season_uncertainty


def test_qb_class_moves_win_prob_vs_fixed_opponent() -> None:
    opponent_roster = build_roster_construction(
        "OPP",
        {
            "returning_production": 50,
            "portal_in_value": 50,
            "portal_out_value": 50,
            "recruiting_class_score": 55,
            "experience_index": 50,
        },
    )
    opponent_qb = build_qb_situation(
        "OPP",
        {"qb_class": "incumbent", "qb_talent": 60, "ol_support": 55, "weapons_support": 55},
    )
    opponent_groups = build_position_groups(
        "OPP",
        {"ol": 55, "skill": 55, "front_seven": 60, "secondary": 58},
        roster=opponent_roster,
        qb=opponent_qb,
    )
    opp = compose_team_projection("OPP", opponent_roster, opponent_qb, opponent_groups)

    roster = build_roster_construction(
        "HOME",
        {
            "returning_production": 55,
            "portal_in_value": 55,
            "portal_out_value": 50,
            "recruiting_class_score": 70,
            "experience_index": 55,
        },
    )
    groups = build_position_groups(
        "HOME",
        {"ol": 70, "skill": 72, "front_seven": 65, "secondary": 64},
        roster=roster,
    )

    def _proj(qb_class: str) -> float:
        qb = build_qb_situation(
            "HOME",
            {
                "qb_class": qb_class,
                "qb_talent": 75,
                "ol_support": 70,
                "weapons_support": 72,
                "experience_starts": 10 if qb_class == "incumbent" else 0,
            },
        )
        home = compose_team_projection("HOME", roster, qb, groups)
        universe = EngineUniverse(
            season=2026,
            schedule=[],
            teams={"HOME": home, "OPP": opp},
        )
        proj = project_game_preview(
            universe, home_team="HOME", away_team="OPP", week=5, neutral_site=True
        )
        return proj.home_win_prob

    wp_inc = _proj("incumbent")
    wp_tf = _proj("true_freshman")
    assert wp_inc - wp_tf >= 0.06


def test_layer_wiring_compose() -> None:
    roster = build_roster_construction(
        "UGA",
        {
            "returning_production": 60,
            "portal_in_score": 55,
            "portal_out_score": 40,
            "recruiting_capital": 95,
            "experience_index": 65,
        },
    )
    qb = build_qb_situation(
        "UGA",
        {
            "qb_class": "incumbent",
            "starter_name": "Test QB",
            "experience_starts": 10,
            "qb_talent": 80,
            "ol_support": 85,
            "weapons_support": 88,
        },
    )
    groups = build_position_groups(
        "UGA",
        {"ol": 90, "skill": 88, "front_seven": 90, "secondary": 85},
        roster=roster,
        qb=qb,
    )
    state = compose_team_projection("UGA", roster, qb, groups)
    assert state.offense_index > 1.0
    assert state.defense_index > 1.0
    assert state.roster is not None
    assert state.qb is not None and state.qb.qb_class == "incumbent"
    assert state.qb.qb_situation_index > 1.0
    assert "roster_strength" in state.notes
    assert state.groups is not None


def test_packaged_universe_and_sample_projection() -> None:
    universe = build_packaged_universe(2026)
    assert len(universe.teams) >= 60
    assert "UGA" in universe.teams
    assert "TEX" in universe.teams
    assert universe.schedule

    uga = universe.teams["UGA"]
    assert uga.roster is not None
    assert uga.roster.roster_strength > 50
    assert uga.qb is not None
    assert uga.qb.qb_situation_index > 0.9

    proj = project_game_preview(
        universe, home_team="ALA", away_team="UGA", week=1, neutral_site=True
    )
    assert proj.engine_version == DEFAULT_SEASON_ENGINE_VERSION
    assert proj.home_team == "ALA"
    assert proj.away_team == "UGA"
    assert 0.02 <= proj.home_win_prob <= 0.98
    assert proj.expected_total > 30
    assert proj.early_season_uncertainty["active"] is True
    assert "roster" in proj.home_layers
    assert "qb" in proj.away_layers
    assert "roster_strength" in proj.home_layers["roster"]
    assert "qb_situation_index" in proj.away_layers["qb"]
    assert proj.fidelity == "approximate"


def test_contrasting_team_profiles_project_differently() -> None:
    """Stable incumbent power vs portal-heavy open/true-freshman profiles."""
    universe = build_packaged_universe(2026)
    uga = universe.teams["UGA"]
    fsu = universe.teams["FSU"]
    assert uga.roster and fsu.roster and uga.qb and fsu.qb
    assert uga.roster.roster_strength > fsu.roster.roster_strength
    assert uga.qb.qb_class == "incumbent"
    assert fsu.qb.qb_class == "portal"
    assert uga.offense_index > fsu.offense_index

    # Same opponent (BALL) — UGA should be a clearer favorite than FSU.
    ball = universe.teams["BALL"]
    u_vs = project_game_preview(
        EngineUniverse(season=2026, schedule=[], teams={"UGA": uga, "BALL": ball}),
        home_team="UGA",
        away_team="BALL",
        week=5,
        neutral_site=True,
    )
    f_vs = project_game_preview(
        EngineUniverse(season=2026, schedule=[], teams={"FSU": fsu, "BALL": ball}),
        home_team="FSU",
        away_team="BALL",
        week=5,
        neutral_site=True,
    )
    assert u_vs.home_win_prob > f_vs.home_win_prob + 0.05


def test_early_season_uncertainty_wider_in_w1() -> None:
    w1 = early_season_uncertainty(1)
    w5 = early_season_uncertainty(5)
    assert w1["active"] is True
    assert w5["active"] is False
    assert w1["win_prob_margin_sd"] > w5["win_prob_margin_sd"]


def test_season_sim_skeleton_path_coherence() -> None:
    universe = build_packaged_universe(2026)
    result = simulate_full_season(universe, n_sims=5, seed=7)
    assert result.n_sims == 5
    assert result.games_per_season == len(universe.schedule)
    assert abs(result.diagnostics["mean_wins_sum"] - len(universe.schedule)) < 0.01
    assert result.engine_version == DEFAULT_SEASON_ENGINE_VERSION


def test_status_contract() -> None:
    payload = engine_status_payload(season=2026, demo=True)
    assert payload["engine_version"] == DEFAULT_SEASON_ENGINE_VERSION
    assert payload["additive"] is True
    assert "edge_board_cfb_markets_only" in payload["does_not_modify"]
    assert len(payload["layers"]) >= 5
    assert "solid" in payload["solid_vs_approximate"]
    assert "Roster strength formula" in " ".join(payload["solid_vs_approximate"]["solid"])
    assert "qb_situation_index" in " ".join(payload["solid_vs_approximate"]["solid"])
    assert payload["entry_points"]["status"] == "GET /cfb/season-engine/status"
    assert "examples" in payload
    assert "roster_strength_ladder" in payload
    assert payload["layers"][0]["name"] == "roster_construction"
    assert "formula" in payload["layers"][0]
    assert "class_offense_mult" in payload["layers"][1]


def test_status_and_project_game_http() -> None:
    from src.main import app

    client = TestClient(app)
    status = client.get("/cfb/season-engine/status")
    assert status.status_code == 200
    body = status.json()
    assert body["engine_version"] == DEFAULT_SEASON_ENGINE_VERSION
    assert body["additive"] is True
    assert "examples" in body

    proj = client.post(
        "/cfb/season-engine/project-game",
        json={
            "home_team": "TEX",
            "away_team": "OSU",
            "week": 1,
            "neutral_site": True,
            "demo": True,
        },
    )
    assert proj.status_code == 200
    data = proj.json()
    assert data["ok"] is True
    assert data["home_team"] == "TEX"
    assert data["away_team"] == "OSU"
    assert data["engine_version"] == DEFAULT_SEASON_ENGINE_VERSION
    assert "expected_home_score" in data
    assert data["early_season_uncertainty"]["week"] == 1
    assert "roster_strength" in data["home_layers"]["roster"]
    assert "qb_situation_index" in data["away_layers"]["qb"]

    sim = client.post(
        "/cfb/season-engine/simulate",
        json={"n_sims": 3, "seed": 1, "demo": True},
    )
    assert sim.status_code == 200
    sim_body = sim.json()
    assert sim_body["ok"] is True
    assert sim_body["skeleton"] is True
    assert sim_body["n_sims"] == 3


def test_compute_qb_situation_index_class_gap() -> None:
    inc, _, bd_inc = compute_qb_situation_index(
        qb_class="incumbent", qb_talent=75, supporting_cast=80
    )
    tf, _, bd_tf = compute_qb_situation_index(
        qb_class="true_freshman", qb_talent=75, supporting_cast=45
    )
    assert inc > tf + 0.20
    assert bd_inc["class_mult"] > bd_tf["class_mult"]
