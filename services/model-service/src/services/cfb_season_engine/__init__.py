"""Hierarchical CFB season engine (position groups + team projection).

College football 2026 reality (design constraints):
- Extreme roster turnover (portal + NIL + draft + freshmen)
- Weak YoY team identity — historical ratings alone are NOT enough
- QB situation is a first-class variable
- Position groups (OL / skill / front seven / secondary) are real drivers
- Early-season uncertainty is very high (wider than NFL W1–W4)

Layers (each module is the source of truth for its concern):

1. ``roster_construction`` — snap/start-weighted returning production, portal
   net, recruiting capital, experience → inspectable ``roster_strength``
2. ``qb_situation`` — incumbent / portal / open competition / true freshman
   + supporting cast → ``qb_situation_index`` (material offense lever)
3. ``position_groups`` — OL, skill, front seven, secondary with inspectable
   talent / experience / portal_impact components
4. ``team_projection`` — compose → O/D indices + unit-aware game projection
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
from src.services.cfb_season_engine.position_groups import (
    groups_to_dict,
    unit_grade_breakdown,
)
from src.services.cfb_season_engine.priors import ENGINE_VERSION, documentation as priors_documentation
from src.services.cfb_season_engine.qb_situation import qb_situation_breakdown, qb_to_dict
from src.services.cfb_season_engine.roster_construction import (
    roster_strength_breakdown,
    roster_to_dict,
)
from src.services.cfb_season_engine.season_sim import season_sim_to_dict, simulate_full_season
from src.services.cfb_season_engine.team_projection import (
    project_game,
    project_game_formula_doc,
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
    # Example team diagnostics — stable power (incumbent) vs rebuild/open QB.
    example_codes = ["UGA", "FSU", "COLO", "BALL"]
    examples: Dict[str, Any] = {}
    for code in example_codes:
        state = universe.teams.get(code)
        if not state or not state.roster or not state.qb:
            continue
        examples[code] = {
            "offense_index": state.offense_index,
            "defense_index": state.defense_index,
            "early_season_uncertainty": state.early_season_uncertainty,
            "roster": roster_to_dict(state.roster),
            "roster_breakdown": roster_strength_breakdown(state.roster),
            "qb": qb_to_dict(state.qb),
            "qb_breakdown": qb_situation_breakdown(state.qb),
            "position_groups": groups_to_dict(state.groups) if state.groups else None,
            "position_groups_breakdown": (
                unit_grade_breakdown(state.groups) if state.groups else None
            ),
            "compose_notes": dict(state.notes),
        }

    ranked = sorted(
        (
            (code, t.roster.roster_strength if t.roster else 0.0)
            for code, t in universe.teams.items()
        ),
        key=lambda row: row[1],
        reverse=True,
    )
    roster_strength_top = [
        {"team": code, "roster_strength": round(score, 2)} for code, score in ranked[:8]
    ]
    roster_strength_bottom = [
        {"team": code, "roster_strength": round(score, 2)} for code, score in ranked[-8:]
    ]

    return {
        "engine_version": DEFAULT_SEASON_ENGINE_VERSION,
        "sport": "cfb",
        "scope": "FBS position-groups + team projection 2026",
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
        "project_game_formula": project_game_formula_doc(),
        "examples": examples,
        "roster_strength_ladder": {
            "top": roster_strength_top,
            "bottom": roster_strength_bottom,
            "note": (
                "Packaged approximate ranks — blue-blood recruiting/returning "
                "profiles should outrank placeholder mid-majors."
            ),
        },
        "data_sources": {
            "packaged_team_priors": loaders.documentation()["packaged_teams"],
            "packaged_sample_schedule": loaders.documentation()["packaged_schedule"],
            "db_portal_recruiting": "not_wired",
            "edge_board_cfb": "markets_only (unchanged)",
            "field_provenance": (
                "returning_snap/start shares, portal values, and unit talent "
                "composites are curated/estimated in packaged JSON or derived "
                "in-layer; not live SNAP% / SP+"
            ),
        },
        "solid_vs_approximate": {
            "solid": [
                "Layer module boundaries + composition feed order",
                "Roster strength formula (snap/start + portal net + recruiting + experience)",
                "QB situation classification rules + class offense multipliers",
                "Position group unit formula (talent/experience/portal_impact)",
                "roster_strength + qb_situation_index + unit grades as projection drivers",
                "project-game formula (strength → margin → spread/total/WP)",
                "Early-season uncertainty posture (inspectable)",
                "API / CLI / status honesty contract",
                "Additive isolation from NFL engine + CFB markets-only Edge Board",
            ],
            "approximate": [
                "Packaged roster snap/start / portal / recruiting numeric priors",
                "Named QB talent scores and depth identities",
                "Position group talent composites and unit component fills",
                "Game win probs / spreads / totals",
                "In-path strength evolution",
            ],
            "placeholder_or_deferred": [
                "Full official 2026 FBS schedule",
                "Live portal / returning production DB feeds",
                "Calibrated unit grades (SP+ / PFF-class)",
                "Special teams model (thin nudge only)",
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
            "ops": "data/ops/cfb-position-projection-20260804.md",
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
