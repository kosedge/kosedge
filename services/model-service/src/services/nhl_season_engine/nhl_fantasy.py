"""NHL Chapter 7 — fantasy from PlayerProjection (same object as props).

fantasy_pts = f(G, A, SOG[, SAVES])  # one published scoring map
cats        = the same vector, unweighted

Skaters score G/A/SOG. Goalies score SAVES (map includes saves; no W in Ch5).
No new scorer. No props tags. No new TOI / G/A/SOG means.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.services.nhl_season_engine import priors as P
from src.services.nhl_season_engine.player_projection import load_player_projection_pack

FANTASY_VERSION = "nhl-fantasy-ch7-v1"
SCORING_PROFILE = "kos_default_points"

# Published Yahoo-style NHL points analog (NFL/NBA Ch7 kos_default_points family).
# P is display-only (G+A) — never weighted. No W in Ch5 → no invented wins.
SCORING_MAP = {
    "G": 3.0,
    "A": 2.0,
    "SOG": 0.4,
    "SAVES": 0.2,
}

SKATER_CAT_KEYS = ("G", "A", "P", "SOG")
GOALIE_CAT_KEYS = ("start_share", "SV_pct", "SA", "GAA", "SAVES")
SEASON_GAMES = 82  # opening-night season total = per-game × 82
MIN_TOI = 1.0  # include any Ch5 skater slot with meaningful ice


def fantasy_points_skater(
    *,
    g: float,
    a: float,
    sog: float,
    scoring_map: Optional[Dict[str, float]] = None,
) -> float:
    """Score one Ch5 skater vector. Does not weight P (G+A)."""
    m = scoring_map or SCORING_MAP
    return round(
        float(g) * float(m["G"])
        + float(a) * float(m["A"])
        + float(sog) * float(m["SOG"]),
        4,
    )


def fantasy_points_goalie(
    *,
    saves: float,
    scoring_map: Optional[Dict[str, float]] = None,
) -> float:
    """Score one Ch5 goalie vector — SAVES only (no W in PlayerProjection)."""
    m = scoring_map or SCORING_MAP
    return round(float(saves) * float(m["SAVES"]), 4)


def fantasy_points_from_projection(
    *,
    g: float = 0.0,
    a: float = 0.0,
    sog: float = 0.0,
    saves: float = 0.0,
    player_type: str = "skater",
    scoring_map: Optional[Dict[str, float]] = None,
) -> float:
    """Unified entry — skater G/A/SOG or goalie SAVES."""
    if str(player_type).lower() == "goalie":
        return fantasy_points_goalie(saves=saves, scoring_map=scoring_map)
    return fantasy_points_skater(g=g, a=a, sog=sog, scoring_map=scoring_map)


def row_from_skater(player: Dict[str, Any]) -> Dict[str, Any]:
    g = round(float(player.get("G") or 0.0), 4)
    a = round(float(player.get("A") or 0.0), 4)
    p = round(float(player.get("P") or (g + a)), 4)
    sog = round(float(player.get("SOG") or 0.0), 4)
    toi_ev = round(float(player.get("TOI_EV") or 0.0), 4)
    toi_pp = round(float(player.get("TOI_PP") or 0.0), 4)
    fp = fantasy_points_skater(g=g, a=a, sog=sog)
    return {
        "player_id": str(player.get("player_id") or ""),
        "player_name": str(player.get("player_name") or ""),
        "team": str(player.get("team") or "").upper(),
        "player_type": "skater",
        "position": player.get("position"),
        "role": player.get("role") or player.get("position"),
        "TOI_EV": toi_ev,
        "TOI_PP": toi_pp,
        "TOI": round(toi_ev + toi_pp, 4),
        "G": g,
        "A": a,
        "P": p,
        "SOG": sog,
        "start_share": None,
        "SV_pct": None,
        "SA": None,
        "GAA": None,
        "SAVES": None,
        "fantasy_pts": fp,
        "season_fantasy_pts": round(fp * SEASON_GAMES, 2),
        "projection_source": "player_projection_ch5",
        "scoring_profile": SCORING_PROFILE,
    }


def row_from_goalie(player: Dict[str, Any]) -> Dict[str, Any]:
    saves = round(float(player.get("SAVES") or 0.0), 4)
    fp = fantasy_points_goalie(saves=saves)
    return {
        "player_id": str(player.get("player_id") or ""),
        "player_name": str(player.get("player_name") or ""),
        "team": str(player.get("team") or "").upper(),
        "player_type": "goalie",
        "position": "G",
        "role": player.get("role") or "goalie",
        "TOI_EV": None,
        "TOI_PP": None,
        "TOI": None,
        "G": None,
        "A": None,
        "P": None,
        "SOG": None,
        "start_share": round(float(player.get("start_share") or 0.0), 6),
        "SV_pct": round(float(player.get("SV_pct") or 0.0), 6),
        "SA": round(float(player.get("SA") or 0.0), 4),
        "GAA": round(float(player.get("GAA") or 0.0), 4),
        "SAVES": saves,
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
    include_goalies: bool = True,
) -> Dict[str, Any]:
    """Season ranks or slate view — same Ch5 means, sorted by fantasy_pts."""
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
    for player in (pack.get("skaters") or {}).values():
        toi = float(player.get("TOI_EV") or 0.0) + float(player.get("TOI_PP") or 0.0)
        if toi < MIN_TOI:
            continue
        tk = str(player.get("team") or "").upper()
        if team_filter and tk != team_filter:
            continue
        rows.append(row_from_skater(player))

    if include_goalies:
        for player in (pack.get("goalies") or {}).values():
            tk = str(player.get("team") or "").upper()
            if team_filter and tk != team_filter:
                continue
            # Listed from Ch5 goalie vector; scored via SAVES (not as skaters).
            rows.append(row_from_goalie(player))

    rows.sort(
        key=lambda r: (
            -float(r.get("fantasy_pts") or 0),
            -float(r.get("TOI") or r.get("start_share") or 0),
            str(r.get("player_name") or ""),
        )
    )
    for i, r in enumerate(rows, start=1):
        r["rank"] = i

    rows = rows[: max(1, int(limit))]

    max_g_drift = 0.0
    start_share_ok = True
    for _t, checks in (pack.get("team_checks") or {}).items():
        drift = abs(float((checks or {}).get("g_drift") or 0.0))
        if drift > max_g_drift:
            max_g_drift = drift
        share = float((checks or {}).get("sum_start_share") or 0.0)
        if abs(share - 1.0) > 1e-6:
            start_share_ok = False

    return {
        "present": True,
        "fantasy_version": FANTASY_VERSION,
        "engine_version": pack.get("engine_version") or P.ENGINE_VERSION,
        "object": "PlayerProjection",
        "scoring_profile": SCORING_PROFILE,
        "scoring_map": dict(SCORING_MAP),
        "skater_cat_keys": list(SKATER_CAT_KEYS),
        "goalie_cat_keys": list(GOALIE_CAT_KEYS),
        "season_games": SEASON_GAMES,
        "view": view_key,
        "NHL_TEAM_CARRY_SHRINK_unchanged": P.NHL_TEAM_CARRY_SHRINK,
        "NHL_TEAM_REBASE_RESIDUAL_CAP": P.NHL_TEAM_REBASE_RESIDUAL_CAP,
        "max_team_g_drift": round(max_g_drift, 6),
        "goalie_start_share_ok": start_share_ok,
        "STARTER_GATE_unchanged": P.STARTER_GATE,
        "count": len(rows),
        "rows": rows,
        "does_not": [
            "new G/A/SOG means",
            "new TOI",
            "props PLAY/LEAN",
            "DFS lineup optimizer",
            "team if",
            "Ch3/Ch4 retune",
            "NBA/WNBA/CFB/NFL",
            "invented goalie wins",
        ],
    }


def documentation() -> Dict[str, Any]:
    return {
        "module": "src.services.nhl_season_engine.nhl_fantasy",
        "fantasy_version": FANTASY_VERSION,
        "scoring_profile": SCORING_PROFILE,
        "scoring_map": dict(SCORING_MAP),
        "skater_cat_keys": list(SKATER_CAT_KEYS),
        "goalie_cat_keys": list(GOALIE_CAT_KEYS),
        "season_games": SEASON_GAMES,
        "reads": "PlayerProjection (Ch5)",
        "analog": "nba_fantasy / nfl fantasy_points_from_projection",
        "does_not": [
            "new means",
            "props tags",
            "DFS optimizer",
            "NBA/WNBA/CFB/NFL",
        ],
    }
