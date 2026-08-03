"""Hierarchical NFL season simulation engine (foundation + player boxes).

Four layers (each module is the single source of truth for its concern):

1. ``team_strength``  – offense/defense ratings that can evolve within a sim path
2. ``game_script``    – pace, total, win prob, lead/trail/neutral script
3. ``player_usage``   – targets, carries, routes, snap share | script + role
4. ``production``     – usage + matchup + script → yards / TDs / receptions / INTs

Injury / availability path shocks (``injury_paths``) adjust Layers 1 and 3
for specified week ranges before Layers 2–4 run. Layer 3 uses an explicit
usage-role taxonomy (``usage_roles``) plus depth-chart structure /
committee splits / weekly role volatility (``depth_chart``) for base
shares, script/personnel modifiers, and role-aware injury reallocation.

Survivor pool outputs (``survivor``) run team W/L-only season paths and
rank remaining picks for a target week with inspectable save / pick-now
scores.

Public entry points
-------------------
- ``simulate_full_season`` – N path-coherent season sims (~272 games each)
- ``project_game_player_boxes`` – future-game player box distributions
- ``evaluate_survivor`` – survivor week rankings + path value
- ``build_demo_universe`` / ``load_universe_from_db`` – input builders
- ``parse_injury_paths`` – API/CLI JSON → ``InjuryPath`` structs

This package is **additive**. It does not replace
``simulate_nfl_game`` / Edge Board / Model-vs-KEI (#70) paths.
"""

from __future__ import annotations

from src.services.nfl_season_engine.calibration import ENGINE_VERSION
from src.services.nfl_season_engine.game_query import project_game_player_boxes
from src.services.nfl_season_engine.injury_paths import (
    InjuryPath,
    parse_injury_paths,
)
from src.services.nfl_season_engine.loaders import (
    build_demo_universe,
    load_universe_from_db,
)
from src.services.nfl_season_engine.season_sim import simulate_full_season
from src.services.nfl_season_engine.survivor import (
    SurvivorEvalResult,
    evaluate_survivor,
    week_win_rate_for_team,
)
from src.services.nfl_season_engine.types import (
    EngineUniverse,
    GameBoxProjection,
    SeasonSimResult,
)

DEFAULT_SEASON_ENGINE_VERSION = ENGINE_VERSION

__all__ = [
    "DEFAULT_SEASON_ENGINE_VERSION",
    "EngineUniverse",
    "GameBoxProjection",
    "InjuryPath",
    "SeasonSimResult",
    "SurvivorEvalResult",
    "build_demo_universe",
    "evaluate_survivor",
    "load_universe_from_db",
    "parse_injury_paths",
    "project_game_player_boxes",
    "simulate_full_season",
    "week_win_rate_for_team",
]
