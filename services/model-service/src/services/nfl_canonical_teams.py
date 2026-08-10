"""Canonical NFL team IDs for Truth Layer joins.

Product / web canonical code for the Rams is ``LAR``. Engine / nflverse
often emit ``LA``. All boundary joins must normalize so LA never drops off
standings/futures/power boards.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Set, Tuple

# Product-facing 32-team set (Rams = LAR).
CANONICAL_TEAMS: Tuple[str, ...] = (
    "ARI",
    "ATL",
    "BAL",
    "BUF",
    "CAR",
    "CHI",
    "CIN",
    "CLE",
    "DAL",
    "DEN",
    "DET",
    "GB",
    "HOU",
    "IND",
    "JAX",
    "KC",
    "LAC",
    "LAR",
    "LV",
    "MIA",
    "MIN",
    "NE",
    "NO",
    "NYG",
    "NYJ",
    "PHI",
    "PIT",
    "SEA",
    "SF",
    "TB",
    "TEN",
    "WAS",
)

TEAM_ALIASES: Dict[str, str] = {
    "LA": "LAR",
    "LAR": "LAR",
    "WSH": "WAS",
    "WAS": "WAS",
    "JAC": "JAX",
    "JAX": "JAX",
    "STL": "LAR",
    "SD": "LAC",
    "OAK": "LV",
}

CONFERENCE_OF: Dict[str, str] = {
    "ARI": "NFC",
    "ATL": "NFC",
    "BAL": "AFC",
    "BUF": "AFC",
    "CAR": "NFC",
    "CHI": "NFC",
    "CIN": "AFC",
    "CLE": "AFC",
    "DAL": "NFC",
    "DEN": "AFC",
    "DET": "NFC",
    "GB": "NFC",
    "HOU": "AFC",
    "IND": "AFC",
    "JAX": "AFC",
    "KC": "AFC",
    "LAC": "AFC",
    "LAR": "NFC",
    "LV": "AFC",
    "MIA": "AFC",
    "MIN": "NFC",
    "NE": "AFC",
    "NO": "NFC",
    "NYG": "NFC",
    "NYJ": "AFC",
    "PHI": "NFC",
    "PIT": "AFC",
    "SEA": "NFC",
    "SF": "NFC",
    "TB": "NFC",
    "TEN": "AFC",
    "WAS": "NFC",
}

DIVISION_OF: Dict[str, str] = {
    "ARI": "West",
    "ATL": "South",
    "BAL": "North",
    "BUF": "East",
    "CAR": "South",
    "CHI": "North",
    "CIN": "North",
    "CLE": "North",
    "DAL": "East",
    "DEN": "West",
    "DET": "North",
    "GB": "North",
    "HOU": "South",
    "IND": "South",
    "JAX": "South",
    "KC": "West",
    "LAC": "West",
    "LAR": "West",
    "LV": "West",
    "MIA": "East",
    "MIN": "North",
    "NE": "East",
    "NO": "South",
    "NYG": "East",
    "NYJ": "East",
    "PHI": "East",
    "PIT": "North",
    "SEA": "West",
    "SF": "West",
    "TB": "South",
    "TEN": "South",
    "WAS": "East",
}


def canonicalize_team(code: Optional[str]) -> Optional[str]:
    if code is None:
        return None
    raw = str(code).strip().upper()
    if not raw:
        return None
    if raw in TEAM_ALIASES:
        return TEAM_ALIASES[raw]
    if raw in CONFERENCE_OF:
        return raw
    return raw


def division_label(team: str) -> str:
    canon = canonicalize_team(team) or team
    conf = CONFERENCE_OF.get(canon, "UNK")
    div = DIVISION_OF.get(canon, "UNK")
    return f"{conf} {div}"


def missing_canonical_teams(present: Iterable[str]) -> List[str]:
    have: Set[str] = set()
    for t in present:
        c = canonicalize_team(t)
        if c:
            have.add(c)
    return [t for t in CANONICAL_TEAMS if t not in have]
