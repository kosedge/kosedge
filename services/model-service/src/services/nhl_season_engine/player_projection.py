"""NHL Chapter 5 — PlayerProjection reader (skater + goalie).

Opening-night means from Ch2 TOI × decayed box rates (skaters) and
Ch2 tandem × SV% (goalies). Team Σ G identity-scaled to Ch1 GF/G within
NHL_TEAM_REBASE_RESIDUAL_CAP. No board emit, no props tags, no new TOI grid.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.services.nhl_season_engine import priors as P

DATA_DIR = Path(__file__).resolve().parent / "data"
PACK_PATH = DATA_DIR / "nhl_player_projection_2026.json"

SKATER_VECTOR_KEYS = ("TOI_EV", "TOI_PP", "G", "A", "P", "SOG")
GOALIE_VECTOR_KEYS = ("start_share", "SV_pct", "SA", "GAA", "SAVES")

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


def get_skater_projection(team: str, player_id: str) -> Optional[Dict[str, Any]]:
    pack = load_player_projection_pack()
    key = f"{str(team).upper()}:{player_id}"
    return (pack.get("skaters") or {}).get(key)


def get_goalie_projection(team: str, player_id: str) -> Optional[Dict[str, Any]]:
    pack = load_player_projection_pack()
    key = f"{str(team).upper()}:{player_id}"
    return (pack.get("goalies") or {}).get(key)


def get_team_skaters(team: str) -> List[Dict[str, Any]]:
    pack = load_player_projection_pack()
    t = str(team).upper()
    rows = [
        row
        for key, row in (pack.get("skaters") or {}).items()
        if key.startswith(f"{t}:") or row.get("team") == t
    ]
    rows.sort(
        key=lambda r: (
            -float(r.get("TOI_EV") or 0) - float(r.get("TOI_PP") or 0),
            str(r.get("player_name") or ""),
        )
    )
    return rows


def get_team_goalies(team: str) -> List[Dict[str, Any]]:
    pack = load_player_projection_pack()
    t = str(team).upper()
    rows = [
        row
        for key, row in (pack.get("goalies") or {}).items()
        if key.startswith(f"{t}:") or row.get("team") == t
    ]
    rows.sort(key=lambda r: (-float(r.get("start_share") or 0), str(r.get("player_name") or "")))
    return rows


def team_g_identity(team: str) -> Dict[str, float]:
    pack = load_player_projection_pack()
    checks = (pack.get("team_checks") or {}).get(str(team).upper()) or {}
    return {
        "sum_g": float(checks.get("sum_g") or 0),
        "target_gf_pg": float(checks.get("target_gf_pg") or 0),
        "g_drift": float(checks.get("g_drift") or 0),
        "sum_toi": float(checks.get("sum_toi") or 0),
        "sum_start_share": float(checks.get("sum_start_share") or 0),
        "residual_cap": float(
            checks.get("residual_cap")
            or pack.get("NHL_TEAM_REBASE_RESIDUAL_CAP")
            or P.NHL_TEAM_REBASE_RESIDUAL_CAP
        ),
    }


def documentation() -> Dict[str, Any]:
    pack = load_player_projection_pack()
    return {
        "module": "src.services.nhl_season_engine.player_projection",
        "engine_version": P.ENGINE_VERSION,
        "object": "PlayerProjection",
        "NHL_TEAM_REBASE_RESIDUAL_CAP": P.NHL_TEAM_REBASE_RESIDUAL_CAP,
        "NHL_TOI_GRID_SKATER_MINUTES": P.NHL_TOI_GRID_SKATER_MINUTES,
        "NHL_GOALIE_TANDEM_SHARE_SUM": P.NHL_GOALIE_TANDEM_SHARE_SUM,
        "PLAYER_YEAR_WEIGHTS": P.PLAYER_YEAR_WEIGHTS,
        "NHL_TEAM_CARRY_SHRINK_unchanged": P.NHL_TEAM_CARRY_SHRINK,
        "skater_vector_keys": list(SKATER_VECTOR_KEYS),
        "goalie_vector_keys": list(GOALIE_VECTOR_KEYS),
        "skater_count": pack.get("skater_count"),
        "goalie_count": pack.get("goalie_count"),
        "path": str(PACK_PATH),
        "does_not": pack.get("does_not")
        or [
            "fill KEINHL / board emit",
            "props PLAY",
            "new TOI grid",
            "MoneyPuck as the mean",
            "team if",
            "changing 0.85",
            "NBA/WNBA/CFB/NFL",
        ],
    }
