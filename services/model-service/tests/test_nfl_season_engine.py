"""Tests for the hierarchical NFL season engine (foundation + player boxes)."""

from __future__ import annotations

from src.services.nfl_season_engine import (
    build_demo_universe,
    project_game_player_boxes,
    simulate_full_season,
)
from src.services.nfl_season_engine.game_script import build_game_script
from src.services.nfl_season_engine.player_usage import allocate_game_usage
from src.services.nfl_season_engine.production import produce_box_scores
from src.services.nfl_season_engine.team_strength import copy_strength_book, evolve_after_game


def test_demo_universe_has_272_games_and_32_teams() -> None:
    universe = build_demo_universe(2026)
    assert len(universe.teams) == 32
    assert len(universe.schedule) == 272
    assert all(universe.rosters[t] for t in universe.teams)


def test_four_layers_produce_coherent_single_game_boxes() -> None:
    import random

    universe = build_demo_universe(2026)
    game = next(g for g in universe.schedule if g.home_team == "KC")
    rng = random.Random(1)
    script, outcome = build_game_script(game, universe.strengths, rng=rng, realized=True)
    assert 0.02 <= script.home_win_prob <= 0.98
    assert script.pace_plays > 40
    usage = allocate_game_usage(script, universe.rosters, rng=rng)
    assert usage
    boxes = produce_box_scores(
        usage_rows=usage,
        roles=universe.rosters,
        script=script,
        strengths=universe.strengths,
        rng=rng,
    )
    qb = next(b for b in boxes if b.position == "QB" and b.team == "KC")
    assert qb.pass_yards > 0
    rb = next(b for b in boxes if b.position == "RB" and b.team == "KC")
    assert rb.rush_yards > 0 or rb.rec_yards > 0
    assert "home_score" in outcome


def test_strength_evolves_within_path() -> None:
    universe = build_demo_universe(2026)
    strengths = copy_strength_book(universe.strengths)
    before = strengths["KC"].offense_index
    evolve_after_game(
        strengths,
        home_team="KC",
        away_team="BUF",
        home_won=True,
        home_score=31,
        away_score=17,
    )
    assert strengths["KC"].games_played == 1
    assert strengths["KC"].offense_index != before or strengths["KC"].defense_index != before


def test_full_season_sim_path_coherence() -> None:
    universe = build_demo_universe(2026)
    result = simulate_full_season(universe, n_sims=5, seed=11)
    assert result.n_sims == 5
    assert result.games_per_season == 272
    # Each game has one winner → 272 wins across the league per path.
    assert abs(result.diagnostics["mean_wins_sum"] - 272.0) < 0.01
    # Named demo QBs should accumulate pass yards across the season.
    mahomes = next(
        (r for r in result.player_season_totals if "Mahomes" in r["player_name"]),
        None,
    )
    assert mahomes is not None
    assert mahomes["pass_yards_mean"] > 2500
    assert mahomes["games_mean"] > 10


def test_future_game_player_box_projection_shape() -> None:
    universe = build_demo_universe(2026)
    proj = project_game_player_boxes(
        universe,
        home_team="KC",
        away_team="BUF",
        week=1,
        n_replicates=80,
        seed=3,
    )
    assert proj.home_team == "KC"
    assert proj.away_team == "BUF"
    assert proj.n_replicates == 80
    assert proj.game_script_summary
    assert proj.players

    qb = next(p for p in proj.players if p["position"] == "QB" and p["team"] == "KC")
    assert "pass_yards" in qb["point_estimate"]
    assert "pass_tds" in qb["point_estimate"]
    assert "ints" in qb["point_estimate"]
    assert "rush_yards" in qb["point_estimate"]
    assert "p10" in qb["distributions"]["pass_yards"]
    assert "p90" in qb["distributions"]["pass_yards"]

    rb = next(p for p in proj.players if p["position"] == "RB")
    assert set(rb["point_estimate"]) >= {"rush_yards", "rush_tds", "rec_yards", "receptions"}

    wr = next(p for p in proj.players if p["position"] == "WR")
    assert set(wr["point_estimate"]) >= {"rec_yards", "receptions", "rec_tds"}
