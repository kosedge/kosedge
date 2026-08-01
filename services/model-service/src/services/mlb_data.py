from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Optional

import requests

MLB_STATS_API = "https://statsapi.mlb.com/api/v1"

# starter_quality construction:
#   era_whip (default / S0–S2): ERA + WHIP results signal
#   kbb_only (S3 trial): predictive K/BB/GB shape only (no ERA/WHIP)
STARTER_QUALITY_MODE = (os.getenv("MLB_STARTER_QUALITY_MODE") or "era_whip").strip().lower()


def apply_starter_quality_mode(mode: str) -> str:
    """Process-local override for densify stack ablation (clears live SP cache)."""
    global STARTER_QUALITY_MODE
    normalized = (mode or "era_whip").strip().lower()
    if normalized not in {"era_whip", "kbb_only"}:
        raise ValueError(f"unsupported starter quality mode: {mode}")
    STARTER_QUALITY_MODE = normalized
    cache_fn = globals().get("_live_starter_features")
    if cache_fn is not None and hasattr(cache_fn, "cache_clear"):
        cache_fn.cache_clear()
    return STARTER_QUALITY_MODE


def get_starter_quality_mode() -> str:
    return STARTER_QUALITY_MODE


def reset_starter_quality_mode_from_env() -> str:
    return apply_starter_quality_mode((os.getenv("MLB_STARTER_QUALITY_MODE") or "era_whip").strip().lower())
OPEN_METEO_FORECAST_API = "https://api.open-meteo.com/v1/forecast"
LEAGUE_BASELINE_OPS = 0.720
RECENT_FORM_WINDOW_DAYS = 30
LINEUP_ORDER_WEIGHTS: Dict[int, float] = {
    1: 1.08,
    2: 1.07,
    3: 1.12,
    4: 1.10,
    5: 1.03,
    6: 0.97,
    7: 0.93,
    8: 0.89,
    9: 0.86,
}

# Team abbreviations and stadium coordinates for weather pulls.
# Source: public stadium geo references (coarse coordinates are enough for V1).
TEAM_STADIUM_GEO: Dict[str, Dict[str, float]] = {
    "ARI": {"lat": 33.4455, "lon": -112.0667},
    "ATL": {"lat": 33.8908, "lon": -84.4677},
    "BAL": {"lat": 39.2841, "lon": -76.6215},
    "BOS": {"lat": 42.3467, "lon": -71.0972},
    "CHC": {"lat": 41.9484, "lon": -87.6553},
    "CIN": {"lat": 39.0979, "lon": -84.5080},
    "CLE": {"lat": 41.4962, "lon": -81.6852},
    "COL": {"lat": 39.7559, "lon": -104.9942},
    "CWS": {"lat": 41.8300, "lon": -87.6338},
    "DET": {"lat": 42.3390, "lon": -83.0485},
    "HOU": {"lat": 29.7572, "lon": -95.3555},
    "KC": {"lat": 39.0515, "lon": -94.4803},
    "LAA": {"lat": 33.8003, "lon": -117.8827},
    "LAD": {"lat": 34.0739, "lon": -118.2400},
    "MIA": {"lat": 25.7781, "lon": -80.2197},
    "MIL": {"lat": 43.0280, "lon": -87.9712},
    "MIN": {"lat": 44.9817, "lon": -93.2776},
    "NYM": {"lat": 40.7571, "lon": -73.8458},
    "NYY": {"lat": 40.8296, "lon": -73.9262},
    "OAK": {"lat": 37.7516, "lon": -122.2005},
    "PHI": {"lat": 39.9061, "lon": -75.1665},
    "PIT": {"lat": 40.4469, "lon": -80.0057},
    "SD": {"lat": 32.7073, "lon": -117.1573},
    "SEA": {"lat": 47.5914, "lon": -122.3325},
    "SF": {"lat": 37.7786, "lon": -122.3893},
    "STL": {"lat": 38.6226, "lon": -90.1928},
    "TB": {"lat": 27.7682, "lon": -82.6534},
    "TEX": {"lat": 32.7473, "lon": -97.0847},
    "TOR": {"lat": 43.6414, "lon": -79.3894},
    "WSH": {"lat": 38.8730, "lon": -77.0074},
}

PARK_FACTOR_RUNS: Dict[str, float] = {
    "ARI": 1.02,
    "ATL": 1.01,
    "BAL": 1.00,
    "BOS": 1.01,
    "CHC": 1.01,
    "CIN": 1.05,
    "CLE": 0.97,
    "COL": 1.12,
    "CWS": 0.99,
    "DET": 0.96,
    "HOU": 0.98,
    "KC": 0.97,
    "LAA": 1.00,
    "LAD": 0.99,
    "MIA": 0.95,
    "MIL": 1.00,
    "MIN": 1.00,
    "NYM": 0.98,
    "NYY": 1.03,
    "OAK": 0.94,
    "PHI": 1.03,
    "PIT": 0.96,
    "SD": 0.95,
    "SEA": 0.96,
    "SF": 0.93,
    "STL": 0.99,
    "TB": 0.97,
    "TEX": 1.04,
    "TOR": 1.01,
    "WSH": 1.00,
}

UMP_RUN_FACTOR_PRIORS: Dict[str, float] = {
    # Coarse priors seeded from public historical run-environment discussions.
    "laz diaz": 1.03,
    "c b bucknor": 1.02,
    "hunter wendelstedt": 1.02,
    "mark wegner": 0.99,
    "pat hoberg": 0.98,
    "tripp gibson": 1.01,
}

STARTER_QUALITY_PRIORS: Dict[str, Dict[str, Any]] = {
    # Compact identity priors for premium v1.5 until full Statcast/arsenal integration.
    # Prefer live Stats API when available; these cover common names when search misses.
    "gerrit cole": {"quality": 0.90, "k_factor": 1.12, "bb_factor": 0.90, "gb_factor": 1.00, "handedness": "R"},
    "zack wheeler": {"quality": 0.91, "k_factor": 1.10, "bb_factor": 0.92, "gb_factor": 1.02, "handedness": "R"},
    "corbin burnes": {"quality": 0.90, "k_factor": 1.11, "bb_factor": 0.93, "gb_factor": 1.04, "handedness": "R"},
    "luis castillo": {"quality": 0.92, "k_factor": 1.08, "bb_factor": 0.95, "gb_factor": 1.01, "handedness": "R"},
    "framber valdez": {"quality": 0.93, "k_factor": 1.03, "bb_factor": 0.94, "gb_factor": 1.14, "handedness": "L"},
    "blake snell": {"quality": 0.91, "k_factor": 1.14, "bb_factor": 0.87, "gb_factor": 1.02, "handedness": "L"},
    "max fried": {"quality": 0.92, "k_factor": 1.05, "bb_factor": 0.93, "gb_factor": 1.10, "handedness": "L"},
    "jose berrios": {"quality": 0.97, "k_factor": 1.00, "bb_factor": 1.00, "gb_factor": 1.02, "handedness": "R"},
    "yoshinobu yamamoto": {"quality": 0.91, "k_factor": 1.09, "bb_factor": 0.91, "gb_factor": 1.06, "handedness": "R"},
    "spencer strider": {"quality": 0.88, "k_factor": 1.20, "bb_factor": 0.95, "gb_factor": 0.95, "handedness": "R"},
    "tarik skubal": {"quality": 0.88, "k_factor": 1.16, "bb_factor": 0.88, "gb_factor": 1.02, "handedness": "L"},
    "paul skenes": {"quality": 0.89, "k_factor": 1.15, "bb_factor": 0.92, "gb_factor": 1.00, "handedness": "R"},
    "garrett crochet": {"quality": 0.90, "k_factor": 1.14, "bb_factor": 0.91, "gb_factor": 1.01, "handedness": "L"},
    "chris sale": {"quality": 0.91, "k_factor": 1.13, "bb_factor": 0.90, "gb_factor": 0.98, "handedness": "L"},
    "logan gilbert": {"quality": 0.92, "k_factor": 1.10, "bb_factor": 0.93, "gb_factor": 1.00, "handedness": "R"},
    "george kirby": {"quality": 0.93, "k_factor": 1.06, "bb_factor": 0.88, "gb_factor": 1.04, "handedness": "R"},
    "tyler glasnow": {"quality": 0.90, "k_factor": 1.14, "bb_factor": 0.89, "gb_factor": 1.02, "handedness": "R"},
    "dylan cease": {"quality": 0.93, "k_factor": 1.13, "bb_factor": 0.96, "gb_factor": 0.97, "handedness": "R"},
    "cole ragans": {"quality": 0.91, "k_factor": 1.12, "bb_factor": 0.94, "gb_factor": 1.00, "handedness": "L"},
    "nathan eovaldi": {"quality": 0.94, "k_factor": 1.05, "bb_factor": 0.93, "gb_factor": 1.03, "handedness": "R"},
    "shota imanaga": {"quality": 0.92, "k_factor": 1.08, "bb_factor": 0.90, "gb_factor": 0.96, "handedness": "L"},
    "hunter brown": {"quality": 0.94, "k_factor": 1.07, "bb_factor": 0.95, "gb_factor": 1.02, "handedness": "R"},
    "jacob degrom": {"quality": 0.89, "k_factor": 1.14, "bb_factor": 0.88, "gb_factor": 1.01, "handedness": "R"},
    "jacob de grom": {"quality": 0.89, "k_factor": 1.14, "bb_factor": 0.88, "gb_factor": 1.01, "handedness": "R"},
    "ranger suarez": {"quality": 0.95, "k_factor": 1.02, "bb_factor": 0.96, "gb_factor": 1.08, "handedness": "L"},
    "sonny gray": {"quality": 0.94, "k_factor": 1.06, "bb_factor": 0.94, "gb_factor": 1.05, "handedness": "R"},
}


def _neutral_starter_features(*, source: str) -> Dict[str, Any]:
    return {
        "starter_quality": 1.0,
        "k_factor": 1.0,
        "bb_factor": 1.0,
        "gb_factor": 1.0,
        "handedness": "U",
        "source": source,
    }


def _iso_date(d: date) -> str:
    return d.isoformat()


def _safe_float(v: Any) -> Optional[float]:
    try:
        if v is None:
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _safe_rate(v: Any) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, str) and v.startswith("."):
        try:
            return float(f"0{v}")
        except ValueError:
            return None
    return _safe_float(v)


def _rate_index(value: Optional[float], *, baseline: float = LEAGUE_BASELINE_OPS) -> Optional[float]:
    if value is None or baseline <= 0:
        return None
    return max(0.78, min(1.25, value / baseline))


def _shrink_index(raw_index: Optional[float], *, sample_size: Optional[float], target_sample: float, anchor: float) -> float:
    if raw_index is None:
        return anchor
    effective_sample = max(0.0, float(sample_size or 0.0))
    weight = min(1.0, effective_sample / max(1.0, target_sample))
    return max(0.78, min(1.25, anchor + (raw_index - anchor) * weight))


def _parse_batting_slot(raw_order: Any) -> Optional[int]:
    if raw_order is None:
        return None
    try:
        slot = int(str(raw_order)) // 100
    except ValueError:
        return None
    if 1 <= slot <= 9:
        return slot
    return None


def _profile_from_stat(stat: Dict[str, Any], *, source: str) -> Dict[str, Any]:
    ops = _safe_rate(stat.get("ops"))
    obp = _safe_rate(stat.get("obp"))
    slg = _safe_rate(stat.get("slg"))
    avg = _safe_rate(stat.get("avg"))
    plate_appearances = _safe_float(stat.get("plateAppearances"))
    runs = _safe_float(stat.get("runs"))
    strikeouts = _safe_float(stat.get("strikeOuts"))
    walks = _safe_float(stat.get("baseOnBalls"))
    ops_index = _rate_index(ops)
    return {
        "ops": ops,
        "obp": obp,
        "slg": slg,
        "avg": avg,
        "plate_appearances": plate_appearances,
        "runs": runs,
        "strikeouts": strikeouts,
        "walks": walks,
        "ops_index": ops_index,
        "source": source,
    }


@lru_cache(maxsize=2048)
def _fetch_team_hitting_profile_cached(
    team_id: int,
    season: int,
    sit_code: Optional[str],
    start_date_iso: Optional[str],
    end_date_iso: Optional[str],
) -> Dict[str, Any]:
    if start_date_iso and end_date_iso:
        params = {
            "stats": "byDateRange",
            "group": "hitting",
            "season": season,
            "startDate": start_date_iso,
            "endDate": end_date_iso,
        }
        source = f"byDateRange:{start_date_iso}:{end_date_iso}"
    elif sit_code:
        params = {
            "stats": "statSplits",
            "group": "hitting",
            "season": season,
            "sitCodes": sit_code,
        }
        source = f"statSplits:{sit_code}"
    else:
        params = {
            "stats": "season",
            "group": "hitting",
            "season": season,
        }
        source = "season"

    response = requests.get(
        f"{MLB_STATS_API}/teams/{team_id}/stats",
        params=params,
        timeout=15,
    )
    response.raise_for_status()
    stats = (response.json() or {}).get("stats") or []
    if not stats:
        return {"source": source}
    split = (stats[0].get("splits") or [{}])[0]
    stat = split.get("stat") or {}
    return _profile_from_stat(stat, source=source)


def fetch_team_hitting_profile(
    team_id: Optional[int],
    *,
    season: int,
    sit_code: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> Dict[str, Any]:
    if not team_id:
        return {"source": "neutral", "ops_index": 1.0}
    try:
        return _fetch_team_hitting_profile_cached(
            int(team_id),
            int(season),
            sit_code,
            start_date.isoformat() if start_date else None,
            end_date.isoformat() if end_date else None,
        )
    except Exception:
        return {"source": "unavailable", "ops_index": 1.0}


def extract_probable_pitchers_from_live_feed(payload: Dict[str, Any]) -> Dict[str, Optional[str]]:
    """Pull home/away probable pitchers from a Stats API live feed payload."""
    game_data = payload.get("gameData") or {}
    probable = game_data.get("probablePitchers") or {}
    out: Dict[str, Optional[str]] = {"home": None, "away": None}
    for side in ("home", "away"):
        block = probable.get(side) or {}
        name = block.get("fullName") if isinstance(block, dict) else None
        if not name:
            teams = (((payload.get("liveData") or {}).get("boxscore") or {}).get("teams") or {})
            team_block = teams.get(side) or {}
            team_pp = team_block.get("probablePitcher") or {}
            if isinstance(team_pp, dict):
                name = team_pp.get("fullName")
        out[side] = str(name).strip() if name else None
    return out


@lru_cache(maxsize=512)
def fetch_game_lineup_features(game_pk: str) -> Dict[str, Dict[str, Any]]:
    response = requests.get(
        f"{MLB_STATS_API}.1/game/{game_pk}/feed/live",
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json() or {}
    teams = (((payload.get("liveData") or {}).get("boxscore") or {}).get("teams") or {})
    live_pitchers = extract_probable_pitchers_from_live_feed(payload)
    out: Dict[str, Dict[str, Any]] = {}
    for side in ("home", "away"):
        players = ((teams.get(side) or {}).get("players") or {})
        lineup_by_slot: Dict[int, Dict[str, Any]] = {}
        for player in players.values():
            slot = _parse_batting_slot(player.get("battingOrder"))
            if slot is None:
                continue
            previous = lineup_by_slot.get(slot)
            if previous is None or str(player.get("battingOrder") or "") < str(previous.get("battingOrder") or ""):
                lineup_by_slot[slot] = player

        weighted_ops = 0.0
        total_weight = 0.0
        player_summaries: List[Dict[str, Any]] = []
        for slot in sorted(lineup_by_slot):
            player = lineup_by_slot[slot]
            batting = (player.get("seasonStats") or {}).get("batting") or {}
            ops = _safe_rate(batting.get("ops"))
            plate_appearances = _safe_float(batting.get("plateAppearances"))
            weight = LINEUP_ORDER_WEIGHTS.get(slot, 1.0)
            if ops is not None:
                weighted_ops += ops * weight
                total_weight += weight
            player_summaries.append(
                {
                    "slot": slot,
                    "name": (player.get("person") or {}).get("fullName"),
                    "ops": ops,
                    "plate_appearances": plate_appearances,
                    "position": ((player.get("position") or {}).get("abbreviation") or ""),
                }
            )

        lineup_ops = (weighted_ops / total_weight) if total_weight > 0 else None
        out[side] = {
            "lineup_strength_index": _rate_index(lineup_ops),
            "weighted_ops": lineup_ops,
            "known_players": len(lineup_by_slot),
            "players": player_summaries,
            "lineup_confirmed": len(lineup_by_slot) >= 8,
            "probable_pitcher": live_pitchers.get(side),
            "source": "feed/live",
        }
    return out


def build_team_offense_context(
    team_id: Optional[int],
    *,
    as_of: date,
    opponent_starter_handedness: str,
    lineup_features: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    season_profile = fetch_team_hitting_profile(team_id, season=as_of.year)
    season_index = _shrink_index(
        season_profile.get("ops_index"),
        sample_size=season_profile.get("plate_appearances"),
        target_sample=2800.0,
        anchor=1.0,
    )

    opponent_handedness = (opponent_starter_handedness or "U").upper()
    split_vs_l_profile = fetch_team_hitting_profile(team_id, season=as_of.year, sit_code="vl")
    split_vs_r_profile = fetch_team_hitting_profile(team_id, season=as_of.year, sit_code="vr")
    split_vs_l = _shrink_index(
        split_vs_l_profile.get("ops_index"),
        sample_size=split_vs_l_profile.get("plate_appearances"),
        target_sample=900.0,
        anchor=season_index,
    )
    split_vs_r = _shrink_index(
        split_vs_r_profile.get("ops_index"),
        sample_size=split_vs_r_profile.get("plate_appearances"),
        target_sample=900.0,
        anchor=season_index,
    )
    if opponent_handedness == "L":
        split_profile = split_vs_l_profile
        split_index = split_vs_l
    elif opponent_handedness == "R":
        split_profile = split_vs_r_profile
        split_index = split_vs_r
    else:
        split_profile = {}
        split_index = season_index

    recent_start = as_of - timedelta(days=RECENT_FORM_WINDOW_DAYS)
    recent_profile = fetch_team_hitting_profile(
        team_id,
        season=as_of.year,
        start_date=recent_start,
        end_date=as_of,
    )
    recent_index = _shrink_index(
        recent_profile.get("ops_index"),
        sample_size=recent_profile.get("plate_appearances"),
        target_sample=350.0,
        anchor=season_index,
    )

    lineup_features = lineup_features or {}
    lineup_index = _shrink_index(
        lineup_features.get("lineup_strength_index"),
        sample_size=float(lineup_features.get("known_players") or 0),
        target_sample=9.0,
        anchor=split_index,
    )
    composite_index = max(
        0.78,
        min(
            1.25,
            0.46 * season_index + 0.24 * split_index + 0.18 * recent_index + 0.12 * lineup_index,
        ),
    )
    return {
        "offense_index": round(season_index, 4),
        "offense_split_index": round(split_index, 4),
        "offense_split_vs_l": round(split_vs_l, 4),
        "offense_split_vs_r": round(split_vs_r, 4),
        "recent_form_index": round(recent_index, 4),
        "lineup_strength_index": round(lineup_index, 4),
        "offense_composite_index": round(composite_index, 4),
        "season_profile": season_profile,
        "split_profile": split_profile,
        "split_vs_l_profile": split_vs_l_profile,
        "split_vs_r_profile": split_vs_r_profile,
        "recent_profile": recent_profile,
        "lineup_profile": lineup_features,
        "opponent_starter_handedness": opponent_handedness,
    }


def fetch_mlb_schedule(start_date: date, end_date: date) -> List[Dict[str, Any]]:
    params = {
        "sportId": 1,  # MLB
        "startDate": _iso_date(start_date),
        "endDate": _iso_date(end_date),
        "hydrate": "probablePitcher,team,linescore,venue,weather,decisions,officials",
    }
    response = requests.get(f"{MLB_STATS_API}/schedule", params=params, timeout=20)
    response.raise_for_status()
    payload = response.json()
    out: List[Dict[str, Any]] = []
    for date_block in payload.get("dates") or []:
        for game in date_block.get("games") or []:
            teams = game.get("teams") or {}
            home = teams.get("home") or {}
            away = teams.get("away") or {}
            home_team = (home.get("team") or {}).get("name")
            away_team = (away.get("team") or {}).get("name")
            home_abbr = (home.get("team") or {}).get("abbreviation")
            away_abbr = (away.get("team") or {}).get("abbreviation")
            home_team_id = (home.get("team") or {}).get("id")
            away_team_id = (away.get("team") or {}).get("id")
            if not home_team or not away_team or not home_abbr or not away_abbr:
                continue

            probable_home = (home.get("probablePitcher") or {}).get("fullName")
            probable_away = (away.get("probablePitcher") or {}).get("fullName")
            game_time = game.get("gameDate")

            umpire_name = None
            for official in game.get("officials") or []:
                if (official.get("officialType") or "").lower() == "home plate":
                    umpire_name = (official.get("official") or {}).get("fullName")
                    break

            out.append(
                {
                    "external_game_id": str(game.get("gamePk")),
                    "game_time": game_time,
                    "status": ((game.get("status") or {}).get("detailedState") or "scheduled").lower(),
                    "home_team": home_team,
                    "away_team": away_team,
                    "home_abbr": home_abbr,
                    "away_abbr": away_abbr,
                    "home_team_id": int(home_team_id) if home_team_id is not None else None,
                    "away_team_id": int(away_team_id) if away_team_id is not None else None,
                    "probable_pitcher_home": probable_home,
                    "probable_pitcher_away": probable_away,
                    "umpire_home_plate": umpire_name,
                    "lineup_confirmed": bool((game.get("lineups") or {}).get("homePlayers")),
                }
            )
    return out


def fetch_forecast_for_game(
    *,
    team_abbr: str,
    game_time_iso: str,
) -> Dict[str, Optional[float]]:
    geo = TEAM_STADIUM_GEO.get(team_abbr)
    if not geo:
        return {
            "weather_temp_f": None,
            "weather_wind_mph": None,
            "weather_wind_dir_deg": None,
            "weather_humidity_pct": None,
        }
    try:
        game_dt = datetime.fromisoformat(game_time_iso.replace("Z", "+00:00"))
    except ValueError:
        return {
            "weather_temp_f": None,
            "weather_wind_mph": None,
            "weather_wind_dir_deg": None,
            "weather_humidity_pct": None,
        }

    params = {
        "latitude": geo["lat"],
        "longitude": geo["lon"],
        "hourly": "temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m",
        "timezone": "UTC",
        "forecast_days": 7,
    }
    r = requests.get(OPEN_METEO_FORECAST_API, params=params, timeout=20)
    r.raise_for_status()
    payload = r.json()
    hourly = payload.get("hourly") or {}
    times: Iterable[str] = hourly.get("time") or []

    # Find nearest forecast hour to game time.
    target = game_dt.replace(minute=0, second=0, microsecond=0)
    idx = None
    for i, t in enumerate(times):
        if t == target.strftime("%Y-%m-%dT%H:%M"):
            idx = i
            break
    if idx is None:
        return {
            "weather_temp_f": None,
            "weather_wind_mph": None,
            "weather_wind_dir_deg": None,
            "weather_humidity_pct": None,
        }

    temp_c = _safe_float((hourly.get("temperature_2m") or [None])[idx])
    wind_kmh = _safe_float((hourly.get("wind_speed_10m") or [None])[idx])
    wind_dir = _safe_float((hourly.get("wind_direction_10m") or [None])[idx])
    humidity = _safe_float((hourly.get("relative_humidity_2m") or [None])[idx])

    return {
        "weather_temp_f": (temp_c * 9.0 / 5.0 + 32.0) if temp_c is not None else None,
        "weather_wind_mph": (wind_kmh * 0.621371) if wind_kmh is not None else None,
        "weather_wind_dir_deg": wind_dir,
        "weather_humidity_pct": humidity,
    }


def normalize_team_key(name: str) -> str:
    return " ".join((name or "").lower().replace(".", "").split())


def normalize_pitcher_name(name: str) -> str:
    """Normalize pitcher identity for prior lookup / Stats API search."""
    key = normalize_team_key(name)
    for suffix in (" jr", " sr", " ii", " iii", " iv"):
        if key.endswith(suffix):
            key = key[: -len(suffix)].strip()
    return key


def _pitcher_search_aliases(starter_name: str) -> List[str]:
    """Ordered search strings: full name, stripped suffixes, last-name fallback."""
    raw = (starter_name or "").strip()
    if not raw:
        return []
    aliases: List[str] = []
    seen: set[str] = set()

    def _add(value: str) -> None:
        cleaned = " ".join(value.split())
        if cleaned and cleaned.lower() not in seen:
            seen.add(cleaned.lower())
            aliases.append(cleaned)

    _add(raw)
    normalized = normalize_pitcher_name(raw)
    if normalized:
        _add(normalized)
    parts = normalized.split()
    if len(parts) >= 2:
        _add(parts[-1])  # last-name search when full-name miss
        _add(f"{parts[0]} {parts[-1]}")
    return aliases


def park_factor_for_team(team_abbr: Optional[str]) -> float:
    if not team_abbr:
        return 1.0
    return PARK_FACTOR_RUNS.get(team_abbr.upper(), 1.0)


def team_rest_days_from_schedule(
    schedule: List[Dict[str, Any]],
    *,
    team_id: Optional[int],
    game_time_iso: Optional[str],
) -> float:
    """Calendar rest days before this game for a team (1.0 = normal next-day)."""
    if not team_id or not game_time_iso:
        return 1.0
    try:
        game_dt = datetime.fromisoformat(game_time_iso.replace("Z", "+00:00"))
    except ValueError:
        return 1.0
    prior: Optional[datetime] = None
    for row in schedule:
        if row.get("home_team_id") != team_id and row.get("away_team_id") != team_id:
            continue
        other_iso = row.get("game_time")
        if not other_iso:
            continue
        try:
            other_dt = datetime.fromisoformat(str(other_iso).replace("Z", "+00:00"))
        except ValueError:
            continue
        if other_dt >= game_dt:
            continue
        if prior is None or other_dt > prior:
            prior = other_dt
    if prior is None:
        return 3.0
    return max(0.0, float((game_dt.date() - prior.date()).days))


def umpire_run_factor(umpire_name: Optional[str]) -> float:
    if not umpire_name:
        return 1.0
    key = normalize_team_key(umpire_name)
    if key in UMP_RUN_FACTOR_PRIORS:
        return UMP_RUN_FACTOR_PRIORS[key]
    # Stable deterministic fallback: tiny shrink around neutral.
    score = sum(ord(c) for c in key if c.isalpha())
    offset = ((score % 7) - 3) * 0.003
    return max(0.97, min(1.03, 1.0 + offset))


def lineup_confidence(
    *,
    lineup_confirmed: bool,
    probable_pitcher_home: Optional[str],
    probable_pitcher_away: Optional[str],
) -> Dict[str, float]:
    # Confidence in modeled batting context (0..1). Starter confirmation helps even if lineup not final.
    base = 0.75
    if lineup_confirmed:
        base += 0.20
    if probable_pitcher_home:
        base += 0.025
    if probable_pitcher_away:
        base += 0.025
    c = max(0.35, min(1.0, base))
    return {"home": c, "away": c}


def _select_pitcher_candidate(people: List[Dict[str, Any]], normalized_name: str) -> Optional[Dict[str, Any]]:
    if not people:
        return None

    def is_pitcher(person: Dict[str, Any]) -> bool:
        primary_position = (person.get("primaryPosition") or {}).get("code")
        return primary_position in {"1", None, ""}

    exact_pitchers = [
        person
        for person in people
        if is_pitcher(person)
        and normalize_team_key(str(person.get("fullName") or "")) == normalized_name
    ]
    if exact_pitchers:
        exact_pitchers.sort(key=lambda person: int(bool(person.get("active"))), reverse=True)
        return exact_pitchers[0]

    pitchers = [person for person in people if is_pitcher(person)]
    if not pitchers:
        return None
    pitchers.sort(key=lambda person: int(bool(person.get("active"))), reverse=True)
    return pitchers[0]


def _extract_pitching_stat_bucket(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    for stat_group in payload.get("stats") or []:
        for split in stat_group.get("splits") or []:
            stat = split.get("stat") or {}
            if stat:
                return stat
    return None


def _starter_features_from_stat(
    *,
    starter_name: str,
    player_id: int,
    season: int,
    handedness: str,
    stat: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    era = _safe_float(stat.get("era"))
    whip = _safe_float(stat.get("whip"))
    k_per_9 = _safe_float(stat.get("strikeoutsPer9Inn"))
    bb_per_9 = _safe_float(stat.get("baseOnBallsPer9Inn"))
    ground_outs_to_air_outs = _safe_float(stat.get("groundOutsToAirouts"))

    if era is None and whip is None and k_per_9 is None and bb_per_9 is None:
        return None

    k_factor = 1.0 if k_per_9 is None else 1.0 + (k_per_9 - 8.5) * 0.028
    bb_factor = 1.0 if bb_per_9 is None else 1.0 + (bb_per_9 - 3.1) * 0.045
    gb_factor = (
        1.0
        if ground_outs_to_air_outs is None
        else 1.0 + (ground_outs_to_air_outs - 1.0) * 0.06
    )

    if STARTER_QUALITY_MODE == "kbb_only":
        # Predictive run-allowed factor: more K / GB suppress; more BB inflate.
        starter_quality = 1.0
        if k_per_9 is not None:
            starter_quality -= (k_per_9 - 8.5) * 0.035
        if bb_per_9 is not None:
            starter_quality += (bb_per_9 - 3.1) * 0.055
        if ground_outs_to_air_outs is not None:
            starter_quality -= (ground_outs_to_air_outs - 1.0) * 0.04
    else:
        starter_quality = 1.0
        if era is not None:
            starter_quality += (era - 4.10) * 0.045
        if whip is not None:
            starter_quality += (whip - 1.28) * 0.18

    return {
        "starter_quality": max(0.82, min(1.18, round(starter_quality, 4))),
        "k_factor": max(0.88, min(1.18, round(k_factor, 4))),
        "bb_factor": max(0.86, min(1.18, round(bb_factor, 4))),
        "gb_factor": max(0.88, min(1.18, round(gb_factor, 4))),
        "handedness": handedness if handedness in {"L", "R"} else "U",
        "source": "mlb-stats-api",
        "player_id": player_id,
        "player_name": starter_name,
        "season": season,
        "quality_mode": STARTER_QUALITY_MODE,
    }


@lru_cache(maxsize=512)
def _live_starter_features(starter_name: str, season: int) -> Optional[Dict[str, Any]]:
    normalized_name = normalize_pitcher_name(starter_name)
    if not normalized_name:
        return None

    candidate: Optional[Dict[str, Any]] = None
    for alias in _pitcher_search_aliases(starter_name):
        search_response = requests.get(
            f"{MLB_STATS_API}/people/search",
            params={"sportId": 1, "names": alias},
            timeout=10,
        )
        search_response.raise_for_status()
        people = (search_response.json() or {}).get("people") or []
        candidate = _select_pitcher_candidate(people, normalized_name)
        if candidate is None and len(alias.split()) == 1:
            # Last-name-only search: require unique active pitcher match.
            pitchers = [
                p
                for p in people
                if ((p.get("primaryPosition") or {}).get("code") in {"1", None, ""})
                and normalize_pitcher_name(str(p.get("fullName") or "")).endswith(f" {alias.lower()}")
            ]
            active = [p for p in pitchers if p.get("active")]
            pool = active or pitchers
            if len(pool) == 1:
                candidate = pool[0]
        if candidate is not None:
            break
    if not candidate:
        return None

    player_id = candidate.get("id")
    if player_id is None:
        return None
    handedness = str(((candidate.get("pitchHand") or {}).get("code") or "U")).upper()

    stat_queries = [
        {"stats": "season", "group": "pitching", "season": season},
        {"stats": "season", "group": "pitching", "season": season - 1},
        {"stats": "career", "group": "pitching"},
    ]
    for params in stat_queries:
        response = requests.get(
            f"{MLB_STATS_API}/people/{player_id}/stats",
            params=params,
            timeout=10,
        )
        response.raise_for_status()
        stat = _extract_pitching_stat_bucket(response.json() or {})
        if not stat:
            continue
        # Require a minimum sample so tiny early-season buckets don't dominate.
        ip = _parse_ip(stat.get("inningsPitched"))
        if params.get("stats") == "season" and ip < 8.0:
            continue
        stat_season = int(params.get("season") or season)
        features = _starter_features_from_stat(
            starter_name=str(candidate.get("fullName") or starter_name),
            player_id=int(player_id),
            season=stat_season,
            handedness=handedness,
            stat=stat,
        )
        if features is not None:
            return features
    return None


def _fetch_team_recent_final_games(team_id: int, as_of: date, limit: int = 3) -> List[int]:
    start = as_of - timedelta(days=18)
    params = {
        "sportId": 1,
        "teamId": team_id,
        "startDate": start.isoformat(),
        "endDate": as_of.isoformat(),
    }
    response = requests.get(f"{MLB_STATS_API}/schedule", params=params, timeout=20)
    response.raise_for_status()
    payload = response.json()

    game_pks: List[int] = []
    for d in payload.get("dates") or []:
        for g in d.get("games") or []:
            state = ((g.get("status") or {}).get("codedGameState") or "").upper()
            if state == "F":
                pk = g.get("gamePk")
                if pk is not None:
                    game_pks.append(int(pk))
    game_pks = sorted(set(game_pks), reverse=True)
    return game_pks[:limit]


def _parse_ip(v: Any) -> float:
    # MLB IP format: "2.1" => 2 + 1/3
    if v is None:
        return 0.0
    s = str(v)
    if "." not in s:
        try:
            return float(s)
        except ValueError:
            return 0.0
    whole, frac = s.split(".", 1)
    try:
        innings = float(whole)
    except ValueError:
        innings = 0.0
    if frac == "1":
        innings += 1.0 / 3.0
    elif frac == "2":
        innings += 2.0 / 3.0
    return innings


def _safe_int(v: Any) -> int:
    try:
        if v is None:
            return 0
        return int(v)
    except (TypeError, ValueError):
        return 0


def fetch_team_bullpen_fatigue(team_id: Optional[int], as_of: date) -> Dict[str, float]:
    if not team_id:
        return {
            "bullpen_ip_last3": 3.0,
            "bullpen_appearances_last3": 6.0,
            "bullpen_fatigue_score": 0.50,
            "bullpen_availability_score": 0.65,
            "bullpen_high_leverage_availability_score": 0.62,
        }

    pks = _fetch_team_recent_final_games(team_id, as_of, limit=3)
    if not pks:
        return {
            "bullpen_ip_last3": 3.0,
            "bullpen_appearances_last3": 6.0,
            "bullpen_fatigue_score": 0.50,
            "bullpen_availability_score": 0.65,
            "bullpen_high_leverage_availability_score": 0.62,
        }

    bullpen_ip_total = 0.0
    bullpen_apps_total = 0.0
    high_lev_apps = 0.0
    high_lev_ip = 0.0
    for pk in pks:
        box = requests.get(f"{MLB_STATS_API}/game/{pk}/boxscore", timeout=20)
        box.raise_for_status()
        payload = box.json()

        side = None
        for s in ("home", "away"):
            info = (payload.get("teams") or {}).get(s) or {}
            team = info.get("team") or {}
            if team.get("id") == team_id:
                side = info
                break
        if not side:
            continue

        players = side.get("players") or {}
        for p in players.values():
            stats = (p.get("stats") or {}).get("pitching") or {}
            if not stats:
                continue
            if str(stats.get("gamesStarted", "0")) == "1":
                continue
            ip = _parse_ip(stats.get("inningsPitched"))
            if ip <= 0:
                continue
            bullpen_ip_total += ip
            bullpen_apps_total += 1.0
            # Proxy for high-leverage usage in recent window.
            is_high_lev = (
                _safe_int(stats.get("holds")) > 0
                or _safe_int(stats.get("saves")) > 0
                or _safe_int(stats.get("blownSaves")) > 0
                or _safe_int(stats.get("gamesFinished")) > 0
            )
            if is_high_lev:
                high_lev_apps += 1.0
                high_lev_ip += ip

    # 0.5 is neutral, >0.5 means more taxed bullpen.
    fatigue = 0.5 + min(0.45, (bullpen_ip_total - 9.0) * 0.03 + (bullpen_apps_total - 9.0) * 0.015)
    fatigue = max(0.05, min(0.95, fatigue))
    availability = 0.80 - min(0.55, (bullpen_ip_total - 7.5) * 0.035 + (bullpen_apps_total - 8.0) * 0.02)
    availability = max(0.10, min(0.95, availability))
    high_lev_availability = 0.78 - min(
        0.60,
        (high_lev_ip - 3.5) * 0.07 + (high_lev_apps - 4.0) * 0.04,
    )
    high_lev_availability = max(0.08, min(0.95, high_lev_availability))
    return {
        "bullpen_ip_last3": round(bullpen_ip_total, 3),
        "bullpen_appearances_last3": round(bullpen_apps_total, 3),
        "bullpen_fatigue_score": round(fatigue, 4),
        "bullpen_availability_score": round(availability, 4),
        "bullpen_high_leverage_availability_score": round(high_lev_availability, 4),
    }


def starter_identity_features(starter_name: Optional[str], *, season: Optional[int] = None) -> Dict[str, Any]:
    if not starter_name:
        return _neutral_starter_features(source="neutral")

    key = normalize_pitcher_name(starter_name)
    target_season = season or date.today().year

    # Prefer live Stats API (true arsenal/shape) over static priors when resolvable.
    try:
        live_features = _live_starter_features(starter_name, target_season)
    except Exception:
        live_features = None
    if live_features is not None:
        return live_features

    known = STARTER_QUALITY_PRIORS.get(key) or STARTER_QUALITY_PRIORS.get(normalize_team_key(starter_name))
    if known:
        k_factor = float(known["k_factor"])
        bb_factor = float(known["bb_factor"])
        gb_factor = float(known["gb_factor"])
        if STARTER_QUALITY_MODE == "kbb_only":
            # Reconstruct quality from prior shape so S3 does not inherit ERA priors.
            quality = 1.0 - (k_factor - 1.0) * 0.55 + (bb_factor - 1.0) * 0.70 - (gb_factor - 1.0) * 0.15
            quality = max(0.85, min(1.15, round(quality, 4)))
        else:
            quality = float(known["quality"])
        return {
            "starter_quality": quality,
            "k_factor": k_factor,
            "bb_factor": bb_factor,
            "gb_factor": gb_factor,
            "handedness": str(known["handedness"]),
            "source": "static-prior",
            "quality_mode": STARTER_QUALITY_MODE,
        }

    # Deterministic fallback from identity signature (low firmness path).
    score = sum(ord(c) for c in key if c.isalpha())
    k_factor = 1.0 + ((score % 11) - 5) * 0.008
    bb_factor = 1.0 - ((score % 9) - 4) * 0.007
    gb_factor = 1.0 + ((score % 7) - 3) * 0.01
    if STARTER_QUALITY_MODE == "kbb_only":
        quality = 1.0 - (k_factor - 1.0) * 0.55 + (bb_factor - 1.0) * 0.70 - (gb_factor - 1.0) * 0.15
    else:
        quality = 1.0 + ((score % 13) - 6) * 0.01
    hand = "L" if key.split(" ")[-1].endswith(("ez", "er", "is")) and (score % 5 == 0) else "R"
    return {
        "starter_quality": max(0.85, min(1.15, round(quality, 4))),
        "k_factor": max(0.88, min(1.16, round(k_factor, 4))),
        "bb_factor": max(0.88, min(1.15, round(bb_factor, 4))),
        "gb_factor": max(0.90, min(1.16, round(gb_factor, 4))),
        "handedness": hand,
        "source": "heuristic-fallback",
        "quality_mode": STARTER_QUALITY_MODE,
    }


def fetch_mlb_standings(season: int) -> List[Dict[str, Any]]:
    response = requests.get(
        f"{MLB_STATS_API}/standings",
        params={"leagueId": 103, "season": int(season), "standingsTypes": "regularSeason"},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json() or {}
    out: List[Dict[str, Any]] = []
    for record in payload.get("records") or []:
        division = (record.get("division") or {}).get("name")
        for team_rec in record.get("teamRecords") or []:
            team = team_rec.get("team") or {}
            team_id = team.get("id")
            if team_id is None:
                continue
            out.append(
                {
                    "season": int(season),
                    "team_id": int(team_id),
                    "team_name": team.get("name"),
                    "division": division,
                    "wins": _safe_int(team_rec.get("wins")),
                    "losses": _safe_int(team_rec.get("losses")),
                    "winning_pct": _safe_float(team_rec.get("winningPercentage")),
                    "runs_scored": _safe_int(team_rec.get("runsScored")),
                    "runs_allowed": _safe_int(team_rec.get("runsAllowed")),
                    "run_diff": _safe_int(team_rec.get("runDifferential")),
                }
            )
    return out


def fetch_team_roster(team_id: int, season: int) -> List[Dict[str, Any]]:
    response = requests.get(
        f"{MLB_STATS_API}/teams/{int(team_id)}/roster",
        params={"rosterType": "active", "season": int(season)},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json() or {}
    out: List[Dict[str, Any]] = []
    for row in payload.get("roster") or []:
        person = row.get("person") or {}
        position = row.get("position") or {}
        pid = person.get("id")
        if pid is None:
            continue
        out.append(
            {
                "team_id": int(team_id),
                "season": int(season),
                "player_id": int(pid),
                "player_name": person.get("fullName"),
                "position_abbr": position.get("abbreviation"),
                "status_code": (row.get("status") or {}).get("code"),
                "status_desc": (row.get("status") or {}).get("description"),
            }
        )
    return out
