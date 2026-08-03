"""Tests for injury / availability path shocks (season-engine v1.2)."""

from __future__ import annotations

from src.services.nfl_season_engine import (
    DEFAULT_SEASON_ENGINE_VERSION,
    InjuryPath,
    build_demo_universe,
    project_game_player_boxes,
    simulate_full_season,
)
from src.services.nfl_season_engine.injury_paths import (
    apply_injury_paths_for_week,
    availability_for_week,
    player_offense_value,
)


def _det_gibbs_key(universe) -> str:
    role = next(r for r in universe.rosters["DET"] if "Gibbs" in r.player_name)
    return role.player_key


def test_engine_version_surfaces_injury_shocks() -> None:
    # Injury paths remain in v1.2+; version string tags the latest capability.
    assert DEFAULT_SEASON_ENGINE_VERSION.startswith("nfl-season-engine-v1.")
    assert (
        "injury-shocks" in DEFAULT_SEASON_ENGINE_VERSION
        or "deeper-usage" in DEFAULT_SEASON_ENGINE_VERSION
        or "survivor" in DEFAULT_SEASON_ENGINE_VERSION
        or "hardened" in DEFAULT_SEASON_ENGINE_VERSION
        or "depth-volatility" in DEFAULT_SEASON_ENGINE_VERSION
    )


def test_out_zeros_injured_usage_in_week_range() -> None:
    universe = build_demo_universe(2026)
    key = _det_gibbs_key(universe)
    path = InjuryPath(
        player_key=key,
        player_name="J.Gibbs",
        team="DET",
        status="out",
        week_start=4,
        week_end=8,
    )
    healthy = next(r for r in universe.rosters["DET"] if r.player_key == key)
    adj_rosters, _, adjustments = apply_injury_paths_for_week(
        universe.rosters, universe.strengths, [path], week=6
    )
    injured = next(r for r in adj_rosters["DET"] if r.player_key == key)
    assert injured.rush_share == 0.0
    assert injured.target_share == 0.0
    assert injured.snap_share == 0.0
    assert adjustments[0].availability == 0.0
    assert adjustments[0].freed_rush_share == healthy.rush_share


def test_teammates_absorb_volume() -> None:
    universe = build_demo_universe(2026)
    key = _det_gibbs_key(universe)
    mont = next(r for r in universe.rosters["DET"] if "Montgomery" in r.player_name)
    path = InjuryPath(
        player_key=key,
        team="DET",
        status="out",
        week_start=1,
        week_end=1,
    )
    adj_rosters, _, _ = apply_injury_paths_for_week(
        universe.rosters, universe.strengths, [path], week=1
    )
    mont_adj = next(r for r in adj_rosters["DET"] if r.player_key == mont.player_key)
    assert mont_adj.rush_share > mont.rush_share
    assert mont_adj.snap_share > mont.snap_share


def test_team_strength_shifts_when_star_out() -> None:
    universe = build_demo_universe(2026)
    key = _det_gibbs_key(universe)
    before = universe.strengths["DET"].offense_index
    path = InjuryPath(
        player_key=key,
        team="DET",
        status="out",
        week_start=1,
        week_end=1,
    )
    _, adj_strengths, adjustments = apply_injury_paths_for_week(
        universe.rosters, universe.strengths, [path], week=1
    )
    assert adj_strengths["DET"].offense_index < before
    assert adjustments[0].offense_delta < 0
    # Value-weighted: Gibbs should be worth a meaningful chunk of offense.
    role = next(r for r in universe.rosters["DET"] if r.player_key == key)
    assert player_offense_value(role) >= 0.03


def test_limited_vs_full_out_differ() -> None:
    universe = build_demo_universe(2026)
    key = _det_gibbs_key(universe)
    out_path = InjuryPath(
        player_key=key, team="DET", status="out", week_start=1, week_end=1
    )
    limited_path = InjuryPath(
        player_key=key,
        team="DET",
        status="limited",
        week_start=1,
        week_end=1,
        availability=0.5,
    )
    out_rosters, out_str, _ = apply_injury_paths_for_week(
        universe.rosters, universe.strengths, [out_path], week=1
    )
    lim_rosters, lim_str, _ = apply_injury_paths_for_week(
        universe.rosters, universe.strengths, [limited_path], week=1
    )
    out_role = next(r for r in out_rosters["DET"] if r.player_key == key)
    lim_role = next(r for r in lim_rosters["DET"] if r.player_key == key)
    healthy = next(r for r in universe.rosters["DET"] if r.player_key == key)

    assert out_role.rush_share == 0.0
    assert abs(lim_role.rush_share - healthy.rush_share * 0.5) < 1e-6
    assert lim_str["DET"].offense_index > out_str["DET"].offense_index
    assert lim_str["DET"].offense_index < universe.strengths["DET"].offense_index


def test_week_outside_range_unaffected() -> None:
    universe = build_demo_universe(2026)
    key = _det_gibbs_key(universe)
    path = InjuryPath(
        player_key=key,
        team="DET",
        status="out",
        week_start=4,
        week_end=8,
    )
    assert availability_for_week(path, 3) == 1.0
    assert availability_for_week(path, 9) == 1.0
    adj_rosters, adj_strengths, adjustments = apply_injury_paths_for_week(
        universe.rosters, universe.strengths, [path], week=3
    )
    role = next(r for r in adj_rosters["DET"] if r.player_key == key)
    healthy = next(r for r in universe.rosters["DET"] if r.player_key == key)
    assert role.rush_share == healthy.rush_share
    assert adj_strengths["DET"].offense_index == universe.strengths["DET"].offense_index
    assert adjustments == []


def test_returning_ramps_availability() -> None:
    path = InjuryPath(
        player_key="x",
        player_name="x",
        team="DET",
        status="returning",
        week_start=4,
        week_end=8,
        availability=0.4,
    )
    assert availability_for_week(path, 4) == 0.4
    assert availability_for_week(path, 8) == 1.0
    mid = availability_for_week(path, 6)
    assert 0.4 < mid < 1.0


def test_game_boxes_respect_injury_path() -> None:
    universe = build_demo_universe(2026)
    key = _det_gibbs_key(universe)
    path = InjuryPath(
        player_key=key,
        player_name="J.Gibbs",
        team="DET",
        status="out",
        week_start=1,
        week_end=1,
    )
    healthy = project_game_player_boxes(
        universe,
        home_team="DET",
        away_team="GB",
        week=1,
        n_replicates=80,
        seed=5,
    )
    injured = project_game_player_boxes(
        universe,
        home_team="DET",
        away_team="GB",
        week=1,
        n_replicates=80,
        seed=5,
        injury_paths=[path],
    )
    g_h = next(p for p in healthy.players if p["player_key"] == key)
    g_i = next(p for p in injured.players if p["player_key"] == key)
    assert g_i["distributions"]["carries"]["mean"] < 0.5
    assert g_i["point_estimate"]["rush_yards"] < g_h["point_estimate"]["rush_yards"] * 0.15

    mont_h = next(p for p in healthy.players if "Montgomery" in p["player_name"])
    mont_i = next(p for p in injured.players if "Montgomery" in p["player_name"])
    assert mont_i["distributions"]["carries"]["mean"] > mont_h["distributions"]["carries"]["mean"]

    # Game script: DET win prob should drop when star RB is out.
    assert (
        injured.game_script_summary["home_win_prob_mean"]
        < healthy.game_script_summary["home_win_prob_mean"]
    )


def test_season_totals_reflect_multiweek_out() -> None:
    universe = build_demo_universe(2026)
    key = _det_gibbs_key(universe)
    path = InjuryPath(
        player_key=key,
        player_name="J.Gibbs",
        team="DET",
        status="out",
        week_start=4,
        week_end=8,
    )
    base = simulate_full_season(universe, n_sims=16, seed=21)
    shocked = simulate_full_season(universe, n_sims=16, seed=21, injury_paths=[path])
    g_base = next(r for r in base.player_season_totals if r["player_key"] == key)
    g_shock = next(r for r in shocked.player_season_totals if r["player_key"] == key)
    assert g_shock["rush_yards_mean"] < g_base["rush_yards_mean"]
    # ~5 / 17 games missed → material but not total wipeout of season yards.
    assert g_shock["rush_yards_mean"] > g_base["rush_yards_mean"] * 0.35
    assert shocked.diagnostics["injury_path_count"] == 1
    # Wins should not rise under a star-RB out path (allow small MC noise).
    assert shocked.team_wins["DET"]["mean"] <= base.team_wins["DET"]["mean"] + 0.35
