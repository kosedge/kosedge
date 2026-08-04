"""Approximate 2026 FBS conference affiliations (packaged, not official feed).

Used for densified schedule pairing preference and optional conference
standings in season_sim. Fidelity is intentionally approximate — realignments
and missing codes fall through to ``Independent``.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Mapping

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
}


@lru_cache(maxsize=1)
def load_conference_map() -> Dict[str, str]:
    if PACKAGED_CONFERENCES.exists():
        raw = json.loads(PACKAGED_CONFERENCES.read_text(encoding="utf-8"))
        teams = raw.get("teams") or {}
        return {str(k).upper(): str(v) for k, v in teams.items()}
    return dict(_FALLBACK)


def conference_for(team: str, mapping: Mapping[str, str] | None = None) -> str:
    m = mapping if mapping is not None else load_conference_map()
    return str(m.get(str(team).upper(), "Independent"))


def documentation() -> Dict[str, Any]:
    return {
        "module": "src.services.cfb_season_engine.conferences",
        "packaged": str(PACKAGED_CONFERENCES),
        "fidelity": "approximate",
        "note": (
            "Packaged affiliation map for schedule densify + optional conference "
            "standings. Not an official realignment feed."
        ),
    }
