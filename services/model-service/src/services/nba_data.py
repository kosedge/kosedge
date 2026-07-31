"""NBA data ingest helpers (stats.nba.com primary; SportsDataIO optional).

Phase 1: schedule/box/PBP via public NBA Stats endpoints. Does not call The Odds
API for historical re-pulls. SportsDataIO is used only when keys are already set.
"""

from __future__ import annotations

import logging
import os
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx

log = logging.getLogger(__name__)

NBA_STATS_BASE = os.getenv("NBA_STATS_BASE_URL", "https://stats.nba.com/stats")
NBA_STATS_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; KosEdgeNbaModel/1.0; +https://www.kosedge.com)"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://www.nba.com",
    "Referer": "https://www.nba.com/",
    "x-nba-stats-origin": "stats",
    "x-nba-stats-token": "true",
}

# Canonical team abbreviations used in rolling features / context.
NBA_TEAM_ABBREV = {
    "Atlanta Hawks": "ATL",
    "Boston Celtics": "BOS",
    "Brooklyn Nets": "BKN",
    "Charlotte Hornets": "CHA",
    "Chicago Bulls": "CHI",
    "Cleveland Cavaliers": "CLE",
    "Dallas Mavericks": "DAL",
    "Denver Nuggets": "DEN",
    "Detroit Pistons": "DET",
    "Golden State Warriors": "GSW",
    "Houston Rockets": "HOU",
    "Indiana Pacers": "IND",
    "LA Clippers": "LAC",
    "Los Angeles Clippers": "LAC",
    "Los Angeles Lakers": "LAL",
    "Memphis Grizzlies": "MEM",
    "Miami Heat": "MIA",
    "Milwaukee Bucks": "MIL",
    "Minnesota Timberwolves": "MIN",
    "New Orleans Pelicans": "NOP",
    "New York Knicks": "NYK",
    "Oklahoma City Thunder": "OKC",
    "Orlando Magic": "ORL",
    "Philadelphia 76ers": "PHI",
    "Phoenix Suns": "PHX",
    "Portland Trail Blazers": "POR",
    "Sacramento Kings": "SAC",
    "San Antonio Spurs": "SAS",
    "Toronto Raptors": "TOR",
    "Utah Jazz": "UTA",
    "Washington Wizards": "WAS",
}


def normalize_team_key(name: str) -> str:
    raw = (name or "").strip()
    if not raw:
        return "UNK"
    if raw.upper() in {v for v in NBA_TEAM_ABBREV.values()}:
        return raw.upper()
    return NBA_TEAM_ABBREV.get(raw, raw.upper()[:3])


def _sportsdata_key() -> Optional[str]:
    key = (
        os.getenv("SPORTSDATA_NBA_API_KEY")
        or os.getenv("SPORTSDATA_API_KEY")
        or ""
    ).strip()
    return key or None


def _nba_stats_get(path: str, params: Dict[str, Any], *, timeout: float = 30.0) -> Dict[str, Any]:
    url = f"{NBA_STATS_BASE.rstrip('/')}/{path.lstrip('/')}"
    with httpx.Client(timeout=timeout, headers=NBA_STATS_HEADERS, follow_redirects=True) as client:
        resp = client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()


def _result_sets_to_dicts(payload: Dict[str, Any], set_name: Optional[str] = None) -> List[Dict[str, Any]]:
    sets = payload.get("resultSets") or payload.get("resultSet") or []
    if isinstance(sets, dict):
        sets = [sets]
    rows_out: List[Dict[str, Any]] = []
    for rs in sets:
        if set_name and rs.get("name") != set_name:
            continue
        headers = rs.get("headers") or []
        for row in rs.get("rowSet") or []:
            rows_out.append({headers[i]: row[i] for i in range(min(len(headers), len(row)))})
        if set_name:
            break
    return rows_out


def fetch_scoreboard(game_date: date) -> List[Dict[str, Any]]:
    """Fetch day's games from stats.nba.com scoreboardv2."""
    date_str = game_date.strftime("%m/%d/%Y")
    try:
        payload = _nba_stats_get(
            "scoreboardv2",
            {
                "GameDate": date_str,
                "LeagueID": "00",
                "DayOffset": "0",
            },
        )
    except Exception as exc:
        log.warning("NBA scoreboard fetch failed for %s: %s", game_date, str(exc)[:240])
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
            "season": str(g.get("SEASON") or ""),
            "home_team_id": g.get("HOME_TEAM_ID"),
            "away_team_id": g.get("VISITOR_TEAM_ID"),
            "source": "stats.nba.com",
            "raw_header": g,
        }
    # Attach team names/scores from linescore when present.
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
            abbr = str(t.get("TEAM_ABBREVIATION") or normalize_team_key(name))
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


def fetch_boxscore_traditional(game_id: str) -> Dict[str, Any]:
    try:
        payload = _nba_stats_get(
            "boxscoretraditionalv2",
            {
                "GameID": game_id,
                "StartPeriod": 0,
                "EndPeriod": 10,
                "StartRange": 0,
                "EndRange": 0,
                "RangeType": 0,
            },
        )
    except Exception as exc:
        log.warning("NBA boxscore fetch failed for %s: %s", game_id, str(exc)[:240])
        return {}
    return {
        "player_stats": _result_sets_to_dicts(payload, "PlayerStats"),
        "team_stats": _result_sets_to_dicts(payload, "TeamStats"),
        "source": "stats.nba.com",
    }


def fetch_play_by_play(game_id: str) -> List[Dict[str, Any]]:
    try:
        payload = _nba_stats_get(
            "playbyplayv2",
            {"GameID": game_id, "StartPeriod": 0, "EndPeriod": 10},
        )
    except Exception as exc:
        log.warning("NBA PBP fetch failed for %s: %s", game_id, str(exc)[:240])
        return []
    return _result_sets_to_dicts(payload, "PlayByPlay")


def derive_possessions_from_pbp(
    pbp_rows: List[Dict[str, Any]],
    *,
    home_team_key: str,
    away_team_key: str,
) -> List[Dict[str, Any]]:
    """Lightweight possession segmentation from NBA Stats PBP rows.

    Not a full chain parser — Phase 1 scaffold that emits rows compatible with
    `nba_possessions` and the typed event vocabulary in the simulator.
    """
    possessions: List[Dict[str, Any]] = []
    if not pbp_rows:
        return possessions

    current_offense: Optional[str] = None
    current_events: List[Dict[str, Any]] = []
    points = 0
    ended_by = "unknown"
    poss_idx = 0
    period = 1
    clock: Optional[float] = None

    def _flush() -> None:
        nonlocal poss_idx, current_events, points, ended_by, current_offense
        if current_offense is None and not current_events:
            return
        defense = away_team_key if current_offense == home_team_key else home_team_key
        possessions.append(
            {
                "possession_index": poss_idx,
                "offense_team_key": current_offense,
                "defense_team_key": defense,
                "points": points,
                "ended_by": ended_by,
                "period": period,
                "clock_seconds": clock,
                "events": current_events,
                "source": "stats.nba.com",
            }
        )
        poss_idx += 1
        current_events = []
        points = 0
        ended_by = "unknown"

    for row in pbp_rows:
        period = int(row.get("PERIOD") or period or 1)
        # EVENTMSGTYPE: 1=make, 2=miss, 3=FT, 4=rebound, 5=turnover, 6=foul, ...
        msg = int(row.get("EVENTMSGTYPE") or 0)
        home_desc = str(row.get("HOMEDESCRIPTION") or "")
        visitor_desc = str(row.get("VISITORDESCRIPTION") or "")
        team_side = home_team_key if home_desc else (away_team_key if visitor_desc else None)
        desc = home_desc or visitor_desc

        if msg in {1, 2, 3, 5} and team_side:
            if current_offense is None:
                current_offense = team_side
            elif current_offense != team_side and current_events:
                _flush()
                current_offense = team_side

        if msg == 1 and team_side:
            is_three = "3PT" in desc.upper()
            scored = 3 if is_three else 2
            points += scored
            current_events.append(
                {
                    "event_type": "shot_make",
                    "team": "home" if team_side == home_team_key else "away",
                    "points": scored,
                    "shot_zone": "three" if is_three else "two",
                }
            )
            ended_by = "shot_make"
            _flush()
            current_offense = away_team_key if team_side == home_team_key else home_team_key
        elif msg == 2 and team_side:
            is_three = "3PT" in desc.upper()
            current_events.append(
                {
                    "event_type": "shot_miss",
                    "team": "home" if team_side == home_team_key else "away",
                    "shot_zone": "three" if is_three else "two",
                }
            )
        elif msg == 5 and team_side:
            current_events.append(
                {
                    "event_type": "turnover",
                    "team": "home" if team_side == home_team_key else "away",
                }
            )
            ended_by = "turnover"
            _flush()
            current_offense = away_team_key if team_side == home_team_key else home_team_key
        elif msg == 4:
            # Rebound: Off vs Def heuristics from description.
            is_off = "OFF:" in desc.upper() or "OFFENSIVE" in desc.upper()
            if team_side:
                current_events.append(
                    {
                        "event_type": "rebound_off" if is_off else "rebound_def",
                        "team": "home" if team_side == home_team_key else "away",
                    }
                )
                if not is_off:
                    ended_by = "defensive_rebound"
                    _flush()
                    current_offense = team_side

        time.sleep(0)  # yield point for cooperative loops

    if current_events or current_offense is not None:
        _flush()
    return possessions


def estimate_team_features_from_box(
    team_stats: List[Dict[str, Any]],
) -> Dict[str, Dict[str, float]]:
    """Derive thin pace/efficiency proxies from traditional team box rows."""
    out: Dict[str, Dict[str, float]] = {}
    for row in team_stats:
        abbr = str(row.get("TEAM_ABBREVIATION") or "").upper()
        if not abbr:
            continue
        fga = float(row.get("FGA") or 0)
        fta = float(row.get("FTA") or 0)
        tov = float(row.get("TO") or row.get("TOV") or 0)
        oreb = float(row.get("OREB") or 0)
        dreb = float(row.get("DREB") or 0)
        fg3a = float(row.get("FG3A") or 0)
        fg3m = float(row.get("FG3M") or 0)
        fgm = float(row.get("FGM") or 0)
        pts = float(row.get("PTS") or 0)
        # Possessions ≈ FGA + 0.44*FTA - OREB + TOV
        poss = max(1.0, fga + 0.44 * fta - oreb + tov)
        two_a = max(0.0, fga - fg3a)
        two_m = max(0.0, fgm - fg3m)
        out[abbr] = {
            "pace": poss,  # per-game possessions; rolling avg later
            "ortg": 100.0 * pts / poss,
            "three_pt_rate": fg3a / max(1.0, fga),
            "three_pt_pct": fg3m / max(1.0, fg3a),
            "two_pt_pct": two_m / max(1.0, two_a),
            "ft_rate": fta / max(1.0, fga),
            "to_rate": tov / poss,
            "orb_rate": oreb / max(1.0, oreb + dreb),
            "points": pts,
            "possessions": poss,
        }
    # Pair DRtg when both teams present.
    keys = list(out.keys())
    if len(keys) == 2:
        a, b = keys[0], keys[1]
        out[a]["drtg"] = out[b]["ortg"]
        out[b]["drtg"] = out[a]["ortg"]
    return out


def fetch_schedule_window(
    start: date,
    end: date,
    *,
    sleep_s: float = 0.6,
) -> List[Dict[str, Any]]:
    """Pull scoreboard for each day in [start, end]. Rate-limited politely."""
    games: List[Dict[str, Any]] = []
    cur = start
    while cur <= end:
        day_games = fetch_scoreboard(cur)
        games.extend(day_games)
        cur += timedelta(days=1)
        if sleep_s > 0 and cur <= end:
            time.sleep(sleep_s)
    return games


def try_sportsdata_games_by_date(game_date: date) -> List[Dict[str, Any]]:
    """Optional SportsDataIO path — only when key already present."""
    key = _sportsdata_key()
    if not key:
        return []
    url = (
        f"https://api.sportsdata.io/v3/nba/scores/json/GamesByDate/"
        f"{game_date.isoformat()}"
    )
    try:
        with httpx.Client(timeout=25.0) as client:
            resp = client.get(url, params={"key": key})
            resp.raise_for_status()
            rows = resp.json()
    except Exception as exc:
        log.warning("SportsDataIO NBA games fetch failed: %s", str(exc)[:240])
        return []
    out: List[Dict[str, Any]] = []
    if not isinstance(rows, list):
        return out
    for g in rows:
        out.append(
            {
                "external_game_id": str(g.get("GameID") or g.get("GlobalGameID") or ""),
                "game_date": game_date.isoformat(),
                "home_team_key": str(g.get("HomeTeam") or ""),
                "away_team_key": str(g.get("AwayTeam") or ""),
                "home_score": g.get("HomeTeamScore"),
                "away_score": g.get("AwayTeamScore"),
                "status": str(g.get("Status") or ""),
                "source": "sportsdata.io",
                "raw": g,
            }
        )
    return out


def default_league_average_inputs(
    game_id: str,
    home_team: str,
    away_team: str,
) -> Dict[str, Any]:
    """Feature-thin defaults for Phase 0 when rolling features are missing."""
    return {
        "game_id": game_id,
        "home_team": home_team,
        "away_team": away_team,
        "pace_home": 100.0,
        "pace_away": 100.0,
        "ortg_home": 114.0,
        "ortg_away": 114.0,
        "drtg_home": 114.0,
        "drtg_away": 114.0,
        "feature_pack_version": "nba-league-avg-v0",
        "sample_games_home": 0,
        "sample_games_away": 0,
    }


def utc_today() -> date:
    return datetime.now(timezone.utc).date()
