"""P3 game + total sim — separate total path, distributions, research-only."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from fastapi.testclient import TestClient

from src.services.cfb_season_engine import (
    DEFAULT_SEASON_ENGINE_VERSION,
    engine_status_payload,
    project_game_preview,
    project_game_to_dict,
    build_packaged_universe,
)
from src.services.cfb_season_engine.game_total_sim import (
    GAME_SIM_N_DEFAULT,
    USED_IN_SPREAD,
    documentation,
    total_path_mean,
)
from src.services.cfb_warehouse.predictions import write_prediction


def test_version_and_status_document_sim() -> None:
    assert DEFAULT_SEASON_ENGINE_VERSION == "cfb-season-engine-v0.11-game-total-sim"
    assert GAME_SIM_N_DEFAULT >= 5000
    assert USED_IN_SPREAD is False
    status = engine_status_payload(season=2026, demo=True)
    assert status["ok"] is True
    assert status["engine_version"] == DEFAULT_SEASON_ENGINE_VERSION
    assert status["used_in_spread"] is False
    assert status["game_total_sim"]["used_in_spread"] is False
    assert status["game_total_sim"]["n_sims_default"] >= 5000
    assert status["game_total_sim"]["weather"] == "not applied"
    assert status["slate"]["official_2026_fbs_schedule"] is False
    assert status["season_futures"]["cfp_make"] is None
    assert status["season_futures"]["natty"] is None
    assert status["season_futures"]["status"] == "placeholder"
    assert documentation()["total_path"].startswith("Separate")


def test_total_is_not_spread_hack() -> None:
    universe = build_packaged_universe(2026)
    home = project_game_preview(
        universe,
        home_team="OSU",
        away_team="BALL",
        week=5,
        neutral_site=False,
        n_sims=800,
        seed=7,
    )
    neut = project_game_preview(
        universe,
        home_team="OSU",
        away_team="BALL",
        week=5,
        neutral_site=True,
        n_sims=800,
        seed=7,
    )
    home_p = project_game_to_dict(home)
    neut_p = project_game_to_dict(neut)
    assert home_p["projection_formula"]["total_path"] == "separate_from_spread"
    assert home_p["drivers"]["matchup"]["total_path"]["not_spread_hack"] is True
    # HFA moves the strength-path sum and the spread; published total must not
    # inherit that HFA (otherwise it is a spread/score hack).
    strength_home = home_p["drivers"]["matchup"]["strength_path_diagnostic"][
        "total_if_summed"
    ]
    strength_neut = neut_p["drivers"]["matchup"]["strength_path_diagnostic"][
        "total_if_summed"
    ]
    assert abs(float(strength_home) - float(strength_neut)) > 1.0
    assert abs(home.spread_home - neut.spread_home) > 1.0
    assert abs(home_p["fair_total"] - neut_p["fair_total"]) < 0.75
    total_mean, diag = total_path_mean(universe.teams["OSU"], universe.teams["BALL"])
    assert diag["not_spread_hack"] is True
    assert total_mean > 30


def test_team_totals_sum_to_fair_total() -> None:
    universe = build_packaged_universe(2026)
    proj = project_game_preview(
        universe,
        home_team="UGA",
        away_team="FSU",
        week=1,
        n_sims=800,
        seed=11,
    )
    payload = project_game_to_dict(proj)
    home = payload["team_total_home"]
    away = payload["team_total_away"]
    total = payload["fair_total"]
    spread = payload["fair_spread"]
    assert abs((home + away) - total) < 1e-9
    assert abs((away - home) - spread) < 1e-9
    assert payload["used_in_spread"] is False
    assert payload["n_sims"] >= 200
    assert "margin" in payload["distributions"]
    assert "total" in payload["distributions"]
    assert payload["distributions"]["used_in_spread"] is False


def test_open_qb_wider_bands_than_incumbents() -> None:
    universe = build_packaged_universe(2026)
    # Dual open-QB chaos vs incumbent-vs-incumbent.
    chaos = project_game_preview(
        universe, home_team="UGA", away_team="FSU", week=1, n_sims=800, seed=3
    )
    stable = project_game_preview(
        universe,
        home_team="TEX",
        away_team="OSU",
        week=1,
        neutral_site=True,
        n_sims=800,
        seed=3,
    )
    assert chaos.uncertainty["open_qb"]["home"] or chaos.uncertainty["open_qb"]["away"]
    assert chaos.margin_sd > stable.margin_sd
    assert chaos.uncertainty["effective_total_sd"] > stable.uncertainty["effective_total_sd"]


def test_default_sim_n_is_research_grade() -> None:
    universe = build_packaged_universe(2026)
    proj = project_game_preview(universe, home_team="OSU", away_team="BALL", week=1)
    assert proj.n_sims >= 5000


def test_immutable_write_used_in_spread_false(tmp_path: Path) -> None:
    row = write_prediction(
        {
            "model_version": DEFAULT_SEASON_ENGINE_VERSION,
            "as_of": "2026-08-13T21:00:00Z",
            "game_id": "2026_w1_BALL@OSU_p3test",
            "season": 2026,
            "week": 1,
            "home_team_id": "OSU",
            "away_team_id": "BALL",
            "fair_spread": -20.5,
            "fair_total": 54.0,
            "wp": 0.9,
            "uncertainty": 24.0,
            "notes": {"used_in_spread": False, "kei": False},
        },
        root=tmp_path,
        prefer_hd=False,
        formats=("json",),
    )
    assert row["used_in_spread"] is False
    assert row["kei"] is False
    assert row["notes"]["used_in_spread"] is False
    assert row["model_version"] == DEFAULT_SEASON_ENGINE_VERSION


def test_status_and_project_game_http_200() -> None:
    from src.main import app

    client = TestClient(app)
    status = client.get("/cfb/season-engine/status")
    assert status.status_code == 200
    body = status.json()
    assert body["engine_version"] == "cfb-season-engine-v0.11-game-total-sim"
    assert body["used_in_spread"] is False
    assert body["season_futures"]["natty"] is None

    proj = client.post(
        "/cfb/season-engine/project-game",
        json={
            "home_team": "OSU",
            "away_team": "BALL",
            "week": 1,
            "demo": True,
            "n_sims": 400,
        },
    )
    assert proj.status_code == 200
    data = proj.json()
    assert data["ok"] is True
    assert data["used_in_spread"] is False
    assert data["n_sims"] == 400
    assert data["fair_total"] == data["team_total_home"] + data["team_total_away"]
