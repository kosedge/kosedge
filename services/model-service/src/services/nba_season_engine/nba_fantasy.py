"""NBA Chapter 7 — fantasy from PlayerProjection (same object as props).

fantasy_pts = f(PTS, REB, AST, STL, BLK, TOV, 3PM)  # one published scoring map
cats        = the same vector, unweighted

No new scorer. No props tags. No minute-grid rewrite.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.services.nba_season_engine import priors as P
from src.services.nba_season_engine.player_projection import (
    load_player_projection_pack,
    team_pts_identity,
)

FANTASY_VERSION = "nba-fantasy-ch7-v1"
SCORING_PROFILE = "kos_default_points"

# Published scoring map (Yahoo-style H2H points analog to NFL fantasy_points_from_projection).
# Documented in docs/NBA_CH7_FANTASY_BRIEF.md — do not invent a second set of means.
SCORING_MAP = {
    "PTS": 1.0,
    "REB": 1.2,
    "AST": 1.5,
    "STL": 3.0,
    "BLK": 3.0,
    "TOV": -1.0,
    "3PM": 0.5,
}

CAT_KEYS = ("PTS", "REB", "AST", "STL", "BLK", "TOV", "3PM")
SEASON_GAMES = 82  # opening-night season total = per-game × 82
MIN_MINUTES = 1.0  # include any Ch5 slot with minutes (opening-night grid)


def fantasy_points_from_projection(
    *,
    pts: float,
    reb: float,
    ast: float,
    stl: float,
    blk: float,
    tov: float,
    threes: float,
    scoring_map: Optional[Dict[str, float]] = None,
) -> float:
    """Score one PlayerProjection vector. NFL analog: fantasy_points_from_projection."""
    m = scoring_map or SCORING_MAP
    return round(
        float(pts) * float(m["PTS"])
        + float(reb) * float(m["REB"])
        + float(ast) * float(m["AST"])
        + float(stl) * float(m["STL"])
        + float(blk) * float(m["BLK"])
        + float(tov) * float(m["TOV"])
        + float(threes) * float(m["3PM"]),
        4,
    )


def cats_from_projection(player: Dict[str, Any]) -> Dict[str, float]:
    """Same vector, unweighted — category board."""
    return {k: round(float(player.get(k) or 0.0), 4) for k in CAT_KEYS}


def row_from_player(player: Dict[str, Any]) -> Dict[str, Any]:
    cats = cats_from_projection(player)
    fp = fantasy_points_from_projection(
        pts=cats["PTS"],
        reb=cats["REB"],
        ast=cats["AST"],
        stl=cats["STL"],
        blk=cats["BLK"],
        tov=cats["TOV"],
        threes=cats["3PM"],
    )
    return {
        "player_id": str(player.get("player_id") or ""),
        "player_name": str(player.get("player_name") or ""),
        "team": str(player.get("team") or "").upper(),
        "role": player.get("role"),
        "MIN": round(float(player.get("MIN") or 0.0), 4),
        "USG": round(float(player.get("USG") or 0.0), 4),
        **cats,
        "fantasy_pts": fp,
        "season_fantasy_pts": round(fp * SEASON_GAMES, 2),
        "projection_source": "player_projection_ch5",
        "scoring_profile": SCORING_PROFILE,
    }


def build_fantasy_board(
    *,
    view: str = "season",
    team: Optional[str] = None,
    limit: int = 250,
) -> Dict[str, Any]:
    """Season ranks or slate view — same players, same Ch5 means, sorted by fantasy_pts."""
    pack = load_player_projection_pack()
    if not pack.get("present"):
        return {
            "present": False,
            "fantasy_version": FANTASY_VERSION,
            "count": 0,
            "rows": [],
            "message": "PlayerProjection pack missing — Ch5 required",
        }

    team_filter = (team or "").strip().upper() or None
    view_key = (view or "season").strip().lower()
    if view_key not in {"season", "slate"}:
        view_key = "season"

    rows: List[Dict[str, Any]] = []
    for player in (pack.get("players") or {}).values():
        mins = float(player.get("MIN") or 0.0)
        if mins < MIN_MINUTES:
            continue
        tk = str(player.get("team") or "").upper()
        if team_filter and tk != team_filter:
            continue
        rows.append(row_from_player(player))

    rows.sort(
        key=lambda r: (
            -float(r.get("fantasy_pts") or 0),
            -float(r.get("MIN") or 0),
            str(r.get("player_name") or ""),
        )
    )
    for i, r in enumerate(rows, start=1):
        r["rank"] = i

    rows = rows[: max(1, int(limit))]

    # Team Σ PTS identity still within residual cap (Ch5 gate).
    max_drift = 0.0
    for t, checks in (pack.get("team_checks") or {}).items():
        drift = abs(float((checks or {}).get("pts_drift") or 0.0))
        if drift > max_drift:
            max_drift = drift

    return {
        "present": True,
        "fantasy_version": FANTASY_VERSION,
        "engine_version": pack.get("engine_version") or P.ENGINE_VERSION,
        "object": "PlayerProjection",
        "scoring_profile": SCORING_PROFILE,
        "scoring_map": dict(SCORING_MAP),
        "cat_keys": list(CAT_KEYS),
        "season_games": SEASON_GAMES,
        "view": view_key,
        "TEAM_CARRY_SHRINK_unchanged": P.TEAM_CARRY_SHRINK,
        "TEAM_REBASE_RESIDUAL_CAP": P.TEAM_REBASE_RESIDUAL_CAP,
        "max_team_pts_drift": round(max_drift, 6),
        "count": len(rows),
        "rows": rows,
        "does_not": [
            "new PTS/REB/AST means",
            "minute-grid rewrite",
            "props PLAY/LEAN",
            "DFS lineup optimizer",
            "team if",
            "Ch3/Ch4 retune",
            "CFB/NFL",
        ],
    }


def documentation() -> Dict[str, Any]:
    return {
        "module": "src.services.nba_season_engine.nba_fantasy",
        "fantasy_version": FANTASY_VERSION,
        "scoring_profile": SCORING_PROFILE,
        "scoring_map": dict(SCORING_MAP),
        "cat_keys": list(CAT_KEYS),
        "season_games": SEASON_GAMES,
        "reads": "PlayerProjection (Ch5)",
        "analog": "nfl_player_projection_engine.fantasy_points_from_projection",
        "does_not": [
            "new means",
            "props tags",
            "DFS optimizer",
            "CFB/NFL",
        ],
    }
