from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Optional

import requests

MLB_STATS_API = "https://statsapi.mlb.com/api/v1"

# starter_quality construction:
#   era_whip (default / S0): ERA + WHIP results signal
#   kbb_only (S3 trial): predictive K/BB/GB shape only (no ERA/WHIP)
#   fip_proxy (SP talent v2): FIP from HR/BB/HBP/K/IP counting stats
#   xfip_proxy (SP talent v2): xFIP-style, HR replaced by GB/AO-implied expected HR
#   stuff_proxy (Statcast as-of): whiff/chase/zone/EV/barrel → quality (else KBB)
STARTER_QUALITY_MODES = frozenset(
    {"era_whip", "kbb_only", "fip_proxy", "xfip_proxy", "stuff_proxy"}
)
STARTER_QUALITY_MODE = (os.getenv("MLB_STARTER_QUALITY_MODE") or "era_whip").strip().lower()

# FIP constant (~MLB recent); quality maps relative to league-average FIP.
FIP_CONSTANT = 3.20
FIP_LEAGUE_AVG = 4.00
# League HR/FB proxy when reconstructing xFIP without Statcast FB%.
XFIP_LG_HR_FB = 0.105
# Approximate FB share of air outs (popups + flies); keeps xFIP scale sane.
XFIP_FB_SHARE_OF_AIR = 0.72


def apply_starter_quality_mode(mode: str) -> str:
    """Process-local override for densify stack ablation (clears live SP cache)."""
    global STARTER_QUALITY_MODE
    normalized = (mode or "era_whip").strip().lower()
    if normalized not in STARTER_QUALITY_MODES:
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

# Stats API team IDs for bullpen refetch on historical densify (abbr → mlb team id).
MLB_TEAM_ID_BY_ABBR: Dict[str, int] = {
    "AZ": 109,
    "ARI": 109,
    "ATL": 144,
    "BAL": 110,
    "BOS": 111,
    "CHC": 112,
    "CWS": 145,
    "CHW": 145,
    "CIN": 113,
    "CLE": 114,
    "COL": 115,
    "DET": 116,
    "HOU": 117,
    "KC": 118,
    "LAA": 108,
    "LAD": 119,
    "MIA": 146,
    "MIL": 158,
    "MIN": 142,
    "NYM": 121,
    "NYY": 147,
    "OAK": 133,
    "ATH": 133,
    "PHI": 143,
    "PIT": 134,
    "SD": 135,
    "SDP": 135,
    "SEA": 136,
    "SF": 137,
    "SFG": 137,
    "STL": 138,
    "TB": 139,
    "TBR": 139,
    "TEX": 140,
    "TOR": 141,
    "WSH": 120,
    "WAS": 120,
}


def mlb_team_id_for_abbr(abbr: Optional[str]) -> Optional[int]:
    if not abbr:
        return None
    return MLB_TEAM_ID_BY_ABBR.get(str(abbr).strip().upper())


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


def clear_game_lineup_features_cache() -> None:
    """Drop stale feed/live lineup cache (nowcast must see late cards / SP flips)."""
    cache_fn = globals().get("fetch_game_lineup_features")
    if cache_fn is not None and hasattr(cache_fn, "cache_clear"):
        cache_fn.cache_clear()


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
        pitcher_slots = 0
        for slot in sorted(lineup_by_slot):
            player = lineup_by_slot[slot]
            batting = (player.get("seasonStats") or {}).get("batting") or {}
            ops = _safe_rate(batting.get("ops"))
            plate_appearances = _safe_float(batting.get("plateAppearances"))
            pos_abbr = ((player.get("position") or {}).get("abbreviation") or "").upper()
            weight = LINEUP_ORDER_WEIGHTS.get(slot, 1.0)
            # Universal DH: skip pitcher batting slots so they do not dilute OPS.
            person = player.get("person") or {}
            person_id = person.get("id")
            try:
                batter_mlbam_id = int(person_id) if person_id is not None else None
            except (TypeError, ValueError):
                batter_mlbam_id = None
            if pos_abbr == "P":
                pitcher_slots += 1
                player_summaries.append(
                    {
                        "slot": slot,
                        "id": batter_mlbam_id,
                        "name": person.get("fullName"),
                        "ops": ops,
                        "plate_appearances": plate_appearances,
                        "position": pos_abbr,
                        "excluded_from_strength": True,
                    }
                )
                continue
            if ops is not None:
                weighted_ops += ops * weight
                total_weight += weight
            player_summaries.append(
                {
                    "slot": slot,
                    "id": batter_mlbam_id,
                    "name": person.get("fullName"),
                    "ops": ops,
                    "plate_appearances": plate_appearances,
                    "position": pos_abbr,
                }
            )

        lineup_ops = (weighted_ops / total_weight) if total_weight > 0 else None
        batting_known = len(lineup_by_slot) - pitcher_slots
        out[side] = {
            "lineup_strength_index": _rate_index(lineup_ops),
            "weighted_ops": lineup_ops,
            "known_players": batting_known,
            "players": player_summaries,
            "lineup_confirmed": batting_known >= 8,
            "probable_pitcher": live_pitchers.get(side),
            "source": "feed/live",
            "fetched_ok": True,
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
        "hydrate": "probablePitcher,team,linescore,venue,weather,decisions,officials,lineups",
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
    known_home: Optional[int] = None,
    known_away: Optional[int] = None,
) -> Dict[str, float]:
    # Confidence in modeled batting context (0..1). Starter confirmation helps even if lineup not final.
    # When per-side known counts are provided, allow mild asymmetry (timing sharp path).
    base = 0.75
    if lineup_confirmed:
        base += 0.20
    if probable_pitcher_home:
        base += 0.025
    if probable_pitcher_away:
        base += 0.025
    c = max(0.35, min(1.0, base))
    if known_home is None and known_away is None:
        return {"home": c, "away": c}
    home = c
    away = c
    if known_home is not None:
        home = max(0.35, min(1.0, c + (0.04 if int(known_home) >= 8 else -0.04 if int(known_home) < 5 else 0.0)))
    if known_away is not None:
        away = max(0.35, min(1.0, c + (0.04 if int(known_away) >= 8 else -0.04 if int(known_away) < 5 else 0.0)))
    return {"home": home, "away": away}


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


def _bb_per_9_from_stat(stat: Dict[str, Any]) -> Optional[float]:
    """Stats API exposes walksPer9Inn; older code looked for baseOnBallsPer9Inn (always null)."""
    return _safe_float(stat.get("walksPer9Inn")) or _safe_float(stat.get("baseOnBallsPer9Inn"))


def compute_fip_from_stat(stat: Dict[str, Any], *, use_xfip: bool = False) -> Optional[float]:
    """FIP / xFIP-proxy from Stats API pitching counting stats. None if IP too small."""
    ip = _parse_ip(stat.get("inningsPitched"))
    if ip < 1.0:
        return None
    hr = float(_safe_int(stat.get("homeRuns")))
    bb = float(_safe_int(stat.get("baseOnBalls")))
    hbp = float(_safe_int(stat.get("hitByPitch")))
    k = float(_safe_int(stat.get("strikeOuts")))
    if use_xfip:
        ground_outs = float(_safe_int(stat.get("groundOuts")))
        air_outs = float(_safe_int(stat.get("airOuts")))
        bip_air = ground_outs + air_outs
        if bip_air > 0 and air_outs > 0:
            fb_est = air_outs * XFIP_FB_SHARE_OF_AIR
            hr = fb_est * XFIP_LG_HR_FB
        else:
            # Fall back to actual HR when GO/AO missing (still predictive via K/BB).
            pass
    return ((13.0 * hr) + (3.0 * (bb + hbp)) - (2.0 * k)) / ip + FIP_CONSTANT


def _quality_from_fip(fip: float) -> float:
    # Run-allowed factor: lower FIP ⇒ lower quality index (better pitcher).
    return 1.0 + (float(fip) - FIP_LEAGUE_AVG) * 0.055


def _quality_from_kbb_shape(
    *,
    k_per_9: Optional[float],
    bb_per_9: Optional[float],
    ground_outs_to_air_outs: Optional[float],
) -> float:
    starter_quality = 1.0
    if k_per_9 is not None:
        starter_quality -= (k_per_9 - 8.5) * 0.035
    if bb_per_9 is not None:
        starter_quality += (bb_per_9 - 3.1) * 0.055
    if ground_outs_to_air_outs is not None:
        starter_quality -= (ground_outs_to_air_outs - 1.0) * 0.04
    return starter_quality


def _starter_features_from_stat(
    *,
    starter_name: str,
    player_id: int,
    season: int,
    handedness: str,
    stat: Dict[str, Any],
    as_of: Optional[date] = None,
) -> Optional[Dict[str, Any]]:
    era = _safe_float(stat.get("era"))
    whip = _safe_float(stat.get("whip"))
    k_per_9 = _safe_float(stat.get("strikeoutsPer9Inn"))
    bb_per_9 = _bb_per_9_from_stat(stat)
    ground_outs_to_air_outs = _safe_float(stat.get("groundOutsToAirouts"))
    ip = _parse_ip(stat.get("inningsPitched"))
    fip = compute_fip_from_stat(stat, use_xfip=False)
    xfip = compute_fip_from_stat(stat, use_xfip=True)

    if (
        era is None
        and whip is None
        and k_per_9 is None
        and bb_per_9 is None
        and fip is None
    ):
        return None

    k_factor = 1.0 if k_per_9 is None else 1.0 + (k_per_9 - 8.5) * 0.028
    bb_factor = 1.0 if bb_per_9 is None else 1.0 + (bb_per_9 - 3.1) * 0.045
    gb_factor = (
        1.0
        if ground_outs_to_air_outs is None
        else 1.0 + (ground_outs_to_air_outs - 1.0) * 0.06
    )

    mode = STARTER_QUALITY_MODE
    stuff_meta: Optional[Dict[str, Any]] = None
    if mode == "kbb_only":
        starter_quality = _quality_from_kbb_shape(
            k_per_9=k_per_9,
            bb_per_9=bb_per_9,
            ground_outs_to_air_outs=ground_outs_to_air_outs,
        )
    elif mode == "fip_proxy":
        if fip is not None and ip >= 8.0:
            starter_quality = _quality_from_fip(fip)
        else:
            # Thin sample: fall back to K-BB shape (still predictive, no ERA leak).
            starter_quality = _quality_from_kbb_shape(
                k_per_9=k_per_9,
                bb_per_9=bb_per_9,
                ground_outs_to_air_outs=ground_outs_to_air_outs,
            )
    elif mode == "xfip_proxy":
        talent = xfip if xfip is not None else fip
        if talent is not None and ip >= 8.0:
            starter_quality = _quality_from_fip(talent)
        else:
            starter_quality = _quality_from_kbb_shape(
                k_per_9=k_per_9,
                bb_per_9=bb_per_9,
                ground_outs_to_air_outs=ground_outs_to_air_outs,
            )
    elif mode == "stuff_proxy":
        # Statcast as-of arsenal proxies; thin/missing → KBB (never ERA leak).
        from .mlb_statcast_stuff import get_pitcher_stuff_as_of, quality_from_stuff_metrics

        stuff_as_of = as_of or date.today()
        stuff = get_pitcher_stuff_as_of(
            int(player_id),
            as_of=stuff_as_of,
            season=season,
            fetch_if_missing=True,
        )
        if stuff is not None:
            starter_quality = quality_from_stuff_metrics(stuff)
            stuff_meta = {
                "whiff_pct": round(float(stuff.get("whiff_pct") or 0), 4),
                "chase_pct": round(float(stuff.get("chase_pct") or 0), 4),
                "zone_pct": round(float(stuff.get("zone_pct") or 0), 4),
                "avg_ev": round(float(stuff.get("avg_ev") or 0), 3),
                "barrel_pct": round(float(stuff.get("barrel_pct") or 0), 4),
                "pitches": round(float(stuff.get("pitches") or 0), 1),
                "as_of_pitches_through": stuff.get("as_of_pitches_through"),
            }
        else:
            starter_quality = _quality_from_kbb_shape(
                k_per_9=k_per_9,
                bb_per_9=bb_per_9,
                ground_outs_to_air_outs=ground_outs_to_air_outs,
            )
    else:
        # era_whip (S0 default)
        starter_quality = 1.0
        if era is not None:
            starter_quality += (era - 4.10) * 0.045
        if whip is not None:
            starter_quality += (whip - 1.28) * 0.18

    out: Dict[str, Any] = {
        "starter_quality": max(0.82, min(1.18, round(starter_quality, 4))),
        "k_factor": max(0.88, min(1.18, round(k_factor, 4))),
        "bb_factor": max(0.86, min(1.18, round(bb_factor, 4))),
        "gb_factor": max(0.88, min(1.18, round(gb_factor, 4))),
        "handedness": handedness if handedness in {"L", "R"} else "U",
        "source": "mlb-stats-api" if mode != "stuff_proxy" or stuff_meta is None else "statcast-stuff",
        "player_id": player_id,
        "player_name": starter_name,
        "season": season,
        "quality_mode": mode,
        "innings_pitched": round(ip, 3),
    }
    if fip is not None:
        out["fip"] = round(fip, 4)
    if xfip is not None:
        out["xfip"] = round(xfip, 4)
    if stuff_meta is not None:
        out["stuff"] = stuff_meta
    if as_of is not None:
        out["as_of"] = as_of.isoformat()
    return out


def _season_start_approx(season: int) -> date:
    return date(int(season), 3, 20)


@lru_cache(maxsize=1024)
def _live_starter_features(
    starter_name: str,
    season: int,
    as_of_iso: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    normalized_name = normalize_pitcher_name(starter_name)
    if not normalized_name:
        return None

    as_of: Optional[date] = None
    if as_of_iso:
        try:
            as_of = date.fromisoformat(as_of_iso)
        except ValueError:
            as_of = None

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

    # Prefer as-of date-range (leakage-safe for historical densify), then full season / prior / career.
    stat_queries: List[Dict[str, Any]] = []
    if as_of is not None:
        end_as_of = as_of - timedelta(days=1)
        season_start = _season_start_approx(season)
        if end_as_of >= season_start:
            stat_queries.append(
                {
                    "stats": "byDateRange",
                    "group": "pitching",
                    "season": season,
                    "startDate": season_start.isoformat(),
                    "endDate": end_as_of.isoformat(),
                }
            )
        # Prior season full (known before game year) as fallback for early-season.
        stat_queries.append({"stats": "season", "group": "pitching", "season": season - 1})
    else:
        stat_queries.extend(
            [
                {"stats": "season", "group": "pitching", "season": season},
                {"stats": "season", "group": "pitching", "season": season - 1},
            ]
        )
    stat_queries.append({"stats": "career", "group": "pitching"})

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
        stats_type = str(params.get("stats") or "")
        if stats_type in {"season", "byDateRange"} and ip < 8.0:
            continue
        stat_season = int(params.get("season") or season)
        features = _starter_features_from_stat(
            starter_name=str(candidate.get("fullName") or starter_name),
            player_id=int(player_id),
            season=stat_season,
            handedness=handedness,
            stat=stat,
            as_of=as_of,
        )
        if features is not None:
            if stats_type == "byDateRange":
                features["stat_window"] = "as_of_season"
            elif stats_type == "season":
                features["stat_window"] = "season"
            else:
                features["stat_window"] = "career"
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


# Bullpen talent (separate from fatigue/availability — do not double-count).
#   off (default): bullpen_quality stays 1.0 (fatigue path handles stress)
#   role_weighted: closer/setup-weighted FIP-lite from recent relief apps
BULLPEN_ROLE_QUALITY_MODES = frozenset({"off", "role_weighted"})
BULLPEN_ROLE_QUALITY_MODE = (os.getenv("MLB_BULLPEN_ROLE_QUALITY_MODE") or "off").strip().lower()


def apply_bullpen_role_quality_mode(mode: str) -> str:
    global BULLPEN_ROLE_QUALITY_MODE
    normalized = (mode or "off").strip().lower()
    if normalized not in BULLPEN_ROLE_QUALITY_MODES:
        raise ValueError(f"unsupported bullpen role quality mode: {mode}")
    BULLPEN_ROLE_QUALITY_MODE = normalized
    return BULLPEN_ROLE_QUALITY_MODE


def get_bullpen_role_quality_mode() -> str:
    return BULLPEN_ROLE_QUALITY_MODE


def _reliever_role_weight(stats: Dict[str, Any]) -> float:
    """Closer/setup get more weight than low-leverage mop-up."""
    if _safe_int(stats.get("saves")) > 0:
        return 1.55
    if _safe_int(stats.get("holds")) > 0:
        return 1.30
    if _safe_int(stats.get("blownSaves")) > 0:
        return 1.25
    if _safe_int(stats.get("gamesFinished")) > 0:
        return 1.10
    return 0.75


def _reliever_app_fip_quality(stats: Dict[str, Any]) -> Optional[float]:
    """Single-appearance FIP-lite quality (run-allowed factor). None if no IP."""
    ip = _parse_ip(stats.get("inningsPitched"))
    if ip <= 0:
        return None
    hr = float(_safe_int(stats.get("homeRuns")))
    bb = float(_safe_int(stats.get("baseOnBalls"))) + float(_safe_int(stats.get("hitByPitch")))
    k = float(_safe_int(stats.get("strikeOuts")))
    fip = ((13.0 * hr) + (3.0 * bb) - (2.0 * k)) / ip + FIP_CONSTANT
    return max(0.82, min(1.18, 1.0 + (fip - FIP_LEAGUE_AVG) * 0.045))


def fetch_team_bullpen_fatigue(team_id: Optional[int], as_of: date) -> Dict[str, float]:
    neutral = {
        "bullpen_ip_last3": 3.0,
        "bullpen_appearances_last3": 6.0,
        "bullpen_fatigue_score": 0.50,
        "bullpen_availability_score": 0.65,
        "bullpen_high_leverage_availability_score": 0.62,
        "bullpen_quality": 1.0,
    }
    if not team_id:
        return dict(neutral)

    pks = _fetch_team_recent_final_games(team_id, as_of, limit=3)
    if not pks:
        return dict(neutral)

    bullpen_ip_total = 0.0
    bullpen_apps_total = 0.0
    high_lev_apps = 0.0
    high_lev_ip = 0.0
    role_quality_num = 0.0
    role_quality_den = 0.0
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
            app_q = _reliever_app_fip_quality(stats)
            if app_q is not None:
                w = _reliever_role_weight(stats)
                role_quality_num += app_q * w * ip
                role_quality_den += w * ip

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

    bullpen_quality = 1.0
    if BULLPEN_ROLE_QUALITY_MODE == "role_weighted" and role_quality_den > 0:
        bullpen_quality = max(0.85, min(1.15, role_quality_num / role_quality_den))

    return {
        "bullpen_ip_last3": round(bullpen_ip_total, 3),
        "bullpen_appearances_last3": round(bullpen_apps_total, 3),
        "bullpen_fatigue_score": round(fatigue, 4),
        "bullpen_availability_score": round(availability, 4),
        "bullpen_high_leverage_availability_score": round(high_lev_availability, 4),
        "bullpen_quality": round(bullpen_quality, 4),
    }


def _prior_quality_from_shape(k_factor: float, bb_factor: float, gb_factor: float) -> float:
    """Predictive prior when ERA/WHIP quality would leak results into FIP/KBB modes."""
    quality = 1.0 - (k_factor - 1.0) * 0.55 + (bb_factor - 1.0) * 0.70 - (gb_factor - 1.0) * 0.15
    return max(0.85, min(1.15, round(quality, 4)))


def starter_identity_features(
    starter_name: Optional[str],
    *,
    season: Optional[int] = None,
    as_of: Optional[date] = None,
) -> Dict[str, Any]:
    if not starter_name:
        return _neutral_starter_features(source="neutral")

    key = normalize_pitcher_name(starter_name)
    target_season = season or (as_of.year if as_of is not None else date.today().year)
    as_of_iso = as_of.isoformat() if as_of is not None else None

    # Prefer live Stats API (true arsenal/shape) over static priors when resolvable.
    try:
        live_features = _live_starter_features(starter_name, target_season, as_of_iso)
    except Exception:
        live_features = None
    if live_features is not None:
        return live_features

    known = STARTER_QUALITY_PRIORS.get(key) or STARTER_QUALITY_PRIORS.get(normalize_team_key(starter_name))
    if known:
        k_factor = float(known["k_factor"])
        bb_factor = float(known["bb_factor"])
        gb_factor = float(known["gb_factor"])
        if STARTER_QUALITY_MODE in {"kbb_only", "fip_proxy", "xfip_proxy"}:
            # Reconstruct quality from prior shape so talent modes do not inherit ERA priors.
            quality = _prior_quality_from_shape(k_factor, bb_factor, gb_factor)
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
            "as_of": as_of_iso,
        }

    # Deterministic fallback from identity signature (low firmness path).
    score = sum(ord(c) for c in key if c.isalpha())
    k_factor = 1.0 + ((score % 11) - 5) * 0.008
    bb_factor = 1.0 - ((score % 9) - 4) * 0.007
    gb_factor = 1.0 + ((score % 7) - 3) * 0.01
    if STARTER_QUALITY_MODE in {"kbb_only", "fip_proxy", "xfip_proxy"}:
        quality = _prior_quality_from_shape(k_factor, bb_factor, gb_factor)
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
        "as_of": as_of_iso,
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
