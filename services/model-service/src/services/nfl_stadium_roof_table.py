"""Explicit NFL stadium roof table — dome / retractable / outdoor.

Doctrine
--------
- Game-card ``roof`` comes from this table (or a venue override), never from notes.
- Do **not** invent wind=0 for outdoor venues.
- Retractable defaults to ``retractable_closed`` for KEI (indoor — weather not applied)
  unless an explicit open override is supplied.
- International / neutral venues use ``VENUE_ROOF_OVERRIDES`` by venue name.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

# Home-team default roof for the 2026 stadium map.
# Values must be parseable by ``nfl_rest_weather_game_card._norm_roof``.
NFL_STADIUM_ROOF: Dict[str, Dict[str, str]] = {
    "ARI": {
        "stadium": "State Farm Stadium",
        "roof": "retractable_closed",
        "roof_kind": "retractable",
    },
    "ATL": {
        "stadium": "Mercedes-Benz Stadium",
        "roof": "retractable_closed",
        "roof_kind": "retractable",
    },
    "BAL": {
        "stadium": "M&T Bank Stadium",
        "roof": "outdoor",
        "roof_kind": "outdoor",
    },
    "BUF": {
        "stadium": "Highmark Stadium",
        "roof": "outdoor",
        "roof_kind": "outdoor",
    },
    "CAR": {
        "stadium": "Bank of America Stadium",
        "roof": "outdoor",
        "roof_kind": "outdoor",
    },
    "CHI": {
        "stadium": "Soldier Field",
        "roof": "outdoor",
        "roof_kind": "outdoor",
    },
    "CIN": {
        "stadium": "Paycor Stadium",
        "roof": "outdoor",
        "roof_kind": "outdoor",
    },
    "CLE": {
        "stadium": "Huntington Bank Field",
        "roof": "outdoor",
        "roof_kind": "outdoor",
    },
    "DAL": {
        "stadium": "AT&T Stadium",
        "roof": "retractable_closed",
        "roof_kind": "retractable",
    },
    "DEN": {
        "stadium": "Empower Field at Mile High",
        "roof": "outdoor",
        "roof_kind": "outdoor",
    },
    "DET": {
        "stadium": "Ford Field",
        "roof": "dome",
        "roof_kind": "dome",
    },
    "GB": {
        "stadium": "Lambeau Field",
        "roof": "outdoor",
        "roof_kind": "outdoor",
    },
    "HOU": {
        "stadium": "NRG Stadium",
        "roof": "retractable_closed",
        "roof_kind": "retractable",
    },
    "IND": {
        "stadium": "Lucas Oil Stadium",
        "roof": "retractable_closed",
        "roof_kind": "retractable",
    },
    "JAX": {
        "stadium": "EverBank Stadium",
        "roof": "outdoor",
        "roof_kind": "outdoor",
    },
    "KC": {
        "stadium": "GEHA Field at Arrowhead Stadium",
        "roof": "outdoor",
        "roof_kind": "outdoor",
    },
    "LA": {
        "stadium": "SoFi Stadium",
        "roof": "outdoor",
        "roof_kind": "outdoor",
    },
    "LAC": {
        "stadium": "SoFi Stadium",
        "roof": "outdoor",
        "roof_kind": "outdoor",
    },
    "LAR": {
        "stadium": "SoFi Stadium",
        "roof": "outdoor",
        "roof_kind": "outdoor",
    },
    "LV": {
        "stadium": "Allegiant Stadium",
        "roof": "dome",
        "roof_kind": "dome",
    },
    "MIA": {
        "stadium": "Hard Rock Stadium",
        "roof": "outdoor",
        "roof_kind": "outdoor",
    },
    "MIN": {
        "stadium": "U.S. Bank Stadium",
        "roof": "dome",
        "roof_kind": "dome",
    },
    "NE": {
        "stadium": "Gillette Stadium",
        "roof": "outdoor",
        "roof_kind": "outdoor",
    },
    "NO": {
        "stadium": "Caesars Superdome",
        "roof": "dome",
        "roof_kind": "dome",
    },
    "NYG": {
        "stadium": "MetLife Stadium",
        "roof": "outdoor",
        "roof_kind": "outdoor",
    },
    "NYJ": {
        "stadium": "MetLife Stadium",
        "roof": "outdoor",
        "roof_kind": "outdoor",
    },
    "PHI": {
        "stadium": "Lincoln Financial Field",
        "roof": "outdoor",
        "roof_kind": "outdoor",
    },
    "PIT": {
        "stadium": "Acrisure Stadium",
        "roof": "outdoor",
        "roof_kind": "outdoor",
    },
    "SEA": {
        "stadium": "Lumen Field",
        "roof": "outdoor",
        "roof_kind": "outdoor",
    },
    "SF": {
        "stadium": "Levi's Stadium",
        "roof": "outdoor",
        "roof_kind": "outdoor",
    },
    "TB": {
        "stadium": "Raymond James Stadium",
        "roof": "outdoor",
        "roof_kind": "outdoor",
    },
    "TEN": {
        "stadium": "Nissan Stadium",
        "roof": "outdoor",
        "roof_kind": "outdoor",
    },
    "WAS": {
        "stadium": "Northwest Stadium",
        "roof": "outdoor",
        "roof_kind": "outdoor",
    },
}

# Neutral / international venues — keyed by canonical schedule ``venue`` string.
VENUE_ROOF_OVERRIDES: Dict[str, str] = {
    "Melbourne Cricket Ground": "outdoor",
    "Wembley Stadium": "outdoor",
    "Tottenham Hotspur Stadium": "outdoor",
    "Deutsche Bank Park": "outdoor",
    "Estadio Azteca": "outdoor",
    "Arena Corinthians": "outdoor",
}

# Optional lat/lon overrides for non-home venues (weather geo).
VENUE_GEO_OVERRIDES: Dict[str, Dict[str, float]] = {
    "Melbourne Cricket Ground": {"lat": -37.8199, "lon": 144.9834},
    "Wembley Stadium": {"lat": 51.5559, "lon": -0.2796},
    "Tottenham Hotspur Stadium": {"lat": 51.6043, "lon": -0.0663},
    "Deutsche Bank Park": {"lat": 50.0686, "lon": 8.6455},
    "Estadio Azteca": {"lat": 19.3029, "lon": -99.1505},
}


def _norm_team(abbr: Any) -> str:
    token = str(abbr or "").strip().upper()
    if token in {"LAR", "LA"}:
        return "LA"
    if token == "AZ":
        return "ARI"
    if token == "WSH":
        return "WAS"
    if token == "JAC":
        return "JAX"
    return token


def stadium_row_for_team(home: str) -> Optional[Dict[str, str]]:
    """Return a copy of the home-team stadium row, or None if unknown."""
    code = _norm_team(home)
    # Prefer LA over LAR alias when both exist (same SoFi row).
    row = NFL_STADIUM_ROOF.get(code) or NFL_STADIUM_ROOF.get("LAR" if code == "LA" else "")
    if not row:
        return None
    return dict(row)


def resolve_roof(
    *,
    home: str,
    venue: Optional[str] = None,
    roof_override: Optional[str] = None,
) -> Optional[str]:
    """Resolve game-card roof from venue override → explicit override → stadium table.

    Never invents outdoor wind; missing table row → None (weather treated as missing).
    """
    if roof_override is not None and str(roof_override).strip():
        return str(roof_override).strip().lower()
    venue_name = str(venue or "").strip()
    if venue_name and venue_name in VENUE_ROOF_OVERRIDES:
        return VENUE_ROOF_OVERRIDES[venue_name]
    row = stadium_row_for_team(home)
    if not row:
        return None
    return str(row.get("roof") or "").strip().lower() or None


def resolve_venue_geo(
    *,
    home: str,
    venue: Optional[str] = None,
    team_geo: Optional[Mapping[str, Mapping[str, float]]] = None,
) -> Optional[Dict[str, float]]:
    """Lat/lon for weather fetch. Venue override wins; else home stadium geo."""
    venue_name = str(venue or "").strip()
    if venue_name and venue_name in VENUE_GEO_OVERRIDES:
        geo = VENUE_GEO_OVERRIDES[venue_name]
        return {"lat": float(geo["lat"]), "lon": float(geo["lon"])}
    code = _norm_team(home)
    geo_map = team_geo
    if geo_map is None:
        try:
            from src.services.nfl_environment import TEAM_HOME_GEO

            geo_map = TEAM_HOME_GEO
        except Exception:
            return None
    # TEAM_HOME_GEO keys LAR for Rams; LAC separate; engine often uses LA.
    row = geo_map.get(code) or geo_map.get("LAR" if code == "LA" else "")
    if not row:
        return None
    try:
        return {"lat": float(row["lat"]), "lon": float(row["lon"])}
    except (KeyError, TypeError, ValueError):
        return None
