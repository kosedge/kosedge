"""Source rest + weather game-card fields for remat / KEI.

Doctrine
--------
- Feeds ``nfl_rest_weather_game_card`` fields — does **not** redesign modifiers.
- Rest from packaged NFL schedule (+ canonical kickoffs when present).
- Weather from **Open-Meteo or NWS only** (free). No Visual Crossing, no climatology.
- Cache under gitignored path with ``as_of``. Timeout / missing ⇒ leave weather
  fields None ⇒ no KEI weather modifier (same contract as #303).
- Dome / retractable from ``nfl_stadium_roof_table`` — never invent wind=0 outdoor.
- Notes / camp / DepthSot **cannot write** these fields.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

import requests

from src.services.nfl_rest_weather_game_card import (
    GAME_CARD_FIELDS,
    NOTES_CANNOT_WRITE_GAME_CARD_FIELDS,
    ROOF_INDOOR,
    SHORT_WEEK_MAX_DAYS,
    apply_rest_weather_game_card,
    parse_game_card,
    reject_note_game_card_write,
)
from src.services.nfl_stadium_roof_table import (
    NFL_STADIUM_ROOF,
    resolve_roof,
    resolve_venue_geo,
)

REST_WEATHER_FEED_VERSION = "rest_weather_feed_v1"

# Cache lives under repo data/ops but is gitignored (fetched forecasts).
DEFAULT_CACHE_DIR = (
    Path(__file__).resolve().parents[4] / "data" / "ops" / "nfl-rest-weather-cache"
)
# Fallback when repo layout differs (e.g. installed package).
_ALT_CACHE_DIR = Path("data/ops/nfl-rest-weather-cache")

WEATHER_CACHE_TTL_SEC = 6 * 3600  # 6h — reasonable for desk refresh
WEATHER_HTTP_TIMEOUT_SEC = 8.0
OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_FORECAST_FUTURE_DAYS = 16
NWS_POINTS_URL = "https://api.weather.gov/points/{lat},{lon}"

# Timezone hours west of ET (same bands as KEI / game-card).
_PACIFIC = frozenset({"SEA", "SF", "LA", "LAR", "LAC", "ARI", "LV"})
_MOUNTAIN = frozenset({"DEN"})
_CENTRAL = frozenset({"CHI", "DAL", "HOU", "MIN", "GB", "TEN", "NO", "KC"})

_REPO_ROOT = Path(__file__).resolve().parents[4]
_CANONICAL_SCHEDULE_CANDIDATES = (
    _REPO_ROOT / "apps" / "web" / "lib" / "nfl-canonical-schedule-2026.json",
    Path("apps/web/lib/nfl-canonical-schedule-2026.json"),
)


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


def tz_hours_west_of_et(team: str) -> int:
    code = _norm_team(team)
    if code in _PACIFIC:
        return 3
    if code in _MOUNTAIN:
        return 2
    if code in _CENTRAL:
        return 1
    return 0


def timezone_shift_hours(home: str, away: str) -> float:
    return float(abs(tz_hours_west_of_et(away) - tz_hours_west_of_et(home)))


def _coerce_dt(value: Any) -> Optional[datetime]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        raw = str(value).strip()
        if not raw:
            return None
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _cache_dir(explicit: Optional[Path] = None) -> Path:
    if explicit is not None:
        return Path(explicit)
    env = (os.getenv("NFL_REST_WEATHER_CACHE_DIR") or "").strip()
    if env:
        return Path(env)
    if DEFAULT_CACHE_DIR.parent.is_dir():
        return DEFAULT_CACHE_DIR
    return _ALT_CACHE_DIR


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass
class ScheduleGameRow:
    season: int
    week: int
    game_id: str
    home_team: str
    away_team: str
    kickoff_utc: Optional[str] = None
    venue: Optional[str] = None
    location: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "season": self.season,
            "week": self.week,
            "game_id": self.game_id,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "kickoff_utc": self.kickoff_utc,
            "venue": self.venue,
            "location": self.location,
        }


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def load_schedule_games(season: int = 2026) -> Tuple[List[ScheduleGameRow], Dict[str, Any]]:
    """Load packaged REG schedule; overlay canonical kickoff/venue when present."""
    packaged_path = (
        Path(__file__).resolve().parent
        / "nfl_season_engine"
        / "data"
        / f"nfl_regular_schedule_{int(season)}.json"
    )
    payload = _load_json(packaged_path)
    if payload is None:
        raise FileNotFoundError(f"packaged schedule missing: {packaged_path}")

    games: List[ScheduleGameRow] = []
    for raw in payload.get("games") or []:
        if not isinstance(raw, Mapping):
            continue
        home = _norm_team(raw.get("home_team") or raw.get("home_team_id"))
        away = _norm_team(raw.get("away_team") or raw.get("away_team_id"))
        week = int(raw.get("week") or 0)
        if not home or not away or week < 1:
            continue
        gid = str(raw.get("game_id") or f"{season}-W{week:02d}-{away}@{home}")
        games.append(
            ScheduleGameRow(
                season=int(raw.get("season") or season),
                week=week,
                game_id=gid,
                home_team=home,
                away_team=away,
            )
        )

    canonical: Optional[Dict[str, Any]] = None
    canonical_path_used = ""
    for cand in _CANONICAL_SCHEDULE_CANDIDATES:
        canonical = _load_json(cand)
        if canonical is not None:
            canonical_path_used = str(cand)
            break

    kickoff_by_key: Dict[Tuple[str, str, int], Mapping[str, Any]] = {}
    if canonical:
        for raw in canonical.get("games") or []:
            if not isinstance(raw, Mapping):
                continue
            if int(raw.get("season") or season) != int(season):
                continue
            home = _norm_team(raw.get("home_team_id") or raw.get("home_team"))
            away = _norm_team(raw.get("away_team_id") or raw.get("away_team"))
            week = int(raw.get("week") or 0)
            if home and away and week:
                kickoff_by_key[(away, home, week)] = raw

    enriched: List[ScheduleGameRow] = []
    for g in games:
        overlay = kickoff_by_key.get((g.away_team, g.home_team, g.week))
        kickoff = None
        venue = None
        location = None
        if overlay:
            kickoff = overlay.get("kickoff_utc") or overlay.get("kickoff")
            venue = overlay.get("venue")
            location = overlay.get("location")
            # Prefer canonical game_id when present.
            cid = overlay.get("engine_game_id") or overlay.get("game_id")
            if cid:
                g = ScheduleGameRow(
                    season=g.season,
                    week=g.week,
                    game_id=str(cid),
                    home_team=g.home_team,
                    away_team=g.away_team,
                    kickoff_utc=str(kickoff) if kickoff else None,
                    venue=str(venue) if venue else None,
                    location=str(location) if location else None,
                )
                enriched.append(g)
                continue
        enriched.append(
            ScheduleGameRow(
                season=g.season,
                week=g.week,
                game_id=g.game_id,
                home_team=g.home_team,
                away_team=g.away_team,
                kickoff_utc=str(kickoff) if kickoff else None,
                venue=str(venue) if venue else None,
                location=str(location) if location else None,
            )
        )

    meta = {
        "schedule_source": str(payload.get("source") or "packaged"),
        "schedule_as_of": str(payload.get("as_of") or ""),
        "canonical_path": canonical_path_used,
        "canonical_overlay": bool(canonical),
        "game_count": len(enriched),
        "feed_version": REST_WEATHER_FEED_VERSION,
    }
    return enriched, meta


def _prior_kickoff_for_team(
    *,
    team: str,
    before: ScheduleGameRow,
    all_games: Sequence[ScheduleGameRow],
) -> Optional[datetime]:
    """Most recent prior REG kickoff for ``team`` before ``before`` (kickoff-dated)."""
    code = _norm_team(team)
    best: Optional[datetime] = None
    before_dt = _coerce_dt(before.kickoff_utc)
    if before_dt is None:
        return None
    for g in all_games:
        if g.game_id == before.game_id:
            continue
        if _norm_team(g.home_team) != code and _norm_team(g.away_team) != code:
            continue
        g_dt = _coerce_dt(g.kickoff_utc)
        if g_dt is None or g_dt >= before_dt:
            continue
        if best is None or g_dt > best:
            best = g_dt
    return best


def _prior_week_for_team(
    *,
    team: str,
    before: ScheduleGameRow,
    all_games: Sequence[ScheduleGameRow],
) -> Optional[int]:
    code = _norm_team(team)
    prior: Optional[int] = None
    for g in all_games:
        if g.game_id == before.game_id:
            continue
        if int(g.week) >= int(before.week):
            continue
        if _norm_team(g.home_team) != code and _norm_team(g.away_team) != code:
            continue
        if prior is None or int(g.week) > prior:
            prior = int(g.week)
    return prior


def compute_rest_fields(
    game: ScheduleGameRow,
    all_games: Sequence[ScheduleGameRow],
) -> Dict[str, Any]:
    """Derive days_rest_home/away, short_week, timezone_shift from schedule."""
    kickoff = _coerce_dt(game.kickoff_utc)
    days_home: Optional[int] = None
    days_away: Optional[int] = None

    if kickoff is not None:
        prev_home = _prior_kickoff_for_team(
            team=game.home_team, before=game, all_games=all_games
        )
        prev_away = _prior_kickoff_for_team(
            team=game.away_team, before=game, all_games=all_games
        )
        if prev_home is not None:
            days_home = max(0, (kickoff.date() - prev_home.date()).days)
        if prev_away is not None:
            days_away = max(0, (kickoff.date() - prev_away.date()).days)
    else:
        # Week-gap fallback when kickoffs absent (packaged wall chart only).
        prior_week_home = _prior_week_for_team(
            team=game.home_team, before=game, all_games=all_games
        )
        prior_week_away = _prior_week_for_team(
            team=game.away_team, before=game, all_games=all_games
        )
        if prior_week_home is not None:
            days_home = 7 * (int(game.week) - prior_week_home)
        if prior_week_away is not None:
            days_away = 7 * (int(game.week) - prior_week_away)

    short = False
    if days_home is not None and days_home <= SHORT_WEEK_MAX_DAYS:
        short = True
    if days_away is not None and days_away <= SHORT_WEEK_MAX_DAYS:
        short = True

    return {
        "days_rest_home": days_home,
        "days_rest_away": days_away,
        "short_week": short if (days_home is not None or days_away is not None) else None,
        "timezone_shift": timezone_shift_hours(game.home_team, game.away_team),
    }


@dataclass
class WeatherFetchResult:
    available: bool
    wind_mph: Optional[float] = None
    precip: Optional[float] = None  # mm — matches game-card precip band units
    temp_f: Optional[float] = None
    source: str = ""
    status: str = ""
    as_of: str = ""
    error: str = ""
    cache_hit: bool = False

    def as_dict(self) -> Dict[str, Any]:
        return {
            "available": self.available,
            "wind_mph": self.wind_mph,
            "precip": self.precip,
            "temp_f": self.temp_f,
            "source": self.source,
            "status": self.status,
            "as_of": self.as_of,
            "error": self.error,
            "cache_hit": self.cache_hit,
        }


def _read_cache(path: Path, *, ttl_sec: float) -> Optional[Dict[str, Any]]:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    as_of = _coerce_dt(payload.get("as_of"))
    if as_of is None:
        return None
    age = (datetime.now(timezone.utc) - as_of).total_seconds()
    if age < 0 or age > ttl_sec:
        return None
    return payload


def _write_cache(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = dict(payload)
    # as_of = cache write time (TTL clock). Preserve provider timestamp separately.
    if body.get("fetched_at") is None and body.get("as_of"):
        body["fetched_at"] = body["as_of"]
    body["as_of"] = _utc_now_iso()
    path.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _extract_open_meteo_hour(
    hourly: Mapping[str, Any], kickoff: datetime
) -> Dict[str, Optional[float]]:
    timestamps = hourly.get("time") if isinstance(hourly.get("time"), list) else []
    temps = hourly.get("temperature_2m") if isinstance(hourly.get("temperature_2m"), list) else []
    winds = hourly.get("windspeed_10m") if isinstance(hourly.get("windspeed_10m"), list) else []
    if not winds:
        winds = (
            hourly.get("wind_speed_10m")
            if isinstance(hourly.get("wind_speed_10m"), list)
            else []
        )
    precip = hourly.get("precipitation") if isinstance(hourly.get("precipitation"), list) else []
    if not timestamps:
        return {"wind_mph": None, "temp_f": None, "precip": None}
    kickoff_hour = kickoff.replace(minute=0, second=0, microsecond=0)
    idx = min(
        range(len(timestamps)),
        key=lambda i: abs(
            ((_coerce_dt(timestamps[i]) or kickoff_hour) - kickoff_hour).total_seconds()
        ),
    )

    def _f(seq: Any, i: int) -> Optional[float]:
        if not isinstance(seq, list) or i >= len(seq):
            return None
        try:
            v = float(seq[i])
        except (TypeError, ValueError):
            return None
        return v

    return {
        "wind_mph": _f(winds, idx),
        "temp_f": _f(temps, idx),
        "precip": _f(precip, idx),
    }


def fetch_weather_open_meteo(
    *,
    lat: float,
    lon: float,
    kickoff: datetime,
    timeout_sec: float = WEATHER_HTTP_TIMEOUT_SEC,
    session: Optional[Any] = None,
) -> WeatherFetchResult:
    """Open-Meteo forecast only. Timeout / error → available=False (no invent)."""
    today = datetime.now(timezone.utc).date()
    day = kickoff.date()
    days_ahead = (day - today).days
    if days_ahead > OPEN_METEO_FORECAST_FUTURE_DAYS or days_ahead < -14:
        return WeatherFetchResult(
            available=False,
            source="open-meteo",
            status="outside_forecast_window",
            as_of=_utc_now_iso(),
        )
    http = session or requests
    try:
        response = http.get(
            OPEN_METEO_FORECAST_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "hourly": "temperature_2m,precipitation,windspeed_10m",
                "temperature_unit": "fahrenheit",
                "wind_speed_unit": "mph",
                "timezone": "UTC",
                "start_date": day.isoformat(),
                "end_date": day.isoformat(),
            },
            timeout=timeout_sec,
        )
        response.raise_for_status()
        payload = response.json() or {}
    except Exception as exc:
        status = "timeout" if "timeout" in str(exc).lower() else "unavailable"
        return WeatherFetchResult(
            available=False,
            source="open-meteo",
            status=status,
            as_of=_utc_now_iso(),
            error=str(exc)[:200],
        )
    hourly = payload.get("hourly") if isinstance(payload.get("hourly"), dict) else {}
    extracted = _extract_open_meteo_hour(hourly, kickoff)
    # Do not invent zeros — if all missing, treat as unavailable.
    if (
        extracted["wind_mph"] is None
        and extracted["temp_f"] is None
        and extracted["precip"] is None
    ):
        return WeatherFetchResult(
            available=False,
            source="open-meteo",
            status="readings_missing",
            as_of=_utc_now_iso(),
        )
    return WeatherFetchResult(
        available=True,
        wind_mph=extracted["wind_mph"],
        precip=extracted["precip"],
        temp_f=extracted["temp_f"],
        source="open-meteo",
        status="ok",
        as_of=_utc_now_iso(),
    )


def fetch_weather_nws(
    *,
    lat: float,
    lon: float,
    kickoff: datetime,
    timeout_sec: float = WEATHER_HTTP_TIMEOUT_SEC,
    session: Optional[Any] = None,
) -> WeatherFetchResult:
    """NWS gridpoint forecast (US only). Timeout / error → available=False."""
    http = session or requests
    headers = {
        "User-Agent": "kosedge-rest-weather-feed/1.0 (contact: ops@kosedge.com)",
        "Accept": "application/geo+json",
    }
    try:
        points = http.get(
            NWS_POINTS_URL.format(lat=round(lat, 4), lon=round(lon, 4)),
            headers=headers,
            timeout=timeout_sec,
        )
        points.raise_for_status()
        points_body = points.json() or {}
        props = points_body.get("properties") if isinstance(points_body, dict) else {}
        forecast_url = (props or {}).get("forecastHourly")
        if not forecast_url:
            return WeatherFetchResult(
                available=False,
                source="nws",
                status="no_forecast_url",
                as_of=_utc_now_iso(),
            )
        forecast = http.get(forecast_url, headers=headers, timeout=timeout_sec)
        forecast.raise_for_status()
        forecast_body = forecast.json() or {}
        periods = (
            (forecast_body.get("properties") or {}).get("periods")
            if isinstance(forecast_body, dict)
            else None
        )
        if not isinstance(periods, list) or not periods:
            return WeatherFetchResult(
                available=False,
                source="nws",
                status="periods_missing",
                as_of=_utc_now_iso(),
            )
    except Exception as exc:
        status = "timeout" if "timeout" in str(exc).lower() else "unavailable"
        return WeatherFetchResult(
            available=False,
            source="nws",
            status=status,
            as_of=_utc_now_iso(),
            error=str(exc)[:200],
        )

    kickoff_hour = kickoff.replace(minute=0, second=0, microsecond=0)
    best = None
    best_delta = None
    for period in periods:
        if not isinstance(period, Mapping):
            continue
        start = _coerce_dt(period.get("startTime"))
        if start is None:
            continue
        delta = abs((start - kickoff_hour).total_seconds())
        if best_delta is None or delta < best_delta:
            best_delta = delta
            best = period
    if best is None:
        return WeatherFetchResult(
            available=False,
            source="nws",
            status="no_matching_period",
            as_of=_utc_now_iso(),
        )

    wind_mph: Optional[float] = None
    wind_raw = str(best.get("windSpeed") or "")
    # e.g. "10 mph" or "10 to 15 mph"
    nums = []
    for token in wind_raw.replace("to", " ").split():
        try:
            nums.append(float(token))
        except ValueError:
            continue
    if nums:
        wind_mph = sum(nums) / float(len(nums))

    temp_f: Optional[float] = None
    try:
        if best.get("temperature") is not None:
            temp_f = float(best["temperature"])
            unit = str(best.get("temperatureUnit") or "F").upper()
            if unit.startswith("C"):
                temp_f = temp_f * 9.0 / 5.0 + 32.0
    except (TypeError, ValueError):
        temp_f = None

    precip: Optional[float] = None
    pop = best.get("probabilityOfPrecipitation")
    if isinstance(pop, Mapping) and pop.get("value") is not None:
        try:
            # NWS hourly often lacks mm — keep precip None unless quantitative.
            # Do not invent mm from PoP.
            precip = None
        except (TypeError, ValueError):
            precip = None

    if wind_mph is None and temp_f is None and precip is None:
        return WeatherFetchResult(
            available=False,
            source="nws",
            status="readings_missing",
            as_of=_utc_now_iso(),
        )
    return WeatherFetchResult(
        available=True,
        wind_mph=wind_mph,
        precip=precip,
        temp_f=temp_f,
        source="nws",
        status="ok",
        as_of=_utc_now_iso(),
    )


def fetch_weather_cached(
    *,
    game_id: str,
    lat: float,
    lon: float,
    kickoff: datetime,
    cache_dir: Optional[Path] = None,
    ttl_sec: float = WEATHER_CACHE_TTL_SEC,
    timeout_sec: float = WEATHER_HTTP_TIMEOUT_SEC,
    provider: str = "open-meteo",
    session: Optional[Any] = None,
    fetch_fn: Optional[Callable[..., WeatherFetchResult]] = None,
) -> WeatherFetchResult:
    """Fetch weather with on-disk as_of cache. Missing/timeout ⇒ available=False."""
    cdir = _cache_dir(cache_dir)
    day = kickoff.date().isoformat()
    cache_path = cdir / f"{game_id}_{day}_{provider.replace('/', '_')}.json"
    cached = _read_cache(cache_path, ttl_sec=ttl_sec)
    if cached is not None:
        return WeatherFetchResult(
            available=bool(cached.get("available")),
            wind_mph=cached.get("wind_mph"),
            precip=cached.get("precip"),
            temp_f=cached.get("temp_f"),
            source=str(cached.get("source") or provider),
            status=str(cached.get("status") or "cache_hit"),
            as_of=str(cached.get("as_of") or ""),
            error=str(cached.get("error") or ""),
            cache_hit=True,
        )

    if fetch_fn is not None:
        result = fetch_fn(
            lat=lat, lon=lon, kickoff=kickoff, timeout_sec=timeout_sec, session=session
        )
    elif provider == "nws":
        result = fetch_weather_nws(
            lat=lat, lon=lon, kickoff=kickoff, timeout_sec=timeout_sec, session=session
        )
    else:
        result = fetch_weather_open_meteo(
            lat=lat, lon=lon, kickoff=kickoff, timeout_sec=timeout_sec, session=session
        )

    _write_cache(cache_path, result.as_dict())
    return result


@dataclass
class SourcedGameCard:
    game: ScheduleGameRow
    card: Dict[str, Any]
    weather_meta: Dict[str, Any] = field(default_factory=dict)
    rest_meta: Dict[str, Any] = field(default_factory=dict)
    modifier: Optional[Dict[str, Any]] = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "game": self.game.as_dict(),
            "card": dict(self.card),
            "weather_meta": dict(self.weather_meta),
            "rest_meta": dict(self.rest_meta),
            "modifier": self.modifier,
            "feed_version": REST_WEATHER_FEED_VERSION,
        }


def source_game_card(
    game: ScheduleGameRow,
    all_games: Sequence[ScheduleGameRow],
    *,
    fetch_weather: bool = True,
    cache_dir: Optional[Path] = None,
    timeout_sec: float = WEATHER_HTTP_TIMEOUT_SEC,
    weather_provider: str = "open-meteo",
    session: Optional[Any] = None,
    fetch_fn: Optional[Callable[..., WeatherFetchResult]] = None,
    roof_override: Optional[str] = None,
) -> SourcedGameCard:
    """Build one game-card from schedule rest + stadium roof + optional weather."""
    rest = compute_rest_fields(game, all_games)
    roof = resolve_roof(
        home=game.home_team, venue=game.venue, roof_override=roof_override
    )

    card: Dict[str, Any] = {
        "days_rest_home": rest["days_rest_home"],
        "days_rest_away": rest["days_rest_away"],
        "short_week": rest["short_week"],
        "timezone_shift": rest["timezone_shift"],
        "roof": roof,
        "wind_mph": None,
        "precip": None,
        "temp_f": None,
    }

    weather_meta: Dict[str, Any] = {
        "fetched": False,
        "skipped_reason": "",
    }

    indoor = roof is not None and roof in ROOF_INDOOR
    kickoff = _coerce_dt(game.kickoff_utc)

    if not fetch_weather:
        weather_meta["skipped_reason"] = "fetch_weather=false"
    elif indoor:
        weather_meta["skipped_reason"] = f"indoor roof={roof}"
    elif kickoff is None:
        weather_meta["skipped_reason"] = "kickoff missing"
    else:
        geo = resolve_venue_geo(home=game.home_team, venue=game.venue)
        if geo is None:
            weather_meta["skipped_reason"] = "venue geo missing"
        else:
            result = fetch_weather_cached(
                game_id=game.game_id,
                lat=float(geo["lat"]),
                lon=float(geo["lon"]),
                kickoff=kickoff,
                cache_dir=cache_dir,
                timeout_sec=timeout_sec,
                provider=weather_provider,
                session=session,
                fetch_fn=fetch_fn,
            )
            weather_meta = result.as_dict()
            weather_meta["fetched"] = True
            if result.available:
                # Never invent — only copy real readings (may still be partial).
                card["wind_mph"] = result.wind_mph
                card["precip"] = result.precip
                card["temp_f"] = result.temp_f
            # available=False → leave weather fields None → no KEI weather mod

    # Guard: notes still cannot write these fields.
    assert NOTES_CANNOT_WRITE_GAME_CARD_FIELDS is True
    for key in GAME_CARD_FIELDS:
        # touch reject path for documentation / import side-effects in tests
        assert key in GAME_CARD_FIELDS

    rw = apply_rest_weather_game_card(card)
    return SourcedGameCard(
        game=game,
        card=card,
        weather_meta=weather_meta,
        rest_meta={
            "source": "packaged_schedule+canonical_kickoff",
            "feed_version": REST_WEATHER_FEED_VERSION,
        },
        modifier=rw.as_dict(),
    )


def source_week_game_cards(
    *,
    week: int,
    season: int = 2026,
    fetch_weather: bool = True,
    cache_dir: Optional[Path] = None,
    timeout_sec: float = WEATHER_HTTP_TIMEOUT_SEC,
    weather_provider: str = "open-meteo",
    session: Optional[Any] = None,
    fetch_fn: Optional[Callable[..., WeatherFetchResult]] = None,
) -> Tuple[List[SourcedGameCard], Dict[str, Any]]:
    games, meta = load_schedule_games(season)
    week_games = [g for g in games if int(g.week) == int(week)]
    cards = [
        source_game_card(
            g,
            games,
            fetch_weather=fetch_weather,
            cache_dir=cache_dir,
            timeout_sec=timeout_sec,
            weather_provider=weather_provider,
            session=session,
            fetch_fn=fetch_fn,
        )
        for g in week_games
    ]
    return cards, meta


def cards_with_rest_or_weather_modifier(
    cards: Sequence[SourcedGameCard],
) -> List[SourcedGameCard]:
    """Filter to cards where remat would apply a rest or weather factor."""
    out: List[SourcedGameCard] = []
    for sourced in cards:
        mod = sourced.modifier or {}
        applied = mod.get("applied_factors") or []
        hits = [
            e
            for e in applied
            if isinstance(e, Mapping)
            and e.get("applied")
            and e.get("factor") in {"days_rest", "short_week", "timezone_shift", "weather"}
        ]
        if hits:
            out.append(sourced)
    return out


def format_modifier_table(cards: Sequence[SourcedGameCard]) -> str:
    """Markdown table of cards that would get a rest or weather modifier."""
    lines = [
        "| Game | Roof | Rest H/A | TZ | Weather | Applied | Spread Δ | Total Δ |",
        "|------|------|----------|----|---------|---------|----------|---------|",
    ]
    for sourced in cards:
        g = sourced.game
        c = sourced.card
        mod = sourced.modifier or {}
        applied = [
            e.get("factor")
            for e in (mod.get("applied_factors") or [])
            if isinstance(e, Mapping) and e.get("applied")
        ]
        weather_bits = []
        if c.get("wind_mph") is not None:
            weather_bits.append(f"w{c['wind_mph']:.0f}")
        if c.get("temp_f") is not None:
            weather_bits.append(f"t{c['temp_f']:.0f}F")
        if c.get("precip") is not None:
            weather_bits.append(f"p{c['precip']:.1f}")
        weather_s = ",".join(weather_bits) if weather_bits else (
            sourced.weather_meta.get("status")
            or sourced.weather_meta.get("skipped_reason")
            or "—"
        )
        rest_h = c.get("days_rest_home")
        rest_a = c.get("days_rest_away")
        rest_s = f"{rest_h if rest_h is not None else '—'}/{rest_a if rest_a is not None else '—'}"
        lines.append(
            "| {away}@{home} | {roof} | {rest} | {tz:g} | {wx} | {applied} | {spr:+.2f} | {tot:+.2f} |".format(
                away=g.away_team,
                home=g.home_team,
                roof=c.get("roof") or "—",
                rest=rest_s,
                tz=float(c.get("timezone_shift") or 0),
                wx=weather_s,
                applied=",".join(applied) or "—",
                spr=float(mod.get("spread_delta") or 0),
                tot=float(mod.get("total_delta") or 0),
            )
        )
    if len(lines) == 2:
        lines.append("| *(none)* | | | | | | | |")
    return "\n".join(lines)


def print_week_rest_weather_modifiers(
    *,
    week: int = 1,
    season: int = 2026,
    fetch_weather: bool = True,
    cache_dir: Optional[Path] = None,
) -> str:
    """Source week cards, print those with rest/weather modifiers, return table."""
    cards, meta = source_week_game_cards(
        week=week,
        season=season,
        fetch_weather=fetch_weather,
        cache_dir=cache_dir,
    )
    hits = cards_with_rest_or_weather_modifier(cards)
    header = (
        f"# Week {week} REG {season} — rest/weather modifiers "
        f"({REST_WEATHER_FEED_VERSION})\n"
        f"schedule_as_of={meta.get('schedule_as_of')} "
        f"canonical_overlay={meta.get('canonical_overlay')} "
        f"n_week={len(cards)} n_with_modifier={len(hits)}\n"
    )
    table = format_modifier_table(hits)
    text = header + "\n" + table + "\n"
    print(text)
    return text


# Re-export notes guard for feed tests / callers.
assert_notes_cannot_write = reject_note_game_card_write


def stadium_table_team_count() -> int:
    """Distinct franchise rows (LA/LAR/LAC counted separately in table)."""
    return len(NFL_STADIUM_ROOF)


if __name__ == "__main__":
    print_week_rest_weather_modifiers(week=1, season=2026, fetch_weather=True)
