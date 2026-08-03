"""Hierarchical NFL season simulation engine (foundation + player boxes).

Four layers (each module is the single source of truth for its concern):

1. ``team_strength``  – offense/defense ratings that can evolve within a sim path
2. ``game_script``    – pace, total, win prob, lead/trail/neutral script
3. ``player_usage``   – targets, carries, routes, snap share | script + role
4. ``production``     – usage + matchup + script → yards / TDs / receptions / INTs

Public entry points
-------------------
- ``simulate_full_season`` – N path-coherent season sims (~272 games each)
- ``project_game_player_boxes`` – future-game player box distributions
- ``build_demo_universe`` / ``load_universe_from_db`` – input builders

This package is **additive**. It does not replace
``simulate_nfl_game`` / Edge Board / Model-vs-KEI (#70) paths.
"""

from __future__ import annotations

from src.services.nfl_season_engine.game_query import project_game_player_boxes
from src.services.nfl_season_engine.loaders import (
    build_demo_universe,
    load_universe_from_db,
)
from src.services.nfl_season_engine.season_sim import simulate_full_season
from src.services.nfl_season_engine.types import (
    EngineUniverse,
    GameBoxProjection,
    SeasonSimResult,
)

DEFAULT_SEASON_ENGINE_VERSION = "nfl-season-engine-v1"

__all__ = [
    "DEFAULT_SEASON_ENGINE_VERSION",
    "EngineUniverse",
    "GameBoxProjection",
    "SeasonSimResult",
    "build_demo_universe",
    "load_universe_from_db",
    "project_game_player_boxes",
    "simulate_full_season",
]
