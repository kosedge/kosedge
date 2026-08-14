"""Hierarchical CFB season engine (projection UI + real 2026 roster overlay).

College football 2026 reality (design constraints):
- Extreme roster turnover (portal + NIL + draft + freshmen)
- Weak YoY team identity — historical ratings alone are NOT enough
- QB situation is a first-class variable
- Position groups (OL / skill / front seven / secondary) are real drivers
- Opponent-adjusted efficiency (SP+/EPA-style) complements roster/QB identity
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
4. ``efficiency`` — opponent-adjusted off/def efficiency (2025 SP+ carry)
5. ``team_projection`` — compose → O/D indices + unit-aware game projection
6. ``home_field`` — variable HFA buckets (baseline ~2 pts)
7. ``coaching_continuity`` — new HC/OC/DC flags + week-decayed penalties
8. ``season_sim`` — path-coherent full-season sims (wins dist, week sample)
9. ``player_hooks`` — QB + skill role-share projections from team totals

v0.6 feeds Layers 1–3 from a packaged ESPN 2026 real-roster snapshot
(DB → snapshot → legacy priors). Returning snap% / portal-out stay approximate
unless a CFBD overlay was applied at package time.

v0.6.1 measured projection calibration (priors / matchup / index clamps) —
real-roster overlay kept intact; fidelity remains approximate (no Edge Board KEI).

v0.7 allocates team pass/rush/TD pools onto named QB + skill hooks
(role shares; residual other OK). Does not mutate team scores/spreads.

v0.8 adds opponent-adjusted efficiency backbone (final-2025 SP+ carry) as a
primary complementary O/D driver; unit weights reduced to avoid double-counting.

v0.8.1 historical closing-line calibration (SportsDataverse ESPN lines +
prior-year ratings proxy). Measured priors only; architecture intact.

v0.8.2 live performance tracking + CLV logging (projection → close → result).
Projection knobs unchanged from v0.8.1.

v0.8.3 player↔team coherence + game-script allocation (player layer only).

v0.9 in-season updating foundation — shrinkaged efficiency deltas from
final scores; preseason baseline preserved and inspectable.

Public entry points
-------------------
- ``project_game`` / ``project_game_preview`` — team-level matchup projection
- ``simulate_full_season`` — N path-coherent season sims
- ``build_packaged_universe`` / ``resolve_season_universe`` — input builders
- ``engine_status_payload`` — honesty contract for API / ops
- ``performance_tracking`` — log / close / result / summary
- ``in_season_update`` — ingest result → rating deltas / state

This package is **additive**. It does not replace CFB Edge Board markets-only
behavior or invent KEI fair lines until a later calibrated pass.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

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
from src.services.cfb_season_engine.efficiency import (
    documentation as efficiency_documentation,
    efficiency_to_dict,
    snapshot_meta as efficiency_snapshot_meta,
)
from src.services.cfb_season_engine.player_hooks import (
    attach_player_projections,
    hooks_to_summaries,
)
from src.services.cfb_season_engine.position_groups import (
    groups_to_dict,
    unit_grade_breakdown,
)
from src.services.cfb_season_engine.priors import (
    BACKBONE_VERSION,
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
    efficiency,
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
    n_sims: int = 5000,
    seed: Optional[int] = None,
) -> GameProjection:
    """Team-level game preview with player-hook identity + role-share projections."""
    hook_rows: List[Dict[str, Any]] = []
    for team in (home_team.upper(), away_team.upper()):
        hook_rows.extend(hooks_to_summaries(universe.player_hooks.get(team, [])))
    proj = project_game(
        universe,
        home_team=home_team,
        away_team=away_team,
        week=week,
        season=season,
        neutral_site=neutral_site,
        night_game=night_game,
        engine_version=DEFAULT_SEASON_ENGINE_VERSION,
        player_hook_summaries=hook_rows,
        n_sims=n_sims,
        seed=seed,
    )
    return attach_player_projections(universe, proj)


def _preseason_prior_status(season: int, example_codes: Sequence[str]) -> Dict[str, Any]:
    from src.services.cfb_warehouse.preseason_prior import load_packaged_prior, lookup_prior

    pack = load_packaged_prior(int(season))
    examples = {code: lookup_prior(code, season=int(season)) for code in example_codes}
    return {
        "present": bool(pack.get("present")),
        "as_of": pack.get("as_of"),
        "n": pack.get("n"),
        "leakage": pack.get("leakage") or "seasons < prior_year",
        "used_in_spread": False,
        "examples": {k: v for k, v in examples.items() if v},
        "ops": "data/ops/cfb-p2-preseason-prior-20260813.md",
        "prior_version": pack.get("prior_version"),
        "universe": pack.get("universe"),
        "note": (
            "Neutral-field points vs average FBS + uncertainty σ. "
            "Research input on project-game; does not change spread/WP/KEI."
        ),
    }


def engine_status_payload(
    *,
    season: int = 2026,
    as_of_week: int = 1,
    demo: bool = True,
) -> Dict[str, Any]:
    """Honesty-first status contract for GET /cfb/season-engine/status."""
    from src.services.cfb_season_engine.fbs_universe import (
        documentation as fbs_doc,
        official_fbs_codes,
    )
    from src.services.cfb_season_engine.official_schedule import (
        documentation as official_schedule_doc,
    )

    try:
        universe, meta = resolve_season_universe(
            season=season, as_of_week=as_of_week, demo=demo, session=None
        )
    except Exception as exc:
        return {
            "ok": False,
            "engine_version": DEFAULT_SEASON_ENGINE_VERSION,
            "used_in_spread": False,
            "calibration_id": "cfb-margin-scale-v0.13-20260814",
            "calibration_as_of": "2026-08-14",
            "schedule_source": "missing",
            "schedule_as_of": "",
            "n_games": 0,
            "slate_complete": False,
            "error": str(exc),
            "backbone_version": BACKBONE_VERSION,
            "n_filled": 0,
            "n_thin": 0,
            "fbs_universe": fbs_doc(),
            "official_schedule": official_schedule_doc(),
            "preseason_prior": _preseason_prior_status(season, ["UGA", "OSU", "MICH", "FSU", "LSU"]),
            "season_futures": {
                "research_only": True,
                "cfp_make": None,
                "natty": None,
                "status": "placeholder",
            },
            "note": "Universe load failed; version + research prior still returned. No KEI.",
        }
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
    official = official_fbs_codes()
    official_in_universe = sorted(c for c in official if c in universe.teams)
    missing_official = sorted(c for c in official if c not in universe.teams)
    # Example team diagnostics — power continuity vs new-HC / weak HFA.
    example_codes = ["UGA", "TEX", "OSU", "LSU", "FSU", "PSU", "COLO", "BALL", "MIZZ"]
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
            "efficiency": efficiency_to_dict(state.efficiency),
            "home_field": profile_to_dict(state.home_field),
            "coaching": coaching_to_dict(state.coaching),
            "compose_notes": dict(state.notes),
        }

    ranked = sorted(
        (
            (code, t.roster.roster_strength if t.roster else 0.0)
            for code, t in universe.teams.items()
            if code in official
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
            if code in official
        ),
        key=lambda row: row[1],
        reverse=True,
    )
    power_style_ladder = []
    for i, (code, power, off, deff, roster_s, early_u) in enumerate(
        power_ranked[:40]
    ):
        st = universe.teams[code]
        power_style_ladder.append(
            {
                "rank": i + 1,
                "team": code,
                "power_index": round(power, 3),
                "offense_index": round(off, 3),
                "defense_index": round(deff, 3),
                "roster_strength": round(roster_s, 2),
                "off_eff": round(st.efficiency.off_eff, 2) if st.efficiency else None,
                "def_eff": round(st.efficiency.def_eff, 2) if st.efficiency else None,
                "sp_plus": round(st.efficiency.sp_plus, 2) if st.efficiency else None,
                "early_season_uncertainty": round(early_u, 3),
                "conference": universe.conferences.get(code, "Independent"),
            }
        )

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

    eff_meta = efficiency_snapshot_meta()
    return {
        "ok": True,
        "engine_version": DEFAULT_SEASON_ENGINE_VERSION,
        "used_in_spread": False,
        "sport": "cfb",
        "fbs_universe": fbs_doc(),
        "scope": (
            "FBS season sim + projection UI + ESPN 2026 real-roster overlay + "
            "variable HFA + coaching + v0.6.1 calibration + v0.7 player hooks + "
            "v0.8 opponent-adjusted efficiency backbone + v0.8.1 historical "
            "closing-line calibration + v0.8.2 performance tracking / CLV + "
            "v0.8.3 player coherence + v0.9 in-season updating foundation + "
            "v0.10 official-FBS preseason prior (research only) + "
            "v0.11 game/total sim distributions (research only) + "
            "v0.12 official 2026 ESPN slate + roster completeness (research only) + "
            "v0.13 margin calibration / blowout-scale (research only) + "
            "v0.14 warehouse efficiency backbone / SP+ fill reduction (research only)"
        ),
        "calibration_tag": priors_documentation().get("calibration_tag"),
        "calibration_id": __import__(
            "src.services.cfb_season_engine.margin_calibration",
            fromlist=["CALIBRATION_ID"],
        ).CALIBRATION_ID,
        "calibration_as_of": priors_documentation().get("calibration_as_of")
        or "2026-08-14",
        "historical_calibration": {
            "ops": "data/ops/cfb-historical-calibration-20260805.md",
            "artifacts": "data/ops/cfb-historical-calibration-20260805/",
            "script": "scripts/cfb/run_historical_calibration.py",
            "fidelity": "approximate_reconstruction",
        },
        "performance_tracking": {
            "ops": "data/ops/cfb-performance-tracking-20260805.md",
            "module": "src.services.cfb_season_engine.performance_tracking",
            "migration": "infra/db/049_cfb_performance_tracking.sql",
            "auto_log_env": "CFB_AUTO_LOG_PROJECTIONS",
            "fidelity": "live_paper_log",
        },
        "in_season_update": __import__(
            "src.services.cfb_season_engine.in_season_update", fromlist=["documentation"]
        ).documentation(),
        "mode": meta.get("mode"),
        "schedule_source": meta.get("schedule_source"),
        "schedule_as_of": meta.get("schedule_as_of") or universe.notes.get("schedule_as_of"),
        "n_games": meta.get("n_games") or meta.get("schedule_game_count"),
        "slate_complete": bool(meta.get("slate_complete")),
        "official_schedule": official_schedule_doc(),
        "schedule_game_count": meta.get("schedule_game_count"),
        "team_count": meta.get("team_count"),
        "roster_coverage_official": {
            "official_fbs": len(official),
            "in_universe": len(official_in_universe),
            "missing": missing_official,
            "independents": {
                "ND": "ND" in universe.teams,
                "CONN": "CONN" in universe.teams,
            },
            "as_of": meta.get("roster_as_of") or snap_meta.get("as_of"),
            "efficiency_league_avg_fill": sorted(
                c
                for c in official_in_universe
                if universe.teams[c].efficiency
                and universe.teams[c].efficiency.source == "league_average_fill"
            ),
            "efficiency_warehouse_fill": sorted(
                c
                for c in official_in_universe
                if universe.teams[c].efficiency
                and "warehouse" in str(universe.teams[c].efficiency.source or "")
            ),
            "efficiency_thin": sorted(
                c
                for c in official_in_universe
                if universe.teams[c].efficiency
                and universe.teams[c].efficiency.source == "thin_sample_labeled"
            ),
        },
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
            efficiency_documentation(),
            team_projection.documentation(),
            home_field.documentation(),
            coaching_continuity.documentation(),
            season_sim.documentation(),
            player_hooks.documentation(),
            official_schedule_doc(),
            __import__(
                "src.services.cfb_season_engine.margin_calibration",
                fromlist=["documentation"],
            ).documentation(),
        ],
        "efficiency": eff_meta,
        "backbone_version": eff_meta.get("backbone_version") or BACKBONE_VERSION,
        "n_filled": int(eff_meta.get("n_filled") or 0),
        "n_thin": int(eff_meta.get("n_thin") or 0),
        "efficiency_backbone": {
            "version": eff_meta.get("backbone_version"),
            "n_sp_plus": eff_meta.get("n_sp_plus"),
            "n_warehouse_fill": eff_meta.get("n_warehouse_fill"),
            "n_filled": eff_meta.get("n_filled"),
            "n_thin": eff_meta.get("n_thin"),
            "thin": eff_meta.get("thin") or [],
            "filled": eff_meta.get("filled") or [],
            "method": eff_meta.get("method"),
            "used_in_spread": False,
        },
        "priors": priors_documentation(),
        "early_season_narrowing": early_season_narrowing_schedule(),
        "schedule": schedule.documentation(),
        "conferences": conferences.documentation(),
        "project_game_formula": project_game_formula_doc(),
        "examples": examples,
        "preseason_prior": _preseason_prior_status(season, example_codes),
        "game_total_sim": __import__(
            "src.services.cfb_season_engine.game_total_sim",
            fromlist=["documentation"],
        ).documentation(),
        "market_diagnostic": __import__(
            "src.services.cfb_warehouse.market_diagnostic",
            fromlist=["documentation"],
        ).documentation(),
        "slate": {
            "official_2026_fbs_schedule": bool(meta.get("official_schedule")),
            "densified": not bool(meta.get("official_schedule")),
            "source": meta.get("schedule_source") or "packaged_sample_densified",
            "as_of": meta.get("schedule_as_of") or universe.notes.get("schedule_as_of"),
            "game_count": meta.get("schedule_game_count"),
            "n_games": meta.get("n_games") or meta.get("schedule_game_count"),
            "slate_complete": bool(meta.get("slate_complete")),
            "product_path": (
                "official_slate_season_sim"
                if meta.get("official_schedule")
                else "on_demand_project_game"
            ),
            "note": (
                "Official ESPN 2026 team schedules when packaged. Densified seed "
                "is never treated as official. project-game remains on-demand "
                "for arbitrary matchups. CFP/natty stay stub."
                if meta.get("official_schedule")
                else (
                    "Densified seed slate is not the official 2026 FBS schedule. "
                    "project-game(home, away, week, neutral?) is the research path."
                )
            ),
        },
        "season_futures": {
            "research_only": True,
            "cfp_make": None,
            "natty": None,
            "status": "placeholder",
            "thin_sample": True,
            "win_tables_final": False,
            "win_tables_status": (
                "research_limited"
                if meta.get("slate_complete")
                else "incomplete_slate_not_final"
            ),
            "note": (
                "CFP make / natty stay stub. Official slate unblocks limited "
                "research win totals only — not playoff percentages as product truth."
            ),
        },
        "qb_situation_overrides": __import__(
            "src.services.cfb_season_engine.qb_situation_overrides",
            fromlist=["documentation"],
        ).documentation(),
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
                "retained from curated priors; efficiency from final-2025 SP+ "
                "carry plus warehouse opponent-adj EPA overlay for official-FBS "
                "fills (success/explosiveness are proxies); "
                "HFA/coaching still curated; official ESPN 2026 slate when "
                "packaged (densified seed never labeled official)"
            ),
            "efficiency": efficiency_snapshot_meta(),
        },
        "solid_vs_approximate": {
            "solid": [
                "Layer module boundaries + composition feed order",
                "Roster strength formula (snap/start + portal net + recruiting + experience)",
                "QB situation classification rules + class offense multipliers",
                "Position group unit formula (talent/experience/portal_impact)",
                "Efficiency blend weights + anti-double-count unit downweight",
                "off_eff/def_eff + roster_strength + qb_situation_index as projection drivers",
                "Opponent-adjusted PBP EPA week snapshots (week W uses same-season week < W)",
                "Preseason prior mean+σ (seasons < Y; roster as_of 2026-08-12; not in spread)",
                "QB situation SoT overrides (camp/news; ESPN pack not silently rewritten)",
                "Packaged ESPN 2026 roster snapshot wiring (DB → snapshot → priors)",
                "Packaged final-2025 SP+ efficiency snapshot wiring",
                "Variable HFA bucket structure (baseline ~2 pts, elite→poor)",
                "Coaching continuity flags + week-decay schedule (HC/DC > OC)",
                "project-game two-path sim (strength→margin + separate total) + drivers block",
                "Early-season uncertainty posture (week-indexed narrowing, inspectable)",
                "Season-sim path coherence (wins dist, week sample, ranking)",
                "v0.6.1 calibration knobs (inspectable priors; measured, not market-grade)",
                "v0.7 player role-share allocation (QB + skill; team totals unchanged)",
                "v0.8.1 historical closing-line backtest framework + measured prior knobs",
                "v0.8.2 performance tracking log → close → result → summary (+ CLV)",
                "Official ESPN 2026 FBS slate packaging (not densified seed)",
                "API / CLI / status honesty contract",
                "Additive isolation from NFL engine + CFB markets-only Edge Board",
            ],
            "approximate": [
                "Returning snap/start shares (class-year proxies, not measured SNAP%)",
                "Portal-out values without a full departure feed",
                "QB talent scores derived from 2025 attempt/yard splits",
                "Position group talent composites from roster composition",
                "Prior-year SP+ efficiency carry (project-game still uses packaged SP+; PBP adj is research)",
                "Garbage-time weights + program-prior EPA→points scale (backtestable defaults)",
                "success_off/def + explosiveness (SP+-correlated proxies, not PBP rates)",
                "Recruiting capital when retained from curated priors",
                "HFA env_scores / venue labels (not live home ATS splits)",
                "Coaching staff change flags for 2026 (curated proxies)",
                "Densified schedule paths (fallback only; never labeled official)",
                "Conference affiliations for standings",
                "Game win probs / spreads / totals (hist-cal vs closes; not CLV/KEI)",
                "Historical reconstruction (league-avg roster/QB; prior-year ratings proxy)",
                "In-path strength evolution",
                "Season win totals / ranking-ish standings (research; not final if slate incomplete)",
                "Player yards/TDs/INTs (role shares of team pools; residual other OK)",
            ],
            "placeholder_or_deferred": [
                "Live DB portal / returning production tables (optional; snapshot ships in-image)",
                "Official preseason depth charts when ESPN publishes them",
                "Live home scoring-margin / ATS feed",
                "Live coaching-change feed",
                "Live weekly SP+ / CFBD advanced / full PBP EPA refresh",
                "True success-rate / iso-explosiveness from play-by-play",
                "Full night-game / weather model",
                "Special teams model (thin nudge only)",
                "Full player box-score engine (completions, routes, air yards)",
                "CFP / natty season futures (P4 stub — not product truth)",
                "Market-grade calibration / KEI fair lines",
                "2026 opens + held-out KEI design (post–Week 3; not shipped)",
                "Full portal player-value translation matrix",
                "Open camp QB battles (human review; not a single starter lock)",
            ],
        },
        "entry_points": {
            "status": "GET /cfb/season-engine/status",
            "project_game": "POST /cfb/season-engine/project-game",
            "simulate": "POST /cfb/season-engine/simulate",
            "projections_log": "POST /cfb/season-engine/projections/log",
            "projections_close": "POST /cfb/season-engine/projections/{id}/close",
            "projections_result": "POST /cfb/season-engine/projections/{id}/result",
            "performance": "GET /cfb/season-engine/performance",
            "cli": "scripts/cfb/run_hierarchical_season_sim.py",
            "package_roster": "scripts/cfb/package_real_roster_2026.py",
            "package_official_schedule": "scripts/cfb/package_official_schedule_2026.py",
            "fill_roster_holes": "scripts/cfb/fill_roster_holes_2026.py",
            "package_efficiency": "scripts/cfb/package_efficiency_2025_carry.py",
            "package_efficiency_backbone": "scripts/cfb/package_efficiency_backbone_2026.py",
            "historical_calibration": "scripts/cfb/run_historical_calibration.py",
            "ops": "data/ops/cfb-historical-calibration-20260805.md",
            "ops_performance": "data/ops/cfb-performance-tracking-20260805.md",
            "ops_efficiency": "data/ops/cfb-efficiency-backbone-20260804.md",
            "ops_efficiency_prior": "data/ops/cfb-efficiency-preseason-prior-v1-20260812.md",
            "ops_qb_honesty": "data/ops/cfb-qb-honesty-prior-20260812.md",
            "ops_p2_prior": "data/ops/cfb-p2-preseason-prior-20260813.md",
            "ops_p3_sim": "data/ops/cfb-p3-game-total-sim-20260813.md",
            "ops_slate_roster": "data/ops/cfb-2026-slate-roster-20260813.md",
            "ops_calibration_scale": "data/ops/cfb-calibration-scale-20260814.md",
            "ops_efficiency_backbone_v014": "data/ops/cfb-efficiency-backbone-20260814.md",
            "ops_market_diagnostic": "data/ops/cfb-market-diagnostic-20260814.md",
            "run_market_diagnostic": "scripts/cfb/run_market_diagnostic.py",
            "build_efficiency_prior": "scripts/cfb/build_efficiency_preseason_prior.py",
            "web_hub": "/pro/cfb/model",
            "web_project_game": "/pro/cfb/project-game",
            "web_slate": "/pro/cfb/slate",
            "web_projections": "/pro/cfb/projections",
            "web_teams": "/pro/cfb/teams",
            "ops_product_closeout": "data/ops/cfb-full-product-closeout-20260814.md",
        },
        "additive": True,
        "does_not_modify": [
            "edge_board_cfb_markets_only",
            "nfl_season_engine",
            "nfl_edge_board",
            "model_vs_kei_#70",
        ],
        "universe_notes": universe.notes,
        "desk": __import__(
            "src.services.cfb_season_engine.product_desk",
            fromlist=["product_desk_payload"],
        ).product_desk_payload(universe, weeks=(0, 1)),
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
