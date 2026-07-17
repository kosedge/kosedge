from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List

import requests

ESPN_NFL_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"


def _to_dt(v: str) -> datetime:
    return datetime.fromisoformat(v.replace("Z", "+00:00"))


def _safe_float(v: Any, default: float) -> float:
    try:
        if v is None:
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def fetch_nfl_schedule(start_date: date, end_date: date) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    day = start_date
    while day <= end_date:
        ymd = day.strftime("%Y%m%d")
        response = requests.get(ESPN_NFL_SCOREBOARD, params={"dates": ymd, "limit": 500}, timeout=20)
        response.raise_for_status()
        payload = response.json() or {}
        for event in payload.get("events") or []:
            game_time = event.get("date")
            comps = (event.get("competitions") or [{}])[0]
            competitors = comps.get("competitors") or []
            home = next((c for c in competitors if c.get("homeAway") == "home"), None)
            away = next((c for c in competitors if c.get("homeAway") == "away"), None)
            if not home or not away:
                continue
            home_team = (home.get("team") or {}).get("displayName")
            away_team = (away.get("team") or {}).get("displayName")
            home_abbr = (home.get("team") or {}).get("abbreviation")
            away_abbr = (away.get("team") or {}).get("abbreviation")
            status = (((comps.get("status") or {}).get("type") or {}).get("description") or "scheduled").lower()
            home_score = home.get("score")
            away_score = away.get("score")
            venue = comps.get("venue") if isinstance(comps.get("venue"), dict) else {}
            venue_geo = venue.get("address") if isinstance(venue.get("address"), dict) else {}
            venue_lat = venue_geo.get("latitude")
            venue_lon = venue_geo.get("longitude")
            if not home_team or not away_team:
                continue
            out.append(
                {
                    "external_game_id": str(event.get("id") or ""),
                    "game_time": game_time,
                    "status": status,
                    "home_team": home_team,
                    "away_team": away_team,
                    "home_abbr": home_abbr,
                    "away_abbr": away_abbr,
                    "home_team_id": int((home.get("team") or {}).get("id")) if (home.get("team") or {}).get("id") else None,
                    "away_team_id": int((away.get("team") or {}).get("id")) if (away.get("team") or {}).get("id") else None,
                    "home_record_summary": ((home.get("records") or [{}])[0]).get("summary"),
                    "away_record_summary": ((away.get("records") or [{}])[0]).get("summary"),
                    "home_score": int(home_score) if home_score is not None else None,
                    "away_score": int(away_score) if away_score is not None else None,
                    "venue_name": venue.get("fullName"),
                    "venue_city": venue_geo.get("city"),
                    "venue_state": venue_geo.get("state"),
                    "venue_latitude": float(venue_lat) if venue_lat is not None else None,
                    "venue_longitude": float(venue_lon) if venue_lon is not None else None,
                    "neutral_site": bool(comps.get("neutralSite")),
                }
            )
        day += timedelta(days=1)
    return out


def team_strength_from_record(record_summary: str | None) -> tuple[float, float]:
    if not record_summary or "-" not in record_summary:
        return 1.0, 1.0
    try:
        wins, losses = record_summary.split("-", 1)
        w = max(0.0, float(wins))
        l = max(0.0, float(losses))
        games = max(1.0, w + l)
        win_pct = w / games
    except Exception:
        return 1.0, 1.0
    offense = _safe_float(0.90 + (0.22 * win_pct), 1.0)
    # Defense index is resistance (higher is stronger defense).
    defense = _safe_float(0.92 + (0.20 * win_pct), 1.0)
    return max(0.82, min(1.18, offense)), max(0.82, min(1.20, defense))


def rest_days_from_schedule(game_time_iso: str | None) -> float:
    if not game_time_iso:
        return 7.0
    try:
        game_dt = _to_dt(game_time_iso)
    except Exception:
        return 7.0
    dow = game_dt.astimezone(timezone.utc).weekday()
    # Sunday=6 -> baseline 7, Thursday shorter rest.
    if dow == 3:
        return 4.0
    if dow == 0:
        return 6.0
    return 7.0
