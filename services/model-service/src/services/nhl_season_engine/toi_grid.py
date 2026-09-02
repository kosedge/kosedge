"""NHL Chapter 2 readers — TOI grid + goalie tandem.

Usage geometry only. Does not emit KEI. Does not retune NHL_TEAM_CARRY_SHRINK.
Does not rebase nhl_team_prior_2026.json.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.services.nhl_season_engine import priors as P

DATA_DIR = Path(__file__).resolve().parent / "data"
TOI_GRID_PATH = DATA_DIR / "nhl_toi_grid_2026.json"
GOALIE_TANDEM_PATH = DATA_DIR / "nhl_goalie_tandem_2026.json"

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


def load_toi_grid() -> Dict[str, Any]:
    return _load(TOI_GRID_PATH, "toi_grid")


def load_goalie_tandem() -> Dict[str, Any]:
    return _load(GOALIE_TANDEM_PATH, "goalie_tandem")


def get_team_toi(team: str) -> List[Dict[str, Any]]:
    pack = load_toi_grid()
    return list((pack.get("teams") or {}).get(str(team).upper()) or [])


def get_team_goalie_tandem(team: str) -> Optional[Dict[str, Any]]:
    pack = load_goalie_tandem()
    return (pack.get("teams") or {}).get(str(team).upper())


def documentation() -> Dict[str, Any]:
    grid = load_toi_grid()
    tandem = load_goalie_tandem()
    return {
        "module": "src.services.nhl_season_engine.toi_grid",
        "engine_version": P.ENGINE_VERSION,
        "PLAYER_YEAR_WEIGHTS": P.PLAYER_YEAR_WEIGHTS,
        "PLAYER_YEAR_WEIGHTS_BY_SEASON_ID": dict(P.PLAYER_YEAR_WEIGHTS_BY_SEASON_ID),
        "NHL_TOI_GRID_SKATER_MINUTES": P.NHL_TOI_GRID_SKATER_MINUTES,
        "NHL_GOALIE_TANDEM_SHARE_SUM": P.NHL_GOALIE_TANDEM_SHARE_SUM,
        "NHL_TEAM_CARRY_SHRINK_unchanged": P.NHL_TEAM_CARRY_SHRINK,
        "toi_grid_teams": len(grid.get("teams") or {}),
        "goalie_tandem_teams": len(tandem.get("teams") or {}),
        "paths": {
            "toi_grid": str(TOI_GRID_PATH),
            "goalie_tandem": str(GOALIE_TANDEM_PATH),
        },
        "does_not": [
            "emit KEI onto /edge-board/nhl",
            "fill blank KEINHL",
            "retune NHL_TEAM_CARRY_SHRINK",
            "rebase nhl_team_prior_2026.json",
            "xG from MoneyPuck/NST",
            "situation / Ch3",
            "copy NBA/WNBA minute grids",
            "CFB/NFL",
        ],
    }
