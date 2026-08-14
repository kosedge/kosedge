"""Tests for CFB in-season updating foundation."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.services.cfb_season_engine import priors as P
from src.services.cfb_season_engine import project_game_preview
from src.services.cfb_season_engine.efficiency import build_efficiency_profile
from src.services.cfb_season_engine.in_season_update import (
    ingest_result,
    learning_rate,
    reset_state,
    state_summary,
    week_weight,
)
from src.services.cfb_season_engine.loaders import resolve_season_universe


@pytest.fixture()
def clean_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    path = tmp_path / "state.json"
    monkeypatch.setenv("CFB_INSEASON_STATE_PATH", str(path))
    # Force reload with empty state
    reset_state(season=2026)
    yield path
    reset_state(season=2026)


def test_week_weight_early_gt_late():
    assert week_weight(1) > week_weight(5) > week_weight(13)


def test_learning_rate_decays():
    assert learning_rate(0) > learning_rate(3) > learning_rate(10)


def test_single_result_moves_rating_modestly(clean_state):
    before = build_efficiency_profile("UGA", apply_inseason=True)
    # UGA favored by ~20 but only wins by 3 → large negative residual for favorite
    out = ingest_result(
        home_team="UGA",
        away_team="BALL",
        home_score=24,
        away_score=21,
        week=1,
        season=2026,
        model_spread_home=-28.0,
        source="test",
    )
    assert out["ok"] is True
    assert out["skipped"] is False
    # Home underperformed model → home off should drop
    assert out["home"]["delta_off_eff"] < 0
    assert abs(out["home"]["delta_off_eff"]) <= 3.5 + 1e-6
    after = build_efficiency_profile("UGA", apply_inseason=True)
    assert after.off_eff < before.off_eff
    # Preseason baseline preserved on state
    st = state_summary(team="UGA")
    assert st["preseason_off_eff"] == pytest.approx(before.off_eff, abs=0.05)


def test_early_season_moves_more_than_late(clean_state):
    early = ingest_result(
        home_team="OSU",
        away_team="MICH",
        home_score=45,
        away_score=10,
        week=1,
        model_spread_home=-3.0,
        game_id="early-test",
    )
    reset_state(season=2026)
    late = ingest_result(
        home_team="OSU",
        away_team="MICH",
        home_score=45,
        away_score=10,
        week=12,
        model_spread_home=-3.0,
        game_id="late-test",
    )
    assert abs(early["home"]["delta_off_eff"]) > abs(late["home"]["delta_off_eff"])


def test_idempotent_same_game_id(clean_state):
    a = ingest_result(
        home_team="TEX",
        away_team="OU",
        home_score=31,
        away_score=28,
        week=2,
        model_spread_home=-7.0,
        game_id="tex-ou-w2",
    )
    b = ingest_result(
        home_team="TEX",
        away_team="OU",
        home_score=31,
        away_score=28,
        week=2,
        model_spread_home=-7.0,
        game_id="tex-ou-w2",
    )
    assert a["skipped"] is False
    assert b["skipped"] is True
    assert a["home"]["n_games"] == 1


def test_project_game_picks_up_inseason_delta(clean_state):
    universe, _ = resolve_season_universe(season=2026, as_of_week=5, demo=True)
    before = project_game_preview(
        universe, home_team="UGA", away_team="BALL", week=5, season=2026
    )
    ingest_result(
        home_team="UGA",
        away_team="BALL",
        home_score=55,
        away_score=3,
        week=1,
        model_spread_home=-20.0,
        game_id="blowout-boost",
    )
    # Rebuild universe so efficiency is reloaded with deltas
    universe2, _ = resolve_season_universe(season=2026, as_of_week=5, demo=True)
    after = project_game_preview(
        universe2, home_team="UGA", away_team="BALL", week=5, season=2026
    )
    # Home crushed expectation → should look stronger (more negative spread / higher WP)
    assert after.home_win_prob >= before.home_win_prob - 1e-9
    assert after.spread_home <= before.spread_home + 1e-9


def test_engine_version_bump():
    assert "v0.13-calibration-scale" in P.ENGINE_VERSION
