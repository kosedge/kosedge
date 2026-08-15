"""Single Power SoT + frozen season-projection artifact."""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.cfb_season_engine import (
    DEFAULT_SEASON_ENGINE_VERSION,
    build_packaged_universe,
    engine_status_payload,
    project_game_preview,
    project_game_to_dict,
)
from src.services.cfb_season_engine.power_sot import (
    POWER_AS_OF,
    POWER_VERSION,
    USED_IN_SPREAD,
    build_power_sot,
    build_season_projection_artifact,
    frozen_expected_scores,
    frozen_home_wp,
    load_packaged_power_sot,
    load_packaged_season_projections,
)
from src.services.cfb_warehouse.predictions import write_prediction


def test_engine_version_v015() -> None:
    assert DEFAULT_SEASON_ENGINE_VERSION == "cfb-season-engine-v0.15-power-sot"


def test_power_sot_is_official_136() -> None:
    universe = build_packaged_universe(2026)
    sot = build_power_sot(universe)
    assert sot["n_teams"] == 136
    assert sot["power_version"] == POWER_VERSION
    assert sot["power_as_of"] == POWER_AS_OF
    assert sot["used_in_spread"] is False
    assert sot["kei"] is False
    assert all(r.get("offense_index") is not None for r in sot["teams"])
    uga = sot["by_team"]["UGA"]
    live = universe.teams["UGA"]
    assert uga["offense_index"] == round(live.offense_index, 4)
    assert uga["defense_index"] == round(live.defense_index, 4)


def test_status_exposes_power_sot_ids() -> None:
    status = engine_status_payload(season=2026, demo=True)
    assert status["used_in_spread"] is False
    assert status["power_version"] == POWER_VERSION
    assert status["power_as_of"] == POWER_AS_OF
    assert status["n_teams"] == 136
    assert status["projection_artifact_id"]
    assert status["desk"]["team_dna"]["power_version"] == POWER_VERSION


def test_project_game_uses_same_indices() -> None:
    universe = build_packaged_universe(2026)
    sot = build_power_sot(universe)
    proj = project_game_to_dict(
        project_game_preview(
            universe, home_team="TCU", away_team="UNC", week=0, n_sims=200, seed=2026
        )
    )
    assert proj["used_in_spread"] is False
    home_power = sot["by_team"]["TCU"]["power_index"]
    away_power = sot["by_team"]["UNC"]["power_index"]
    # Neutral Week 0: higher power should be favored (not inverted).
    if home_power > away_power:
        assert proj["spread_home"] < 0
    elif away_power > home_power:
        assert proj["spread_home"] > 0


def test_frozen_projection_schema_and_conservation() -> None:
    universe = build_packaged_universe(2026)
    art = build_season_projection_artifact(universe, n_sims=200, seed=7)
    assert art["n_sims"] == 200
    assert art["n_teams"] == 136
    assert art["used_in_spread"] is False
    assert art["cfp_make"] is None
    assert art["natty"] is None
    assert art["win_tables_final"] is False
    assert art["n_games_scored"] >= 700
    # FBS E[wins] cannot exceed scored games; should be close when FCS take few.
    assert 400 < art["sum_expected_wins"] <= art["n_games_scored"] + 1e-6
    teams = {r["team"] for r in art["teams"]}
    assert "OSU" in teams and "UGA" in teams and "ALA" in teams
    top = {r["team"] for r in art["teams"][:15]}
    assert top & {"OSU", "UGA", "ALA", "TEX", "ND", "ORE", "PSU", "MICH"}


def test_packaged_artifact_schema_if_present() -> None:
    pack = load_packaged_season_projections()
    power = load_packaged_power_sot()
    if not pack or not power:
        return
    assert power["n_teams"] == 136
    assert power["used_in_spread"] is False
    assert pack["n_sims"] >= 5000
    assert pack["cfp_make"] is None
    assert pack["used_in_spread"] is False
    assert len(pack["teams"]) == 136


def test_prediction_write_stays_research(tmp_path) -> None:
    row = write_prediction(
        {
            "model_version": DEFAULT_SEASON_ENGINE_VERSION,
            "as_of": "2026-08-14T18:00:00Z",
            "game_id": "2026_w0_power_sot_test",
            "season": 2026,
            "week": 0,
            "home_team_id": "TCU",
            "away_team_id": "UNC",
            "fair_spread": -3.5,
            "fair_total": 52.0,
            "wp": 0.58,
            "uncertainty": 14.0,
            "notes": {"used_in_spread": False, "kei": False},
        },
        root=tmp_path,
        prefer_hd=False,
        formats=("json",),
    )
    assert row["used_in_spread"] is False
    assert USED_IN_SPREAD is False


def test_frozen_wp_matches_expected_score_sign() -> None:
    universe = build_packaged_universe(2026)
    game = next(
        g
        for g in universe.schedule
        if g.home_team == "TCU" and g.away_team == "UNC" and g.week == 0
    )
    pair = frozen_expected_scores(game, universe.teams)
    assert pair is not None
    home_exp, away_exp, sd = pair
    wp = frozen_home_wp(home_exp, away_exp, sd)
    if home_exp > away_exp:
        assert wp > 0.5
    elif away_exp > home_exp:
        assert wp < 0.5
