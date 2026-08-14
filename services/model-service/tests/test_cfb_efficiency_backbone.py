"""v0.14 warehouse efficiency backbone + SP+ fill reduction — research only."""

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
from src.services.cfb_season_engine.efficiency import (
    build_efficiency_profile,
    load_efficiency_snapshot,
    snapshot_meta,
)
from src.services.cfb_season_engine.fbs_universe import official_fbs_codes
from src.services.cfb_season_engine.priors import BACKBONE_VERSION

FILLED = (
    "ARST",
    "CSU",
    "ECU",
    "JVST",
    "M-OH",
    "MIZZ",
    "NEV",
    "ODU",
    "TOL",
    "UAB",
    "UNM",
    "UNT",
)
CAMP_OPEN_QB = ("UGA", "MICH", "FSU", "LSU", "ALA")


def test_version_and_status_expose_backbone() -> None:
    assert DEFAULT_SEASON_ENGINE_VERSION == "cfb-season-engine-v0.14-efficiency-backbone"
    assert BACKBONE_VERSION == "cfb-efficiency-backbone-v0.14-20260814"
    status = engine_status_payload(season=2026, demo=True)
    assert status["ok"] is True
    assert status["engine_version"] == DEFAULT_SEASON_ENGINE_VERSION
    assert status["used_in_spread"] is False
    assert status["backbone_version"] == BACKBONE_VERSION
    assert status["n_filled"] == 12
    assert status["n_thin"] == 0
    bb = status["efficiency_backbone"]
    assert bb["n_sp_plus"] == 124
    assert bb["n_warehouse_fill"] == 12
    assert bb["n_thin"] == 0
    assert bb["thin"] == []
    assert sorted(bb["filled"]) == sorted(FILLED)
    assert bb["used_in_spread"] is False
    assert status["season_futures"]["cfp_make"] is None
    assert status["season_futures"]["natty"] is None
    assert status["used_in_spread"] is False
    cov = status["roster_coverage_official"]
    assert cov["efficiency_league_avg_fill"] == []
    assert sorted(cov["efficiency_warehouse_fill"]) == sorted(FILLED)
    assert cov["efficiency_thin"] == []


def test_official_snapshot_has_zero_silent_league_average() -> None:
    snap = load_efficiency_snapshot()
    official = official_fbs_codes()
    teams = snap.get("teams") or {}
    assert set(teams) == official
    silent = [
        code
        for code, row in teams.items()
        if row.get("source") == "league_average_fill"
    ]
    assert silent == []
    meta = snapshot_meta(snap)
    assert meta["n_sp_plus"] == 124
    assert meta["n_filled"] == 12
    assert meta["n_thin"] == 0
    assert meta["n_league_average_fill"] == 0
    assert snap.get("used_in_spread") is False


def test_filled_teams_use_warehouse_not_fifty_fifty() -> None:
    for code in FILLED:
        prof = build_efficiency_profile(code, apply_inseason=False)
        assert prof.source == "warehouse_pbp_epa_adj_2025"
        assert prof.fidelity == "approximate"
        assert (prof.off_eff, prof.def_eff) != (50.0, 50.0)
        assert 5.0 <= prof.off_eff <= 95.0
        assert 5.0 <= prof.def_eff <= 95.0
    mizz = build_efficiency_profile("MIZZ", apply_inseason=False)
    assert mizz.def_eff > 60.0
    unt = build_efficiency_profile("UNT", apply_inseason=False)
    assert unt.off_eff > 70.0


def test_missing_code_is_labeled_thin_not_silent_fill() -> None:
    prof = build_efficiency_profile("ZZZ", apply_inseason=False)
    assert prof.source == "thin_sample_labeled"
    assert prof.fidelity == "placeholder"
    assert "silent" not in prof.notes.lower() or "not a silent" in prof.notes.lower()


def test_osu_ball_scale_still_compressed() -> None:
    universe = build_packaged_universe(2026)
    proj = project_game_preview(
        universe, home_team="OSU", away_team="BALL", week=1, n_sims=400, seed=7
    )
    payload = project_game_to_dict(proj)
    assert payload["used_in_spread"] is False
    assert proj.spread_home < -10.0
    assert proj.spread_home > -28.5


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
    for team in CAMP_OPEN_QB:
        qb = universe.teams[team].qb
        assert qb is not None
        assert qb.uncertainty >= 0.35


def test_blue_blood_stronger_than_g5_fill() -> None:
    universe = build_packaged_universe(2026)
    osu = universe.teams["OSU"]
    ball = universe.teams["BALL"]
    mizz = universe.teams["MIZZ"]
    nev = universe.teams["NEV"]
    osu_power = 0.5 * (osu.offense_index + osu.defense_index)
    ball_power = 0.5 * (ball.offense_index + ball.defense_index)
    mizz_power = 0.5 * (mizz.offense_index + mizz.defense_index)
    nev_power = 0.5 * (nev.offense_index + nev.defense_index)
    assert osu_power > ball_power
    assert mizz_power > nev_power
    assert osu.efficiency and osu.efficiency.source.startswith("packaged_sp_plus")
    assert mizz.efficiency and mizz.efficiency.source == "warehouse_pbp_epa_adj_2025"
