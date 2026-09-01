"""WNBA Chapter 5 — PlayerProjection reader (single scorer).

Opening-night means from Ch2 minutes × decayed box rates × team pace.
Team Σ PTS identity-scaled to Ch2 implied_ppg within WNBA_TEAM_REBASE_RESIDUAL_CAP.
No board emit, no props tags, no new minute grid, no NBA means.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.services.wnba_season_engine import priors as P

DATA_DIR = Path(__file__).resolve().parent / "data"
PACK_PATH = DATA_DIR / "wnba_player_projection_2026.json"

VECTOR_KEYS = (
    "MIN",
    "USG",
    "PTS",
    "REB",
    "AST",
    "STL",
    "BLK",
    "TOV",
    "3PM",
    "PRA",
    "PR",
    "RA",
)

_CACHE: Dict[str, Any] = {}


def clear_ch5_cache() -> None:
    _CACHE.clear()


def load_player_projection_pack(force: bool = False) -> Dict[str, Any]:
    if not force and "pack" in _CACHE:
        return _CACHE["pack"]
    if not PACK_PATH.is_file():
        out = {"present": False}
        _CACHE["pack"] = out
        return out
    raw = json.loads(PACK_PATH.read_text(encoding="utf-8"))
    raw["present"] = True
    _CACHE["pack"] = raw
    return raw


def get_player_projection(team: str, player_id: str) -> Optional[Dict[str, Any]]:
    pack = load_player_projection_pack()
    key = f"{str(team).upper()}:{player_id}"
    return (pack.get("players") or {}).get(key)


def get_team_projections(team: str) -> List[Dict[str, Any]]:
    pack = load_player_projection_pack()
    t = str(team).upper()
    rows = [
        row
        for key, row in (pack.get("players") or {}).items()
        if key.startswith(f"{t}:") or row.get("team") == t
    ]
    rows.sort(
        key=lambda r: (-float(r.get("MIN") or 0), str(r.get("player_name") or ""))
    )
    return rows


def team_pts_identity(team: str) -> Dict[str, float]:
    pack = load_player_projection_pack()
    checks = (pack.get("team_checks") or {}).get(str(team).upper()) or {}
    return {
        "sum_pts": float(checks.get("sum_pts") or 0),
        "target_pts": float(checks.get("target_pts") or 0),
        "pts_drift": float(checks.get("pts_drift") or 0),
        "sum_min": float(checks.get("sum_min") or 0),
        "residual_cap": float(
            checks.get("residual_cap")
            or pack.get("WNBA_TEAM_REBASE_RESIDUAL_CAP")
            or P.WNBA_TEAM_REBASE_RESIDUAL_CAP
        ),
    }


def documentation() -> Dict[str, Any]:
    pack = load_player_projection_pack()
    return {
        "module": "src.services.wnba_season_engine.player_projection",
        "engine_version": P.ENGINE_VERSION,
        "object": "PlayerProjection",
        "WNBA_TEAM_REBASE_RESIDUAL_CAP": P.WNBA_TEAM_REBASE_RESIDUAL_CAP,
        "MINUTE_GRID_SUM": P.MINUTE_GRID_SUM,
        "PLAYER_YEAR_WEIGHTS": P.PLAYER_YEAR_WEIGHTS,
        "WNBA_TEAM_CARRY_SHRINK_unchanged": P.WNBA_TEAM_CARRY_SHRINK,
        "vector_keys": list(VECTOR_KEYS),
        "player_count": pack.get("player_count"),
        "path": str(PACK_PATH),
        "does_not": pack.get("does_not")
        or [
            "board emit",
            "props / PLAY / LEAN",
            "new minute grid",
            "NBA means as the prior",
            "team if",
            "changing 0.85",
            "Aug 1 leftover KEI blend",
            "NBA/CFB/NFL packs",
        ],
    }
