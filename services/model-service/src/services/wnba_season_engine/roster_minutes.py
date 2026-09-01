"""WNBA Chapter 2 readers — talent, minutes grid, rebased team prior."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.services.wnba_season_engine import priors as P

DATA_DIR = Path(__file__).resolve().parent / "data"
TALENT_PATH = DATA_DIR / "wnba_player_talent_3y_2026.json"
GRID_PATH = DATA_DIR / "wnba_minutes_grid_2026.json"
REBASED_PATH = DATA_DIR / "wnba_team_prior_rebased_2026.json"

_CACHE: Dict[str, Any] = {}


def _load(path: Path, key: str) -> Dict[str, Any]:
    if key in _CACHE:
        return _CACHE[key]
    if not path.is_file():
        _CACHE[key] = {"present": False}
        return _CACHE[key]
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["present"] = True
    _CACHE[key] = raw
    return raw


def clear_ch2_cache() -> None:
    _CACHE.clear()


def load_player_talent_pack() -> Dict[str, Any]:
    return _load(TALENT_PATH, "talent")


def load_minutes_grid() -> Dict[str, Any]:
    return _load(GRID_PATH, "grid")


def load_rebased_team_prior() -> Dict[str, Any]:
    return _load(REBASED_PATH, "rebased")


def get_rebased_team(team: str) -> Optional[Dict[str, Any]]:
    pack = load_rebased_team_prior()
    return (pack.get("teams") or {}).get(str(team).upper())


def get_team_minutes(team: str) -> List[Dict[str, Any]]:
    pack = load_minutes_grid()
    return list((pack.get("teams") or {}).get(str(team).upper()) or [])


def documentation() -> Dict[str, Any]:
    talent = load_player_talent_pack()
    grid = load_minutes_grid()
    rebased = load_rebased_team_prior()
    return {
        "module": "src.services.wnba_season_engine.roster_minutes",
        "engine_version": P.ENGINE_VERSION,
        "PLAYER_YEAR_WEIGHTS": P.PLAYER_YEAR_WEIGHTS,
        "MINUTE_GRID_SUM": P.MINUTE_GRID_SUM,
        "WNBA_TEAM_REBASE_RESIDUAL_CAP": P.WNBA_TEAM_REBASE_RESIDUAL_CAP,
        "WNBA_TEAM_CARRY_SHRINK_unchanged": P.WNBA_TEAM_CARRY_SHRINK,
        "talent_players": talent.get("player_count"),
        "grid_teams": len(grid.get("teams") or {}),
        "rebased_teams": rebased.get("team_count"),
        "paths": {
            "talent": str(TALENT_PATH),
            "minutes_grid": str(GRID_PATH),
            "rebased": str(REBASED_PATH),
        },
        "does_not": [
            "emit KEI onto /edge-board/wnba",
            "props / Edge PLAY/LEAN",
            "change WNBA_TEAM_CARRY_SHRINK",
            "copy NBA minute classes as-is",
            "blend Aug-1 leftover fair-lines 401857105/401857106",
            "NBA/CFB/NFL packs",
        ],
    }
