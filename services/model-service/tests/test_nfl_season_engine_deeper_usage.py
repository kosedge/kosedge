"""Tests for deeper Layer-3 usage (season-engine v1.3)."""

from __future__ import annotations

import random
from dataclasses import replace

from src.services.nfl_season_engine import (
    DEFAULT_SEASON_ENGINE_VERSION,
    InjuryPath,
    build_demo_universe,
    project_game_player_boxes,
)
from src.services.nfl_season_engine.game_script import build_game_script
from src.services.nfl_season_engine.injury_paths import apply_injury_paths_for_week
from src.services.nfl_season_engine.player_usage import (
    allocate_team_usage,
    usage_share_diagnostics,
)
from src.services.nfl_season_engine.types import GameScript, ScheduledGame
from src.services.nfl_season_engine.usage_roles import (
    annotate_usage_roles,
    effective_usage_shares,
    infer_personnel_package,
)


def test_engine_version_surfaces_deeper_usage() -> None:
    # Deeper usage remains a capability; version tag moved to survivor in v1.4.
    assert DEFAULT_SEASON_ENGINE_VERSION.startswith("nfl-season-engine-v1.")
    assert (
        "deeper-usage" in DEFAULT_SEASON_ENGINE_VERSION
        or "survivor" in DEFAULT_SEASON_ENGINE_VERSION
        or "hardened" in DEFAULT_SEASON_ENGINE_VERSION
        or "depth-volatility" in DEFAULT_SEASON_ENGINE_VERSION
        or "game-script" in DEFAULT_SEASON_ENGINE_VERSION
        or "red-zone" in DEFAULT_SEASON_ENGINE_VERSION
        or "coaching" in DEFAULT_SEASON_ENGINE_VERSION
        or "real-2026" in DEFAULT_SEASON_ENGINE_VERSION
    )


def test_role_ranks_wr1_gt_wr2_gt_wr3_targets_healthy() -> None:
    universe = build_demo_universe(2026)
    kc = annotate_usage_roles(universe.rosters["KC"])
    by_role = {r.usage_role: r for r in kc}
    assert by_role["WR1"].player_name == "R.Rice"
    assert by_role["WR2"].player_name == "X.Worthy"
    assert by_role["WR3"].player_name == "J.Watson"
    assert by_role["WR1"].target_share > by_role["WR2"].target_share > by_role["WR3"].target_share

    # Effective shares under neutral script preserve rank.
    eff = {
        r.usage_role: effective_usage_shares(r, script="neutral", pass_rate=0.58)
        for r in kc
        if r.usage_role.startswith("WR")
    }
    assert eff["WR1"]["target_share"] > eff["WR2"]["target_share"] > eff["WR3"]["target_share"]

    # Allocated targets across many draws: WR1 > WR2 > WR3 means.
    game = ScheduledGame(season=2026, week=1, game_id="t", home_team="KC", away_team="BUF")
    script, _ = build_game_script(game, universe.strengths, rng=random.Random(1), realized=False)
    # Force neutral home script for a clean rank check.
    script = replace(script, home_script="neutral", home_pass_rate=0.58)
    tgt = {"WR1": [], "WR2": [], "WR3": []}
    rng = random.Random(11)
    for _ in range(80):
        usage = allocate_team_usage(
            team="KC", roles=kc, script=script, side="home", rng=rng
        )
        for u in usage:
            if u.usage_role in tgt:
                tgt[u.usage_role].append(u.targets)
    assert sum(tgt["WR1"]) / len(tgt["WR1"]) > sum(tgt["WR2"]) / len(tgt["WR2"])
    assert sum(tgt["WR2"]) / len(tgt["WR2"]) > sum(tgt["WR3"]) / len(tgt["WR3"])


def test_trailing_vs_leading_shifts_pass_rush_usage() -> None:
    universe = build_demo_universe(2026)
    phi = annotate_usage_roles(universe.rosters["PHI"])
    rb1 = next(r for r in phi if r.usage_role == "RB1")
    wr1 = next(r for r in phi if r.usage_role == "WR1")

    lead = effective_usage_shares(rb1, script="lead", pass_rate=0.48)
    trail = effective_usage_shares(rb1, script="trail", pass_rate=0.66)
    assert lead["rush_share"] > trail["rush_share"]

    wr_lead = effective_usage_shares(wr1, script="lead", pass_rate=0.48)
    wr_trail = effective_usage_shares(wr1, script="trail", pass_rate=0.66)
    assert wr_trail["target_share"] > wr_lead["target_share"]

    # Personnel inference aligns with script/pass rate.
    assert infer_personnel_package(0.66, "trail") == "pass_heavy"
    assert infer_personnel_package(0.48, "lead") == "rush_heavy"

    base_script = GameScript(
        game_id="x",
        home_team="PHI",
        away_team="DAL",
        home_win_prob=0.55,
        expected_total=44.0,
        expected_home_score=24.0,
        expected_away_score=20.0,
        pace_plays=63.0,
        home_pass_rate=0.58,
        away_pass_rate=0.58,
        home_script="neutral",
        away_script="neutral",
        home_implied_total=24.0,
        away_implied_total=20.0,
    )
    rng = random.Random(3)
    lead_script = replace(base_script, home_script="lead", home_pass_rate=0.48)
    trail_script = replace(base_script, home_script="trail", home_pass_rate=0.66)
    lead_carries, trail_carries = [], []
    lead_targets, trail_targets = [], []
    for _ in range(60):
        lu = allocate_team_usage(team="PHI", roles=phi, script=lead_script, side="home", rng=rng)
        tu = allocate_team_usage(team="PHI", roles=phi, script=trail_script, side="home", rng=rng)
        lead_carries.append(next(u.carries for u in lu if u.usage_role == "RB1"))
        trail_carries.append(next(u.carries for u in tu if u.usage_role == "RB1"))
        lead_targets.append(next(u.targets for u in lu if u.usage_role == "WR1"))
        trail_targets.append(next(u.targets for u in tu if u.usage_role == "WR1"))
    assert sum(lead_carries) / len(lead_carries) > sum(trail_carries) / len(trail_carries)
    assert sum(trail_targets) / len(trail_targets) > sum(lead_targets) / len(lead_targets)


def test_injury_reallocation_differentiated_by_role() -> None:
    universe = build_demo_universe(2026)
    # SF: CMC is RB1, Mason RB2 — not a committee.
    cmc = next(r for r in universe.rosters["SF"] if "McCaffrey" in r.player_name)
    mason = next(r for r in universe.rosters["SF"] if "Mason" in r.player_name)
    assert cmc.usage_role == "RB1"
    assert mason.usage_role == "RB2"

    path = InjuryPath(
        player_key=cmc.player_key,
        team="SF",
        status="out",
        week_start=1,
        week_end=1,
    )
    adj, _, adjustments = apply_injury_paths_for_week(
        universe.rosters, universe.strengths, [path], week=1
    )
    cmc_adj = next(r for r in adj["SF"] if r.player_key == cmc.player_key)
    mason_adj = next(r for r in adj["SF"] if r.player_key == mason.player_key)
    assert cmc_adj.rush_share == 0.0
    assert mason_adj.rush_share > mason.rush_share
    # RB2 should absorb a large differentiated chunk (not a tiny equal split).
    absorbed = mason_adj.rush_share - mason.rush_share
    assert absorbed >= 0.20
    assert "RB1_out" in adjustments[0].realloc_notes or "RB2" in adjustments[0].realloc_notes

    # WR1 out → WR2 gets more target boost than WR3.
    wr1 = next(r for r in universe.rosters["SF"] if r.usage_role == "WR1")
    wr2 = next(r for r in universe.rosters["SF"] if r.usage_role == "WR2")
    wr3 = next(r for r in universe.rosters["SF"] if r.usage_role == "WR3")
    wr_path = InjuryPath(
        player_key=wr1.player_key, team="SF", status="out", week_start=2, week_end=2
    )
    adj2, _, _ = apply_injury_paths_for_week(
        universe.rosters, universe.strengths, [wr_path], week=2
    )
    wr2_adj = next(r for r in adj2["SF"] if r.player_key == wr2.player_key)
    wr3_adj = next(r for r in adj2["SF"] if r.player_key == wr3.player_key)
    assert (wr2_adj.target_share - wr2.target_share) > (wr3_adj.target_share - wr3.target_share)


def test_week_outside_injury_range_unaffected() -> None:
    universe = build_demo_universe(2026)
    cmc = next(r for r in universe.rosters["SF"] if "McCaffrey" in r.player_name)
    path = InjuryPath(
        player_key=cmc.player_key,
        team="SF",
        status="out",
        week_start=4,
        week_end=8,
    )
    adj, strengths, adjustments = apply_injury_paths_for_week(
        universe.rosters, universe.strengths, [path], week=3
    )
    role = next(r for r in adj["SF"] if r.player_key == cmc.player_key)
    assert role.rush_share == cmc.rush_share
    assert strengths["SF"].offense_index == universe.strengths["SF"].offense_index
    assert adjustments == []


def test_buf_kc_calibration_sanity_preserved() -> None:
    universe = build_demo_universe(2026)
    proj = project_game_player_boxes(
        universe,
        home_team="KC",
        away_team="BUF",
        week=1,
        n_replicates=200,
        seed=2026,
    )
    assert (
        "deeper-usage" in proj.engine_version
        or "survivor" in proj.engine_version
        or "hardened" in proj.engine_version
        or "depth-volatility" in proj.engine_version
        or "game-script" in proj.engine_version
        or "red-zone" in proj.engine_version
        or "coaching" in proj.engine_version
        or "real-2026" in proj.engine_version
    )
    cook = next(p for p in proj.players if "Cook" in p["player_name"])
    rice = next(p for p in proj.players if "Rice" in p["player_name"])
    # No return of Cook 100+ rush / Rice 9-catch nonsense.
    assert cook["point_estimate"]["rush_yards"] < 95.0
    assert rice["distributions"]["receptions"]["mean"] < 8.0
    assert cook["usage_role"] == "RB1"
    assert rice["usage_role"] == "WR1"


def test_usage_share_diagnostics_expose_roles() -> None:
    universe = build_demo_universe(2026)
    rows = usage_share_diagnostics(universe.rosters["KC"], script="trail", pass_rate=0.65)
    labels = {r["usage_role"] for r in rows}
    assert "WR1" in labels and "RB1" in labels and "TE1" in labels
    wr1 = next(r for r in rows if r["usage_role"] == "WR1")
    assert wr1["target_share"] >= wr1["base_target_share"]
    assert wr1["personnel"] == "pass_heavy"
