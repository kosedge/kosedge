"""WNBA Chapter 7 — fantasy from PlayerProjection (same object as props).

fantasy_pts = f(PTS, REB, AST, STL, BLK, TOV, 3PM)  # one published scoring map
cats        = the same vector, unweighted

No new scorer. No props tags. No minute-grid rewrite.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.services.wnba_season_engine import priors as P
from src.services.wnba_season_engine.player_projection import (
    load_player_projection_pack,
)

FANTASY_VERSION = "wnba-fantasy-ch7-v1"
SCORING_PROFILE = "kos_default_points"

# Published scoring map — same weights as NBA Ch7 / NFL analog.
# Documented in docs/WNBA_CH7_FANTASY_BRIEF.md — do not invent a second set of means.
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
SEASON_GAMES = 40  # WNBA RS length; season total = per-game × 40
MIN_MINUTES = 1.0


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
    """Score one PlayerProjection vector. Same map as NBA Ch7 / NFL analog."""
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

    max_drift = 0.0
    for _t, checks in (pack.get("team_checks") or {}).items():
        drift = abs(float((checks or {}).get("pts_drift") or 0.0))
        if drift > max_drift:
            max_drift = drift

    # Σ MIN identity from pack (Ch2 grid 200) — team_checks uses sum_min.
    minute_grid_ok = True
    team_checks = pack.get("team_checks") or {}
    if team_checks:
        for _t, checks in team_checks.items():
            mins_sum = float(
                (checks or {}).get("sum_min")
                or (checks or {}).get("minutes_sum")
                or (checks or {}).get("min_sum")
                or 0.0
            )
            if abs(mins_sum - float(P.MINUTE_GRID_SUM)) > 1e-3:
                minute_grid_ok = False
                break
    else:
        from collections import defaultdict

        sums: Dict[str, float] = defaultdict(float)
        for pl in (pack.get("players") or {}).values():
            sums[str(pl.get("team") or "").upper()] += float(pl.get("MIN") or 0.0)
        minute_grid_ok = all(
            abs(v - float(P.MINUTE_GRID_SUM)) < 1e-3 for v in sums.values() if v > 0
        )

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
        "WNBA_TEAM_CARRY_SHRINK_unchanged": P.WNBA_TEAM_CARRY_SHRINK,
        "WNBA_TEAM_REBASE_RESIDUAL_CAP": P.WNBA_TEAM_REBASE_RESIDUAL_CAP,
        "MINUTE_GRID_SUM_unchanged": P.MINUTE_GRID_SUM,
        "minute_grid_ok": minute_grid_ok,
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
            "NBA/CFB/NFL",
            "15 team previews",
            "Ch9 grades schema (later)",
        ],
    }


def documentation() -> Dict[str, Any]:
    return {
        "module": "src.services.wnba_season_engine.wnba_fantasy",
        "fantasy_version": FANTASY_VERSION,
        "scoring_profile": SCORING_PROFILE,
        "scoring_map": dict(SCORING_MAP),
        "cat_keys": list(CAT_KEYS),
        "season_games": SEASON_GAMES,
        "reads": "PlayerProjection (Ch5)",
        "analog": "nba_fantasy.fantasy_points_from_projection",
        "does_not": [
            "new means",
            "props tags",
            "DFS optimizer",
            "NBA/CFB/NFL",
        ],
    }
