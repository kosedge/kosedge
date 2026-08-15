"""Compact CFB research-desk payloads (W0/W1 slate + optional team DNA).

Read-only. used_in_spread stays false. No KEI.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

USED_IN_SPREAD = False
DATA_DIR = Path(__file__).resolve().parent / "data"
OFFICIAL_SCHEDULE_PATH = DATA_DIR / "cfb_official_schedule_2026.json"
FBS_UNIVERSE_PATH = DATA_DIR / "cfb_fbs_universe_2026.json"


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    return raw if isinstance(raw, dict) else {}


def official_fbs_codes() -> List[str]:
    book = _load_json(FBS_UNIVERSE_PATH)
    teams = book.get("teams") or {}
    if isinstance(teams, dict):
        return sorted(str(k).upper() for k in teams.keys())
    if isinstance(teams, list):
        return sorted(str(t).upper() for t in teams)
    return []


def official_week_board(
    weeks: Sequence[int] = (0, 1),
    *,
    season: int = 2026,
) -> Dict[str, Any]:
    blob = _load_json(OFFICIAL_SCHEDULE_PATH)
    wanted = {int(w) for w in weeks}
    rows: List[Dict[str, Any]] = []
    for raw in blob.get("games") or []:
        if not isinstance(raw, dict):
            continue
        try:
            week = int(raw.get("week"))
        except (TypeError, ValueError):
            continue
        if week not in wanted:
            continue
        home = str(raw.get("home") or raw.get("home_team") or "").upper()
        away = str(raw.get("away") or raw.get("away_team") or "").upper()
        if not home or not away or home == away:
            continue
        fcs_home = bool(raw.get("fcs_home"))
        fcs_away = bool(raw.get("fcs_away"))
        rows.append(
            {
                "week": week,
                "game_id": raw.get("game_id"),
                "home": home,
                "away": away,
                "kickoff": raw.get("kickoff") or raw.get("date"),
                "neutral_site": bool(raw.get("neutral_site")),
                "fcs_home": fcs_home,
                "fcs_away": fcs_away,
                "fbs_vs_fbs": (not fcs_home) and (not fcs_away),
                "conference_game": bool(raw.get("conference_game")),
            }
        )
    return {
        "season": season,
        "weeks": sorted(wanted),
        "n_games": len(rows),
        "n_fbs_vs_fbs": sum(1 for r in rows if r["fbs_vs_fbs"]),
        "slate_complete": bool(blob.get("slate_complete", True) and rows),
        "official": bool(blob.get("official", True) and rows),
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
    universe: Any = None,
    *,
    board: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    official = official_fbs_codes()
    board = board if board is not None else official_week_board()
    teams = getattr(universe, "teams", None) or {}
    conferences = getattr(universe, "conferences", None) or {}
    rows: List[Dict[str, Any]] = []
    for code in official:
        st = teams.get(code) if hasattr(teams, "get") else None
        qb = getattr(st, "qb", None) if st is not None else None
        eff = getattr(st, "efficiency", None) if st is not None else None
        src = str(getattr(eff, "source", "") or "") if eff is not None else ""
        fill = (
            "warehouse"
            if "warehouse" in src
            else (
                "thin"
                if src == "thin_sample_labeled"
                else ("league_avg" if src == "league_average_fill" else "sp_plus_or_packaged")
            )
        )
        off = getattr(st, "offense_index", None) if st is not None else None
        deff = getattr(st, "defense_index", None) if st is not None else None
        rows.append(
            {
                "team": code,
                "conference": conferences.get(code) if hasattr(conferences, "get") else None,
                "offense_index": round(off, 3) if isinstance(off, (int, float)) else None,
                "defense_index": round(deff, 3) if isinstance(deff, (int, float)) else None,
                "power_index": (
                    round(0.5 * (off + deff), 3)
                    if isinstance(off, (int, float)) and isinstance(deff, (int, float))
                    else None
                ),
                "early_season_uncertainty": (
                    round(st.early_season_uncertainty, 3)
                    if st is not None and isinstance(getattr(st, "early_season_uncertainty", None), (int, float))
                    else None
                ),
                "qb_class": getattr(qb, "qb_class", None) if qb is not None else None,
                "qb_name": getattr(qb, "starter_name", None) if qb is not None else None,
                "open_qb": bool(qb is not None and getattr(qb, "qb_class", None) == "open_competition"),
                "efficiency_source": src or None,
                "efficiency_fill": fill if st is not None else None,
                "off_eff": round(eff.off_eff, 2) if eff is not None and hasattr(eff, "off_eff") else None,
                "def_eff": round(eff.def_eff, 2) if eff is not None and hasattr(eff, "def_eff") else None,
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
    universe: Any = None,
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
