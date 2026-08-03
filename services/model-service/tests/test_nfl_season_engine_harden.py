"""Regression / harden tests for season-engine v1.4.1."""

from __future__ import annotations

import math
import random

from src.services.nfl_season_engine import (
    DEFAULT_SEASON_ENGINE_VERSION,
    InjuryPath,
    build_demo_universe,
    evaluate_survivor,
    parse_injury_paths,
    project_game_player_boxes,
    simulate_full_season,
)
from src.services.nfl_season_engine.calibration import GAME_SANITY
from src.services.nfl_season_engine.game_script import build_game_script
from src.services.nfl_season_engine.injury_paths import (
    apply_injury_paths_for_week,
    names_match,
    normalize_team_code,
)
from src.services.nfl_season_engine.player_usage import (
    allocate_team_usage,
    share_integrity_summary,
)
from src.services.nfl_season_engine.team_strength import initialize_strengths
from src.services.nfl_season_engine.types import (
    EngineUniverse,
    GameScript,
    PlayerRole,
    ScheduledGame,
)


def test_engine_version_hardened_patch() -> None:
    assert DEFAULT_SEASON_ENGINE_VERSION == "nfl-season-engine-v1.4.1-hardened"


def test_dual_name_injury_match_christian_vs_initial() -> None:
    assert names_match("Christian McCaffrey", "C.McCaffrey")
    assert names_match("C.McCaffrey", "Christian McCaffrey")
    assert names_match("McCaffrey", "C.McCaffrey")
    assert normalize_team_code("LAR") == "LA"

    universe = build_demo_universe(2026)
    paths = parse_injury_paths(
        [
            {
                "player_name": "Christian McCaffrey",
                "team": "SF",
                "status": "out",
                "week_start": 1,
                "week_end": 3,
            }
        ]
    )
    adj, _, adjustments = apply_injury_paths_for_week(
        universe.rosters, universe.strengths, paths, week=2
    )
    assert adjustments
    assert adjustments[0].realloc_notes != "player_not_found_on_roster"
    cmc = next(r for r in adj["SF"] if "McCaffrey" in r.player_name)
    assert cmc.rush_share == 0.0


def test_injury_outside_week_range_noop() -> None:
    universe = build_demo_universe(2026)
    key = next(r.player_key for r in universe.rosters["SF"] if "McCaffrey" in r.player_name)
    path = InjuryPath(
        player_key=key,
        player_name="C.McCaffrey",
        team="SF",
        status="out",
        week_start=4,
        week_end=8,
    )
    healthy = next(r for r in universe.rosters["SF"] if r.player_key == key)
    adj, _, adjustments = apply_injury_paths_for_week(
        universe.rosters, universe.strengths, [path], week=10
    )
    assert adjustments == []
    outside = next(r for r in adj["SF"] if r.player_key == key)
    assert outside.rush_share == healthy.rush_share


def test_cmc_out_reallocates_to_rb2() -> None:
    universe = build_demo_universe(2026)
    key = next(r.player_key for r in universe.rosters["SF"] if "McCaffrey" in r.player_name)
    mason = next(r for r in universe.rosters["SF"] if "Mason" in r.player_name)
    path = InjuryPath(
        player_key=key, team="SF", status="out", week_start=1, week_end=1
    )
    adj, _, _ = apply_injury_paths_for_week(
        universe.rosters, universe.strengths, [path], week=1
    )
    mason_adj = next(r for r in adj["SF"] if r.player_key == mason.player_key)
    assert mason_adj.rush_share > mason.rush_share


def test_thin_roster_no_rb2_does_not_crash() -> None:
    roles = [
        PlayerRole(
            player_key="X-QB1",
            player_name="X QB",
            team="XXX",
            position="QB",
            depth_order=1,
            snap_share=0.98,
            rush_share=0.08,
        ),
        PlayerRole(
            player_key="X-RB1",
            player_name="X RB",
            team="XXX",
            position="RB",
            depth_order=1,
            snap_share=0.65,
            rush_share=0.55,
            target_share=0.10,
        ),
        PlayerRole(
            player_key="X-WR1",
            player_name="X WR",
            team="XXX",
            position="WR",
            depth_order=1,
            snap_share=0.85,
            target_share=0.22,
            route_share=0.9,
        ),
    ]
    script = GameScript(
        game_id="g",
        home_team="XXX",
        away_team="YYY",
        home_win_prob=0.5,
        expected_total=44,
        expected_home_score=22,
        expected_away_score=22,
        pace_plays=63,
        home_pass_rate=0.58,
        away_pass_rate=0.58,
        home_script="neutral",
        away_script="neutral",
        home_implied_total=22,
        away_implied_total=22,
    )
    usage = allocate_team_usage(
        team="XXX", roles=roles, script=script, side="home", rng=random.Random(1)
    )
    assert usage
    assert all(math.isfinite(u.carries) and math.isfinite(u.targets) for u in usage)
    integrity = share_integrity_summary(roles, script="neutral", pass_rate=0.58)
    assert integrity["ok"] is True
    assert integrity["residual_other_rush"] >= 0.08


def test_empty_roster_returns_empty_usage() -> None:
    script = GameScript(
        game_id="g",
        home_team="XXX",
        away_team="YYY",
        home_win_prob=0.5,
        expected_total=44,
        expected_home_score=22,
        expected_away_score=22,
        pace_plays=63,
        home_pass_rate=0.58,
        away_pass_rate=0.58,
        home_script="neutral",
        away_script="neutral",
        home_implied_total=22,
        away_implied_total=22,
    )
    assert allocate_team_usage(
        team="XXX", roles=[], script=script, side="home", rng=random.Random(1)
    ) == []


def test_buf_kc_box_score_realism_bounds() -> None:
    universe = build_demo_universe(2026)
    proj = project_game_player_boxes(
        universe,
        home_team="KC",
        away_team="BUF",
        week=1,
        n_replicates=120,
        seed=7,
        include_diagnostics=True,
    )
    assert proj.diagnostics
    assert "usage_shares_home" in proj.diagnostics
    assert proj.diagnostics["share_integrity_home"]["ok"] is True

    cook = next(p for p in proj.players if p["team"] == "BUF" and "Cook" in p["player_name"])
    rice = next(p for p in proj.players if p["team"] == "KC" and "Rice" in p["player_name"])
    mahomes = next(p for p in proj.players if "Mahomes" in p["player_name"])
    assert GAME_SANITY["rb1_rush_yards"][0] <= cook["point_estimate"]["rush_yards"] <= 110.0
    assert GAME_SANITY["wr1_rec_yards"][0] <= rice["point_estimate"]["rec_yards"] <= 120.0
    assert GAME_SANITY["qb_pass_yards"][0] <= mahomes["point_estimate"]["pass_yards"] <= GAME_SANITY["qb_pass_yards"][1]
    assert cook.get("usage_role")
    assert rice.get("script") in ("lead", "trail", "neutral", "")


def test_season_win_distribution_not_collapsed() -> None:
    universe = build_demo_universe(2026)
    result = simulate_full_season(universe, n_sims=20, seed=13, include_diagnostics=True)
    means = [v["mean"] for v in result.team_wins.values()]
    assert all(math.isfinite(m) for m in means)
    assert abs(result.diagnostics["mean_wins_sum"] - 272.0) < 0.01
    assert result.diagnostics["win_mean_spread"] >= 2.0
    assert result.diagnostics["win_mean_min"] >= GAME_SANITY["team_win_mean"][0]
    assert result.diagnostics["win_mean_max"] <= GAME_SANITY["team_win_mean"][1]


def test_survivor_already_used_and_bye_excluded() -> None:
    teams = ["AAA", "BBB", "CCC", "DDD"]
    strengths = initialize_strengths(
        {
            "AAA": {"offense_index": 1.2, "defense_index": 1.1, "source": "test"},
            "BBB": {"offense_index": 1.0, "defense_index": 1.0, "source": "test"},
            "CCC": {"offense_index": 0.9, "defense_index": 0.95, "source": "test"},
            "DDD": {"offense_index": 0.8, "defense_index": 0.85, "source": "test"},
        }
    )
    # Week 1: AAA/BBB play; CCC/DDD on bye. Week 2: reverse.
    schedule = [
        ScheduledGame(2026, 1, "g1", "AAA", "BBB"),
        ScheduledGame(2026, 2, "g2", "CCC", "DDD"),
    ]
    rosters = {
        t: [
            PlayerRole(
                player_key=f"{t}-QB1",
                player_name=f"{t} QB",
                team=t,
                position="QB",
                depth_order=1,
                snap_share=0.98,
            )
        ]
        for t in teams
    }
    universe = EngineUniverse(
        season=2026, schedule=schedule, strengths=strengths, rosters=rosters
    )
    result = evaluate_survivor(
        universe,
        week=1,
        n_sims=40,
        seed=3,
        already_used=["AAA"],
        top_n=8,
        include_diagnostics=True,
    )
    ranked = {r["team"] for r in result.ranked_picks}
    assert "AAA" not in ranked
    assert "CCC" not in ranked  # bye
    assert "DDD" not in ranked  # bye
    assert "BBB" in ranked
    assert set(result.diagnostics["bye_teams_this_week"]) == {"CCC", "DDD"}


def test_missing_team_strength_does_not_crash_script() -> None:
    game = ScheduledGame(2026, 1, "g", "ZZZ", "YYY")
    strengths = initialize_strengths(
        {"YYY": {"offense_index": 1.0, "defense_index": 1.0, "source": "test"}}
    )
    script, outcome = build_game_script(game, strengths, rng=random.Random(1), realized=True)
    assert 0.02 <= script.home_win_prob <= 0.98
    assert "home_won" in outcome


def test_diagnostics_default_off_for_game_boxes() -> None:
    universe = build_demo_universe(2026)
    lean = project_game_player_boxes(
        universe, home_team="KC", away_team="BUF", week=1, n_replicates=50, seed=1
    )
    assert lean.diagnostics == {}
    rich = project_game_player_boxes(
        universe,
        home_team="KC",
        away_team="BUF",
        week=1,
        n_replicates=50,
        seed=1,
        include_diagnostics=True,
    )
    assert rich.diagnostics["injury_adjustments"]["active_count"] == 0
