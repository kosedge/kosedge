"""Compact CFB research-desk payloads (slate weeks + 136-team DNA).

Read-only. used_in_spread stays false. No KEI.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from src.services.cfb_season_engine.official_schedule import (
    games_from_blob,
    load_official_schedule_blob,
)
from src.services.cfb_season_engine.power_sot import build_power_sot
from src.services.cfb_season_engine.types import EngineUniverse

USED_IN_SPREAD = False


def official_week_board(
    weeks: Sequence[int] = (0, 1),
    *,
    season: int = 2026,
) -> Dict[str, Any]:
    blob = load_official_schedule_blob(season)
    wanted = {int(w) for w in weeks}
    games = [
        g
        for g in games_from_blob(blob, season=season)
        if int(g.week) in wanted
    ]
    rows = [
        {
            "week": g.week,
            "game_id": g.game_id,
            "home": g.home_team,
            "away": g.away_team,
            "kickoff": g.kickoff,
            "neutral_site": bool(g.neutral_site),
            "fcs_home": bool(g.fcs_home),
            "fcs_away": bool(g.fcs_away),
            "fbs_vs_fbs": (not g.fcs_home) and (not g.fcs_away),
            "conference_game": bool(g.conference_game),
        }
        for g in games
    ]
    return {
        "season": season,
        "weeks": sorted(wanted),
        "n_games": len(rows),
        "n_fbs_vs_fbs": sum(1 for r in rows if r["fbs_vs_fbs"]),
        "slate_complete": bool(blob.get("slate_complete")),
        "official": bool(blob.get("official")),
        "source": blob.get("source") or "packaged_official",
        "used_in_spread": USED_IN_SPREAD,
        "kei": False,
        "games": rows,
    }


def _next_opponent(
    code: str,
    board: Mapping[str, Any],
) -> Optional[Dict[str, Any]]:
    for row in board.get("games") or []:
        if row.get("home") == code:
            return {
                "week": row.get("week"),
                "opponent": row.get("away"),
                "home": True,
                "neutral_site": row.get("neutral_site"),
            }
        if row.get("away") == code:
            return {
                "week": row.get("week"),
                "opponent": row.get("home"),
                "home": False,
                "neutral_site": row.get("neutral_site"),
            }
    return None


def team_dna_table(
    universe: EngineUniverse,
    *,
    board: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """DNA rows are the Power SoT pack — no parallel rating."""
    sot = build_power_sot(universe)
    return {
        "n": sot["n_teams"],
        "official_fbs": sot["official_fbs"],
        "used_in_spread": USED_IN_SPREAD,
        "kei": False,
        "power_version": sot["power_version"],
        "power_as_of": sot["power_as_of"],
        "teams": sot["teams"],
    }


def product_desk_payload(
    universe: EngineUniverse,
    *,
    weeks: Iterable[int] = (0, 1),
) -> Dict[str, Any]:
    board = official_week_board(tuple(weeks))
    dna = team_dna_table(universe, board=board)
    return {
        "used_in_spread": USED_IN_SPREAD,
        "kei": False,
        "research_only": True,
        "week_board": board,
        "team_dna": dna,
    }
