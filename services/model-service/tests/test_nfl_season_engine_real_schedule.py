"""Real 2026 schedule cutover tests (v1.9)."""

from __future__ import annotations

from src.services.nfl_season_engine import (
    DEFAULT_SEASON_ENGINE_VERSION,
    build_demo_universe,
    build_packaged_real_universe,
    evaluate_survivor,
    load_packaged_regular_schedule,
    project_game_player_boxes,
    resolve_season_universe,
    simulate_full_season,
)
from src.services.nfl_season_engine.loaders import (
    SCHEDULE_SOURCE_DEMO,
    SCHEDULE_SOURCE_PACKAGED,
)


def test_engine_version_real_2026() -> None:
    assert DEFAULT_SEASON_ENGINE_VERSION.startswith("nfl-season-engine-v1.")
    assert (
        "real" in DEFAULT_SEASON_ENGINE_VERSION
        or "smoke-polish" in DEFAULT_SEASON_ENGINE_VERSION
        or "survivor-planner" in DEFAULT_SEASON_ENGINE_VERSION
        or "calibration" in DEFAULT_SEASON_ENGINE_VERSION
        or "player-regression" in DEFAULT_SEASON_ENGINE_VERSION
        or "projected-sos" in DEFAULT_SEASON_ENGINE_VERSION
        or "season-coherence" in DEFAULT_SEASON_ENGINE_VERSION
        or "phase2-features" in DEFAULT_SEASON_ENGINE_VERSION
        or "soft-flags" in DEFAULT_SEASON_ENGINE_VERSION
        or "true-pr-harden" in DEFAULT_SEASON_ENGINE_VERSION
    )


def test_packaged_schedule_has_272_reg_games_and_byes() -> None:
    games, meta = load_packaged_regular_schedule(2026)
    assert len(games) == 272
    assert meta["schedule_source"] == SCHEDULE_SOURCE_PACKAGED
    assert meta["schedule_game_count"] == 272

    w1 = {(g.away_team, g.home_team) for g in games if g.week == 1}
    assert ("ARI", "LAC") in w1
    assert ("SF", "LA") in w1  # wall-chart LAR vs SF

    # Week 5 byes include KC / CAR; week 6 includes DET.
    playing_w5 = {g.home_team for g in games if g.week == 5} | {
        g.away_team for g in games if g.week == 5
    }
    playing_w6 = {g.home_team for g in games if g.week == 6} | {
        g.away_team for g in games if g.week == 6
    }
    assert "KC" not in playing_w5
    assert "CAR" not in playing_w5
    assert "DET" not in playing_w6
    assert len(playing_w5) == 30  # 15 games
    assert len([g for g in games if g.week == 5]) == 15


def test_resolve_default_is_real_not_demo() -> None:
    universe, meta = resolve_season_universe(season=2026, demo=False, session=None)
    assert meta["mode"] == "real"
    assert meta["schedule_source"] == SCHEDULE_SOURCE_PACKAGED
    assert len(universe.schedule) == 272
    assert universe.notes.get("mode") == "real"


def test_demo_true_still_round_robin() -> None:
    universe, meta = resolve_season_universe(season=2026, demo=True, session=None)
    assert meta["mode"] == "demo"
    assert meta["schedule_source"] == SCHEDULE_SOURCE_DEMO
    assert len(universe.schedule) == 272
    # Demo has no byes — every team plays week 5.
    playing = {g.home_team for g in universe.schedule if g.week == 5} | {
        g.away_team for g in universe.schedule if g.week == 5
    }
    assert len(playing) == 32
    demo = build_demo_universe(2026)
    assert demo.notes["schedule_source"] == SCHEDULE_SOURCE_DEMO


def test_survivor_respects_real_byes() -> None:
    universe = build_packaged_real_universe(2026)
    result = evaluate_survivor(
        universe,
        week=5,
        n_sims=40,
        seed=9,
        already_used=[],
        top_n=32,
        include_diagnostics=True,
    )
    ranked_teams = {p["team"] for p in result.ranked_picks}
    assert "KC" not in ranked_teams
    assert "CAR" not in ranked_teams
    byes = (result.diagnostics or {}).get("bye_teams_this_week") or []
    assert "KC" in byes
    assert "CAR" in byes


def test_real_matchup_game_boxes_and_sim() -> None:
    universe = build_packaged_real_universe(2026)
    # Week 1: SF @ LA (Rams home)
    proj = project_game_player_boxes(
        universe,
        home_team="LA",
        away_team="SF",
        week=1,
        n_replicates=60,
        seed=3,
    )
    assert proj.home_team == "LA"
    assert proj.away_team == "SF"
    assert proj.players
    assert proj.notes.get("schedule_match") == "on_loaded_schedule"

    sim = simulate_full_season(universe, n_sims=3, seed=5)
    assert sim.games_per_season == 272
    assert abs(sim.diagnostics["mean_wins_sum"] - 272.0) < 0.01
