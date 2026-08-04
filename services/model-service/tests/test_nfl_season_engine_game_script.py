"""Tests for stronger Layer-2 game-script / play-calling (v1.6)."""

from __future__ import annotations

import random
from dataclasses import replace

from src.services.nfl_season_engine import (
    DEFAULT_SEASON_ENGINE_VERSION,
    InjuryPath,
    build_demo_universe,
    project_game_player_boxes,
)
from src.services.nfl_season_engine.game_script import (
    build_game_script,
    coarse_script,
    play_mix_from_script,
    script_detail_from_margin,
    script_intensity,
    time_bucket_from_minutes,
)
from src.services.nfl_season_engine.injury_paths import apply_injury_paths_for_week
from src.services.nfl_season_engine.player_usage import allocate_team_usage
from src.services.nfl_season_engine.types import ScheduledGame
from src.services.nfl_season_engine.usage_roles import (
    annotate_usage_roles,
    effective_usage_shares,
)


def test_engine_version_game_script() -> None:
    # v1.7 supersedes v1.6; play-calling tests remain valid under red-zone.
    assert DEFAULT_SEASON_ENGINE_VERSION.startswith("nfl-season-engine-v1.")
    assert (
        "game-script" in DEFAULT_SEASON_ENGINE_VERSION
        or "red-zone" in DEFAULT_SEASON_ENGINE_VERSION
        or "coaching" in DEFAULT_SEASON_ENGINE_VERSION
        or "real-2026" in DEFAULT_SEASON_ENGINE_VERSION
        or "real-depth" in DEFAULT_SEASON_ENGINE_VERSION
        or "smoke-polish" in DEFAULT_SEASON_ENGINE_VERSION
        or "survivor-planner" in DEFAULT_SEASON_ENGINE_VERSION
    )


def test_script_detail_and_time_buckets() -> None:
    assert script_detail_from_margin(28, 10) == "large_lead"
    assert script_detail_from_margin(24, 20) == "small_lead"
    assert script_detail_from_margin(21, 21) == "neutral"
    assert script_detail_from_margin(14, 20) == "small_deficit"
    assert script_detail_from_margin(7, 28) == "large_deficit"
    assert coarse_script("large_lead") == "lead"
    assert coarse_script("small_deficit") == "trail"
    assert time_bucket_from_minutes(45) == "early"
    assert time_bucket_from_minutes(30) == "mid"
    assert time_bucket_from_minutes(8) == "late"
    late_inten = script_intensity(own_score=7, opp_score=28, minutes_remaining=6)
    early_inten = script_intensity(own_score=7, opp_score=28, minutes_remaining=50)
    assert late_inten > early_inten


def test_trailing_late_higher_pass_rate_than_leading_late() -> None:
    universe = build_demo_universe(2026)
    game = ScheduledGame(
        season=2026, week=1, game_id="script-cmp", home_team="KC", away_team="BUF"
    )
    # Same seed family + forced late clock / margins.
    trail_script, _ = build_game_script(
        game,
        universe.strengths,
        rng=random.Random(101),
        realized=False,
        force_home_score=10.0,
        force_away_score=27.0,
        force_minutes_remaining=6.0,
        force_home_detail="large_deficit",
    )
    lead_script, _ = build_game_script(
        game,
        universe.strengths,
        rng=random.Random(101),
        realized=False,
        force_home_score=27.0,
        force_away_score=10.0,
        force_minutes_remaining=6.0,
        force_home_detail="large_lead",
    )
    assert trail_script.time_bucket == "late"
    assert lead_script.time_bucket == "late"
    assert trail_script.home_pass_rate > lead_script.home_pass_rate + 0.08
    assert trail_script.home_hurry_up > lead_script.home_hurry_up
    assert trail_script.home_early_down_pass_rate > lead_script.home_early_down_pass_rate

    # Pure play-mix helper agrees.
    trail_mix = play_mix_from_script(
        base_pass_rate=0.58, detail="large_deficit", intensity=0.9, time_bucket="late"
    )
    lead_mix = play_mix_from_script(
        base_pass_rate=0.58, detail="large_lead", intensity=0.9, time_bucket="late"
    )
    assert trail_mix["pass_rate"] > lead_mix["pass_rate"]


def test_leading_late_increases_rb1_carry_share() -> None:
    universe = build_demo_universe(2026)
    kc = annotate_usage_roles(universe.rosters["KC"])
    game = ScheduledGame(
        season=2026, week=1, game_id="rb-script", home_team="KC", away_team="BUF"
    )
    lead_script, _ = build_game_script(
        game,
        universe.strengths,
        rng=random.Random(7),
        realized=False,
        force_home_score=31.0,
        force_away_score=10.0,
        force_minutes_remaining=5.0,
        force_home_detail="large_lead",
    )
    trail_script, _ = build_game_script(
        game,
        universe.strengths,
        rng=random.Random(7),
        realized=False,
        force_home_score=10.0,
        force_away_score=31.0,
        force_minutes_remaining=5.0,
        force_home_detail="large_deficit",
    )
    rng = random.Random(21)
    lead_carries, trail_carries = [], []
    lead_plays_rush, trail_plays_rush = [], []
    for _ in range(80):
        lu = allocate_team_usage(team="KC", roles=kc, script=lead_script, side="home", rng=rng)
        tu = allocate_team_usage(team="KC", roles=kc, script=trail_script, side="home", rng=rng)
        lead_rb = next(u for u in lu if u.usage_role == "RB1")
        trail_rb = next(u for u in tu if u.usage_role == "RB1")
        lead_carries.append(lead_rb.carries)
        trail_carries.append(trail_rb.carries)
        lead_plays_rush.append(sum(u.carries for u in lu))
        trail_plays_rush.append(sum(u.carries for u in tu))
    assert sum(lead_carries) / len(lead_carries) > sum(trail_carries) / len(trail_carries)
    # Team rush volume also higher when protecting a late lead.
    assert sum(lead_plays_rush) / len(lead_plays_rush) > sum(trail_plays_rush) / len(
        trail_plays_rush
    )


def test_trailing_increases_wr1_te_target_share() -> None:
    universe = build_demo_universe(2026)
    kc = annotate_usage_roles(universe.rosters["KC"])
    wr1 = next(r for r in kc if r.usage_role == "WR1")
    te1 = next(r for r in kc if r.usage_role == "TE1")

    lead = effective_usage_shares(
        wr1,
        script="lead",
        pass_rate=0.45,
        script_intensity=0.9,
        time_bucket="late",
        script_detail="large_lead",
    )
    trail = effective_usage_shares(
        wr1,
        script="trail",
        pass_rate=0.70,
        script_intensity=0.9,
        time_bucket="late",
        script_detail="large_deficit",
    )
    assert trail["target_share"] > lead["target_share"]

    te_lead = effective_usage_shares(
        te1,
        script="lead",
        pass_rate=0.45,
        script_intensity=0.9,
        time_bucket="late",
        script_detail="large_lead",
    )
    te_trail = effective_usage_shares(
        te1,
        script="trail",
        pass_rate=0.70,
        script_intensity=0.9,
        time_bucket="late",
        script_detail="large_deficit",
    )
    assert te_trail["target_share"] > te_lead["target_share"]

    game = ScheduledGame(
        season=2026, week=1, game_id="wr-script", home_team="KC", away_team="BUF"
    )
    lead_script, _ = build_game_script(
        game,
        universe.strengths,
        rng=random.Random(3),
        realized=False,
        force_home_score=30.0,
        force_away_score=13.0,
        force_minutes_remaining=7.0,
        force_home_detail="large_lead",
    )
    trail_script, _ = build_game_script(
        game,
        universe.strengths,
        rng=random.Random(3),
        realized=False,
        force_home_score=13.0,
        force_away_score=30.0,
        force_minutes_remaining=7.0,
        force_home_detail="large_deficit",
    )
    rng = random.Random(9)
    lead_tgt, trail_tgt = [], []
    lead_te, trail_te = [], []
    for _ in range(70):
        lu = allocate_team_usage(team="KC", roles=kc, script=lead_script, side="home", rng=rng)
        tu = allocate_team_usage(team="KC", roles=kc, script=trail_script, side="home", rng=rng)
        lead_tgt.append(next(u.targets for u in lu if u.usage_role == "WR1"))
        trail_tgt.append(next(u.targets for u in tu if u.usage_role == "WR1"))
        lead_te.append(next(u.targets for u in lu if u.usage_role == "TE1"))
        trail_te.append(next(u.targets for u in tu if u.usage_role == "TE1"))
    assert sum(trail_tgt) / len(trail_tgt) > sum(lead_tgt) / len(lead_tgt)
    assert sum(trail_te) / len(trail_te) > sum(lead_te) / len(lead_te)


def test_injury_and_depth_chart_still_work_under_new_scripts() -> None:
    universe = build_demo_universe(2026)
    rice = next(r for r in universe.rosters["KC"] if "Rice" in r.player_name)
    path = InjuryPath(
        player_key=rice.player_key,
        team="KC",
        status="out",
        week_start=1,
        week_end=1,
    )
    adj, _, adjustments = apply_injury_paths_for_week(
        universe.rosters, universe.strengths, [path], week=1
    )
    rice_adj = next(r for r in adj["KC"] if r.player_key == rice.player_key)
    assert rice_adj.target_share == 0.0
    assert adjustments

    game = ScheduledGame(
        season=2026, week=1, game_id="inj-script", home_team="KC", away_team="BUF"
    )
    script, _ = build_game_script(
        game,
        universe.strengths,
        rng=random.Random(5),
        realized=False,
        force_home_score=14.0,
        force_away_score=28.0,
        force_minutes_remaining=8.0,
        force_home_detail="large_deficit",
    )
    usage = allocate_team_usage(
        team="KC",
        roles=annotate_usage_roles(adj["KC"]),
        script=script,
        side="home",
        rng=random.Random(5),
    )
    rice_u = next(u for u in usage if u.player_key == rice.player_key)
    assert rice_u.targets == 0.0
    # Other WRs still get volume under trail script.
    wr_targets = sum(u.targets for u in usage if u.position == "WR" and u.player_key != rice.player_key)
    assert wr_targets > 0.0


def test_buf_kc_realism_bounds_and_diagnostics_play_mix() -> None:
    universe = build_demo_universe(2026)
    proj = project_game_player_boxes(
        universe,
        home_team="KC",
        away_team="BUF",
        week=1,
        n_replicates=200,
        seed=2026,
        include_diagnostics=True,
    )
    assert (
        "coaching" in proj.engine_version
        or "red-zone" in proj.engine_version
        or "game-script" in proj.engine_version
        or "real-2026" in proj.engine_version
        or "real-depth" in proj.engine_version
        or "smoke-polish" in proj.engine_version
        or "survivor-planner" in proj.engine_version
    )
    by_name = {p["player_name"]: p for p in proj.players}

    mahomes = by_name["P.Mahomes"]
    cook = by_name.get("J.Cook") or next(
        p for p in proj.players if p["team"] == "BUF" and p["position"] == "RB"
    )
    rice = by_name["R.Rice"]

    m_py = float(mahomes["point_estimate"]["pass_yards"])
    assert 160.0 <= m_py <= 320.0
    cook_ry = float(cook["point_estimate"]["rush_yards"])
    assert 35.0 <= cook_ry <= 110.0
    rice_rec = float(rice["point_estimate"]["receptions"])
    assert 3.0 <= rice_rec <= 9.0

    diag = proj.diagnostics
    assert "play_mix_home" in diag
    assert "play_mix_away" in diag
    assert "pass_rate_mean" in diag["play_mix_home"]
    assert "early_down_pass_rate_mean" in diag["play_mix_home"]
    assert "script_detail_mode" in diag["play_mix_home"]
    assert "play_mix_sample" in diag
    gss = diag["game_script_summary"]
    assert "home_early_down_pass_rate_mean" in gss
    assert "time_bucket_late_rate" in gss


def test_forced_script_deterministic() -> None:
    universe = build_demo_universe(2026)
    game = ScheduledGame(
        season=2026, week=1, game_id="det", home_team="KC", away_team="BUF"
    )
    a, _ = build_game_script(
        game,
        universe.strengths,
        rng=random.Random(99),
        force_home_score=17.0,
        force_away_score=31.0,
        force_minutes_remaining=9.0,
        force_home_detail="large_deficit",
    )
    b, _ = build_game_script(
        game,
        universe.strengths,
        rng=random.Random(99),
        force_home_score=17.0,
        force_away_score=31.0,
        force_minutes_remaining=9.0,
        force_home_detail="large_deficit",
    )
    assert a.home_pass_rate == b.home_pass_rate
    assert a.home_script_detail == "large_deficit"
    assert a.home_script == "trail"
    # replace() still works for coarse overrides used by older tests.
    neutral = replace(a, home_script="neutral", home_pass_rate=0.58)
    assert neutral.home_script == "neutral"
