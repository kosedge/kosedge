"""Week 1 fair-lines game cards — venue / kickoff SoT for KEI chips.

Railway model-service image does **not** ship ``apps/web``; canonical overlay
paths that walk to the monorepo root therefore miss Melbourne. This module:

1. Loads packaged schedule + any in-tree canonical JSON under model-service.
2. Always injects baked Week 1 international sites (Melbourne SF@LAR, …).
3. Indexes cards the same way the fair-lines route looks them up:
   ``(home_abbr, away_abbr)`` with LA↔LAR aliases (LA → LAR product key).

Tests must call :func:`build_week1_game_cards` + :func:`lookup_week1_game_card`
with API keys (``LAR``, ``SF``) — never hand-set ``_international`` after the fact.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Tuple

# Baked international Week 1 sites — fail-closed when schedule JSON is missing
# on the Railway image. Keys use product abbrs (LAR not LA).
WEEK1_INTERNATIONAL_SITES: Tuple[Dict[str, Any], ...] = (
    {
        "home_abbr": "LAR",
        "away_abbr": "SF",
        "venue": "Melbourne Cricket Ground",
        "location": "Melbourne",
        "kickoff_utc": "2026-09-11T00:35:00.000Z",
        "international": True,
    },
)

_INTERNATIONAL_LOCATIONS = {
    "melbourne",
    "london",
    "rio de janeiro",
    "munich",
    "mexico city",
    "sao paulo",
    "frankfurt",
    "paris",
    "madrid",
}


def _norm_product_abbr(abbr: Any) -> str:
    """Match fair-lines ``_nfl_team_to_abbr`` product keys (LA → LAR)."""
    token = str(abbr or "").strip().upper()
    if not token:
        return ""
    if token == "LA":
        return "LAR"
    if token == "WSH":
        return "WAS"
    if token == "JAC":
        return "JAX"
    if token == "AZ":
        return "ARI"
    return token


def _is_international_site(*, venue: Any, location: Any) -> bool:
    loc = str(location or "").strip().lower()
    ven = str(venue or "").strip().lower()
    if loc in _INTERNATIONAL_LOCATIONS:
        return True
    return any(
        token in ven
        for token in (
            "cricket",
            "wembley",
            "tottenham",
            "maracan",
            "bernabeu",
            "bernabéu",
            "stade de france",
            "bayern",
        )
    )


def _empty_card(*, roof: str = "outdoor") -> Dict[str, Any]:
    return {
        "days_rest_home": None,
        "days_rest_away": None,
        "short_week": None,
        "timezone_shift": 0.0,
        "roof": roof,
        "wind_mph": None,
        "precip": None,
        "temp_f": None,
    }


def _with_venue(
    card: Mapping[str, Any],
    *,
    venue: str,
    location: str,
    international: bool,
) -> Dict[str, Any]:
    out = dict(card)
    out["_venue"] = str(venue)
    out["_location"] = str(location)
    out["_international"] = bool(international)
    return out


@dataclass
class Week1GameCardIndex:
    cards: Dict[Tuple[str, str], Dict[str, Any]] = field(default_factory=dict)
    kickoffs: Dict[Tuple[str, str], str] = field(default_factory=dict)
    source: str = "missing"
    errors: List[str] = field(default_factory=list)

    def lookup(self, home_abbr: Any, away_abbr: Any) -> Optional[Dict[str, Any]]:
        home = _norm_product_abbr(home_abbr)
        away = _norm_product_abbr(away_abbr)
        if not home or not away:
            return None
        return self.cards.get((home, away))

    def kickoff_for(self, home_abbr: Any, away_abbr: Any) -> Optional[str]:
        home = _norm_product_abbr(home_abbr)
        away = _norm_product_abbr(away_abbr)
        return self.kickoffs.get((home, away))


def _store(
    index: Week1GameCardIndex,
    *,
    home_abbr: Any,
    away_abbr: Any,
    card: Mapping[str, Any],
    kickoff_utc: Optional[str] = None,
) -> None:
    home = _norm_product_abbr(home_abbr)
    away = _norm_product_abbr(away_abbr)
    if not home or not away:
        return
    payload = dict(card)
    index.cards[(home, away)] = payload
    # LA ↔ LAR alias (API emits LAR; packaged schedule often LA).
    if home == "LAR":
        index.cards[("LA", away)] = payload
    if kickoff_utc:
        ko = str(kickoff_utc)
        index.kickoffs[(home, away)] = ko
        if home == "LAR":
            index.kickoffs[("LA", away)] = ko


def _inject_baked_international(index: Week1GameCardIndex) -> int:
    injected = 0
    for site in WEEK1_INTERNATIONAL_SITES:
        home = site["home_abbr"]
        away = site["away_abbr"]
        existing = index.lookup(home, away)
        venue = str(site["venue"])
        location = str(site["location"])
        kickoff = str(site.get("kickoff_utc") or "") or None
        if existing is not None and existing.get("_international"):
            if kickoff and not index.kickoff_for(home, away):
                _store(index, home_abbr=home, away_abbr=away, card=existing, kickoff_utc=kickoff)
            continue
        card = _with_venue(
            existing or _empty_card(roof="outdoor"),
            venue=venue,
            location=location,
            international=True,
        )
        _store(index, home_abbr=home, away_abbr=away, card=card, kickoff_utc=kickoff)
        injected += 1
    return injected


def build_week1_game_cards(
    *,
    season: int = 2026,
    fetch_weather: bool = True,
) -> Week1GameCardIndex:
    """Build the same card index the fair-lines route uses for Gate B."""
    index = Week1GameCardIndex()

    try:
        from src.services.nfl_rest_weather_feed import source_week_game_cards
        from src.services.nfl_stadium_roof_table import resolve_roof

        try:
            sourced_list, _meta = source_week_game_cards(
                week=1, season=int(season), fetch_weather=bool(fetch_weather)
            )
            index.source = "schedule+weather" if fetch_weather else "schedule_no_weather"
        except Exception as exc:
            index.errors.append(f"source_week_game_cards:{type(exc).__name__}:{exc}")
            sourced_list, _meta = source_week_game_cards(
                week=1, season=int(season), fetch_weather=False
            )
            index.source = "schedule_no_weather"

        for sourced in sourced_list:
            g = sourced.game
            card = dict(sourced.card)
            venue = getattr(g, "venue", None)
            location = getattr(g, "location", None)
            if venue and location:
                card = _with_venue(
                    card,
                    venue=str(venue),
                    location=str(location),
                    international=_is_international_site(venue=venue, location=location),
                )
            elif not card.get("roof"):
                try:
                    card["roof"] = resolve_roof(home=g.home_team, venue=venue)
                except Exception:
                    card["roof"] = "outdoor"
            _store(
                index,
                home_abbr=g.home_team,
                away_abbr=g.away_team,
                card=card,
                kickoff_utc=getattr(g, "kickoff_utc", None),
            )
    except Exception as exc:
        index.errors.append(f"schedule_path:{type(exc).__name__}:{exc}")
        index.source = "failed"

    injected = _inject_baked_international(index)
    if index.source in {"missing", "failed"}:
        index.source = "baked_international"
    elif injected and "baked" not in index.source:
        index.source = f"{index.source}+baked"

    # Absolute guarantee: LAR/SF Melbourne exists for route lookup.
    if index.lookup("LAR", "SF") is None:
        _inject_baked_international(index)
        index.source = "baked_international"

    return index


def lookup_week1_game_card(
    index: Week1GameCardIndex,
    *,
    home_abbr: Any,
    away_abbr: Any,
) -> Optional[Dict[str, Any]]:
    """Route-identical lookup: product abbrs as fair-lines emits (LAR, SF)."""
    return index.lookup(home_abbr, away_abbr)
