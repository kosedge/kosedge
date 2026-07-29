"""Env-gated external source clients with DB cache + graceful degradation.

Production path (this session): Visual Crossing weather only.
OTC / Spotrac / PFF skeletons are deferred — do not reintroduce until
holdout-safe and wired end-to-end.

Never raise into the main sim path — callers get empty payloads + diagnostics.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Optional
from urllib.parse import quote

from sqlalchemy import text

SOURCE_VISUAL_CROSSING = "visual_crossing"

# Conservative floor so free-tier VC is not burned by retries.
VC_MIN_INTERVAL_SEC = 1.1
DEFAULT_CACHE_HOURS = 18


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _cache_key(*parts: Any) -> str:
    joined = "|".join(str(p) for p in parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:48]


def _unavailable(source: str, reason: str) -> Dict[str, Any]:
    return {
        "available": False,
        "source": source,
        "reason": reason,
        "payload": {},
        "cache_hit": False,
    }


def _read_cache(session: Any, *, source: str, cache_key: str) -> Optional[Dict[str, Any]]:
    try:
        row = session.execute(
            text(
                """
                SELECT payload, http_status, fetched_at, expires_at, notes
                FROM nfl_dp_external_cache
                WHERE source = :source AND cache_key = :cache_key
                  AND (expires_at IS NULL OR expires_at > NOW())
                """
            ),
            {"source": source, "cache_key": cache_key},
        ).fetchone()
    except Exception:
        return None
    if not row:
        return None
    m = dict(row._mapping)
    payload = m.get("payload")
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            payload = {}
    return {
        "payload": payload if isinstance(payload, dict) else {},
        "http_status": m.get("http_status"),
        "fetched_at": m.get("fetched_at"),
        "expires_at": m.get("expires_at"),
        "notes": m.get("notes"),
        "cache_hit": True,
        "source": source,
    }


def _write_cache(
    session: Any,
    *,
    source: str,
    cache_key: str,
    payload: Dict[str, Any],
    http_status: Optional[int] = None,
    season: Optional[int] = None,
    week: Optional[int] = None,
    object_type: str = "response",
    ttl_hours: float = DEFAULT_CACHE_HOURS,
    notes: Optional[str] = None,
    commit: bool = True,
) -> None:
    expires = _now() + timedelta(hours=float(ttl_hours))
    try:
        session.execute(
            text(
                """
                INSERT INTO nfl_dp_external_cache (
                  source, cache_key, season, week, object_type, payload,
                  http_status, fetched_at, expires_at, notes
                ) VALUES (
                  :source, :cache_key, :season, :week, :object_type,
                  CAST(:payload AS jsonb), :http_status, :fetched_at, :expires_at, :notes
                )
                ON CONFLICT (source, cache_key) DO UPDATE SET
                  season = EXCLUDED.season,
                  week = EXCLUDED.week,
                  object_type = EXCLUDED.object_type,
                  payload = EXCLUDED.payload,
                  http_status = EXCLUDED.http_status,
                  fetched_at = EXCLUDED.fetched_at,
                  expires_at = EXCLUDED.expires_at,
                  notes = EXCLUDED.notes
                """
            ),
            {
                "source": source,
                "cache_key": cache_key,
                "season": season,
                "week": week,
                "object_type": object_type,
                "payload": json.dumps(payload if isinstance(payload, dict) else {}),
                "http_status": http_status,
                "fetched_at": _now(),
                "expires_at": expires,
                "notes": notes,
            },
        )
        if commit:
            session.commit()
    except Exception:
        try:
            session.rollback()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Visual Crossing
# ---------------------------------------------------------------------------

_vc_last_call_monotonic = 0.0


def fetch_visual_crossing_weather(
    session: Any,
    *,
    lat: float,
    lon: float,
    forecast_date: date,
    location_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Fetch daily weather; cache by location+date. No-op without API key."""
    global _vc_last_call_monotonic

    if not _env_bool("NFL_VC_WEATHER_ENABLED", True):
        return _unavailable(SOURCE_VISUAL_CROSSING, "disabled_by_env")

    api_key = (os.getenv("VISUAL_CROSSING_API_KEY") or os.getenv("VISUALCROSSING_API_KEY") or "").strip()
    if not api_key:
        return _unavailable(SOURCE_VISUAL_CROSSING, "missing_api_key")

    loc = location_key or f"{round(lat, 3)},{round(lon, 3)}"
    day = forecast_date.isoformat()

    # Dedicated weather table first.
    try:
        row = session.execute(
            text(
                """
                SELECT temp_f, wind_mph, precip_mm, humidity, conditions, payload, fetched_at
                FROM nfl_dp_weather_forecast_cache
                WHERE location_key = :loc AND forecast_date = :day AND provider = :provider
                  AND (expires_at IS NULL OR expires_at > NOW())
                """
            ),
            {"loc": loc, "day": day, "provider": SOURCE_VISUAL_CROSSING},
        ).fetchone()
        if row:
            m = dict(row._mapping)
            return {
                "available": True,
                "source": SOURCE_VISUAL_CROSSING,
                "cache_hit": True,
                "temp_f": m.get("temp_f"),
                "wind_mph": m.get("wind_mph"),
                "precip_mm": m.get("precip_mm"),
                "humidity": m.get("humidity"),
                "conditions": m.get("conditions"),
                "payload": m.get("payload") if isinstance(m.get("payload"), dict) else {},
                "fetched_at": m.get("fetched_at"),
            }
    except Exception:
        pass

    # Rate limit.
    elapsed = time.monotonic() - _vc_last_call_monotonic
    if elapsed < VC_MIN_INTERVAL_SEC:
        time.sleep(VC_MIN_INTERVAL_SEC - elapsed)

    url = (
        f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/"
        f"{quote(str(lat))}%2C{quote(str(lon))}/{day}/{day}"
        f"?unitGroup=us&include=days&key={quote(api_key)}&contentType=json"
    )
    try:
        import requests

        _vc_last_call_monotonic = time.monotonic()
        resp = requests.get(url, timeout=20)
        status = int(resp.status_code)
        if status != 200:
            _write_cache(
                session,
                source=SOURCE_VISUAL_CROSSING,
                cache_key=_cache_key(loc, day),
                payload={"error": resp.text[:500]},
                http_status=status,
                notes="http_error",
                ttl_hours=2.0,
            )
            return _unavailable(SOURCE_VISUAL_CROSSING, f"http_{status}")
        body = resp.json()
    except Exception as exc:
        return _unavailable(SOURCE_VISUAL_CROSSING, f"fetch_error:{type(exc).__name__}")

    days = body.get("days") if isinstance(body, dict) else None
    day_row = days[0] if isinstance(days, list) and days else {}
    temp_f = day_row.get("temp")
    wind_mph = day_row.get("windspeed")
    precip_in = day_row.get("precip")
    precip_mm = float(precip_in) * 25.4 if precip_in is not None else None
    humidity = day_row.get("humidity")
    conditions = day_row.get("conditions")

    try:
        session.execute(
            text(
                """
                INSERT INTO nfl_dp_weather_forecast_cache (
                  location_key, forecast_date, provider, lat, lon,
                  temp_f, wind_mph, precip_mm, humidity, conditions,
                  payload, fetched_at, expires_at
                ) VALUES (
                  :loc, :day, :provider, :lat, :lon,
                  :temp_f, :wind_mph, :precip_mm, :humidity, :conditions,
                  CAST(:payload AS jsonb), :fetched_at, :expires_at
                )
                ON CONFLICT (location_key, forecast_date, provider) DO UPDATE SET
                  temp_f = EXCLUDED.temp_f,
                  wind_mph = EXCLUDED.wind_mph,
                  precip_mm = EXCLUDED.precip_mm,
                  humidity = EXCLUDED.humidity,
                  conditions = EXCLUDED.conditions,
                  payload = EXCLUDED.payload,
                  fetched_at = EXCLUDED.fetched_at,
                  expires_at = EXCLUDED.expires_at
                """
            ),
            {
                "loc": loc,
                "day": day,
                "provider": SOURCE_VISUAL_CROSSING,
                "lat": lat,
                "lon": lon,
                "temp_f": temp_f,
                "wind_mph": wind_mph,
                "precip_mm": precip_mm,
                "humidity": humidity,
                "conditions": conditions,
                "payload": json.dumps(body if isinstance(body, dict) else {}),
                "fetched_at": _now(),
                "expires_at": _now() + timedelta(hours=DEFAULT_CACHE_HOURS),
            },
        )
        session.commit()
    except Exception:
        try:
            session.rollback()
        except Exception:
            pass

    return {
        "available": True,
        "source": SOURCE_VISUAL_CROSSING,
        "cache_hit": False,
        "temp_f": temp_f,
        "wind_mph": wind_mph,
        "precip_mm": precip_mm,
        "humidity": humidity,
        "conditions": conditions,
        "payload": body if isinstance(body, dict) else {},
    }


def external_source_status() -> Dict[str, Any]:
    """Diagnostics for ops / dry-run without hitting network."""
    return {
        "visual_crossing": {
            "enabled": _env_bool("NFL_VC_WEATHER_ENABLED", True),
            "has_key": bool(
                (os.getenv("VISUAL_CROSSING_API_KEY") or os.getenv("VISUALCROSSING_API_KEY") or "").strip()
            ),
        },
        "deferred": {
            "otc": "not_implemented_holdout_deferred",
            "spotrac": "not_implemented_holdout_deferred",
            "pff": "not_implemented_holdout_deferred",
        },
    }
