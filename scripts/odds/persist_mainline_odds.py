"""Lightweight psycopg persister for Odds API mainline events → odds_snapshots."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import psycopg

SPORT_MAP: Dict[str, Tuple[str, str, str]] = {
    "basketball_ncaab": ("ncaam", "NCAAM", "NCAA Men's Basketball"),
    "baseball_mlb": ("mlb", "MLB", "Major League Baseball"),
    "basketball_nba": ("nba", "NBA", "National Basketball Association"),
    "basketball_wnba": ("wnba", "WNBA", "Women's National Basketball Association"),
    "icehockey_nhl": ("nhl", "NHL", "National Hockey League"),
    "americanfootball_nfl": ("nfl", "NFL", "National Football League"),
    "americanfootball_ncaaf": ("cfb", "CFB", "NCAA Football"),
}

MARKET_MAP = {"h2h": "moneyline", "spreads": "spread", "totals": "total"}

NFL_FULL_NAME_TO_ABBR = {
    "Arizona Cardinals": "ARI",
    "Atlanta Falcons": "ATL",
    "Baltimore Ravens": "BAL",
    "Buffalo Bills": "BUF",
    "Carolina Panthers": "CAR",
    "Chicago Bears": "CHI",
    "Cincinnati Bengals": "CIN",
    "Cleveland Browns": "CLE",
    "Dallas Cowboys": "DAL",
    "Denver Broncos": "DEN",
    "Detroit Lions": "DET",
    "Green Bay Packers": "GB",
    "Houston Texans": "HOU",
    "Indianapolis Colts": "IND",
    "Jacksonville Jaguars": "JAX",
    "Kansas City Chiefs": "KC",
    "Las Vegas Raiders": "LV",
    "Los Angeles Chargers": "LAC",
    "Los Angeles Rams": "LA",
    "Miami Dolphins": "MIA",
    "Minnesota Vikings": "MIN",
    "New England Patriots": "NE",
    "New Orleans Saints": "NO",
    "New York Giants": "NYG",
    "New York Jets": "NYJ",
    "Philadelphia Eagles": "PHI",
    "Pittsburgh Steelers": "PIT",
    "San Francisco 49ers": "SF",
    "Seattle Seahawks": "SEA",
    "Tampa Bay Buccaneers": "TB",
    "Tennessee Titans": "TEN",
    "Washington Commanders": "WAS",
    "Washington Football Team": "WAS",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(raw: Optional[str]) -> Optional[datetime]:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None


def _abbr(team_name: str) -> str:
    letters = re.findall(r"[A-Za-z]+", team_name or "")
    if not letters:
        return "TEAM"
    if len(letters) == 1:
        return letters[0][:6].upper()
    if len(letters) == 2:
        return f"{letters[0][:2]}{letters[1][:2]}".upper()[:6]
    return "".join(p[:2] for p in letters[:3]).upper()[:6]


def _normalize_team(sport_key: str, team_name: str) -> str:
    if sport_key == "americanfootball_nfl":
        return NFL_FULL_NAME_TO_ABBR.get(team_name, team_name)
    return team_name


def _get_or_create(
    conn: psycopg.Connection,
    cache: Dict[Tuple[Any, ...], str],
    *,
    table: str,
    where_sql: str,
    where_params: Dict[str, Any],
    insert_sql: str,
    insert_params: Dict[str, Any],
) -> str:
    key = (table, where_sql, tuple(sorted(where_params.items())))
    if key in cache:
        return cache[key]
    found = conn.execute(f"SELECT id FROM {table} WHERE {where_sql} LIMIT 1", where_params).fetchone()
    if found:
        result = str(found[0])
    else:
        new_id = str(uuid.uuid4())
        conn.execute(insert_sql, {"id": new_id, **insert_params})
        result = new_id
    cache[key] = result
    return result


def _ensure_game(
    conn: psycopg.Connection,
    cache: Dict[Tuple[Any, ...], str],
    *,
    sport_key: str,
    game_dt: datetime,
    home_team: str,
    away_team: str,
    event_id: str,
) -> str:
    sport_code, sport_name, league_name = SPORT_MAP.get(
        sport_key, ("unknown", sport_key.upper(), sport_key.upper())
    )
    home_team = _normalize_team(sport_key, home_team)
    away_team = _normalize_team(sport_key, away_team)
    season_year = game_dt.year
    # NBA/NHL/NCAAM seasons: Oct–Jun → season_year = spring year
    if sport_key in {"basketball_nba", "icehockey_nhl", "basketball_ncaab"} and game_dt.month >= 8:
        season_year = game_dt.year + 1
    # NFL / NCAAF: Jan–Feb games belong to prior calendar season year
    if sport_key in {"americanfootball_nfl", "americanfootball_ncaaf"} and game_dt.month <= 2:
        season_year = game_dt.year - 1

    sport_id = _get_or_create(
        conn,
        cache,
        table="sports",
        where_sql="code = %(code)s",
        where_params={"code": sport_code},
        insert_sql="INSERT INTO sports (id, code, name, created_at) VALUES (%(id)s, %(code)s, %(name)s, %(created_at)s)",
        insert_params={"code": sport_code, "name": sport_name, "created_at": _now()},
    )
    league_id = _get_or_create(
        conn,
        cache,
        table="leagues",
        where_sql="sport_id = %(sport_id)s AND code = %(code)s",
        where_params={"sport_id": sport_id, "code": sport_code},
        insert_sql="INSERT INTO leagues (id, sport_id, code, name, created_at) VALUES (%(id)s, %(sport_id)s, %(code)s, %(name)s, %(created_at)s)",
        insert_params={
            "sport_id": sport_id,
            "code": sport_code,
            "name": league_name,
            "created_at": _now(),
        },
    )
    season_id = _get_or_create(
        conn,
        cache,
        table="seasons",
        where_sql="league_id = %(league_id)s AND season_year = %(season_year)s",
        where_params={"league_id": league_id, "season_year": season_year},
        insert_sql="INSERT INTO seasons (id, league_id, season_year, created_at) VALUES (%(id)s, %(league_id)s, %(season_year)s, %(created_at)s)",
        insert_params={"league_id": league_id, "season_year": season_year, "created_at": _now()},
    )
    # Teams may already exist under abbr OR full name — try both for NFL
    home_candidates = [home_team]
    away_candidates = [away_team]
    if sport_key == "americanfootball_nfl":
        # reverse map not needed; DB stores abbrs and we normalize to abbr
        pass

    def _team_id(name: str) -> str:
        return _get_or_create(
            conn,
            cache,
            table="teams",
            where_sql="league_id = %(league_id)s AND name = %(name)s",
            where_params={"league_id": league_id, "name": name},
            insert_sql="INSERT INTO teams (id, league_id, external_id, abbr, name, market, created_at) VALUES (%(id)s, %(league_id)s, %(external_id)s, %(abbr)s, %(name)s, %(market)s, %(created_at)s)",
            insert_params={
                "league_id": league_id,
                "external_id": None,
                "abbr": _abbr(name),
                "name": name,
                "market": None,
                "created_at": _now(),
            },
        )

    home_id = _team_id(home_candidates[0])
    away_id = _team_id(away_candidates[0])

    # Prefer Odds API external_id, then natural key (season/date/teams).
    # Existing schedule rows often use non-Odds external_ids (e.g. 2024_10_NYJ_ARI).
    found = conn.execute(
        """
        SELECT id FROM games
        WHERE season_id = %(season_id)s
          AND (
            external_id = %(eid)s
            OR (
              game_date = %(game_date)s
              AND home_team_id = %(home_team_id)s
              AND away_team_id = %(away_team_id)s
            )
          )
        LIMIT 1
        """,
        {
            "season_id": season_id,
            "eid": event_id,
            "game_date": game_dt.date(),
            "home_team_id": home_id,
            "away_team_id": away_id,
        },
    ).fetchone()
    if found:
        return str(found[0])

    # Also match ±1 calendar day (UTC commence vs local slate date)
    nearby = conn.execute(
        """
        SELECT id FROM games
        WHERE season_id = %(season_id)s
          AND home_team_id = %(home_team_id)s
          AND away_team_id = %(away_team_id)s
          AND game_date BETWEEN %(d0)s AND %(d1)s
        ORDER BY abs(game_date - %(game_date)s)
        LIMIT 1
        """,
        {
            "season_id": season_id,
            "home_team_id": home_id,
            "away_team_id": away_id,
            "d0": game_dt.date() - timedelta(days=1),
            "d1": game_dt.date() + timedelta(days=1),
            "game_date": game_dt.date(),
        },
    ).fetchone()
    if nearby:
        return str(nearby[0])

    game_id = str(uuid.uuid4())
    try:
        conn.execute(
            """
            INSERT INTO games (
              id, season_id, external_id, game_date, start_time, status,
              home_team_id, away_team_id, venue_name, created_at
            ) VALUES (
              %(id)s, %(season_id)s, %(external_id)s, %(game_date)s, %(start_time)s, %(status)s,
              %(home_team_id)s, %(away_team_id)s, NULL, %(created_at)s
            )
            """,
            {
                "id": game_id,
                "season_id": season_id,
                "external_id": event_id,
                "game_date": game_dt.date(),
                "start_time": game_dt,
                "status": "scheduled",
                "home_team_id": home_id,
                "away_team_id": away_id,
                "created_at": _now(),
            },
        )
        return game_id
    except Exception:
        again = conn.execute(
            """
            SELECT id FROM games
            WHERE season_id = %(season_id)s
              AND (
                external_id = %(eid)s
                OR (
                  game_date = %(game_date)s
                  AND home_team_id = %(home_team_id)s
                  AND away_team_id = %(away_team_id)s
                )
              )
            LIMIT 1
            """,
            {
                "season_id": season_id,
                "eid": event_id,
                "game_date": game_dt.date(),
                "home_team_id": home_id,
                "away_team_id": away_id,
            },
        ).fetchone()
        if again:
            return str(again[0])
        raise


def _extract_values(
    market_key: str, market: Dict[str, Any], home_team: str, away_team: str
) -> Optional[Dict[str, Any]]:
    outcomes = {}
    for o in market.get("outcomes") or []:
        name = (o.get("name") or "").strip()
        if name:
            outcomes[name] = o
    if market_key == "h2h":
        home, away = outcomes.get(home_team), outcomes.get(away_team)
        if not home or not away:
            return None
        return {
            "price_home": home.get("price"),
            "price_away": away.get("price"),
            "spread_home": None,
            "spread_away": None,
            "total_points": None,
            "over_price": None,
            "under_price": None,
        }
    if market_key == "spreads":
        home, away = outcomes.get(home_team), outcomes.get(away_team)
        if not home or not away:
            return None
        return {
            "price_home": home.get("price"),
            "price_away": away.get("price"),
            "spread_home": home.get("point"),
            "spread_away": away.get("point"),
            "total_points": None,
            "over_price": None,
            "under_price": None,
        }
    if market_key == "totals":
        over, under = outcomes.get("Over"), outcomes.get("Under")
        if not over or not under:
            return None
        total = over.get("point") if over.get("point") is not None else under.get("point")
        return {
            "price_home": None,
            "price_away": None,
            "spread_home": None,
            "spread_away": None,
            "total_points": total,
            "over_price": over.get("price"),
            "under_price": under.get("price"),
        }
    return None


def persist_odds_events(
    conn: psycopg.Connection,
    *,
    sport_key: str,
    events: List[Dict[str, Any]],
    source_label: str = "the-odds-api-historical-enterprise",
) -> Dict[str, int]:
    cache: Dict[Tuple[Any, ...], str] = {}
    events_persisted = 0
    snapshots_inserted = 0
    event_errors = 0
    for event in events:
        try:
            event_id = (event or {}).get("id")
            home_team = (event or {}).get("home_team")
            away_team = (event or {}).get("away_team")
            game_dt = _parse_iso((event or {}).get("commence_time")) or _now()
            sk = (event or {}).get("sport_key") or sport_key
            if not event_id or not home_team or not away_team:
                continue
            game_id = _ensure_game(
                conn,
                cache,
                sport_key=sk,
                game_dt=game_dt,
                home_team=home_team,
                away_team=away_team,
                event_id=str(event_id),
            )
            events_persisted += 1
            home_norm = _normalize_team(sk, home_team)
            away_norm = _normalize_team(sk, away_team)
            for book in event.get("bookmakers") or []:
                book_key = (book or {}).get("key")
                if not book_key:
                    continue
                sportsbook_id = _get_or_create(
                    conn,
                    cache,
                    table="sportsbooks",
                    where_sql="code = %(code)s",
                    where_params={"code": book_key},
                    insert_sql="INSERT INTO sportsbooks (id, code, name, created_at) VALUES (%(id)s, %(code)s, %(name)s, %(created_at)s)",
                    insert_params={
                        "code": book_key,
                        "name": str(book_key).replace("_", " ").title(),
                        "created_at": _now(),
                    },
                )
                captured_at = _parse_iso(book.get("last_update")) or _now()
                for market in book.get("markets") or []:
                    market_key = market.get("key")
                    market_code = MARKET_MAP.get(str(market_key or ""))
                    if not market_code:
                        continue
                    market_id = _get_or_create(
                        conn,
                        cache,
                        table="markets",
                        where_sql="code = %(code)s",
                        where_params={"code": market_code},
                        insert_sql="INSERT INTO markets (id, code, created_at) VALUES (%(id)s, %(code)s, %(created_at)s)",
                        insert_params={"code": market_code, "created_at": _now()},
                    )
                    # Use original team names for outcome matching (API uses full names)
                    values = _extract_values(str(market_key), market, home_team, away_team)
                    if values is None and sk == "americanfootball_nfl":
                        values = _extract_values(str(market_key), market, home_norm, away_norm)
                    if values is None:
                        continue
                    conn.execute(
                        """
                        INSERT INTO odds_snapshots (
                          id, game_id, sportsbook_id, market_id,
                          price_home, price_away, spread_home, spread_away,
                          total_points, over_price, under_price,
                          captured_at, source, created_at
                        ) VALUES (
                          %(id)s, %(game_id)s, %(sportsbook_id)s, %(market_id)s,
                          %(price_home)s, %(price_away)s, %(spread_home)s, %(spread_away)s,
                          %(total_points)s, %(over_price)s, %(under_price)s,
                          %(captured_at)s, %(source)s, %(created_at)s
                        )
                        """,
                        {
                            "id": str(uuid.uuid4()),
                            "game_id": game_id,
                            "sportsbook_id": sportsbook_id,
                            "market_id": market_id,
                            "price_home": values["price_home"],
                            "price_away": values["price_away"],
                            "spread_home": values["spread_home"],
                            "spread_away": values["spread_away"],
                            "total_points": values["total_points"],
                            "over_price": values["over_price"],
                            "under_price": values["under_price"],
                            "captured_at": captured_at,
                            "source": source_label,
                            "created_at": _now(),
                        },
                    )
                    snapshots_inserted += 1
        except Exception:
            event_errors += 1
            continue
    return {
        "events_persisted": events_persisted,
        "snapshots_inserted": snapshots_inserted,
        "event_errors": event_errors,
    }
