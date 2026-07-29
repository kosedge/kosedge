from __future__ import annotations

import math
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests

OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

# Forecast API covers near-term (+16d) and recent past via start_date / past runs.
# Archive covers older days (ERA5; ~2d lag). Deep history stays on climatology.
OPEN_METEO_FORECAST_PAST_DAYS = 14
OPEN_METEO_FORECAST_FUTURE_DAYS = 16
OPEN_METEO_ARCHIVE_MAX_PAST_DAYS = 90
OPEN_METEO_CACHE_TTL_SEC = 3600.0

# Process-local Open-Meteo cache: key -> (expires_monotonic, payload).
_om_response_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}


def _try_visual_crossing_weather(
    *,
    lat: float,
    lon: float,
    kickoff: datetime,
) -> Optional[Dict[str, Any]]:
    """Optional Visual Crossing overlay; never raises into the sim path.

    Requires ``VISUAL_CROSSING_API_KEY`` (alias ``VISUALCROSSING_API_KEY``).
    Free tier ~1000 req/day; DB cache TTL ~18h in ``nfl_dp_weather_forecast_cache``.
    Without a key, callers fall through to Open-Meteo (then climatology).
    """
    key = (os.getenv("VISUAL_CROSSING_API_KEY") or os.getenv("VISUALCROSSING_API_KEY") or "").strip()
    if not key:
        return None
    enabled = (os.getenv("NFL_VC_WEATHER_ENABLED") or "true").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if not enabled:
        return None
    try:
        from data_platform_nfl.db import SessionLocal
        from data_platform_nfl.external_sources import fetch_visual_crossing_weather

        session = SessionLocal()
        try:
            result = fetch_visual_crossing_weather(
                session,
                lat=lat,
                lon=lon,
                forecast_date=kickoff.date(),
            )
        finally:
            session.close()
        if not result.get("available"):
            return None
        return {
            "available": True,
            "source": "visual_crossing",
            "status": "ok" if not result.get("cache_hit") else "cache_hit",
            "wind_mph": _safe_float(result.get("wind_mph")),
            "temp_f": _safe_float(result.get("temp_f")),
            "precip_mm": _safe_float(result.get("precip_mm")),
            "at": kickoff.replace(minute=0, second=0, microsecond=0).isoformat(),
        }
    except Exception:
        return None


def _om_cache_key(lat: float, lon: float, day: str, endpoint: str) -> str:
    return f"{endpoint}|{round(lat, 3)}|{round(lon, 3)}|{day}"


def _om_cache_get(cache_key: str) -> Optional[Dict[str, Any]]:
    row = _om_response_cache.get(cache_key)
    if not row:
        return None
    expires_at, payload = row
    if time.monotonic() > expires_at:
        _om_response_cache.pop(cache_key, None)
        return None
    return payload


def _om_cache_set(cache_key: str, payload: Dict[str, Any]) -> None:
    _om_response_cache[cache_key] = (time.monotonic() + OPEN_METEO_CACHE_TTL_SEC, payload)


def _mean_or_none(values: List[Optional[float]]) -> Optional[float]:
    nums = [v for v in values if v is not None]
    if not nums:
        return None
    return sum(nums) / float(len(nums))


def _extract_kickoff_weather(
    *,
    hourly: Dict[str, Any],
    kickoff: datetime,
) -> Dict[str, Any]:
    """Nearest hour ±1h mean for wind/temp; precip uses the kickoff hour (mm/h)."""
    timestamps = hourly.get("time") if isinstance(hourly.get("time"), list) else []
    temps = hourly.get("temperature_2m") if isinstance(hourly.get("temperature_2m"), list) else []
    winds = hourly.get("windspeed_10m") if isinstance(hourly.get("windspeed_10m"), list) else []
    if not winds:
        winds = hourly.get("wind_speed_10m") if isinstance(hourly.get("wind_speed_10m"), list) else []
    precip = hourly.get("precipitation") if isinstance(hourly.get("precipitation"), list) else []
    if not timestamps:
        raise ValueError("weather_times_missing")
    kickoff_hour = kickoff.replace(minute=0, second=0, microsecond=0)
    idx = min(
        range(len(timestamps)),
        key=lambda i: abs(
            (_coerce_datetime(timestamps[i]) or kickoff_hour) - kickoff_hour
        ).total_seconds(),
    )
    window = [j for j in (idx - 1, idx, idx + 1) if 0 <= j < len(timestamps)]
    wind_vals = [_safe_float(winds[j]) if j < len(winds) else None for j in window]
    temp_vals = [_safe_float(temps[j]) if j < len(temps) else None for j in window]
    precip_val = _safe_float(precip[idx]) if idx < len(precip) else None
    return {
        "wind_mph": _mean_or_none(wind_vals),
        "temp_f": _mean_or_none(temp_vals),
        "precip_mm": precip_val,
        "at": timestamps[idx],
    }

# Approximate stadium/home-market coordinates and standard offsets.
TEAM_HOME_GEO: Dict[str, Dict[str, float]] = {
    "ARI": {"lat": 33.5276, "lon": -112.2626, "tz_offset": -7.0},
    "ATL": {"lat": 33.7554, "lon": -84.4008, "tz_offset": -5.0},
    "BAL": {"lat": 39.2781, "lon": -76.6227, "tz_offset": -5.0},
    "BUF": {"lat": 42.7738, "lon": -78.7868, "tz_offset": -5.0},
    "CAR": {"lat": 35.2258, "lon": -80.8528, "tz_offset": -5.0},
    "CHI": {"lat": 41.8623, "lon": -87.6167, "tz_offset": -6.0},
    "CIN": {"lat": 39.0954, "lon": -84.5160, "tz_offset": -5.0},
    "CLE": {"lat": 41.5061, "lon": -81.6996, "tz_offset": -5.0},
    "DAL": {"lat": 32.7473, "lon": -97.0945, "tz_offset": -6.0},
    "DEN": {"lat": 39.7439, "lon": -105.0201, "tz_offset": -7.0},
    "DET": {"lat": 42.3400, "lon": -83.0456, "tz_offset": -5.0},
    "GB": {"lat": 44.5013, "lon": -88.0622, "tz_offset": -6.0},
    "HOU": {"lat": 29.6847, "lon": -95.4107, "tz_offset": -6.0},
    "IND": {"lat": 39.7601, "lon": -86.1639, "tz_offset": -5.0},
    "JAX": {"lat": 30.3239, "lon": -81.6373, "tz_offset": -5.0},
    "KC": {"lat": 39.0490, "lon": -94.4839, "tz_offset": -6.0},
    "LV": {"lat": 36.0909, "lon": -115.1833, "tz_offset": -8.0},
    "LAC": {"lat": 33.9535, "lon": -118.3392, "tz_offset": -8.0},
    "LAR": {"lat": 33.9535, "lon": -118.3392, "tz_offset": -8.0},
    "MIA": {"lat": 25.9580, "lon": -80.2389, "tz_offset": -5.0},
    "MIN": {"lat": 44.9738, "lon": -93.2580, "tz_offset": -6.0},
    "NE": {"lat": 42.0909, "lon": -71.2643, "tz_offset": -5.0},
    "NO": {"lat": 29.9511, "lon": -90.0812, "tz_offset": -6.0},
    "NYG": {"lat": 40.8135, "lon": -74.0745, "tz_offset": -5.0},
    "NYJ": {"lat": 40.8135, "lon": -74.0745, "tz_offset": -5.0},
    "PHI": {"lat": 39.9008, "lon": -75.1675, "tz_offset": -5.0},
    "PIT": {"lat": 40.4468, "lon": -80.0158, "tz_offset": -5.0},
    "SEA": {"lat": 47.5952, "lon": -122.3316, "tz_offset": -8.0},
    "SF": {"lat": 37.4030, "lon": -121.9700, "tz_offset": -8.0},
    "TB": {"lat": 27.9759, "lon": -82.5033, "tz_offset": -5.0},
    "TEN": {"lat": 36.1665, "lon": -86.7713, "tz_offset": -6.0},
    "WAS": {"lat": 38.9078, "lon": -76.8644, "tz_offset": -5.0},
}


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _coerce_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_miles = 3958.8
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2.0) ** 2) + math.cos(p1) * math.cos(p2) * (math.sin(d_lon / 2.0) ** 2)
    return 2.0 * radius_miles * math.asin(math.sqrt(max(0.0, min(1.0, a))))


def _infer_timezone_offset(lon: float) -> float:
    if lon <= -120:
        return -8.0
    if lon <= -105:
        return -7.0
    if lon <= -90:
        return -6.0
    return -5.0


def _normalize_team_abbr(abbr: Optional[str]) -> Optional[str]:
    if not abbr:
        return None
    cleaned = str(abbr).strip().upper()
    if cleaned == "WSH":
        return "WAS"
    if cleaned == "JAC":
        return "JAX"
    return cleaned


def _estimate_weather_from_climatology(
    *,
    game_time_iso: Optional[str],
    lat: Optional[float],
) -> Dict[str, Any]:
    kickoff = _coerce_datetime(game_time_iso)
    resolved_lat = _safe_float(lat)
    if kickoff is None or resolved_lat is None:
        return {
            "available": False,
            "source": "climatology-heuristic",
            "status": "missing_kickoff_or_latitude",
            "wind_mph": None,
            "temp_f": None,
            "precip_mm": None,
            "at": None,
        }
    month = int(kickoff.month)
    # Simple seasonality curve (warmest around Jul, coolest around Jan).
    seasonal = math.cos(((float(month) - 7.0) / 12.0) * (2.0 * math.pi))
    lat_abs = abs(float(resolved_lat))
    temp_f = 62.0 + (20.0 * seasonal) - (0.22 * max(0.0, lat_abs - 25.0))
    wind_mph = 7.5 + (0.09 * max(0.0, lat_abs - 25.0))
    precip_mm = 0.7 - (0.012 * max(0.0, temp_f - 55.0))
    return {
        "available": True,
        "source": "climatology-heuristic",
        "status": "estimated",
        "wind_mph": round(max(2.0, min(22.0, wind_mph)), 3),
        "temp_f": round(max(10.0, min(100.0, temp_f)), 3),
        "precip_mm": round(max(0.0, min(4.5, precip_mm)), 3),
        "at": kickoff.replace(minute=0, second=0, microsecond=0).isoformat(),
    }


def fetch_game_weather_context(
    *,
    game_time_iso: Optional[str],
    lat: Optional[float],
    lon: Optional[float],
) -> Dict[str, Any]:
    resolved_lat = _safe_float(lat)
    resolved_lon = _safe_float(lon)
    kickoff = _coerce_datetime(game_time_iso)
    if resolved_lat is None or resolved_lon is None or kickoff is None:
        return {
            "available": False,
            "source": "open-meteo",
            "status": "missing_coordinates_or_kickoff",
            "wind_mph": None,
            "temp_f": None,
            "precip_mm": None,
            "at": None,
        }
    today_utc = datetime.now(timezone.utc).date()
    kickoff_date = kickoff.date()
    days_ahead = (kickoff_date - today_utc).days
    days_ago = (today_utc - kickoff_date).days
    # Prefer VC when keyed; otherwise Open-Meteo forecast/archive; else climatology upstream.
    if days_ahead > OPEN_METEO_FORECAST_FUTURE_DAYS or days_ago > OPEN_METEO_ARCHIVE_MAX_PAST_DAYS:
        return {
            "available": False,
            "source": "open-meteo",
            "status": "outside_forecast_window",
            "wind_mph": None,
            "temp_f": None,
            "precip_mm": None,
            "at": None,
        }

    vc = _try_visual_crossing_weather(lat=resolved_lat, lon=resolved_lon, kickoff=kickoff)
    if vc is not None and bool(vc.get("available")):
        return vc

    use_archive = days_ago > OPEN_METEO_FORECAST_PAST_DAYS
    endpoint = "archive" if use_archive else "forecast"
    url = OPEN_METEO_ARCHIVE_URL if use_archive else OPEN_METEO_FORECAST_URL
    day = kickoff_date.isoformat()
    cache_key = _om_cache_key(resolved_lat, resolved_lon, day, endpoint)

    try:
        payload = _om_cache_get(cache_key)
        cache_hit = payload is not None
        if payload is None:
            response = requests.get(
                url,
                params={
                    "latitude": resolved_lat,
                    "longitude": resolved_lon,
                    "hourly": "temperature_2m,precipitation,windspeed_10m",
                    "temperature_unit": "fahrenheit",
                    "wind_speed_unit": "mph",
                    "timezone": "UTC",
                    "start_date": day,
                    "end_date": day,
                },
                timeout=10,
            )
            response.raise_for_status()
            payload = response.json() or {}
            if isinstance(payload, dict):
                _om_cache_set(cache_key, payload)
        hourly = payload.get("hourly") if isinstance(payload.get("hourly"), dict) else {}
        extracted = _extract_kickoff_weather(hourly=hourly, kickoff=kickoff)
        return {
            "available": True,
            "source": "open-meteo-archive" if use_archive else "open-meteo",
            "status": "cache_hit" if cache_hit else "ok",
            "wind_mph": extracted["wind_mph"],
            "temp_f": extracted["temp_f"],
            "precip_mm": extracted["precip_mm"],
            "at": extracted["at"],
        }
    except Exception as exc:
        return {
            "available": False,
            "source": "open-meteo-archive" if use_archive else "open-meteo",
            "status": "unavailable",
            "error": str(exc)[:200],
            "wind_mph": None,
            "temp_f": None,
            "precip_mm": None,
            "at": None,
        }


def build_travel_context(
    *,
    home_abbr: Optional[str],
    away_abbr: Optional[str],
    venue_lat: Optional[float],
    venue_lon: Optional[float],
    neutral_site: Optional[bool] = None,
) -> Dict[str, Any]:
    normalized_home = _normalize_team_abbr(home_abbr)
    normalized_away = _normalize_team_abbr(away_abbr)
    home_geo = TEAM_HOME_GEO.get(normalized_home or "")
    away_geo = TEAM_HOME_GEO.get(normalized_away or "")
    if not home_geo or not away_geo:
        return {
            "available": False,
            "status": "team_geo_unavailable",
            "travel_miles_home": None,
            "travel_miles_away": None,
            "timezone_delta_home": None,
            "timezone_delta_away": None,
        }

    resolved_venue_lat = _safe_float(venue_lat)
    resolved_venue_lon = _safe_float(venue_lon)
    if resolved_venue_lat is None or resolved_venue_lon is None:
        resolved_venue_lat = float(home_geo["lat"])
        resolved_venue_lon = float(home_geo["lon"])
    venue_tz_offset = _infer_timezone_offset(float(resolved_venue_lon))
    is_neutral = bool(neutral_site)
    home_miles = (
        _haversine_miles(float(home_geo["lat"]), float(home_geo["lon"]), resolved_venue_lat, resolved_venue_lon)
        if is_neutral
        else 0.0
    )
    away_miles = _haversine_miles(float(away_geo["lat"]), float(away_geo["lon"]), resolved_venue_lat, resolved_venue_lon)
    return {
        "available": True,
        "status": "ok",
        "travel_miles_home": round(home_miles, 3),
        "travel_miles_away": round(away_miles, 3),
        "timezone_delta_home": round(abs(float(home_geo["tz_offset"]) - venue_tz_offset), 3),
        "timezone_delta_away": round(abs(float(away_geo["tz_offset"]) - venue_tz_offset), 3),
        "neutral_site": is_neutral,
    }


def build_nfl_environment_context(
    *,
    game_time_iso: Optional[str],
    home_abbr: Optional[str],
    away_abbr: Optional[str],
    venue_lat: Optional[float],
    venue_lon: Optional[float],
    neutral_site: Optional[bool] = None,
) -> Dict[str, Any]:
    normalized_home = _normalize_team_abbr(home_abbr)
    home_geo = TEAM_HOME_GEO.get(normalized_home or "")
    resolved_venue_lat = _safe_float(venue_lat)
    resolved_venue_lon = _safe_float(venue_lon)
    if (resolved_venue_lat is None or resolved_venue_lon is None) and isinstance(home_geo, dict):
        resolved_venue_lat = float(home_geo["lat"])
        resolved_venue_lon = float(home_geo["lon"])

    weather = fetch_game_weather_context(
        game_time_iso=game_time_iso,
        lat=resolved_venue_lat,
        lon=resolved_venue_lon,
    )
    if not bool(weather.get("available")):
        weather = _estimate_weather_from_climatology(
            game_time_iso=game_time_iso,
            lat=resolved_venue_lat,
        )
    travel = build_travel_context(
        home_abbr=home_abbr,
        away_abbr=away_abbr,
        venue_lat=resolved_venue_lat,
        venue_lon=resolved_venue_lon,
        neutral_site=neutral_site,
    )
    return {
        "weather": weather,
        "travel": travel,
        "available": bool(weather.get("available") or travel.get("available")),
    }
