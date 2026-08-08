"""Tests for v1.8 coaching / tendency layer."""

from __future__ import annotations

import random
from dataclasses import replace

from src.services.nfl_season_engine import (
    DEFAULT_SEASON_ENGINE_VERSION,
    InjuryPath,
    build_demo_universe,
    evaluate_survivor,
    project_game_player_boxes,
)
from src.services.nfl_season_engine.coaching_tendencies import (
    CoachingProfile,
    all_team_profiles,
    baseline_pass_rate,
    profile_for_team,
)
from src.services.nfl_season_engine.game_script import (
    build_game_script,
    play_mix_from_script,
)
from src.services.nfl_season_engine.injury_paths import apply_injury_paths_for_week
from src.services.nfl_season_engine.red_zone import rz_pass_rate_from_script
from src.services.nfl_season_engine.types import ScheduledGame


def test_engine_version_coaching() -> None:
    assert DEFAULT_SEASON_ENGINE_VERSION.startswith("nfl-season-engine-v1.")
    assert (
        "coaching" in DEFAULT_SEASON_ENGINE_VERSION
        or "real-2026" in DEFAULT_SEASON_ENGINE_VERSION
        or "real-depth" in DEFAULT_SEASON_ENGINE_VERSION
        or "smoke-polish" in DEFAULT_SEASON_ENGINE_VERSION
        or "survivor-planner" in DEFAULT_SEASON_ENGINE_VERSION
        or "calibration" in DEFAULT_SEASON_ENGINE_VERSION
        or "player-regression" in DEFAULT_SEASON_ENGINE_VERSION
    )


def test_all_32_teams_have_stable_profiles() -> None:
    profiles = all_team_profiles()
    assert len(profiles) == 32
    # Seed stability: repeated lookup is identical.
    for team, profile in profiles.items():
        again = profile_for_team(team)
        assert again == profile
        assert -0.035 <= profile.pass_rate_bias <= 0.035
        assert 0.80 <= profile.script_aggression <= 1.20
        assert -0.040 <= profile.rz_pass_bias <= 0.040


def test_opposite_pass_rate_bias_neutral_script() -> None:
    """High vs low coaching pass_rate_bias → different baseline pass under neutral."""
    pass_heavy = CoachingProfile(
        team="XXX",
        pass_rate_bias=0.030,
        script_aggression=1.0,
        label="test_pass",
        source="test",
    )
    run_heavy = CoachingProfile(
        team="YYY",
        pass_rate_bias=-0.030,
        script_aggression=1.0,
        label="test_run",
        source="test",
    )
    base_hi = baseline_pass_rate(
        league_base=0.58, strength_pass_bias=0.0, coaching=pass_heavy
    )
    base_lo = baseline_pass_rate(
        league_base=0.58, strength_pass_bias=0.0, coaching=run_heavy
    )
    assert base_hi > base_lo + 0.05

    hi_mix = play_mix_from_script(
        base_pass_rate=base_hi,
        detail="neutral",
        intensity=0.0,
        time_bucket="mid",
        coaching=pass_heavy,
    )
    lo_mix = play_mix_from_script(
        base_pass_rate=base_lo,
        detail="neutral",
        intensity=0.0,
        time_bucket="mid",
        coaching=run_heavy,
    )
    assert hi_mix["pass_rate"] > lo_mix["pass_rate"] + 0.05

    # Real clubs: KC pass-aggressive vs SF run-scheme under forced neutral.
    universe = build_demo_universe(2026)
    # Zero strength pass bias so coaching identity dominates the comparison.
    strengths = {
        "KC": replace(universe.strengths["KC"], pass_rate_bias=0.0),
        "SF": replace(universe.strengths["SF"], pass_rate_bias=0.0),
        "BUF": universe.strengths["BUF"],
    }
    game_kc = ScheduledGame(
        season=2026, week=1, game_id="coach-kc", home_team="KC", away_team="BUF"
    )
    game_sf = ScheduledGame(
        season=2026, week=1, game_id="coach-sf", home_team="SF", away_team="BUF"
    )
    kc_script, _ = build_game_script(
        game_kc,
        strengths,
        rng=random.Random(1),
        realized=False,
        force_home_score=21.0,
        force_away_score=21.0,
        force_minutes_remaining=30.0,
        force_home_detail="neutral",
        force_away_detail="neutral",
    )
    sf_script, _ = build_game_script(
        game_sf,
        strengths,
        rng=random.Random(1),
        realized=False,
        force_home_score=21.0,
        force_away_score=21.0,
        force_minutes_remaining=30.0,
        force_home_detail="neutral",
        force_away_detail="neutral",
    )
    assert kc_script.home_pass_rate > sf_script.home_pass_rate + 0.03


def test_high_script_aggression_trailing_larger_pass_lift() -> None:
    high = CoachingProfile(
        team="HI",
        pass_rate_bias=0.0,
        script_aggression=1.18,
        label="agg",
        source="test",
    )
    low = CoachingProfile(
        team="LO",
        pass_rate_bias=0.0,
        script_aggression=0.82,
        label="soft",
        source="test",
    )
    base = 0.58
    hi_mix = play_mix_from_script(
        base_pass_rate=base,
        detail="large_deficit",
        intensity=0.9,
        time_bucket="late",
        coaching=high,
    )
    lo_mix = play_mix_from_script(
        base_pass_rate=base,
        detail="large_deficit",
        intensity=0.9,
        time_bucket="late",
        coaching=low,
    )
    hi_lift = hi_mix["pass_rate"] - base
    lo_lift = lo_mix["pass_rate"] - base
    assert hi_lift > lo_lift + 0.02
    assert hi_mix["hurry_up"] >= lo_mix["hurry_up"]


def test_high_rz_pass_bias_raises_rz_pass_rate() -> None:
    high = CoachingProfile(
        team="HI", rz_pass_bias=0.035, label="rz_pass", source="test"
    )
    low = CoachingProfile(
        team="LO", rz_pass_bias=-0.035, label="rz_run", source="test"
    )
    hi_rz = rz_pass_rate_from_script(
        base_team_pass_rate=0.58,
        detail="neutral",
        intensity=0.0,
        time_bucket="mid",
        coaching=high,
    )
    lo_rz = rz_pass_rate_from_script(
        base_team_pass_rate=0.58,
        detail="neutral",
        intensity=0.0,
        time_bucket="mid",
        coaching=low,
    )
    assert hi_rz > lo_rz + 0.05

    # Curated KC vs SF under same script inputs.
    kc = rz_pass_rate_from_script(
        base_team_pass_rate=0.60,
        detail="small_lead",
        intensity=0.55,
        time_bucket="mid",
        team="KC",
    )
    sf = rz_pass_rate_from_script(
        base_team_pass_rate=0.60,
        detail="small_lead",
        intensity=0.55,
        time_bucket="mid",
        team="SF",
    )
    assert kc > sf


def test_injury_depth_red_zone_survivor_still_function() -> None:
    universe = build_demo_universe(2026)
    cook = next(r for r in universe.rosters["BUF"] if r.player_name == "J.Cook")
    path = InjuryPath(
        player_key=cook.player_key,
        player_name=cook.player_name,
        team="BUF",
        status="out",
        week_start=1,
        week_end=3,
    )
    adj, _, adjustments = apply_injury_paths_for_week(
        universe.rosters, universe.strengths, [path], week=1
    )
    assert adjustments
    injured = next(r for r in adj["BUF"] if r.player_key == cook.player_key)
    assert injured.rush_share == 0.0

    proj = project_game_player_boxes(
        universe,
        home_team="KC",
        away_team="BUF",
        week=1,
        n_replicates=120,
        seed=42,
        injury_paths=[path],
        include_diagnostics=True,
    )
    assert (
        "coaching" in proj.engine_version
        or "real-2026" in proj.engine_version
        or "real-depth" in proj.engine_version
        or "smoke-polish" in proj.engine_version
        or "survivor-planner" in proj.engine_version
        or "calibration" in proj.engine_version
        or "player-regression" in DEFAULT_SEASON_ENGINE_VERSION
    )
    assert "coaching_profile" in proj.diagnostics
    assert "tendency_effects" in proj.diagnostics
    assert "red_zone" in proj.diagnostics
    assert "depth_structure" in proj.diagnostics
    assert proj.diagnostics["coaching_profile"]["home"]["team"] == "KC"
    assert "pass_rate_bias_applied" in proj.diagnostics["tendency_effects"]["home"]

    by_name = {p["player_name"]: p for p in proj.players}
    mahomes = by_name["P.Mahomes"]
    assert 160.0 <= float(mahomes["point_estimate"]["pass_yards"]) <= 320.0
    assert 0.5 <= float(mahomes["point_estimate"]["pass_tds"]) <= 2.8

    # Survivor still ranks.
    surv = evaluate_survivor(
        universe,
        week=5,
        already_used=[],
        n_sims=40,
        seed=7,
        include_diagnostics=True,
    )
    assert surv.ranked_picks
    assert (
        "coaching" in surv.engine_version
        or "real-2026" in surv.engine_version
        or "real-depth" in surv.engine_version
        or "smoke-polish" in surv.engine_version
        or "survivor-planner" in surv.engine_version
        or "calibration" in surv.engine_version
        or "player-regression" in DEFAULT_SEASON_ENGINE_VERSION
    )


def test_early_down_bias_and_two_minute_aggression() -> None:
    aggressive = CoachingProfile(
        team="A",
        early_down_pass_bias=0.02,
        two_minute_aggression=1.15,
        script_aggression=1.0,
        source="test",
    )
    soft = CoachingProfile(
        team="B",
        early_down_pass_bias=-0.02,
        two_minute_aggression=0.85,
        script_aggression=1.0,
        source="test",
    )
    a_mix = play_mix_from_script(
        base_pass_rate=0.58,
        detail="large_deficit",
        intensity=0.85,
        time_bucket="late",
        coaching=aggressive,
    )
    b_mix = play_mix_from_script(
        base_pass_rate=0.58,
        detail="large_deficit",
        intensity=0.85,
        time_bucket="late",
        coaching=soft,
    )
    assert a_mix["early_down_pass_rate"] > b_mix["early_down_pass_rate"]
    assert a_mix["hurry_up"] > b_mix["hurry_up"]
