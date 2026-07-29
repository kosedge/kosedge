"""Env-gated external source clients with DB cache + graceful degradation.

Sources:
  - Visual Crossing weather (VISUAL_CROSSING_API_KEY; ~1000/day free tier)
  - Over The Cap / Spotrac contract intel (OTC_*/SPOTRAC_*; optional)
  - PFF skeleton (export dir preferred; login scrape rate-limited stub)

Never raise into the main sim path — callers get empty payloads + diagnostics.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple
from urllib.parse import quote

from sqlalchemy import text

SOURCE_VISUAL_CROSSING = "visual_crossing"
SOURCE_OTC = "over_the_cap"
SOURCE_SPOTRAC = "spotrac"
SOURCE_PFF = "pff"

# Conservative floor so free-tier VC is not burned by retries.
VC_MIN_INTERVAL_SEC = 1.1
PFF_MIN_INTERVAL_SEC = 5.0
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
                "payload": json.dumps(payload),
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


def _unavailable(source: str, reason: str) -> Dict[str, Any]:
    return {
        "available": False,
        "source": source,
        "reason": reason,
        "payload": {},
        "cache_hit": False,
    }


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


# ---------------------------------------------------------------------------
# OTC / Spotrac (env-gated stubs)
# ---------------------------------------------------------------------------


def fetch_otc_team_cap(
    session: Any,
    *,
    season: int,
    team: str,
) -> Dict[str, Any]:
    if not _env_bool("OTC_ENABLED", False):
        return _unavailable(SOURCE_OTC, "disabled_by_env")
    api_key = (os.getenv("OTC_API_KEY") or "").strip()
    if not api_key:
        return _unavailable(SOURCE_OTC, "missing_api_key")

    key = _cache_key("team_cap", season, team)
    cached = _read_cache(session, source=SOURCE_OTC, cache_key=key)
    if cached:
        return {"available": True, **cached}

    # Skeleton: no live scrape in production path without explicit base URL.
    base = (os.getenv("OTC_API_BASE_URL") or "").strip()
    if not base:
        _write_cache(
            session,
            source=SOURCE_OTC,
            cache_key=key,
            payload={"team": team, "season": season, "status": "skeleton_no_base_url"},
            notes="skeleton",
            ttl_hours=24.0,
        )
        return {
            "available": False,
            "source": SOURCE_OTC,
            "reason": "skeleton_no_base_url",
            "payload": {},
            "cache_hit": False,
        }

    try:
        import requests

        resp = requests.get(
            f"{base.rstrip('/')}/teams/{quote(team)}/cap/{season}",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=25,
        )
        payload = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {"text": resp.text[:2000]}
        _write_cache(
            session,
            source=SOURCE_OTC,
            cache_key=key,
            payload=payload if isinstance(payload, dict) else {"raw": payload},
            http_status=resp.status_code,
            season=season,
            object_type="team_cap",
            ttl_hours=48.0,
        )
        return {
            "available": resp.status_code == 200,
            "source": SOURCE_OTC,
            "cache_hit": False,
            "payload": payload if isinstance(payload, dict) else {},
            "http_status": resp.status_code,
        }
    except Exception as exc:
        return _unavailable(SOURCE_OTC, f"fetch_error:{type(exc).__name__}")


def fetch_spotrac_team_contracts(
    session: Any,
    *,
    season: int,
    team: str,
) -> Dict[str, Any]:
    if not _env_bool("SPOTRAC_ENABLED", False):
        return _unavailable(SOURCE_SPOTRAC, "disabled_by_env")
    api_key = (os.getenv("SPOTRAC_API_KEY") or "").strip()
    if not api_key and not _env_bool("SPOTRAC_ALLOW_PUBLIC", False):
        return _unavailable(SOURCE_SPOTRAC, "missing_api_key")

    key = _cache_key("contracts", season, team)
    cached = _read_cache(session, source=SOURCE_SPOTRAC, cache_key=key)
    if cached:
        return {"available": True, **cached}

    _write_cache(
        session,
        source=SOURCE_SPOTRAC,
        cache_key=key,
        payload={"team": team, "season": season, "status": "skeleton"},
        season=season,
        object_type="team_contracts",
        notes="skeleton_export_preferred",
        ttl_hours=72.0,
    )
    return {
        "available": False,
        "source": SOURCE_SPOTRAC,
        "reason": "skeleton_export_preferred",
        "payload": {},
        "cache_hit": False,
    }


# ---------------------------------------------------------------------------
# PFF skeleton — prefer local exports; never scrape hard
# ---------------------------------------------------------------------------

_pff_last_call_monotonic = 0.0


def load_pff_export(
    session: Any,
    *,
    season: int,
    object_type: str = "grades_offense",
) -> Dict[str, Any]:
    """Load PFF data from PFF_EXPORT_DIR JSON/CSV exports when present."""
    if not _env_bool("PFF_ENABLED", False):
        return _unavailable(SOURCE_PFF, "disabled_by_env")

    export_dir = (os.getenv("PFF_EXPORT_DIR") or "").strip()
    key = _cache_key("export", season, object_type)
    cached = _read_cache(session, source=SOURCE_PFF, cache_key=key)
    if cached:
        return {"available": True, **cached}

    if not export_dir:
        return _unavailable(SOURCE_PFF, "missing_export_dir")

    candidates = [
        os.path.join(export_dir, f"{object_type}_{season}.json"),
        os.path.join(export_dir, str(season), f"{object_type}.json"),
        os.path.join(export_dir, f"{object_type}.json"),
    ]
    path = next((p for p in candidates if os.path.isfile(p)), None)
    if path is None:
        return _unavailable(SOURCE_PFF, "export_not_found")

    try:
        with open(path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except Exception as exc:
        return _unavailable(SOURCE_PFF, f"export_read_error:{type(exc).__name__}")

    if not isinstance(payload, dict):
        payload = {"rows": payload}

    _write_cache(
        session,
        source=SOURCE_PFF,
        cache_key=key,
        payload=payload,
        season=season,
        object_type=object_type,
        notes=f"export:{os.path.basename(path)}",
        ttl_hours=168.0,
    )
    return {
        "available": True,
        "source": SOURCE_PFF,
        "cache_hit": False,
        "payload": payload,
        "path": path,
    }


def fetch_pff_rate_limited_stub(
    session: Any,
    *,
    season: int,
    path: str = "/api/v1/placeholder",
) -> Dict[str, Any]:
    """Placeholder for authenticated PFF pulls. Prefer exports; rate-limit hard."""
    global _pff_last_call_monotonic

    if not _env_bool("PFF_ENABLED", False):
        return _unavailable(SOURCE_PFF, "disabled_by_env")
    if not _env_bool("PFF_ALLOW_LIVE_FETCH", False):
        return _unavailable(SOURCE_PFF, "live_fetch_disabled_use_exports")

    user = (os.getenv("PFF_USERNAME") or "").strip()
    password = (os.getenv("PFF_PASSWORD") or "").strip()
    if not user or not password:
        return _unavailable(SOURCE_PFF, "missing_credentials")

    elapsed = time.monotonic() - _pff_last_call_monotonic
    if elapsed < PFF_MIN_INTERVAL_SEC:
        time.sleep(PFF_MIN_INTERVAL_SEC - elapsed)
    _pff_last_call_monotonic = time.monotonic()

    key = _cache_key("live", season, path)
    cached = _read_cache(session, source=SOURCE_PFF, cache_key=key)
    if cached:
        return {"available": True, **cached}

    # Intentionally no live endpoint hardcoding — ops must set PFF_API_BASE_URL.
    base = (os.getenv("PFF_API_BASE_URL") or "").strip()
    if not base:
        return _unavailable(SOURCE_PFF, "missing_api_base_url")

    return _unavailable(SOURCE_PFF, "live_fetch_not_implemented_use_exports")


def external_source_status() -> Dict[str, Any]:
    """Diagnostics for ops / dry-run without hitting network."""
    return {
        "visual_crossing": {
            "enabled": _env_bool("NFL_VC_WEATHER_ENABLED", True),
            "has_key": bool((os.getenv("VISUAL_CROSSING_API_KEY") or os.getenv("VISUALCROSSING_API_KEY") or "").strip()),
        },
        "otc": {
            "enabled": _env_bool("OTC_ENABLED", False),
            "has_key": bool((os.getenv("OTC_API_KEY") or "").strip()),
        },
        "spotrac": {
            "enabled": _env_bool("SPOTRAC_ENABLED", False),
            "has_key": bool((os.getenv("SPOTRAC_API_KEY") or "").strip()),
        },
        "pff": {
            "enabled": _env_bool("PFF_ENABLED", False),
            "export_dir": (os.getenv("PFF_EXPORT_DIR") or "").strip() or None,
            "allow_live": _env_bool("PFF_ALLOW_LIVE_FETCH", False),
        },
    }
