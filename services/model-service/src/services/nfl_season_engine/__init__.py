"""Hierarchical NFL season simulation engine (foundation + player boxes).

Four layers (each module is the single source of truth for its concern):

1. ``team_strength``  – offense/defense ratings that can evolve within a sim path
2. ``game_script``    – pace, total, win prob, script detail / play-calling mix
   (+ ``coaching_tendencies`` modest team identity overlays on play-mix / RZ)
3. ``player_usage``   – targets, carries, routes, snap share | script + role
   (+ ``red_zone`` scoring-usage opportunities between usage and TDs)
4. ``production``     – usage + matchup + script → yards / TDs / receptions / INTs
   (TDs primarily from RZ opportunities × finish rates; yards from general usage)
   (+ ``player_regression`` process priors / regression posture + finite team
   yards/TD caps so named players stay inside the script pool)

Injury / availability path shocks (``injury_paths``) adjust Layers 1 and 3
for specified week ranges before Layers 2–4 run. Layer 3 uses an explicit
usage-role taxonomy (``usage_roles``) plus depth-chart structure /
committee splits / weekly role volatility (``depth_chart``) for base
shares, script/personnel modifiers, and role-aware injury reallocation.

Survivor pool outputs (``survivor``) run team W/L-only season paths and
rank remaining picks for a target week with inspectable save / pick-now
scores. The multi-week planner (``evaluate_survivor_plan``) reuses the
same path matrix for slate metrics + per-week recommendations.
``suggest_survivor_paths`` adds chalk / balanced / contrarian-save paths.

v1.13 keeps cal-v2 / survivor-planner-ux and adds player process regression
+ finite production (capability ``player-regression``).

Public entry points
-------------------
- ``simulate_full_season`` – N path-coherent season sims (~272 games each)
- ``project_game_player_boxes`` – future-game player box distributions
- ``evaluate_survivor`` – survivor week rankings + path value
- ``evaluate_survivor_plan`` – multi-week planner + slate metrics
- ``suggest_survivor_paths`` – heuristic full-season path suggestions
- ``resolve_season_universe`` / ``build_demo_universe`` /
  ``load_universe_from_db`` / ``build_packaged_real_universe`` – input builders
- ``parse_injury_paths`` – API/CLI JSON → ``InjuryPath`` structs
- ``apply_process_priors`` / ``build_player_process_prior`` – player regression

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
from src.services.nfl_season_engine.efficiency_backbone import (
    EFFICIENCY_BACKBONE_VERSION,
    TeamEfficiencyPackage,
    package_to_strength_indices,
)
from src.services.nfl_season_engine.loaders import (
    build_demo_universe,
    build_packaged_real_universe,
    load_packaged_depth_chart,
    load_packaged_efficiency_backbone,
    load_packaged_epa_priors,
    load_packaged_regular_schedule,
    load_universe_from_db,
    resolve_season_universe,
    universe_schedule_meta,
)
from src.services.nfl_season_engine.player_regression import (
    apply_process_priors,
    build_player_process_prior,
    enforce_finite_team_production,
)
from src.services.nfl_season_engine.season_sim import simulate_full_season
from src.services.nfl_season_engine.survivor import (
    SurvivorEvalResult,
    SurvivorPlanResult,
    SurvivorSuggestedPathsResult,
    evaluate_survivor,
    evaluate_survivor_plan,
    suggest_survivor_paths,
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
    "EFFICIENCY_BACKBONE_VERSION",
    "EngineUniverse",
    "GameBoxProjection",
    "InjuryPath",
    "SeasonSimResult",
    "SurvivorEvalResult",
    "SurvivorPlanResult",
    "SurvivorSuggestedPathsResult",
    "TeamEfficiencyPackage",
    "apply_process_priors",
    "build_demo_universe",
    "build_packaged_real_universe",
    "build_player_process_prior",
    "enforce_finite_team_production",
    "evaluate_survivor",
    "evaluate_survivor_plan",
    "load_packaged_depth_chart",
    "load_packaged_efficiency_backbone",
    "load_packaged_epa_priors",
    "load_packaged_regular_schedule",
    "load_universe_from_db",
    "package_to_strength_indices",
    "parse_injury_paths",
    "project_game_player_boxes",
    "resolve_season_universe",
    "simulate_full_season",
    "suggest_survivor_paths",
    "universe_schedule_meta",
    "week_win_rate_for_team",
]
