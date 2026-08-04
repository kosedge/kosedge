"""Hierarchical CFB season engine (projection UI + real 2026 roster overlay).

College football 2026 reality (design constraints):
- Extreme roster turnover (portal + NIL + draft + freshmen)
- Weak YoY team identity — historical ratings alone are NOT enough
- QB situation is a first-class variable
- Position groups (OL / skill / front seven / secondary) are real drivers
- Early-season uncertainty is very high (wider than NFL W1–W4)
- Home-field advantage is variable (not a flat 3-pt blanket)
- Coaching continuity / staff change is a first-class early-season lever

Layers (each module is the source of truth for its concern):

1. ``roster_construction`` — snap/start-weighted returning production, portal
   net, recruiting capital, experience → inspectable ``roster_strength``
2. ``qb_situation`` — incumbent / portal / open competition / true freshman
   + supporting cast → ``qb_situation_index`` (material offense lever)
3. ``position_groups`` — OL, skill, front seven, secondary with inspectable
   talent / experience / portal_impact components
4. ``team_projection`` — compose → O/D indices + unit-aware game projection
5. ``home_field`` — variable HFA buckets (baseline ~2 pts)
6. ``coaching_continuity`` — new HC/OC/DC flags + week-decayed penalties
7. ``season_sim`` — path-coherent full-season sims (wins dist, week sample)
8. ``player_hooks`` — thin QB/skill identity hooks where data allows

v0.6 feeds Layers 1–3 from a packaged ESPN 2026 real-roster snapshot
(DB → snapshot → legacy priors). Returning snap% / portal-out stay approximate
unless a CFBD overlay was applied at package time.

Public entry points
-------------------
- ``project_game`` / ``project_game_preview`` — team-level matchup projection
- ``simulate_full_season`` — N path-coherent season sims
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
from src.services.cfb_season_engine.real_roster import (
    load_real_roster_snapshot,
    snapshot_meta,
)
from src.services.cfb_season_engine.player_hooks import hooks_to_summaries
from src.services.cfb_season_engine.position_groups import (
    groups_to_dict,
    unit_grade_breakdown,
)
from src.services.cfb_season_engine.priors import (
    ENGINE_VERSION,
    documentation as priors_documentation,
    early_season_narrowing_schedule,
)
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
    coaching_continuity,
    conferences,
    home_field,
    loaders,
    player_hooks,
    position_groups,
    qb_situation,
    roster_construction,
    schedule,
    season_sim,
    team_projection,
)
from src.services.cfb_season_engine.coaching_continuity import coaching_to_dict
from src.services.cfb_season_engine.home_field import profile_to_dict

DEFAULT_SEASON_ENGINE_VERSION = ENGINE_VERSION


def project_game_preview(
    universe: EngineUniverse,
    *,
    home_team: str,
    away_team: str,
    week: int = 1,
    season: Optional[int] = None,
    neutral_site: bool = False,
    night_game: bool = False,
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
        night_game=night_game,
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
    real_identity = sum(
        1
        for t in universe.teams.values()
        if t.qb and t.qb.starter_name and "espn" in (t.qb.source or "").lower()
    )
    snap_meta = snapshot_meta(load_real_roster_snapshot())
    if not snap_meta.get("present"):
        # Priors may already carry the merged overlay without a separate file read hit.
        snap_meta = {
            "present": meta.get("roster_source", "").startswith("packaged_espn"),
            "roster_source": meta.get("roster_source"),
            "depth_source": meta.get("depth_source"),
            "portal_source": meta.get("portal_source"),
            "returning_source": meta.get("returning_source"),
            "as_of": meta.get("roster_as_of") or universe.notes.get("priors_as_of", ""),
            "coverage": {
                "team_count": meta.get("team_count"),
                "teams_with_named_qb": real_identity,
            },
        }
    # Example team diagnostics — power continuity vs new-HC / weak HFA.
    example_codes = ["UGA", "PSU", "FSU", "LSU", "BALL"]
    examples: Dict[str, Any] = {}
    for code in example_codes:
        state = universe.teams.get(code)
        if not state or not state.roster or not state.qb:
            continue
        examples[code] = {
            "offense_index": state.offense_index,
            "defense_index": state.defense_index,
            "early_season_uncertainty": state.early_season_uncertainty,
            "conference": universe.conferences.get(code, "Independent"),
            "roster": roster_to_dict(state.roster),
            "roster_breakdown": roster_strength_breakdown(state.roster),
            "qb": qb_to_dict(state.qb),
            "qb_breakdown": qb_situation_breakdown(state.qb),
            "position_groups": groups_to_dict(state.groups) if state.groups else None,
            "position_groups_breakdown": (
                unit_grade_breakdown(state.groups) if state.groups else None
            ),
            "home_field": profile_to_dict(state.home_field),
            "coaching": coaching_to_dict(state.coaching),
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

    power_ranked = sorted(
        (
            (
                code,
                0.5 * (t.offense_index + t.defense_index),
                t.offense_index,
                t.defense_index,
                t.roster.roster_strength if t.roster else 0.0,
                t.early_season_uncertainty,
            )
            for code, t in universe.teams.items()
        ),
        key=lambda row: row[1],
        reverse=True,
    )
    power_style_ladder = [
        {
            "rank": i + 1,
            "team": code,
            "power_index": round(power, 3),
            "offense_index": round(off, 3),
            "defense_index": round(deff, 3),
            "roster_strength": round(roster_s, 2),
            "early_season_uncertainty": round(early_u, 3),
            "conference": universe.conferences.get(code, "Independent"),
        }
        for i, (code, power, off, deff, roster_s, early_u) in enumerate(
            power_ranked[:40]
        )
    ]

    hfa_buckets: Dict[str, int] = {}
    coaching_flags = {"new_hc": 0, "new_oc": 0, "new_dc": 0, "all_returning": 0}
    for state in universe.teams.values():
        if state.home_field:
            hfa_buckets[state.home_field.bucket] = (
                hfa_buckets.get(state.home_field.bucket, 0) + 1
            )
        if state.coaching:
            if state.coaching.new_hc:
                coaching_flags["new_hc"] += 1
            if state.coaching.new_oc:
                coaching_flags["new_oc"] += 1
            if state.coaching.new_dc:
                coaching_flags["new_dc"] += 1
            if state.coaching.returning_hc and state.coaching.returning_oc and state.coaching.returning_dc:
                coaching_flags["all_returning"] += 1

    return {
        "engine_version": DEFAULT_SEASON_ENGINE_VERSION,
        "sport": "cfb",
        "scope": (
            "FBS season sim + projection UI + ESPN 2026 real-roster overlay + "
            "variable HFA + coaching"
        ),
        "mode": meta.get("mode"),
        "schedule_source": meta.get("schedule_source"),
        "schedule_game_count": meta.get("schedule_game_count"),
        "team_count": meta.get("team_count"),
        "roster_source": meta.get("roster_source") or snap_meta.get("roster_source"),
        "depth_source": meta.get("depth_source") or snap_meta.get("depth_source"),
        "portal_source": meta.get("portal_source") or snap_meta.get("portal_source"),
        "returning_source": meta.get("returning_source")
        or snap_meta.get("returning_source"),
        "roster_as_of": meta.get("roster_as_of") or snap_meta.get("as_of"),
        "as_of": meta.get("roster_as_of") or snap_meta.get("as_of"),
        "roster_coverage": snap_meta.get("coverage") or {},
        "team_codes": sorted(universe.teams.keys()),
        "team_fidelity_counts": {
            "approximate_curated": curated,
            "placeholder_fbs": placeholder,
            "espn_named_qb": real_identity,
        },
        "layers": [
            roster_construction.documentation(),
            qb_situation.documentation(),
            position_groups.documentation(),
            team_projection.documentation(),
            home_field.documentation(),
            coaching_continuity.documentation(),
            season_sim.documentation(),
            player_hooks.documentation(),
        ],
        "priors": priors_documentation(),
        "early_season_narrowing": early_season_narrowing_schedule(),
        "schedule": schedule.documentation(),
        "conferences": conferences.documentation(),
        "project_game_formula": project_game_formula_doc(),
        "examples": examples,
        "hfa_bucket_counts": hfa_buckets,
        "coaching_flag_counts": coaching_flags,
        "roster_strength_ladder": {
            "top": roster_strength_top,
            "bottom": roster_strength_bottom,
            "note": (
                "Ranks from ESPN 2026 roster-derived returning/portal/experience "
                "plus retained recruiting priors — not market-grade."
            ),
        },
        "power_style_ladder": {
            "top": power_style_ladder,
            "note": (
                "Thin power-style ranks from 0.5*(offense_index+defense_index). "
                "Roster/QB drivers use real ESPN 2026 identities where available; "
                "not market-grade power ratings."
            ),
            "fidelity": "approximate",
        },
        "data_sources": {
            "packaged_team_priors": loaders.documentation()["packaged_teams"],
            "packaged_real_roster_snapshot": loaders.documentation().get(
                "packaged_real_roster"
            ),
            "packaged_sample_schedule": loaders.documentation()["packaged_schedule"],
            "schedule_policy": loaders.documentation()["schedule_policy"],
            "roster_source": meta.get("roster_source") or snap_meta.get("roster_source"),
            "depth_source": meta.get("depth_source") or snap_meta.get("depth_source"),
            "portal_source": meta.get("portal_source") or snap_meta.get("portal_source"),
            "returning_source": meta.get("returning_source")
            or snap_meta.get("returning_source"),
            "as_of": meta.get("roster_as_of") or snap_meta.get("as_of"),
            "db_portal_recruiting": "optional_unpopulated (packaged snapshot preferred)",
            "db_home_splits": "not_wired",
            "db_coaching_changes": "not_wired",
            "edge_board_cfb": "markets_only (unchanged)",
            "field_provenance": (
                "QB names/classes and depth order from ESPN 2026 rosters + "
                "athlete teamHistory/career splits; returning snap/start shares "
                "are class-year proxies; portal-out incomplete; recruiting often "
                "retained from curated priors; HFA/coaching still curated; "
                "densified schedule is synthetic approximate paths"
            ),
        },
        "solid_vs_approximate": {
            "solid": [
                "Layer module boundaries + composition feed order",
                "Roster strength formula (snap/start + portal net + recruiting + experience)",
                "QB situation classification rules + class offense multipliers",
                "Position group unit formula (talent/experience/portal_impact)",
                "roster_strength + qb_situation_index + unit grades as projection drivers",
                "Packaged ESPN 2026 roster snapshot wiring (DB → snapshot → priors)",
                "Variable HFA bucket structure (baseline ~2 pts, elite→poor)",
                "Coaching continuity flags + week-decay schedule (HC/DC > OC)",
                "project-game formula (strength → margin → spread/total/WP) + drivers block",
                "Early-season uncertainty posture (week-indexed narrowing, inspectable)",
                "Season-sim path coherence (wins dist, week sample, ranking)",
                "API / CLI / status honesty contract",
                "Additive isolation from NFL engine + CFB markets-only Edge Board",
            ],
            "approximate": [
                "Returning snap/start shares (class-year proxies, not measured SNAP%)",
                "Portal-out values without a full departure feed",
                "QB talent scores derived from 2025 attempt/yard splits",
                "Position group talent composites from roster composition",
                "Recruiting capital when retained from curated priors",
                "HFA env_scores / venue labels (not live home ATS splits)",
                "Coaching staff change flags for 2026 (curated proxies)",
                "Densified schedule paths (not official FBS slate)",
                "Conference affiliations for standings",
                "Game win probs / spreads / totals",
                "In-path strength evolution",
                "Season win totals / ranking-ish standings",
            ],
            "placeholder_or_deferred": [
                "Full official 2026 FBS schedule feed",
                "Live DB portal / returning production tables (optional; snapshot ships in-image)",
                "Official preseason depth charts when ESPN publishes them",
                "Live home scoring-margin / ATS feed",
                "Live coaching-change feed",
                "Calibrated unit grades (SP+ / PFF-class)",
                "Full night-game / weather model",
                "Special teams model (thin nudge only)",
                "Player box production path",
                "CFP bracket",
                "Market-grade calibration / KEI fair lines",
            ],
        },
        "entry_points": {
            "status": "GET /cfb/season-engine/status",
            "project_game": "POST /cfb/season-engine/project-game",
            "simulate": "POST /cfb/season-engine/simulate",
            "cli": "scripts/cfb/run_hierarchical_season_sim.py",
            "package_roster": "scripts/cfb/package_real_roster_2026.py",
            "ops": "data/ops/cfb-real-roster-20260804.md",
            "web_hub": "/pro/cfb/model",
            "web_project_game": "/pro/cfb/project-game",
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
