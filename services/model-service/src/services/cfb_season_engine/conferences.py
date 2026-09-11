"""Approximate 2026 FBS conference affiliations (packaged, not official feed).

Used for densified schedule pairing preference and optional conference
standings in season_sim. Official FBS codes must resolve from the packaged
map or the FBS universe. Missing required affiliations fail closed — they
do not silently become Independent.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from src.services.cfb_season_engine.fbs_universe import (
    is_official_fbs,
    membership_row,
)
from src.services.cfb_season_engine.team_features import MissingRequiredTeamFeature

DATA_DIR = Path(__file__).resolve().parent / "data"
PACKAGED_CONFERENCES = DATA_DIR / "cfb_fbs_conferences_2026.json"

# Compact fallback if JSON missing — covers Power + major G5 cores only.
_FALLBACK: Dict[str, str] = {
    # SEC
    "ALA": "SEC",
    "ARK": "SEC",
    "AUB": "SEC",
    "UF": "SEC",
    "UGA": "SEC",
    "UK": "SEC",
    "LSU": "SEC",
    "MISS": "SEC",
    "MSST": "SEC",
    "MIZZ": "SEC",
    "OU": "SEC",
    "SCAR": "SEC",
    "TENN": "SEC",
    "TEX": "SEC",
    "TAMU": "SEC",
    "TXAM": "SEC",
    "TA&M": "SEC",
    "VAN": "SEC",
    "OLE": "SEC",
    # Big Ten
    "ILL": "Big Ten",
    "IU": "Big Ten",
    "IOWA": "Big Ten",
    "MD": "Big Ten",
    "MICH": "Big Ten",
    "MSU": "Big Ten",
    "MINN": "Big Ten",
    "NEB": "Big Ten",
    "NW": "Big Ten",
    "OSU": "Big Ten",
    "ORE": "Big Ten",
    "PSU": "Big Ten",
    "PUR": "Big Ten",
    "RUT": "Big Ten",
    "UCLA": "Big Ten",
    "USC": "Big Ten",
    "WASH": "Big Ten",
    "WIS": "Big Ten",
    # ACC
    "BC": "ACC",
    "CAL": "ACC",
    "CLEM": "ACC",
    "DUKE": "ACC",
    "FSU": "ACC",
    "GT": "ACC",
    "LOU": "ACC",
    "MIA": "ACC",
    "UNC": "ACC",
    "NCSU": "ACC",
    "PITT": "ACC",
    "SMU": "ACC",
    "STAN": "ACC",
    "SYR": "ACC",
    "UVA": "ACC",
    "VT": "ACC",
    "WAKE": "ACC",
    # Big 12
    "ARI": "Big 12",
    "ASU": "Big 12",
    "BAY": "Big 12",
    "BYU": "Big 12",
    "CIN": "Big 12",
    "COLO": "Big 12",
    "HOU": "Big 12",
    "ISU": "Big 12",
    "KU": "Big 12",
    "KSU": "Big 12",
    "OKST": "Big 12",
    "TCU": "Big 12",
    "TTU": "Big 12",
    "UCF": "Big 12",
    "UTAH": "Big 12",
    "WVU": "Big 12",
    # Independents / others commonly packaged
    "ND": "Independent",
    "ARMY": "Independent",
    "CONN": "Independent",
    "UMASS": "Independent",
    "MASS": "Independent",
    # P0 leftover Independents — 2026 affiliation (FBS universe SoT)
    "MIZZ": "SEC",
    "ARST": "Sun Belt",
    "CSU": "Pac-12",
    "ECU": "AAC",
    "JVST": "CUSA",
    "NEV": "Mountain West",
    "ODU": "Sun Belt",
    "TOL": "MAC",
    "UAB": "AAC",
    "UNM": "Mountain West",
    "UNT": "AAC",
}


@lru_cache(maxsize=1)
def load_conference_map() -> Dict[str, str]:
    if PACKAGED_CONFERENCES.exists():
        raw = json.loads(PACKAGED_CONFERENCES.read_text(encoding="utf-8"))
        teams = raw.get("teams") or {}
        return {str(k).upper(): str(v) for k, v in teams.items()}
    return dict(_FALLBACK)


def _universe_conference(code: str) -> Optional[str]:
    row = membership_row(code)
    if not row:
        return None
    conf = str(row.get("conference") or "").strip()
    return conf or None


def conference_for(team: str, mapping: Mapping[str, str] | None = None) -> str:
    """Resolve affiliation. Official FBS never silently becomes Independent."""
    code = str(team or "").upper()
    m = mapping if mapping is not None else load_conference_map()
    mapped = m.get(code)
    universe_conf = _universe_conference(code)
    official = is_official_fbs(code, include_transition=True)

    if mapped and mapped != "Independent":
        return str(mapped)
    if mapped == "Independent" and universe_conf and universe_conf != "Independent":
        # Leftover Independent packaging — restore the universe affiliation.
        return universe_conf
    if mapped:
        return str(mapped)
    if universe_conf:
        return universe_conf
    if official:
        raise MissingRequiredTeamFeature(
            f"Official FBS {code} missing conference affiliation — "
            "sit, do not invent Independent"
        )
    # FCS / non-FBS only. Not an official-FBS Independent.
    return "Independent"


def documentation() -> Dict[str, Any]:
    return {
        "module": "src.services.cfb_season_engine.conferences",
        "packaged": str(PACKAGED_CONFERENCES),
        "fidelity": "approximate",
        "note": (
            "Packaged affiliation map for schedule densify + optional conference "
            "standings. Official FBS missing a conference fail closed. "
            "Not an official realignment feed."
        ),
    }
