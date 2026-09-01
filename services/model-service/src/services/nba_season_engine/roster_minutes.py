"""NBA Chapter 2 readers — talent, minutes grid, rebased team prior."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.services.nba_season_engine import priors as P

DATA_DIR = Path(__file__).resolve().parent / "data"
TALENT_PATH = DATA_DIR / "nba_player_talent_3y_2026.json"
GRID_PATH = DATA_DIR / "nba_minutes_grid_2026.json"
REBASED_PATH = DATA_DIR / "nba_team_prior_rebased_2026_27.json"
TX_PATH = DATA_DIR / "nba_transactions_2026.json"

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


def load_transactions() -> Dict[str, Any]:
    return _load(TX_PATH, "tx")


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
        "module": "src.services.nba_season_engine.roster_minutes",
        "engine_version": P.ENGINE_VERSION,
        "PLAYER_YEAR_WEIGHTS": P.PLAYER_YEAR_WEIGHTS,
        "MINUTE_GRID_SUM": P.MINUTE_GRID_SUM,
        "TEAM_REBASE_RESIDUAL_CAP": P.TEAM_REBASE_RESIDUAL_CAP,
        "TEAM_CARRY_SHRINK_unchanged": P.TEAM_CARRY_SHRINK,
        "talent_players": talent.get("player_count"),
        "grid_teams": len(grid.get("teams") or {}),
        "rebased_teams": rebased.get("team_count"),
        "paths": {
            "talent": str(TALENT_PATH),
            "minutes_grid": str(GRID_PATH),
            "rebased": str(REBASED_PATH),
            "transactions": str(TX_PATH),
        },
        "does_not": [
            "emit KEI / Edge PLAY/LEAN",
            "props / fantasy scorer",
            "change TEAM_CARRY_SHRINK",
            "situation / B2B (Ch3)",
            "DARKO/EPM/CTG",
            "props desk / Edge tags (Ch6)",
        ],
    }
