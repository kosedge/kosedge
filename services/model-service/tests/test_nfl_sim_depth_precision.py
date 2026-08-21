"""Sim depth defaults, caches, and TD honesty helpers (2026-08-11)."""

from __future__ import annotations

import os

import pytest

from src.services.nfl_season_engine.game_query import (
    _enrich_td_stat,
    project_game_player_boxes,
)
from src.services.nfl_season_engine.loaders import resolve_season_universe
from src.services.nfl_season_engine.sim_depth import (
    HONEST_PRECISION_MIN_N,
    clear_sim_depth_caches,
    default_n_game_box,
    default_n_survivor_paths,
    depth_label,
    depth_meta,
    is_honest_precision,
    prob_to_american,
    resolve_n_game_box,
    resolve_n_survivor_paths,
)
from src.services.nfl_season_engine.survivor import (
    evaluate_survivor_plan,
    get_or_build_survivor_path_pool,
    suggest_survivor_paths,
)


@pytest.fixture(autouse=True)
def _clear_caches(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("NFL_SEASON_ENGINE_THIN_DEPTH", raising=False)
    monkeypatch.delenv("NFL_SEASON_ENGINE_N_GAME_BOX", raising=False)
    monkeypatch.delenv("NFL_SEASON_ENGINE_N_SURVIVOR_PATHS", raising=False)
    clear_sim_depth_caches()
    yield
    clear_sim_depth_caches()


def test_defaults_are_research_depth() -> None:
    assert default_n_game_box() >= HONEST_PRECISION_MIN_N
    assert default_n_survivor_paths() >= HONEST_PRECISION_MIN_N
    assert default_n_game_box() == 2000
    assert default_n_survivor_paths() == 2000
    assert is_honest_precision(2000)
    assert not is_honest_precision(120)
    assert depth_label(50) == "low-depth estimate"
    assert depth_meta(2000, surface="game_boxes")["honest_precision"] is True


def test_env_knobs_and_thin_depth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NFL_SEASON_ENGINE_N_GAME_BOX", "5000")
    monkeypatch.setenv("NFL_SEASON_ENGINE_N_SURVIVOR_PATHS", "5000")
    assert default_n_game_box() == 5000
    assert default_n_survivor_paths() == 5000
    monkeypatch.setenv("NFL_SEASON_ENGINE_THIN_DEPTH", "1")
    # Thin mode prefers thin defaults unless env still overrides above thin.
    assert resolve_n_game_box(None) == 5000  # explicit env still wins
    monkeypatch.delenv("NFL_SEASON_ENGINE_N_GAME_BOX", raising=False)
    monkeypatch.delenv("NFL_SEASON_ENGINE_N_SURVIVOR_PATHS", raising=False)
    assert default_n_game_box() == 50
    assert default_n_survivor_paths() == 120


def test_td_enrichment_prefers_p_td() -> None:
    values = [0.0, 0.0, 1.0, 0.0, 2.0]
    base = {"mean": 0.6, "std": 0.8, "p10": 0.0, "p50": 0.0, "p90": 1.0}
    out = _enrich_td_stat(values, base)
    assert out["p_td"] == pytest.approx(0.4)
    assert out["expected_rate"] == pytest.approx(0.6)
    assert out["display"] == "p_td"
    assert out["fair_american"] == prob_to_american(0.4)


def test_game_box_cache_hit_same_key() -> None:
    universe, _ = resolve_season_universe(
        season=2026, as_of_week=1, demo=True, session=None
    )
    g = next(x for x in universe.schedule if x.week == 1)
    a = project_game_player_boxes(
        universe,
        home_team=g.home_team,
        away_team=g.away_team,
        week=1,
        n_replicates=40,
        seed=7,
    )
    b = project_game_player_boxes(
        universe,
        home_team=g.home_team,
        away_team=g.away_team,
        week=1,
        n_replicates=40,
        seed=7,
    )
    assert a.notes.get("cache") == "miss"
    assert b.notes.get("cache") == "hit"
    assert a.n_replicates == 40
    # Different game must not cross-serve.
    other = next(
        x
        for x in universe.schedule
        if x.week == 1 and x.game_id != g.game_id
    )
    c = project_game_player_boxes(
        universe,
        home_team=other.home_team,
        away_team=other.away_team,
        week=1,
        n_replicates=40,
        seed=7,
    )
    assert c.game_id != a.game_id
    assert c.notes.get("cache") == "miss"


def test_survivor_path_pool_shared_plan_and_suggest() -> None:
    universe, _ = resolve_season_universe(
        season=2026, as_of_week=1, demo=True, session=None
    )
    pool1, hit1 = get_or_build_survivor_path_pool(
        universe, n_sims=24, seed=11, injury_paths=[]
    )
    pool2, hit2 = get_or_build_survivor_path_pool(
        universe, n_sims=24, seed=11, injury_paths=[]
    )
    assert hit1 is False
    assert hit2 is True
    assert pool1.n_sims == 24
    assert pool2.cache_key == pool1.cache_key

    plan = evaluate_survivor_plan(
        universe, picks={}, n_sims=24, seed=11, injury_paths=[], top_n=3
    )
    suggested = suggest_survivor_paths(
        universe, n_sims=24, seed=11, injury_paths=[], already_locked={}
    )
    assert plan.n_sims == 24
    assert suggested.n_sims == 24
    assert plan.notes.get("path_pool_cache") == "hit"
    assert suggested.notes.get("path_pool_cache") == "hit"
    assert plan.notes.get("depth_label") == "low-depth estimate"


def test_empty_survivor_plan_result_cached() -> None:
    universe, _ = resolve_season_universe(
        season=2026, as_of_week=1, demo=True, session=None
    )
    first = evaluate_survivor_plan(
        universe, picks={}, n_sims=16, seed=5, injury_paths=[], top_n=4
    )
    second = evaluate_survivor_plan(
        universe, picks={}, n_sims=16, seed=5, injury_paths=[], top_n=4
    )
    assert first.weeks and second.weeks
    assert first.weeks[0]["ranked_picks"] == second.weeks[0]["ranked_picks"]
    # Locked slates are not served from the empty cache.
    team = str(first.weeks[0]["ranked_picks"][0]["team"])
    locked = evaluate_survivor_plan(
        universe,
        picks={"1": team},
        n_sims=16,
        seed=5,
        injury_paths=[],
        top_n=4,
    )
    assert locked.locked_pick_count == 1
    assert locked.weeks[0]["status"] == "locked"


def test_game_box_means_stable_across_two_cached_runs() -> None:
    universe, _ = resolve_season_universe(
        season=2026, as_of_week=1, demo=True, session=None
    )
    g = next(x for x in universe.schedule if x.week == 1)
    a = project_game_player_boxes(
        universe,
        home_team=g.home_team,
        away_team=g.away_team,
        week=1,
        n_replicates=80,
        seed=3,
    )
    clear_sim_depth_caches()
    b = project_game_player_boxes(
        universe,
        home_team=g.home_team,
        away_team=g.away_team,
        week=1,
        n_replicates=80,
        seed=3,
    )
    assert a.players and b.players
    # Same seed → identical means (deterministic engine).
    for pa, pb in zip(a.players, b.players):
        assert pa["player_key"] == pb["player_key"]
        for stat, dist in pa["distributions"].items():
            assert dist["mean"] == pb["distributions"][stat]["mean"]
