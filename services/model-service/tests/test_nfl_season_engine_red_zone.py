"""Tests for v1.7 red-zone / scoring-usage layer."""

from __future__ import annotations

import random

from src.services.nfl_season_engine import (
    DEFAULT_SEASON_ENGINE_VERSION,
    InjuryPath,
    build_demo_universe,
    project_game_player_boxes,
)
from src.services.nfl_season_engine.game_script import build_game_script
from src.services.nfl_season_engine.injury_paths import apply_injury_paths_for_week
from src.services.nfl_season_engine.player_usage import allocate_team_usage
from src.services.nfl_season_engine.red_zone import (
    RZ_CARRY_SHARE_I10,
    RZ_TARGET_SHARE_I10,
    rz_pass_rate_from_script,
    scoring_usage_diagnostics,
)
from src.services.nfl_season_engine.types import PlayerRole, ScheduledGame
from src.services.nfl_season_engine.usage_roles import annotate_usage_roles


def test_engine_version_red_zone() -> None:
    assert DEFAULT_SEASON_ENGINE_VERSION.startswith("nfl-season-engine-v1.")
    assert (
        "coaching" in DEFAULT_SEASON_ENGINE_VERSION
        or "red-zone" in DEFAULT_SEASON_ENGINE_VERSION
        or "real-2026" in DEFAULT_SEASON_ENGINE_VERSION
        or "real-depth" in DEFAULT_SEASON_ENGINE_VERSION
    )


def test_rb1_higher_i10_carry_share_than_wr_in_feature() -> None:
    """RB1 table I10 carry share >> WR; feature backfield concentrates GL."""
    assert RZ_CARRY_SHARE_I10["RB1"] > RZ_CARRY_SHARE_I10.get("WR1", 0.01) + 0.4
    universe = build_demo_universe(2026)
    kc = annotate_usage_roles(universe.rosters["KC"])
    # KC demo is feature-ish (Pacheco / Hunt split is not equal committee).
    diag = scoring_usage_diagnostics(kc)
    rb1 = next(p for p in diag["players"] if p["usage_role"] == "RB1")
    wr1 = next(p for p in diag["players"] if p["usage_role"] == "WR1")
    assert rb1["rz_carry_share_i10"] > wr1["rz_carry_share_i10"] + 0.4

    game = ScheduledGame(
        season=2026, week=1, game_id="rz-rb", home_team="KC", away_team="BUF"
    )
    script, _ = build_game_script(
        game,
        universe.strengths,
        rng=random.Random(11),
        realized=False,
        force_home_score=24.0,
        force_away_score=17.0,
        force_minutes_remaining=20.0,
        force_home_detail="small_lead",
    )
    rng = random.Random(3)
    rb_i10, wr_i10 = [], []
    for _ in range(60):
        usage = allocate_team_usage(
            team="KC", roles=kc, script=script, side="home", rng=rng
        )
        rb = next(u for u in usage if u.usage_role == "RB1")
        wr = next(u for u in usage if u.usage_role == "WR1")
        rb_i10.append(rb.rz_carries_i10)
        wr_i10.append(wr.rz_carries_i10)
    assert sum(rb_i10) / len(rb_i10) > sum(wr_i10) / len(wr_i10) + 0.3


def test_te1_wr1_elevated_rz_targets_vs_wr3() -> None:
    assert RZ_TARGET_SHARE_I10["TE1"] > RZ_TARGET_SHARE_I10["WR3"]
    assert RZ_TARGET_SHARE_I10["WR1"] > RZ_TARGET_SHARE_I10["WR3"]
    universe = build_demo_universe(2026)
    kc = annotate_usage_roles(universe.rosters["KC"])
    diag = scoring_usage_diagnostics(kc)
    by_role = {p["usage_role"]: p for p in diag["players"]}
    assert by_role["TE1"]["rz_target_share_i10"] > by_role["WR3"]["rz_target_share_i10"]
    assert by_role["WR1"]["rz_target_share_i10"] > by_role["WR3"]["rz_target_share_i10"]

    game = ScheduledGame(
        season=2026, week=1, game_id="rz-tgt", home_team="KC", away_team="BUF"
    )
    script, _ = build_game_script(
        game,
        universe.strengths,
        rng=random.Random(5),
        realized=False,
        force_home_score=14.0,
        force_away_score=21.0,
        force_minutes_remaining=12.0,
        force_home_detail="small_deficit",
    )
    rng = random.Random(7)
    wr1_t, te1_t, wr3_t = [], [], []
    for _ in range(70):
        usage = allocate_team_usage(
            team="KC", roles=kc, script=script, side="home", rng=rng
        )
        wr1_t.append(next(u.rz_targets_i10 for u in usage if u.usage_role == "WR1"))
        te1_t.append(next(u.rz_targets_i10 for u in usage if u.usage_role == "TE1"))
        wr3 = next((u for u in usage if u.usage_role == "WR3"), None)
        if wr3 is not None:
            wr3_t.append(wr3.rz_targets_i10)
    assert sum(wr1_t) / len(wr1_t) > sum(wr3_t) / len(wr3_t)
    assert sum(te1_t) / len(te1_t) > sum(wr3_t) / len(wr3_t)


def test_leading_late_more_rz_run_and_rb_td_share() -> None:
    lead_pass = rz_pass_rate_from_script(
        base_team_pass_rate=0.58,
        detail="large_lead",
        intensity=0.9,
        time_bucket="late",
    )
    trail_pass = rz_pass_rate_from_script(
        base_team_pass_rate=0.58,
        detail="large_deficit",
        intensity=0.9,
        time_bucket="late",
    )
    assert trail_pass > lead_pass + 0.10

    universe = build_demo_universe(2026)
    kc = annotate_usage_roles(universe.rosters["KC"])
    game = ScheduledGame(
        season=2026, week=1, game_id="rz-script", home_team="KC", away_team="BUF"
    )
    lead_script, _ = build_game_script(
        game,
        universe.strengths,
        rng=random.Random(101),
        realized=False,
        force_home_score=31.0,
        force_away_score=10.0,
        force_minutes_remaining=5.0,
        force_home_detail="large_lead",
    )
    trail_script, _ = build_game_script(
        game,
        universe.strengths,
        rng=random.Random(101),
        realized=False,
        force_home_score=10.0,
        force_away_score=31.0,
        force_minutes_remaining=5.0,
        force_home_detail="large_deficit",
    )
    rng = random.Random(21)
    lead_rb_i10, trail_rb_i10 = [], []
    lead_rb_td_share, trail_rb_td_share = [], []
    lead_wr_t10, trail_wr_t10 = [], []
    for _ in range(80):
        lu = allocate_team_usage(
            team="KC", roles=kc, script=lead_script, side="home", rng=rng
        )
        tu = allocate_team_usage(
            team="KC", roles=kc, script=trail_script, side="home", rng=rng
        )
        lead_rb = next(u for u in lu if u.usage_role == "RB1")
        trail_rb = next(u for u in tu if u.usage_role == "RB1")
        lead_rb_i10.append(lead_rb.rz_carries_i10)
        trail_rb_i10.append(trail_rb.rz_carries_i10)
        lead_rb_td_share.append(lead_rb.td_opportunity_share)
        trail_rb_td_share.append(trail_rb.td_opportunity_share)
        lead_wr_t10.append(next(u.rz_targets_i10 for u in lu if u.usage_role == "WR1"))
        trail_wr_t10.append(next(u.rz_targets_i10 for u in tu if u.usage_role == "WR1"))
    assert sum(lead_rb_i10) / len(lead_rb_i10) > sum(trail_rb_i10) / len(trail_rb_i10)
    assert sum(lead_rb_td_share) / len(lead_rb_td_share) > sum(trail_rb_td_share) / len(
        trail_rb_td_share
    )
    assert sum(trail_wr_t10) / len(trail_wr_t10) > sum(lead_wr_t10) / len(lead_wr_t10)


def test_committee_less_concentrated_rz_carries_than_feature() -> None:
    """Feature RB1 owns more I10 share mass than a two-back committee top share."""
    feature_roles = annotate_usage_roles(
        [
            PlayerRole(
                player_key="F-RB1",
                player_name="Feature",
                team="AAA",
                position="RB",
                depth_order=1,
                rush_share=0.58,
                target_share=0.08,
                snap_share=0.65,
                red_zone_share=0.50,
            ),
            PlayerRole(
                player_key="F-RB2",
                player_name="Backup",
                team="AAA",
                position="RB",
                depth_order=2,
                rush_share=0.22,
                target_share=0.04,
                snap_share=0.28,
                red_zone_share=0.18,
            ),
        ]
    )
    committee_roles = annotate_usage_roles(
        [
            PlayerRole(
                player_key="C-RB1",
                player_name="CommA",
                team="BBB",
                position="RB",
                depth_order=1,
                rush_share=0.38,
                target_share=0.07,
                snap_share=0.48,
                red_zone_share=0.30,
            ),
            PlayerRole(
                player_key="C-RB2",
                player_name="CommB",
                team="BBB",
                position="RB",
                depth_order=2,
                rush_share=0.34,
                target_share=0.06,
                snap_share=0.44,
                red_zone_share=0.28,
            ),
        ]
    )
    f_diag = scoring_usage_diagnostics(feature_roles)
    c_diag = scoring_usage_diagnostics(committee_roles)
    f_top = max(p["rz_carry_share_i10"] for p in f_diag["players"])
    c_shares = sorted(
        (p["rz_carry_share_i10"] for p in c_diag["players"]), reverse=True
    )
    # Committee labels get RB_COMMITTEE table share (~0.32) each — less
    # concentrated than feature RB1 (~0.66).
    assert f_top > c_shares[0] + 0.15
    # Herfindahl-ish: feature more peaked.
    f_hhi = sum(p["rz_carry_share_i10"] ** 2 for p in f_diag["players"])
    c_hhi = sum(p["rz_carry_share_i10"] ** 2 for p in c_diag["players"])
    assert f_hhi > c_hhi


def test_injury_zeros_rz_and_td_opportunities() -> None:
    # BUF has RB1+RB2 so RZ/GL carries can reallocate (KC demo is RB1-only).
    universe = build_demo_universe(2026)
    cook = next(r for r in universe.rosters["BUF"] if "Cook" in r.player_name)
    path = InjuryPath(
        player_key=cook.player_key,
        team="BUF",
        status="out",
        week_start=1,
        week_end=1,
    )
    adj, _, _ = apply_injury_paths_for_week(
        universe.rosters, universe.strengths, [path], week=1
    )
    injured = next(r for r in adj["BUF"] if r.player_key == cook.player_key)
    assert injured.rush_share == 0.0

    game = ScheduledGame(
        season=2026, week=1, game_id="rz-inj", home_team="KC", away_team="BUF"
    )
    script, _ = build_game_script(
        game,
        universe.strengths,
        rng=random.Random(9),
        realized=False,
        force_away_score=27.0,
        force_home_score=13.0,
        force_minutes_remaining=8.0,
        force_away_detail="large_lead",
    )
    usage = allocate_team_usage(
        team="BUF",
        roles=annotate_usage_roles(adj["BUF"]),
        script=script,
        side="away",
        rng=random.Random(9),
    )
    inj_u = next(u for u in usage if u.player_key == cook.player_key)
    assert inj_u.rz_carries_i20 == 0.0
    assert inj_u.rz_carries_i10 == 0.0
    assert inj_u.td_opportunity_share == 0.0
    # Remaining RBs absorb RZ carries via committee/feature sinks.
    other_rz = sum(
        u.rz_carries_i10
        for u in usage
        if u.position == "RB" and u.player_key != cook.player_key
    )
    assert other_rz > 0.0


def test_buf_kc_td_sanity_and_rz_diagnostics() -> None:
    universe = build_demo_universe(2026)
    proj = project_game_player_boxes(
        universe,
        home_team="KC",
        away_team="BUF",
        week=1,
        n_replicates=220,
        seed=2026,
        include_diagnostics=True,
    )
    assert (
        "coaching" in proj.engine_version
        or "real-2026" in proj.engine_version
        or "real-depth" in proj.engine_version
        or proj.engine_version == "nfl-season-engine-v1.7-red-zone"
    )
    by_name = {p["player_name"]: p for p in proj.players}

    mahomes = by_name["P.Mahomes"]
    cook = by_name.get("J.Cook") or next(
        p for p in proj.players if p["team"] == "BUF" and p["position"] == "RB"
    )
    rice = by_name["R.Rice"]

    m_td = float(mahomes["point_estimate"]["pass_tds"])
    cook_td = float(cook["point_estimate"]["rush_tds"])
    rice_td = float(rice["point_estimate"]["rec_tds"])
    # Plausible bands — not exploding.
    assert 0.5 <= m_td <= 2.8
    assert 0.15 <= cook_td <= 1.4
    assert 0.08 <= rice_td <= 1.2
    # Yards still sane.
    assert 160.0 <= float(mahomes["point_estimate"]["pass_yards"]) <= 320.0

    diag = proj.diagnostics
    assert "red_zone" in diag
    assert "scoring_usage" in diag
    assert "rz_pass_rate_mean" in diag["red_zone"]["home"]
    assert diag["red_zone"]["players"]
    sample = next(p for p in diag["red_zone"]["players"] if p["player_name"] == "P.Mahomes")
    # Mahomes may have RZ rush; skill players have targets/carries.
    rice_rz = next(p for p in diag["red_zone"]["players"] if p["player_name"] == "R.Rice")
    assert rice_rz["rz_targets_i20"]["mean"] >= 0.0
    assert "rz_carries_i10" in rice_rz or "rz_targets_i10" in rice_rz
    assert sample["td_opportunity_share"]["mean"] >= 0.0


def test_scoring_role_optional_rb_gl() -> None:
    roles = annotate_usage_roles(
        [
            PlayerRole(
                player_key="X-RB1",
                player_name="Starter",
                team="XXX",
                position="RB",
                depth_order=1,
                rush_share=0.55,
                red_zone_share=0.40,
                snap_share=0.60,
            ),
            PlayerRole(
                player_key="X-GL",
                player_name="ShortYard",
                team="XXX",
                position="RB",
                depth_order=3,
                rush_share=0.10,
                red_zone_share=0.22,
                snap_share=0.15,
            ),
        ]
    )
    diag = scoring_usage_diagnostics(roles)
    gl = next(p for p in diag["players"] if p["player_name"] == "ShortYard")
    assert gl["scoring_role"] == "RB_GL"
    assert gl["rz_carry_share_i10"] > RZ_CARRY_SHARE_I10["RB2"]
