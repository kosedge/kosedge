"""Compact CFB research-desk payloads (slate weeks + 136-team DNA).

Read-only. used_in_spread stays false. No KEI.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from src.services.cfb_season_engine.conferences import conference_for
from src.services.cfb_season_engine.fbs_universe import official_fbs_codes
from src.services.cfb_season_engine.official_schedule import (
    games_from_blob,
    load_official_schedule_blob,
)
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
    official = official_fbs_codes()
    board = board if board is not None else official_week_board()
    rows: List[Dict[str, Any]] = []
    for code in official:
        st = universe.teams.get(code)
        qb = st.qb if st else None
        eff = st.efficiency if st else None
        src = str(eff.source or "") if eff else ""
        fill = "warehouse" if "warehouse" in src else (
            "thin" if src == "thin_sample_labeled" else (
                "league_avg" if src == "league_average_fill" else "sp_plus_or_packaged"
            )
        )
        rows.append(
            {
                "team": code,
                "conference": universe.conferences.get(code) or conference_for(code),
                "offense_index": round(st.offense_index, 3) if st else None,
                "defense_index": round(st.defense_index, 3) if st else None,
                "power_index": (
                    round(0.5 * (st.offense_index + st.defense_index), 3)
                    if st
                    else None
                ),
                "early_season_uncertainty": (
                    round(st.early_season_uncertainty, 3) if st else None
                ),
                "qb_class": qb.qb_class if qb else None,
                "qb_name": qb.starter_name if qb else None,
                "open_qb": bool(qb and qb.qb_class == "open_competition"),
                "efficiency_source": src or None,
                "efficiency_fill": fill,
                "off_eff": round(eff.off_eff, 2) if eff else None,
                "def_eff": round(eff.def_eff, 2) if eff else None,
                "next": _next_opponent(code, board),
            }
        )
    return {
        "n": len(rows),
        "official_fbs": len(official),
        "used_in_spread": USED_IN_SPREAD,
        "kei": False,
        "teams": rows,
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
