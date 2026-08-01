"""WNBA data ingest helpers (data.wnba.com primary; SportsDataIO / ESPN fallback).

Phase 1: schedule/box via public WNBA CDN patterns analogous to data.nba.com.
Does not call The Odds API here. Never imports NBA pace/player priors.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import httpx

from src.services.wnba_possession_simulator import (
    WNBA_LEAGUE_DRTG,
    WNBA_LEAGUE_ORTG,
    WNBA_LEAGUE_PACE,
)

log = logging.getLogger(__name__)

WNBA_STATS_BASE = os.getenv("WNBA_STATS_BASE_URL", "https://stats.wnba.com/stats")
WNBA_DATA_BASE = os.getenv(
    "WNBA_DATA_BASE_URL",
    "https://data.wnba.com/data/10s/v2015/json/mobile_teams/wnba",
)
WNBA_LEAGUE_ID = os.getenv("WNBA_LEAGUE_ID", "10")
ESPN_SCOREBOARD = os.getenv(
    "WNBA_ESPN_SCOREBOARD_URL",
    "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard",
)

WNBA_STATS_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; KosEdgeWnbaModel/1.0; +https://www.kosedge.com)"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://www.wnba.com",
    "Referer": "https://www.wnba.com/",
    "x-nba-stats-origin": "stats",
    "x-nba-stats-token": "true",
}
WNBA_DATA_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; KosEdgeWnbaModel/1.0; +https://www.kosedge.com)"
    ),
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.wnba.com/",
}

# Canonical team abbreviations — matches apps/web WNBA_TEAM_DIRECTORY.
# 2026 expansion: Portland Fire + Toronto Tempo (15 clubs). Sport-scoped:
# CHI/DAL/IND/MIN/PHX also exist in NBA — always join via leagues.code='wnba'.
WNBA_TEAM_ABBREV = {
    "Atlanta Dream": "ATL",
    "Chicago Sky": "CHI",
    "Connecticut Sun": "CON",
    "Dallas Wings": "DAL",
    "Golden State Valkyries": "GSV",
    "Indiana Fever": "IND",
    "Las Vegas Aces": "LAS",
    "Los Angeles Sparks": "LA",
    "Minnesota Lynx": "MIN",
    "New York Liberty": "NY",
    "Phoenix Mercury": "PHX",
    "Portland Fire": "POR",
    "Seattle Storm": "SEA",
    "Toronto Tempo": "TOR",
    "Washington Mystics": "WSH",
}

# CDN / Odds / ESPN abbr variants → canonical desk keys.
WNBA_TEAM_ABBR_ALIASES: Dict[str, str] = {
    "LVA": "LAS",
    "LV": "LAS",
    "LAC": "LA",  # rare Sparks collision token — prefer full name
    "LAK": "LA",
    "LOS": "LA",
    "NYL": "NY",
    "NYK": "NY",  # Odds sometimes mangles Liberty
    "WAS": "WSH",
    "WSH": "WSH",
    "PHO": "PHX",
    "CONN": "CON",
    "CT": "CON",
    "GS": "GSV",
    "GSW": "GSV",
    "PDX": "POR",
    "PORT": "POR",
    "TT": "TOR",
    "TEMP": "TOR",
}

# Exhibition / All-Star / international visitors in full_schedule — skip for features.
WNBA_NON_LEAGUE_TEAMS = frozenset({"BRA", "CLK", "COL", "TOY", "USA", "ROW", "TEAM"})

# Calendar-year seasons (May–Oct). Tip year = season label.
DEFAULT_WNBA_INGEST_SEASONS = ("2023", "2024", "2025", "2026")


def normalize_team_key(name: str) -> str:
    raw = (name or "").strip()
    if not raw:
        return "UNK"
    if raw in WNBA_TEAM_ABBREV:
        return WNBA_TEAM_ABBREV[raw]
    upper = raw.upper()
    if upper in WNBA_TEAM_ABBR_ALIASES:
        return WNBA_TEAM_ABBR_ALIASES[upper]
    canonical = {v for v in WNBA_TEAM_ABBREV.values()}
    if upper in canonical:
        return upper
    titled = " ".join(part.capitalize() for part in raw.split())
    if titled in WNBA_TEAM_ABBREV:
        return WNBA_TEAM_ABBREV[titled]
    # Soft match on last token (Dream / Sky / Fever …).
    for full, abbr in WNBA_TEAM_ABBREV.items():
        if raw.lower() in full.lower() or full.lower() in raw.lower():
            return abbr
    return upper[:3]


def wnba_full_names_for_abbr(abbr: str) -> List[str]:
    key = normalize_team_key(abbr)
    names = {name for name, code in WNBA_TEAM_ABBREV.items() if code == key}
    names.add(key)
    # Include common Odds API variants.
    if key == "LAS":
        names.update({"Las Vegas Aces", "LVA", "LV"})
    if key == "NY":
        names.update({"New York Liberty", "NYL"})
    if key == "WSH":
        names.update({"Washington Mystics", "WAS"})
    if key == "LA":
        names.update({"Los Angeles Sparks", "LA Sparks"})
    return sorted(names)


def wnba_abbr_match_keys(abbr: str) -> List[str]:
    key = normalize_team_key(abbr)
    keys = {key}
    for alias, canon in WNBA_TEAM_ABBR_ALIASES.items():
        if canon == key:
            keys.add(alias)
    return sorted(keys)


def wnba_season_year_from_date(game_date: date) -> int:
    """WNBA calendar-year season: tip year (May–Oct). Jan–Apr → prior tip year."""
    if game_date.month >= 5:
        return game_date.year
    return game_date.year - 1


def _sportsdata_key() -> Optional[str]:
    key = (
        os.getenv("SPORTSDATA_WNBA_API_KEY")
        or os.getenv("SPORTSDATA_API_KEY")
        or ""
    ).strip()
    return key or None


def _wnba_stats_get(
    path: str,
    params: Dict[str, Any],
    *,
    timeout: float = 25.0,
    retries: int = 1,
) -> Dict[str, Any]:
    url = f"{WNBA_STATS_BASE.rstrip('/')}/{path.lstrip('/')}"
    last_exc: Optional[Exception] = None
    for attempt in range(max(1, retries)):
        try:
            with httpx.Client(
                timeout=timeout, headers=WNBA_STATS_HEADERS, follow_redirects=True
            ) as client:
                resp = client.get(url, params=params)
                resp.raise_for_status()
                return resp.json()
        except Exception as exc:
            last_exc = exc
            sleep_s = 0.8 * (attempt + 1)
            log.warning(
                "WNBA stats GET %s attempt %s failed: %s; sleep %.1fs",
                path,
                attempt + 1,
                str(exc)[:200],
                sleep_s,
            )
            time.sleep(sleep_s)
    raise RuntimeError(f"WNBA stats GET failed for {path}: {last_exc}")


def _wnba_data_get(url: str, *, timeout: float = 60.0) -> Dict[str, Any]:
    with httpx.Client(
        timeout=timeout, headers=WNBA_DATA_HEADERS, follow_redirects=True
    ) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return json.loads(resp.text.lstrip("\ufeff"))


def season_label_to_start_year(season: str) -> int:
    """'2025' → 2025 (WNBA calendar-year labels)."""
    s = (season or "").strip()
    if len(s) >= 4 and s[:4].isdigit():
        return int(s[:4])
    raise ValueError(f"Unrecognized WNBA season label: {season}")


def _result_sets_to_dicts(
    payload: Dict[str, Any], set_name: Optional[str] = None
) -> List[Dict[str, Any]]:
    sets = payload.get("resultSets") or payload.get("resultSet") or []
    if isinstance(sets, dict):
        sets = [sets]
    rows_out: List[Dict[str, Any]] = []
    for rs in sets:
        if set_name and rs.get("name") != set_name:
            continue
        headers = rs.get("headers") or []
        for row in rs.get("rowSet") or []:
            rows_out.append(
                {headers[i]: row[i] for i in range(min(len(headers), len(row)))}
            )
        if set_name:
            break
    return rows_out


def fetch_scoreboard(game_date: date) -> List[Dict[str, Any]]:
    """Fetch day's games from stats.wnba.com scoreboardv2 (LeagueID=10)."""
    date_str = game_date.strftime("%m/%d/%Y")
    try:
        payload = _wnba_stats_get(
            "scoreboardv2",
            {
                "GameDate": date_str,
                "LeagueID": WNBA_LEAGUE_ID,
                "DayOffset": "0",
            },
        )
    except Exception as exc:
        log.warning("WNBA scoreboard fetch failed for %s: %s", game_date, str(exc)[:240])
        return []
    games = _result_sets_to_dicts(payload, "GameHeader")
    linescores = _result_sets_to_dicts(payload, "LineScore")
    by_game: Dict[str, Dict[str, Any]] = {}
    for g in games:
        gid = str(g.get("GAME_ID") or "")
        if not gid:
            continue
        by_game[gid] = {
            "external_game_id": gid,
            "game_date": game_date.isoformat(),
            "start_time": g.get("GAME_STATUS_TEXT"),
            "status": str(g.get("GAME_STATUS_TEXT") or g.get("GAME_STATUS_ID") or ""),
            "season": str(g.get("SEASON") or wnba_season_year_from_date(game_date)),
            "home_team_id": g.get("HOME_TEAM_ID"),
            "away_team_id": g.get("VISITOR_TEAM_ID"),
            "source": "stats.wnba.com",
            "raw_header": g,
        }
    team_rows: Dict[str, List[Dict[str, Any]]] = {}
    for ls in linescores:
        gid = str(ls.get("GAME_ID") or "")
        team_rows.setdefault(gid, []).append(ls)
    for gid, teams in team_rows.items():
        if gid not in by_game:
            continue
        home_id = by_game[gid].get("home_team_id")
        away_id = by_game[gid].get("away_team_id")
        for t in teams:
            tid = t.get("TEAM_ID")
            name = f"{t.get('TEAM_CITY_NAME', '')} {t.get('TEAM_NAME', '')}".strip()
            abbr = normalize_team_key(str(t.get("TEAM_ABBREVIATION") or name))
            pts = t.get("PTS")
            if tid == home_id:
                by_game[gid]["home_team_key"] = abbr
                by_game[gid]["home_team"] = name or abbr
                by_game[gid]["home_score"] = pts
            elif tid == away_id:
                by_game[gid]["away_team_key"] = abbr
                by_game[gid]["away_team"] = name or abbr
                by_game[gid]["away_score"] = pts
    return list(by_game.values())


def fetch_espn_scoreboard(game_date: date) -> List[Dict[str, Any]]:
    """Public ESPN scoreboard fallback."""
    url = f"{ESPN_SCOREBOARD}?dates={game_date.strftime('%Y%m%d')}"
    try:
        with httpx.Client(timeout=20.0, follow_redirects=True) as client:
            resp = client.get(url, headers={"User-Agent": WNBA_DATA_HEADERS["User-Agent"]})
            resp.raise_for_status()
            payload = resp.json()
    except Exception as exc:
        log.warning("ESPN WNBA scoreboard failed for %s: %s", game_date, str(exc)[:200])
        return []
    out: List[Dict[str, Any]] = []
    for ev in payload.get("events") or []:
        comps = ev.get("competitions") or []
        if not comps:
            continue
        c0 = comps[0]
        competitors = c0.get("competitors") or []
        home = next((x for x in competitors if x.get("homeAway") == "home"), None)
        away = next((x for x in competitors if x.get("homeAway") == "away"), None)
        if not home or not away:
            continue
        home_team = home.get("team") or {}
        away_team = away.get("team") or {}
        out.append(
            {
                "external_game_id": str(ev.get("id") or ""),
                "game_date": game_date.isoformat(),
                "home_team_key": normalize_team_key(
                    str(home_team.get("abbreviation") or home_team.get("displayName") or "")
                ),
                "away_team_key": normalize_team_key(
                    str(away_team.get("abbreviation") or away_team.get("displayName") or "")
                ),
                "home_team": str(home_team.get("displayName") or ""),
                "away_team": str(away_team.get("displayName") or ""),
                "home_score": int(home["score"]) if str(home.get("score") or "").isdigit() else None,
                "away_score": int(away["score"]) if str(away.get("score") or "").isdigit() else None,
                "status": str((c0.get("status") or {}).get("type", {}).get("description") or ""),
                "season": str(wnba_season_year_from_date(game_date)),
                "source": "espn.scoreboard",
                "raw": ev,
            }
        )
    return out


def fetch_season_schedule_data_wnba(season: str) -> List[Dict[str, Any]]:
    """Full season schedule+scores from data.wnba.com."""
    try:
        year = season_label_to_start_year(season)
    except ValueError:
        return []
    url = f"{WNBA_DATA_BASE.rstrip('/')}/{year}/league/{WNBA_LEAGUE_ID}_full_schedule.json"
    try:
        payload = _wnba_data_get(url, timeout=60.0)
    except Exception as exc:
        log.warning("data.wnba.com schedule failed for %s: %s", season, str(exc)[:240])
        return []
    games_out: List[Dict[str, Any]] = []
    for month in payload.get("lscd") or []:
        mscd = month.get("mscd") or {}
        for g in mscd.get("g") or []:
            gid = str(g.get("gid") or "").strip()
            if not gid:
                continue
            home = g.get("h") or {}
            away = g.get("v") or {}
            home_raw = str(home.get("ta") or "").upper()
            away_raw = str(away.get("ta") or "").upper()
            # Skip exhibition / international visitors.
            if home_raw in WNBA_NON_LEAGUE_TEAMS or away_raw in WNBA_NON_LEAGUE_TEAMS:
                continue
            home_key = normalize_team_key(home_raw)
            away_key = normalize_team_key(away_raw)
            if home_key == "UNK" or away_key == "UNK":
                continue
            home_score = home.get("s")
            away_score = away.get("s")
            try:
                home_score_i = int(home_score) if home_score not in (None, "") else None
            except (TypeError, ValueError):
                home_score_i = None
            try:
                away_score_i = int(away_score) if away_score not in (None, "") else None
            except (TypeError, ValueError):
                away_score_i = None
            stt = str(g.get("stt") or "")
            status = stt or str(g.get("st") or "")
            games_out.append(
                {
                    "external_game_id": gid,
                    "game_date": str(g.get("gdte") or "")[:10] or None,
                    "home_team_key": home_key,
                    "away_team_key": away_key,
                    "home_score": home_score_i,
                    "away_score": away_score_i,
                    "status": status or ("Final" if home_score_i is not None else ""),
                    "season": season,
                    "source": "data.wnba.com/schedule",
                    "raw": g,
                    "season_year": year,
                }
            )
    games_out.sort(key=lambda x: (x.get("game_date") or "", x["external_game_id"]))
    return games_out


def fetch_game_detail_data_wnba(season_year: int, game_id: str) -> Dict[str, Any]:
    gid = str(game_id).strip()
    url = (
        f"{WNBA_DATA_BASE.rstrip('/')}/{int(season_year)}/scores/gamedetail/"
        f"{gid}_gamedetail.json"
    )
    try:
        payload = _wnba_data_get(url, timeout=45.0)
    except Exception as exc:
        log.warning("data.wnba.com gamedetail failed for %s: %s", gid, str(exc)[:200])
        return {}
    return payload.get("g") or {}


def features_from_gamelog_row(row: Dict[str, Any]) -> Dict[str, float]:
    """Derive pace/efficiency proxies from a team box/gamelog row (per-40)."""
    fga = float(row.get("FGA") or 0)
    fta = float(row.get("FTA") or 0)
    tov = float(row.get("TOV") or row.get("TO") or 0)
    oreb = float(row.get("OREB") or 0)
    dreb = float(row.get("DREB") or 0)
    fg3a = float(row.get("FG3A") or 0)
    fg3m = float(row.get("FG3M") or 0)
    fgm = float(row.get("FGM") or 0)
    ftm = float(row.get("FTM") or 0)
    pts = float(row.get("PTS") or 0)
    poss = max(1.0, fga + 0.44 * fta - oreb + tov)
    two_a = max(0.0, fga - fg3a)
    two_m = max(0.0, fgm - fg3m)
    return {
        "pace": poss,  # team possessions in a 40-min game
        "ortg": 100.0 * pts / poss,
        "three_pt_rate": fg3a / max(1.0, fga),
        "three_pt_pct": fg3m / max(1.0, fg3a),
        "two_pt_pct": two_m / max(1.0, two_a),
        "ft_rate": fta / max(1.0, fga),
        "ft_pct": ftm / max(1.0, fta),
        "to_rate": tov / poss,
        "orb_rate": oreb / max(1.0, oreb + dreb),
        "points": pts,
        "possessions": poss,
    }


def features_from_data_wnba_team_stats(team_block: Dict[str, Any]) -> Dict[str, float]:
    stats = team_block.get("tstsg") or {}
    row = {
        "FGA": stats.get("fga"),
        "FTA": stats.get("fta"),
        "TOV": stats.get("tov"),
        "OREB": stats.get("oreb"),
        "DREB": stats.get("dreb"),
        "FG3A": stats.get("tpa"),
        "FG3M": stats.get("tpm"),
        "FGM": stats.get("fgm"),
        "FTM": stats.get("ftm"),
        "PTS": team_block.get("s"),
    }
    return features_from_gamelog_row(row)


def player_stubs_from_data_wnba_detail(detail: Dict[str, Any]) -> List[Dict[str, Any]]:
    stubs: List[Dict[str, Any]] = []
    for side_key in ("hls", "vls"):
        block = detail.get(side_key) or {}
        team_key = normalize_team_key(str(block.get("ta") or ""))
        for p in block.get("pstsg") or []:
            minutes = float(p.get("min") or 0) + float(p.get("sec") or 0) / 60.0
            fga = float(p.get("fga") or 0)
            fta = float(p.get("fta") or 0)
            tov = float(p.get("tov") or 0)
            stubs.append(
                {
                    "player_id": str(p.get("pid") or ""),
                    "player_name": f"{p.get('fn', '')} {p.get('ln', '')}".strip(),
                    "team_key": team_key,
                    "minutes": minutes,
                    "usage_proxy": fga + 0.44 * fta + tov,
                    "pts": float(p.get("pts") or 0),
                    "reb": float(p.get("reb") or 0),
                    "ast": float(p.get("ast") or 0),
                    "fg3m": float(p.get("tpm") or p.get("fg3m") or 0),
                    "fga": fga,
                    "fta": fta,
                    "tov": tov,
                }
            )
    return stubs


def _parse_game_date(raw: Any) -> Optional[date]:
    if raw is None:
        return None
    if isinstance(raw, date) and not isinstance(raw, datetime):
        return raw
    s = str(raw).strip()
    if not s:
        return None
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        pass
    for fmt in ("%b %d, %Y", "%m/%d/%Y", "%Y%m%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def compute_rest_days_by_team(
    games: Sequence[Dict[str, Any]],
) -> Dict[Tuple[str, str], float]:
    last_date: Dict[str, date] = {}
    out: Dict[Tuple[str, str], float] = {}
    ordered = sorted(
        games,
        key=lambda g: (g.get("game_date") or "", g.get("external_game_id") or ""),
    )
    for g in ordered:
        gid = str(g.get("external_game_id") or "")
        gd = _parse_game_date(g.get("game_date"))
        if not gid or gd is None:
            continue
        for side in ("home_team_key", "away_team_key"):
            team = normalize_team_key(str(g.get(side) or ""))
            if not team or team == "UNK":
                continue
            prev = last_date.get(team)
            rest = float((gd - prev).days) if prev is not None else 3.0
            out[(gid, team)] = rest
            last_date[team] = gd
    return out


def fetch_schedule_window(
    start: date,
    end: date,
    *,
    sleep_s: float = 0.35,
) -> List[Dict[str, Any]]:
    """Near-term slate. Prefer ESPN — data.wnba.com/stats often 403/timeout in 2026."""
    games: List[Dict[str, Any]] = []
    cur = start
    while cur <= end:
        day_games = fetch_espn_scoreboard(cur)
        if not day_games:
            day_games = fetch_scoreboard(cur)
        if not day_games:
            day_games = try_sportsdata_games_by_date(cur)
        games.extend(day_games)
        cur += timedelta(days=1)
        if sleep_s > 0 and cur <= end:
            time.sleep(sleep_s)
    return games


def try_sportsdata_games_by_date(game_date: date) -> List[Dict[str, Any]]:
    key = _sportsdata_key()
    if not key:
        return []
    url = (
        f"https://api.sportsdata.io/v3/wnba/scores/json/GamesByDate/"
        f"{game_date.isoformat()}"
    )
    try:
        with httpx.Client(timeout=25.0) as client:
            resp = client.get(url, params={"key": key})
            resp.raise_for_status()
            rows = resp.json()
    except Exception as exc:
        log.warning("SportsDataIO WNBA games fetch failed: %s", str(exc)[:240])
        return []
    out: List[Dict[str, Any]] = []
    if not isinstance(rows, list):
        return out
    for g in rows:
        out.append(
            {
                "external_game_id": str(g.get("GameID") or g.get("GlobalGameID") or ""),
                "game_date": game_date.isoformat(),
                "home_team_key": normalize_team_key(str(g.get("HomeTeam") or "")),
                "away_team_key": normalize_team_key(str(g.get("AwayTeam") or "")),
                "home_score": g.get("HomeTeamScore"),
                "away_score": g.get("AwayTeamScore"),
                "status": str(g.get("Status") or ""),
                "source": "sportsdata.io",
                "raw": g,
            }
        )
    return out


def rolling_average_features(
    samples: Sequence[Dict[str, float]],
    *,
    defaults: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    defaults = defaults or {
        "pace": WNBA_LEAGUE_PACE,
        "ortg": WNBA_LEAGUE_ORTG,
        "drtg": WNBA_LEAGUE_DRTG,
        "three_pt_rate": 0.34,
        "three_pt_pct": 0.34,
        "two_pt_pct": 0.50,
        "ft_rate": 0.24,
        "ft_pct": 0.80,
        "to_rate": 0.155,
        "orb_rate": 0.28,
    }

    def _avg(key: str) -> float:
        vals = [float(s[key]) for s in samples if s.get(key) is not None]
        return sum(vals) / len(vals) if vals else float(defaults[key])

    return {k: _avg(k) for k in defaults}


def default_league_average_inputs(
    game_id: str,
    home_team: str,
    away_team: str,
) -> Dict[str, Any]:
    """Feature-thin WNBA defaults — never NBA pace/ORtg."""
    return {
        "game_id": game_id,
        "home_team": home_team,
        "away_team": away_team,
        "pace_home": WNBA_LEAGUE_PACE,
        "pace_away": WNBA_LEAGUE_PACE,
        "ortg_home": WNBA_LEAGUE_ORTG,
        "ortg_away": WNBA_LEAGUE_ORTG,
        "drtg_home": WNBA_LEAGUE_DRTG,
        "drtg_away": WNBA_LEAGUE_DRTG,
        "three_pt_rate_home": 0.34,
        "three_pt_rate_away": 0.34,
        "three_pt_pct_home": 0.34,
        "three_pt_pct_away": 0.34,
        "feature_pack_version": "wnba-league-avg-v0",
        "sample_games_home": 0,
        "sample_games_away": 0,
    }


def utc_today() -> date:
    return datetime.now(timezone.utc).date()


def iter_season_labels(seasons: Optional[Iterable[str]] = None) -> List[str]:
    if seasons is None:
        return list(DEFAULT_WNBA_INGEST_SEASONS)
    return [str(s).strip() for s in seasons if str(s).strip()]
