"""Current CFB market observations for Edge Board (read path).

Prefer fresh ``odds_snapshots`` (beat-owned PROD_LIVE). If the warehouse
has no current priced NCAAF rows, do one live Odds pull (cached) — never HIST.
Does not persist. Does not invent Fair→Market.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from src.services.odds_api import fetch_odds, get_odds_api_keys

log = logging.getLogger("kosedge.cfb.edge_board_odds")

CFB_SPORT_KEY = "americanfootball_ncaaf"
CFB_LEAGUE_CODE = "cfb"
# Match web CFB carried inventory (us/us2). Dead keys never requested.
CFB_CARRIED_BOOKS = (
    "draftkings,fanduel,betmgm,betrivers,hardrockbet,fanatics,"
    "bovada,williamhill_us,betonlineag"
)
CFB_REGIONS = "us,us2"
WAREHOUSE_MAX_AGE = timedelta(hours=6)
LIVE_CACHE_TTL_SECONDS = 60

_LIVE_CACHE: Dict[str, Any] = {"ts": 0.0, "payload": None}

MARKET_CODE_TO_ODDS_KEY = {
    "spread": "spreads",
    "total": "totals",
    "moneyline": "h2h",
}


def _iso(dt: Any) -> Optional[str]:
    if dt is None:
        return None
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    raw = str(dt).strip()
    return raw or None


def _parse_dt(raw: Any) -> Optional[datetime]:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=timezone.utc)
    text = str(raw).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _max_event_as_of(events: List[Dict[str, Any]]) -> Optional[str]:
    best: Optional[datetime] = None
    for ev in events:
        for book in ev.get("bookmakers") or []:
            cand = _parse_dt(book.get("last_update"))
            if cand is None:
                continue
            for market in book.get("markets") or []:
                mdt = _parse_dt(market.get("last_update"))
                if mdt is not None and (cand is None or mdt > cand):
                    cand = mdt
            if cand is not None and (best is None or cand > best):
                best = cand
    return _iso(best)


def reconstruct_events_from_warehouse_rows(
    rows: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Flattened odds_snapshots → Odds-API-shaped events (no invented prices)."""
    by_game: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        home = str(row.get("home_team") or "").strip()
        away = str(row.get("away_team") or "").strip()
        if not home or not away:
            continue
        gid = str(row.get("external_id") or f"{away}@{home}")
        event = by_game.get(gid)
        if event is None:
            event = {
                "id": gid,
                "sport_key": CFB_SPORT_KEY,
                "commence_time": _iso(row.get("start_time")),
                "home_team": home,
                "away_team": away,
                "bookmakers": [],
            }
            by_game[gid] = event
        book_key = str(row.get("book") or "").strip().lower()
        if not book_key:
            continue
        captured = _iso(row.get("captured_at"))
        books: List[Dict[str, Any]] = event["bookmakers"]
        book = next((b for b in books if b.get("key") == book_key), None)
        if book is None:
            book = {
                "key": book_key,
                "title": book_key,
                "last_update": captured,
                "markets": [],
            }
            books.append(book)
        else:
            prev = _parse_dt(book.get("last_update"))
            nxt = _parse_dt(captured)
            if nxt is not None and (prev is None or nxt > prev):
                book["last_update"] = captured

        market_code = str(row.get("market") or "").strip().lower()
        odds_key = MARKET_CODE_TO_ODDS_KEY.get(market_code)
        if not odds_key:
            continue
        markets: List[Dict[str, Any]] = book["markets"]
        market = next((m for m in markets if m.get("key") == odds_key), None)
        if market is None:
            market = {"key": odds_key, "last_update": captured, "outcomes": []}
            markets.append(market)

        outcomes: List[Dict[str, Any]] = []
        if odds_key == "spreads":
            away_pt = row.get("spread_away")
            home_pt = row.get("spread_home")
            if away_pt is None and home_pt is not None:
                try:
                    away_pt = -float(home_pt)
                except (TypeError, ValueError):
                    away_pt = None
            if away_pt is None:
                continue
            outcomes.append(
                {
                    "name": away,
                    "point": float(away_pt),
                    "price": row.get("price_away"),
                }
            )
            if home_pt is not None:
                outcomes.append(
                    {
                        "name": home,
                        "point": float(home_pt),
                        "price": row.get("price_home"),
                    }
                )
        elif odds_key == "totals":
            total = row.get("total_points")
            if total is None:
                continue
            outcomes.append(
                {
                    "name": "Over",
                    "point": float(total),
                    "price": row.get("over_price"),
                }
            )
            outcomes.append(
                {
                    "name": "Under",
                    "point": float(total),
                    "price": row.get("under_price"),
                }
            )
        else:
            continue
        market["outcomes"] = outcomes
        market["last_update"] = captured or market.get("last_update")

    events = [ev for ev in by_game.values() if ev.get("bookmakers")]
    events.sort(key=lambda e: str(e.get("commence_time") or ""))
    return events


def _load_warehouse_events(now: datetime) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    try:
        from src.db import SessionLocal
        from sqlalchemy import text
    except Exception:
        log.exception("CFB edge-board-odds warehouse import failed")
        return [], None

    cutoff = now - WAREHOUSE_MAX_AGE
    session = SessionLocal()
    try:
        rows = session.execute(
            text(
                """
                SELECT
                  g.external_id,
                  g.start_time,
                  th.name AS home_team,
                  ta.name AS away_team,
                  sb.code AS book,
                  m.code AS market,
                  os.spread_away,
                  os.spread_home,
                  os.price_away,
                  os.price_home,
                  os.total_points,
                  os.over_price,
                  os.under_price,
                  os.captured_at
                FROM odds_snapshots os
                JOIN games g ON g.id = os.game_id
                JOIN seasons s ON s.id = g.season_id
                JOIN leagues l ON l.id = s.league_id
                JOIN teams th ON th.id = g.home_team_id
                JOIN teams ta ON ta.id = g.away_team_id
                JOIN sportsbooks sb ON sb.id = os.sportsbook_id
                JOIN markets m ON m.id = os.market_id
                WHERE l.code = :league
                  AND os.captured_at >= :cutoff
                  AND g.start_time > :now
                """
            ),
            {"league": CFB_LEAGUE_CODE, "cutoff": cutoff, "now": now},
        ).mappings()
        payload = [dict(r) for r in rows]
    except Exception:
        log.exception("CFB edge-board-odds warehouse query failed")
        return [], None
    finally:
        session.close()

    events = reconstruct_events_from_warehouse_rows(payload)
    return events, _max_event_as_of(events)


def _live_pull_events() -> Tuple[List[Dict[str, Any]], Optional[str], Optional[str]]:
    now = time.time()
    cached = _LIVE_CACHE.get("payload")
    if cached is not None and (now - float(_LIVE_CACHE.get("ts") or 0)) < LIVE_CACHE_TTL_SECONDS:
        events = list(cached.get("events") or [])
        return events, cached.get("captured_at"), "live_cache"

    keys = get_odds_api_keys()
    if not keys:
        return [], None, "no_key"

    try:
        payload = fetch_odds(
            endpoint=f"sports/{CFB_SPORT_KEY}/odds",
            params={
                "regions": CFB_REGIONS,
                "markets": "spreads,totals",
                "oddsFormat": "american",
                "bookmakers": CFB_CARRIED_BOOKS,
            },
        )
    except Exception:
        log.exception("CFB edge-board-odds live pull failed")
        return [], None, "live_error"

    events = payload if isinstance(payload, list) else []
    captured = _max_event_as_of(events)
    _LIVE_CACHE["payload"] = {"events": events, "captured_at": captured}
    _LIVE_CACHE["ts"] = now
    return events, captured, "live"


def current_cfb_odds_events(
    *,
    now: Optional[datetime] = None,
    allow_live: bool = True,
) -> Dict[str, Any]:
    clock = now or datetime.now(timezone.utc)
    if clock.tzinfo is None:
        clock = clock.replace(tzinfo=timezone.utc)

    warehouse, warehouse_as_of = _load_warehouse_events(clock)
    if warehouse:
        return {
            "sport": "cfb",
            "sport_key": CFB_SPORT_KEY,
            "source": "odds_snapshots",
            "captured_at": warehouse_as_of,
            "event_count": len(warehouse),
            "events": warehouse,
            "fresh": True,
        }

    if not allow_live:
        return {
            "sport": "cfb",
            "sport_key": CFB_SPORT_KEY,
            "source": "none",
            "captured_at": None,
            "event_count": 0,
            "events": [],
            "fresh": False,
            "reason": "warehouse_empty",
        }

    live, live_as_of, live_source = _live_pull_events()
    if live:
        return {
            "sport": "cfb",
            "sport_key": CFB_SPORT_KEY,
            "source": live_source,
            "captured_at": live_as_of,
            "event_count": len(live),
            "events": live,
            "fresh": True,
        }

    return {
        "sport": "cfb",
        "sport_key": CFB_SPORT_KEY,
        "source": "none",
        "captured_at": None,
        "event_count": 0,
        "events": [],
        "fresh": False,
        "reason": live_source or "empty",
    }
