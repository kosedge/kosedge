"""NHL Chapter 1 — team prior shell reader.

Formula:
  team' = league_mean + NHL_TEAM_CARRY_SHRINK * (team_2025_26 - league_mean)

Reads pack SoT only. Does not emit KEI onto /edge-board/nhl.
Does not invent xG or player tables.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from src.services.nhl_season_engine import priors as P

DATA_DIR = Path(__file__).resolve().parent / "data"
PACK_PATH = DATA_DIR / "nhl_team_prior_2026.json"
TEAM_BOX_PATH = DATA_DIR / "nhl_team_box_2025.json"

_CACHE: Optional[Dict[str, Any]] = None


def pack_path() -> Path:
    return PACK_PATH


def team_box_path() -> Path:
    return TEAM_BOX_PATH


def load_team_prior_pack(*, force: bool = False) -> Dict[str, Any]:
    global _CACHE
    if _CACHE is not None and not force:
        return _CACHE
    if not PACK_PATH.is_file():
        _CACHE = {"present": False, "teams": {}, "engine_version": P.ENGINE_VERSION}
        return _CACHE
    raw = json.loads(PACK_PATH.read_text(encoding="utf-8"))
    raw["present"] = True
    _CACHE = raw
    return raw


def clear_team_prior_cache() -> None:
    global _CACHE
    _CACHE = None


def apply_nhl_team_carry_shrink(
    value: float,
    league_mean: float,
    *,
    shrink: Optional[float] = None,
) -> float:
    s = float(P.NHL_TEAM_CARRY_SHRINK if shrink is None else shrink)
    return float(league_mean) + s * (float(value) - float(league_mean))


def get_team_prior(team: str) -> Optional[Dict[str, Any]]:
    pack = load_team_prior_pack()
    teams = pack.get("teams") or {}
    return teams.get(str(team).upper())


def documentation() -> Dict[str, Any]:
    pack = load_team_prior_pack()
    return {
        "module": "src.services.nhl_season_engine.team_prior",
        "engine_version": pack.get("engine_version") or P.ENGINE_VERSION,
        "NHL_TEAM_CARRY_SHRINK": P.NHL_TEAM_CARRY_SHRINK,
        "season": pack.get("season"),
        "carry_to_season": pack.get("carry_to_season"),
        "team_count": pack.get("team_count") or len(pack.get("teams") or {}),
        "path": str(PACK_PATH),
        "present": bool(pack.get("present")),
        "does_not": [
            "emit KEI onto /edge-board/nhl",
            "fill blank KEINHL",
            "xG from MoneyPuck/NST",
            "new player / skater-goalie tables",
            "situation layer",
            "reuse NBA/WNBA TEAM_CARRY_SHRINK",
            "CFB/NFL",
        ],
    }
