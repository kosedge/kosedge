"""Hierarchical CFB season engine (foundation).

College football 2026 reality (design constraints):
- Extreme roster turnover (portal + NIL + draft + freshmen)
- Weak YoY team identity — historical ratings alone are NOT enough
- QB situation is a first-class variable
- Early-season uncertainty is very high (wider than NFL W1–W4)

Layers (each module is the source of truth for its concern):

1. ``roster_construction`` — returning production, portal, recruiting, experience
2. ``qb_situation`` — incumbent / portal / open competition / true freshman
3. ``position_groups`` — OL, skill, front seven, secondary
4. ``team_projection`` — compose → O/D indices + game projection
5. ``season_sim`` — path-coherent season skeleton (team W/L)
6. ``player_hooks`` — thin QB/skill identity hooks where data allows

Public entry points
-------------------
- ``project_game`` / ``project_game_preview`` — team-level matchup projection
- ``simulate_full_season`` — N path-coherent season sims (skeleton)
- ``build_packaged_universe`` / ``resolve_season_universe`` — input builders
- ``engine_status_payload`` — honesty contract for API / ops

This package is **additive**. It does not replace CFB Edge Board markets-only
behavior or invent KEI fair lines until a later calibrated pass.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.services.cfb_season_engine.loaders import (
    build_demo_universe,
    build_packaged_universe,
    load_universe_from_db,
    resolve_season_universe,
)
from src.services.cfb_season_engine.player_hooks import hooks_to_summaries
from src.services.cfb_season_engine.priors import ENGINE_VERSION, documentation as priors_documentation
from src.services.cfb_season_engine.season_sim import season_sim_to_dict, simulate_full_season
from src.services.cfb_season_engine.team_projection import (
    project_game,
    project_game_to_dict,
)
from src.services.cfb_season_engine.types import (
    EngineUniverse,
    GameProjection,
    SeasonSimResult,
)
from src.services.cfb_season_engine import (
    loaders,
    player_hooks,
    position_groups,
    qb_situation,
    roster_construction,
    season_sim,
    team_projection,
)

DEFAULT_SEASON_ENGINE_VERSION = ENGINE_VERSION


def project_game_preview(
    universe: EngineUniverse,
    *,
    home_team: str,
    away_team: str,
    week: int = 1,
    season: Optional[int] = None,
    neutral_site: bool = False,
) -> GameProjection:
    """Team-level game preview with optional player-hook summaries."""
    hook_rows: List[Dict[str, Any]] = []
    for team in (home_team.upper(), away_team.upper()):
        hook_rows.extend(hooks_to_summaries(universe.player_hooks.get(team, [])))
    return project_game(
        universe,
        home_team=home_team,
        away_team=away_team,
        week=week,
        season=season,
        neutral_site=neutral_site,
        engine_version=DEFAULT_SEASON_ENGINE_VERSION,
        player_hook_summaries=hook_rows,
    )


def engine_status_payload(
    *,
    season: int = 2026,
    as_of_week: int = 1,
    demo: bool = True,
) -> Dict[str, Any]:
    """Honesty-first status contract for GET /cfb/season-engine/status."""
    universe, meta = resolve_season_universe(
        season=season, as_of_week=as_of_week, demo=demo, session=None
    )
    curated = sum(
        1
        for t in universe.teams.values()
        if t.roster and t.roster.fidelity == "approximate"
    )
    placeholder = sum(
        1
        for t in universe.teams.values()
        if t.roster and t.roster.fidelity == "placeholder"
    )
    return {
        "engine_version": DEFAULT_SEASON_ENGINE_VERSION,
        "sport": "cfb",
        "scope": "FBS foundation 2026",
        "mode": meta.get("mode"),
        "schedule_source": meta.get("schedule_source"),
        "schedule_game_count": meta.get("schedule_game_count"),
        "team_count": meta.get("team_count"),
        "team_fidelity_counts": {
            "approximate_curated": curated,
            "placeholder_fbs": placeholder,
        },
        "layers": [
            roster_construction.documentation(),
            qb_situation.documentation(),
            position_groups.documentation(),
            team_projection.documentation(),
            season_sim.documentation(),
            player_hooks.documentation(),
        ],
        "priors": priors_documentation(),
        "data_sources": {
            "packaged_team_priors": loaders.documentation()["packaged_teams"],
            "packaged_sample_schedule": loaders.documentation()["packaged_schedule"],
            "db_portal_recruiting": "not_wired",
            "edge_board_cfb": "markets_only (unchanged)",
        },
        "solid_vs_approximate": {
            "solid": [
                "Layer module boundaries + composition feed order",
                "QB situation classification rules",
                "Early-season uncertainty posture (inspectable)",
                "API / CLI / status honesty contract",
                "Additive isolation from NFL engine + CFB markets-only Edge Board",
            ],
            "approximate": [
                "Packaged roster / portal / recruiting numeric priors",
                "Named QB talent scores and depth identities",
                "Position group grades",
                "Game win probs / spreads / totals",
                "In-path strength evolution",
            ],
            "placeholder_or_deferred": [
                "Full official 2026 FBS schedule",
                "Live portal / returning production DB feeds",
                "Player box production path",
                "CFP bracket / conference standings",
                "Market-grade calibration / KEI fair lines",
            ],
        },
        "entry_points": {
            "status": "GET /cfb/season-engine/status",
            "project_game": "POST /cfb/season-engine/project-game",
            "simulate": "POST /cfb/season-engine/simulate",
            "cli": "scripts/cfb/run_hierarchical_season_sim.py",
            "ops": "data/ops/cfb-full-model-foundation-report.md",
        },
        "additive": True,
        "does_not_modify": [
            "edge_board_cfb_markets_only",
            "nfl_season_engine",
            "nfl_edge_board",
            "model_vs_kei_#70",
        ],
        "universe_notes": universe.notes,
    }


__all__ = [
    "DEFAULT_SEASON_ENGINE_VERSION",
    "EngineUniverse",
    "GameProjection",
    "SeasonSimResult",
    "build_demo_universe",
    "build_packaged_universe",
    "engine_status_payload",
    "load_universe_from_db",
    "project_game",
    "project_game_preview",
    "project_game_to_dict",
    "resolve_season_universe",
    "season_sim_to_dict",
    "simulate_full_season",
]
