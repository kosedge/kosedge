"""Assemble Phase 1 measurement artifacts. Research only."""

from __future__ import annotations

from typing import Any, Dict, List, Sequence

from src.services.ke_football import PIPELINE_VERSION, PRODUCTION_PROMOTE, TAXONOMY
from src.services.ke_football.aggregate import (
    build_team_games,
    filter_week_lt,
    snapshots_for_week,
)
from src.services.ke_football.disruption import inventory_report
from src.services.ke_football.finishing import finishing_diagnosis
from src.services.ke_football.opp_adj import adjust_league
from src.services.ke_football.plays import CanonicalPlay
from src.services.ke_football.validation import (
    missingness,
    next_game_epa,
    provenance_audit,
    ranking_sanity,
    week_to_week_stability,
)


def run_measurement(
    plays: Sequence[CanonicalPlay],
    *,
    sport: str,
    season: int,
    as_of_week: int,
    example_teams: Sequence[str] | None = None,
) -> Dict[str, Any]:
    window = filter_week_lt(plays, season=season, as_of_week=as_of_week)
    # ADJUSTED target drops OT; DERIVED snapshots keep OT (spec).
    derived_plays = window
    adj_plays = [p for p in window if not p.overtime]
    derived_games = build_team_games(derived_plays)
    adj_games = build_team_games(adj_plays)
    snaps = snapshots_for_week(derived_plays, sport=sport, season=season, as_of_week=as_of_week)
    adj = adjust_league(adj_games, as_of_week=as_of_week)
    adj_by_team = {row["team"]: row for row in adj}
    for snap in snaps:
        extra = adj_by_team.get(snap["team"])
        if extra:
            snap["components"].update(extra["components"])
            snap["opp_adj"] = {
                "n_adjusted_games": extra["n_adjusted_games"],
                "n_skipped_no_opp_book": extra["n_skipped_no_opp_book"],
                "method": extra["method"],
            }

    weeks = sorted({g.week for g in derived_games})
    by_week: Dict[int, List[Dict[str, Any]]] = {}
    for w in weeks:
        # snapshots as_of w+1 use weeks <= w i.e. week < w+1
        by_week[w + 1] = snapshots_for_week(
            derived_plays, sport=sport, season=season, as_of_week=w + 1
        )

    examples = []
    wanted = list(example_teams or [])
    if not wanted:
        ranked = ranking_sanity(snaps, k=3)
        wanted = [r["team"] for r in ranked["best_offense"][:3]] + [
            r["team"] for r in ranked["worst_offense"][:2]
        ]
        wanted += [r["team"] for r in ranked["best_defense"][:2]]
    seen = set()
    for team in wanted:
        if team in seen:
            continue
        seen.add(team)
        snap = next((s for s in snaps if s["team"] == team), None)
        if snap:
            examples.append(_example_card(snap, derived_games))

    return {
        "pipeline_version": PIPELINE_VERSION,
        "production_promote": PRODUCTION_PROMOTE,
        "taxonomy": list(TAXONOMY),
        "sport": sport,
        "season": season,
        "as_of_week": as_of_week,
        "n_plays_window": len(window),
        "n_team_games": len(derived_games),
        "n_snapshots": len(snaps),
        "snapshots": snaps,
        "examples": examples,
        "disruption_inventory": inventory_report(sport=sport, plays=window),
        "finishing_diagnosis": finishing_diagnosis(window) if sport == "nfl" else None,
        "validation": {
            "next_game_epa": next_game_epa(adj_games),
            "stability_off": week_to_week_stability(by_week, component_id="ke.off_eff"),
            "stability_def": week_to_week_stability(by_week, component_id="ke.def_eff"),
            "ranking_sanity": ranking_sanity(snaps),
            "missingness": missingness(snaps),
            "provenance": provenance_audit(snaps),
        },
        "hard_stops": {
            "team_strength": False,
            "scoring": False,
            "matchup": False,
            "market": False,
            "ui": False,
            "issue_562_tuning": False,
        },
    }


def _example_card(snap: Dict[str, Any], games: Sequence[Any]) -> Dict[str, Any]:
    team = snap["team"]
    mine = [g for g in games if g.team == team]
    comps = snap.get("components") or {}
    keep = [
        "ke.off_eff",
        "ke.def_eff",
        "ke.success_native",
        "ke.success_standard",
        "ke.pace",
        "ke.pace_competitive",
        "ke.expl",
        "ke.expl_pass",
        "ke.expl_rush",
        "ke.expl_allowed",
        "ke.off_pass_epa",
        "ke.off_rush_epa",
        "ke.off_early_epa",
        "ke.ppo",
        "ke.finish",
        "ke.opp_rate",
        "ke.rz_td",
        "ke.st",
        "ke.havoc",
        "ke.disruption_proxy_nfl",
        "ke.disruption_sack",
        "ke.disruption_interception",
        "ke.disruption_tfl",
        "ke.disruption_fumble_forced",
        "ke.opp_adj_epa.off",
        "ke.opp_adj_epa.def",
        "ke.team_strength",
    ]
    return {
        "team": team,
        "n_games": snap.get("n_games"),
        "opponents": snap.get("opponents"),
        "components": {k: comps[k] for k in keep if k in comps},
        "team_games": [
            {
                "week": g.week,
                "game_id": g.game_id,
                "opponent": g.opponent,
                "off_epa": g.off_epa,
                "def_epa": g.def_epa,
                "n_off": g.off_epa_n,
                "n_def": g.def_epa_n,
                "pace": g.n_off_plays,
                "ppo": (g.opp_points / g.n_opp) if g.n_opp else None,
                "expl": (g.expl_n / g.expl_d) if g.expl_d else None,
            }
            for g in sorted(mine, key=lambda x: x.week)
        ],
    }
