"""Tests for the hierarchical CFB season engine foundation."""

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
from src.services.cfb_season_engine.qb_situation import classify_qb_situation
from src.services.cfb_season_engine.roster_construction import build_roster_construction
from src.services.cfb_season_engine.team_projection import compose_team_projection
from src.services.cfb_season_engine.position_groups import build_position_groups
from src.services.cfb_season_engine.qb_situation import build_qb_situation
from src.services.cfb_season_engine.priors import early_season_uncertainty


def test_engine_version_string() -> None:
    assert DEFAULT_SEASON_ENGINE_VERSION == "cfb-season-engine-v0.1-foundation"


def test_qb_situation_classification() -> None:
    assert classify_qb_situation(qb_class="incumbent") == "incumbent"
    assert classify_qb_situation(is_portal=True) == "portal"
    assert classify_qb_situation(open_competition=True) == "open_competition"
    assert classify_qb_situation(is_true_freshman=True) == "true_freshman"
    assert classify_qb_situation(experience_starts=12) == "incumbent"
    # Priority: true freshman beats portal flag
    assert (
        classify_qb_situation(is_true_freshman=True, is_portal=True) == "true_freshman"
    )


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
    groups = build_position_groups("UGA", {"ol": 90, "skill": 88, "front_seven": 90, "secondary": 85}, roster=roster, qb=qb)
    state = compose_team_projection("UGA", roster, qb, groups)
    assert state.offense_index > 1.0
    assert state.defense_index > 1.0
    assert state.roster is not None
    assert state.qb is not None and state.qb.qb_class == "incumbent"
    assert state.groups is not None


def test_packaged_universe_and_sample_projection() -> None:
    universe = build_packaged_universe(2026)
    assert len(universe.teams) >= 60
    assert "UGA" in universe.teams
    assert "TEX" in universe.teams
    assert universe.schedule

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
    assert proj.fidelity == "approximate"


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
    # Each game produces one win → mean wins sum ≈ game count
    assert abs(result.diagnostics["mean_wins_sum"] - len(universe.schedule)) < 0.01


def test_status_contract() -> None:
    payload = engine_status_payload(season=2026, demo=True)
    assert payload["engine_version"] == DEFAULT_SEASON_ENGINE_VERSION
    assert payload["additive"] is True
    assert "edge_board_cfb_markets_only" in payload["does_not_modify"]
    assert len(payload["layers"]) >= 5
    assert "solid" in payload["solid_vs_approximate"]
    assert payload["entry_points"]["status"] == "GET /cfb/season-engine/status"


def test_status_and_project_game_http() -> None:
    from src.main import app

    client = TestClient(app)
    status = client.get("/cfb/season-engine/status")
    assert status.status_code == 200
    body = status.json()
    assert body["engine_version"] == DEFAULT_SEASON_ENGINE_VERSION
    assert body["additive"] is True

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
    assert "expected_home_score" in data
    assert data["early_season_uncertainty"]["week"] == 1

    sim = client.post(
        "/cfb/season-engine/simulate",
        json={"n_sims": 3, "seed": 1, "demo": True},
    )
    assert sim.status_code == 200
    sim_body = sim.json()
    assert sim_body["ok"] is True
    assert sim_body["skeleton"] is True
    assert sim_body["n_sims"] == 3
