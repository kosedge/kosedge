"""Official 2026 FBS universe (full members + transitioning).

This is the team-list lock for the preseason prior. The official 2026
game slate lives in ``official_schedule`` (ESPN team schedules), not the
densified sample seed.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from src.services.cfb_warehouse.identity import canonical_code

DATA_DIR = Path(__file__).resolve().parent / "data"
UNIVERSE_PATH = DATA_DIR / "cfb_fbs_universe_2026.json"

# FCS / alias codes that must never enter the 2026 prior as FBS.
NON_FBS_CODES = frozenset(
    {
        "ACU",
        "CHAT",
        "IDHO",
        "FAY",
        "SOUTH",
        "FAU2",
        "OLE",
        "OREST",
        "TA&M",
        "TXAM",
        "ULL",
    }
)


@lru_cache(maxsize=1)
def load_fbs_universe(season: int = 2026) -> Dict[str, Any]:
    if not UNIVERSE_PATH.is_file():
        return {
            "present": False,
            "season": int(season),
            "teams": {},
            "transitioning": {},
            "n_fbs_full": 0,
        }
    raw = json.loads(UNIVERSE_PATH.read_text(encoding="utf-8"))
    raw["present"] = True
    return raw


def official_fbs_codes(*, include_transition: bool = False) -> frozenset[str]:
    book = load_fbs_universe()
    codes = {canonical_code(c) for c in (book.get("teams") or {})}
    if include_transition:
        codes |= {canonical_code(c) for c in (book.get("transitioning") or {})}
    return frozenset(codes)


def is_official_fbs(team: str, *, include_transition: bool = False) -> bool:
    code = canonical_code(team)
    if not code or code in NON_FBS_CODES:
        return False
    return code in official_fbs_codes(include_transition=include_transition)


def membership_row(team: str) -> Optional[Dict[str, Any]]:
    book = load_fbs_universe()
    code = canonical_code(team)
    row = (book.get("teams") or {}).get(code)
    if row:
        return {"team_id": code, **row}
    row = (book.get("transitioning") or {}).get(code)
    if row:
        return {"team_id": code, **row}
    return None


def fcs_or_unknown_label(team: str) -> str:
    code = canonical_code(team)
    excluded = (load_fbs_universe().get("excluded_from_prior") or {}).get(code)
    if excluded:
        return str(excluded)
    row = membership_row(code)
    if row and row.get("membership") == "fbs_transition":
        return (
            "FBS transition (not full member). Separate strength prior later — "
            "do not treat as generic -25."
        )
    if code.startswith("fcs:") or not is_official_fbs(code, include_transition=True):
        return "FCS / non-FBS — keep historical games; do not treat as generic -25."
    return ""


def documentation() -> Dict[str, Any]:
    book = load_fbs_universe()
    return {
        "module": "src.services.cfb_season_engine.fbs_universe",
        "path": str(UNIVERSE_PATH),
        "as_of": book.get("as_of"),
        "source": book.get("source"),
        "n_fbs_full": book.get("n_fbs_full"),
        "n_fbs_transition": book.get("n_fbs_transition"),
        "independents": book.get("independents"),
        "notes": book.get("notes"),
        "is_official_slate": False,
    }
