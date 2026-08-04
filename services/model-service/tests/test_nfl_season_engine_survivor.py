"""Tests for survivor-pool outputs (season-engine v1.4 / v1.10 planner)."""

from __future__ import annotations

import pytest

from src.services.nfl_season_engine import (
    DEFAULT_SEASON_ENGINE_VERSION,
    InjuryPath,
    build_demo_universe,
    build_packaged_real_universe,
    evaluate_survivor,
    evaluate_survivor_plan,
    week_win_rate_for_team,
)
from src.services.nfl_season_engine.survivor import (
    FORMULA_NOTES,
    PATH_FORMULA_NOTES,
    score_team_survivor,
)
from src.services.nfl_season_engine.team_strength import initialize_strengths
from src.services.nfl_season_engine.types import (
    EngineUniverse,
    PlayerRole,
    ScheduledGame,
)


def test_engine_version_surfaces_survivor() -> None:
    assert DEFAULT_SEASON_ENGINE_VERSION.startswith("nfl-season-engine-v1.")
    assert (
        "survivor" in DEFAULT_SEASON_ENGINE_VERSION
        or "hardened" in DEFAULT_SEASON_ENGINE_VERSION
        or "depth-volatility" in DEFAULT_SEASON_ENGINE_VERSION
        or "game-script" in DEFAULT_SEASON_ENGINE_VERSION
        or "red-zone" in DEFAULT_SEASON_ENGINE_VERSION
        or "coaching" in DEFAULT_SEASON_ENGINE_VERSION
        or "real-2026" in DEFAULT_SEASON_ENGINE_VERSION
        or "real-depth" in DEFAULT_SEASON_ENGINE_VERSION
        or "smoke-polish" in DEFAULT_SEASON_ENGINE_VERSION
        or "survivor-planner" in DEFAULT_SEASON_ENGINE_VERSION
    )
    assert "save_score" in FORMULA_NOTES
    assert "pick_now_score" in FORMULA_NOTES
    assert "bye_handling" in FORMULA_NOTES


def test_already_used_excluded_from_ranked_picks() -> None:
    universe = build_demo_universe(2026)
    result = evaluate_survivor(
        universe,
        week=5,
        n_sims=40,
        seed=42,
        already_used=["KC", "BUF"],
        top_n=32,
    )
    ranked_teams = {r["team"] for r in result.ranked_picks}
    assert "KC" not in ranked_teams
    assert "BUF" not in ranked_teams
    assert result.already_used == ["KC", "BUF"]
    for row in result.all_teams_week:
        if row["team"] in ("KC", "BUF"):
            assert row["already_used"] is True
            assert row["remaining"] is False


def test_week_rankings_ordered_by_win_rate_in_all_teams() -> None:
    universe = build_demo_universe(2026)
    result = evaluate_survivor(
        universe, week=3, n_sims=60, seed=7, already_used=[], top_n=32
    )
    playing = [r for r in result.all_teams_week if r["plays_this_week"]]
    rates = [float(r["win_rate"]) for r in playing]
    assert rates == sorted(rates, reverse=True)
    # Ranked picks (remaining) are ordered by pick_now then win_rate.
    pick_now = [float(r["pick_now_score"]) for r in result.ranked_picks]
    assert pick_now == sorted(pick_now, reverse=True)
    by_team = {r["team"]: r["win_rate"] for r in result.all_teams_week}
    assert week_win_rate_for_team(result, "KC") == by_team["KC"]
    assert 0.0 <= by_team["KC"] <= 1.0


def test_future_value_higher_for_easier_later_spots() -> None:
    """Construct win-rate matrix: easy-later team gets higher save_score."""
    # Soft spot later for AAA; BBB has harder future weeks.
    win_counts = {
        "AAA": {5: 55, 6: 85, 7: 80, 8: 78},
        "BBB": {5: 70, 6: 40, 7: 35, 8: 38},
    }
    games_scheduled = {
        "AAA": {5: 1, 6: 1, 7: 1, 8: 1},
        "BBB": {5: 1, 6: 1, 7: 1, 8: 1},
    }
    aaa = score_team_survivor(
        team="AAA",
        week=5,
        n_sims=100,
        win_counts=win_counts,
        games_scheduled=games_scheduled,
        max_week=8,
        already_used=[],
        game=None,
    )
    bbb = score_team_survivor(
        team="BBB",
        week=5,
        n_sims=100,
        win_counts=win_counts,
        games_scheduled=games_scheduled,
        max_week=8,
        already_used=[],
        game=None,
    )
    assert aaa["future_value"] > bbb["future_value"]
    assert aaa["save_score"] > bbb["save_score"]
    # BBB is hotter this week → higher pick_now despite lower save value.
    assert bbb["win_rate"] > aaa["win_rate"]
    assert bbb["pick_now_score"] > aaa["pick_now_score"]


def test_injury_paths_accepted_without_breaking_survivor() -> None:
    universe = build_demo_universe(2026)
    key = next(r.player_key for r in universe.rosters["SF"] if "McCaffrey" in r.player_name)
    paths = [
        InjuryPath(
            player_key=key,
            player_name="C.McCaffrey",
            team="SF",
            status="out",
            week_start=4,
            week_end=8,
        )
    ]
    result = evaluate_survivor(
        universe,
        week=5,
        n_sims=30,
        seed=99,
        already_used=["DET"],
        injury_paths=paths,
        top_n=10,
    )
    assert result.n_sims == 30
    assert result.diagnostics["injury_path_count"] == 1
    assert len(result.ranked_picks) >= 1
    assert "DET" not in {r["team"] for r in result.ranked_picks}
    assert (
        "survivor" in result.engine_version
        or "hardened" in result.engine_version
        or "depth-volatility" in result.engine_version
        or "game-script" in result.engine_version
        or "red-zone" in result.engine_version
        or "coaching" in result.engine_version
        or "real-2026" in result.engine_version
        or "real-depth" in result.engine_version
        or "smoke-polish" in result.engine_version
        or "survivor-planner" in result.engine_version
    )


def test_mini_universe_survivor_runs() -> None:
    """Tiny custom schedule still produces coherent week winners."""
    teams = ["AAA", "BBB", "CCC", "DDD"]
    strengths = initialize_strengths(
        {
            "AAA": {"offense_index": 1.20, "defense_index": 1.15, "source": "test"},
            "BBB": {"offense_index": 1.05, "defense_index": 1.00, "source": "test"},
            "CCC": {"offense_index": 0.95, "defense_index": 0.95, "source": "test"},
            "DDD": {"offense_index": 0.80, "defense_index": 0.85, "source": "test"},
        }
    )
    schedule = [
        ScheduledGame(2026, 1, "g1", "AAA", "BBB"),
        ScheduledGame(2026, 1, "g2", "CCC", "DDD"),
        ScheduledGame(2026, 2, "g3", "AAA", "DDD"),
        ScheduledGame(2026, 2, "g4", "BBB", "CCC"),
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
        season=2026,
        schedule=schedule,
        strengths=strengths,
        rosters=rosters,
        notes={"test": "mini"},
    )
    result = evaluate_survivor(
        universe, week=1, n_sims=80, seed=1, already_used=["CCC"], top_n=4
    )
    ranked = {r["team"] for r in result.ranked_picks}
    assert "CCC" not in ranked
    assert "AAA" in ranked or "BBB" in ranked or "DDD" in ranked
    assert week_win_rate_for_team(result, "AAA") is not None
    assert week_win_rate_for_team(result, "AAA") >= week_win_rate_for_team(result, "DDD")


def test_planner_excludes_used_teams_across_weeks() -> None:
    universe = build_demo_universe(2026)
    plan = evaluate_survivor_plan(
        universe,
        picks={"1": "KC", "3": "BUF"},
        n_sims=40,
        seed=11,
        top_n=16,
    )
    assert plan.locked_picks == {"1": "KC", "3": "BUF"}
    assert set(plan.used_teams) == {"KC", "BUF"}
    assert "survivor-planner" in plan.engine_version or "survivor" in PATH_FORMULA_NOTES
    assert "path_survival" in PATH_FORMULA_NOTES
    open_weeks = [w for w in plan.weeks if w["status"] == "open"]
    assert open_weeks
    for week in open_weeks:
        ranked_teams = {r["team"] for r in week["ranked_picks"]}
        assert "KC" not in ranked_teams
        assert "BUF" not in ranked_teams


def test_planner_rejects_bye_pick_on_real_schedule() -> None:
    universe = build_packaged_real_universe(2026)
    # KC bye week 5 on 2026 wall-chart.
    with pytest.raises(ValueError, match="bye|not scheduled"):
        evaluate_survivor_plan(
            universe,
            picks={"5": "KC"},
            n_sims=10,
            seed=1,
            top_n=4,
        )


def test_planner_rejects_duplicate_team() -> None:
    universe = build_demo_universe(2026)
    with pytest.raises(ValueError, match="multiple weeks"):
        evaluate_survivor_plan(
            universe,
            picks={"1": "KC", "2": "KC"},
            n_sims=10,
            seed=1,
        )


def test_path_survival_monotonic_when_adding_chalk() -> None:
    """Adding a strong week-1 lock should not raise path survival vs empty."""
    universe = build_demo_universe(2026)
    empty = evaluate_survivor_plan(
        universe, picks={}, n_sims=80, seed=7, top_n=4
    )
    assert empty.path_survival == 1.0
    assert empty.path_strength == "Empty"

    # Lock a chalky team in week 1 (highest strength side typically wins often).
    chalk = evaluate_survivor_plan(
        universe, picks={"1": "KC"}, n_sims=80, seed=7, top_n=4
    )
    assert 0.0 < chalk.path_survival <= 1.0
    assert chalk.path_survival <= empty.path_survival

    fragile = evaluate_survivor_plan(
        universe,
        picks={"1": "KC", "2": "BUF", "3": "PHI", "4": "DET"},
        n_sims=80,
        seed=7,
        top_n=4,
    )
    assert fragile.path_survival <= chalk.path_survival
    assert fragile.locked_pick_count == 4
    assert fragile.path_strength in {"Strong", "OK", "Fragile"}


def test_planner_open_week_recommendations_present() -> None:
    universe = build_demo_universe(2026)
    plan = evaluate_survivor_plan(
        universe, picks={"2": "DET"}, n_sims=30, seed=3, top_n=5
    )
    week1 = next(w for w in plan.weeks if w["week"] == 1)
    assert week1["status"] == "open"
    assert 1 <= len(week1["ranked_picks"]) <= 5
    assert week1["ranked_picks"][0]["pick_now_score"] >= week1["ranked_picks"][-1][
        "pick_now_score"
    ]
    locked = next(w for w in plan.weeks if w["week"] == 2)
    assert locked["status"] == "locked"
    assert locked["locked_team"] == "DET"
