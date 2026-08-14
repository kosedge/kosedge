"""v0.13 margin calibration / blowout-scale — research only."""

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
from src.services.cfb_season_engine.fbs_universe import is_official_fbs
from src.services.cfb_season_engine.margin_calibration import (
    CALIBRATION_ID,
    USED_IN_SPREAD,
    calibrate_margin,
)
from src.services.cfb_warehouse.predictions import write_prediction


def test_version_and_status_expose_calibration() -> None:
    assert DEFAULT_SEASON_ENGINE_VERSION == "cfb-season-engine-v0.14-efficiency-backbone"
    status = engine_status_payload(season=2026, demo=True)
    assert status["ok"] is True
    assert status["engine_version"] == DEFAULT_SEASON_ENGINE_VERSION
    assert status["used_in_spread"] is False
    assert status["calibration_id"] == CALIBRATION_ID
    assert status["calibration_as_of"] == "2026-08-14"
    assert status["season_futures"]["cfp_make"] is None
    assert status["season_futures"]["natty"] is None


def test_tanh_compresses_blowouts_keeps_close_games() -> None:
    blow = calibrate_margin(39.0, fcs_matchup=False)
    mid = calibrate_margin(12.0, fcs_matchup=False)
    close = calibrate_margin(4.0, fcs_matchup=False)
    assert abs(blow["calibrated_margin"]) < abs(blow["raw_margin"])
    assert abs(blow["calibrated_margin"]) < 28.0
    assert abs(mid["calibrated_margin"]) < abs(mid["raw_margin"])
    assert abs(close["calibrated_margin"]) <= 4.2
    fcs = calibrate_margin(39.0, fcs_matchup=True)
    assert abs(fcs["calibrated_margin"]) > abs(blow["calibrated_margin"])
    assert blow["used_in_spread"] is False


def test_osu_ball_no_longer_routine_minus_35() -> None:
    universe = build_packaged_universe(2026)
    proj = project_game_preview(
        universe, home_team="OSU", away_team="BALL", week=1, n_sims=400, seed=7
    )
    payload = project_game_to_dict(proj)
    assert payload["used_in_spread"] is False
    assert proj.spread_home < -10.0
    assert proj.spread_home > -28.5
    cal = payload["drivers"]["matchup"]["margin_calibration"]
    assert abs(cal["calibrated_margin"]) < abs(cal["raw_margin"])
    assert abs((payload["team_total_home"] + payload["team_total_away"]) - payload["fair_total"]) < 1e-9


def test_open_qb_sigma_still_wider() -> None:
    universe = build_packaged_universe(2026)
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


def test_fcs_label_intact() -> None:
    universe = build_packaged_universe(2026)
    fcs = [c for c in universe.teams if not is_official_fbs(c, include_transition=True)]
    assert fcs
    state = universe.teams[fcs[0]]
    assert state.source == "fcs_placeholder" or str(state.fidelity) == "placeholder"
    assert "generic" not in str(state.notes).lower() or "not_generic" in str(state.notes)


def test_prediction_write_stays_research(tmp_path) -> None:
    row = write_prediction(
        {
            "model_version": DEFAULT_SEASON_ENGINE_VERSION,
            "as_of": "2026-08-14T12:00:00Z",
            "game_id": "2026_w0_cal_scale_test",
            "season": 2026,
            "week": 0,
            "home_team_id": "USC",
            "away_team_id": "SJSU",
            "fair_spread": -18.0,
            "fair_total": 62.0,
            "wp": 0.82,
            "uncertainty": 22.0,
            "notes": {"used_in_spread": False, "kei": False},
        },
        root=tmp_path,
        prefer_hd=False,
        formats=("json",),
    )
    assert row["used_in_spread"] is False
    assert row["kei"] is False
    assert USED_IN_SPREAD is False
