from __future__ import annotations

import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import httpx
from fastapi import APIRouter, HTTPException
from zoneinfo import ZoneInfo

router = APIRouter(prefix="/edge-board", tags=["edge-board"])

ODDS_API_BASE = "https://api.the-odds-api.com/v4"
SPORT_KEY_NCAAB = "basketball_ncaab"
ET = ZoneInfo("America/New_York")

CACHE_TTL_SECONDS = int(os.getenv("EDGE_BOARD_CACHE_TTL_SECONDS", "25"))
_HTTP_TIMEOUT_SECONDS = float(os.getenv("EDGE_BOARD_HTTP_TIMEOUT_SECONDS", "15"))

# Simple in-memory cache to avoid hammering Odds API
_CACHE: Dict[str, Any] = {"ts": 0.0, "data": None}


def _american_to_str(price: Optional[int]) -> str:
    if price is None:
        return "—"
    return f"{price:+d}" if price > 0 else str(price)


def _fmt_spread(points: Optional[float]) -> str:
    if points is None:
        return "—"
    return f"{points:+.1f}".rstrip("0").rstrip(".")


def _fmt_total(points: Optional[float]) -> str:
    if points is None:
        return "—"
    return f"{points:.1f}".rstrip("0").rstrip(".")


def _fmt_time_et(commence_iso: Optional[str]) -> str:
    if not commence_iso:
        return "—"
    try:
        dt = datetime.fromisoformat(commence_iso.replace("Z", "+00:00")).astimezone(ET)
        return dt.strftime("%-I:%M%p").lower()
    except Exception:
        return "—"


def _pick_open_book(bookmakers: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    "Open" isn't truly available without historical odds.
    For now: first available bookmaker, preferring DraftKings when present.
    """
    if not bookmakers:
        return None
    for b in bookmakers:
        if (b.get("key") or "").lower() == "draftkings":
            return b
    return bookmakers[0]


def _iter_market_outcomes(
    books: List[Dict[str, Any]], market_key: str
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Generator helper pattern: yields (book, outcome) for a given market.
    Not exposed; kept as a local iterator via tuple return to avoid a generator type export.
    """
    # This is just a type-friendly placeholder; actual iteration happens in the caller loops.
    return {}, {}


def _best_spread_for_team(team: str, books: List[Dict[str, Any]]) -> Tuple[str, str]:
    """
    Best spread for a team:
      1) prefer larger point (better for that team)
      2) if point ties, prefer higher price (e.g. +120 > +110, -105 > -110)
    """
    best_point: Optional[float] = None
    best_price: Optional[int] = None

    for b in books:
        for m in b.get("markets", []) or []:
            if m.get("key") != "spreads":
                continue
            for o in m.get("outcomes", []) or []:
                if o.get("name") != team:
                    continue
                pt = o.get("point")
                pr = o.get("price")
                if pt is None or pr is None:
                    continue

                if best_point is None:
                    best_point, best_price = float(pt), int(pr)
                    continue

                if float(pt) > best_point:
                    best_point, best_price = float(pt), int(pr)
                elif float(pt) == best_point and int(pr) > (best_price or -10_000):
                    best_price = int(pr)

    return _fmt_spread(best_point), _american_to_str(best_price)


def _best_total(over_under: str, books: List[Dict[str, Any]]) -> Tuple[str, str]:
    """
    Best total for Over/Under:
      - Over prefers LOWER total
      - Under prefers HIGHER total
      - if point ties, prefer higher price (better juice)
    """
    best_point: Optional[float] = None
    best_price: Optional[int] = None

    for b in books:
        for m in b.get("markets", []) or []:
            if m.get("key") != "totals":
                continue
            for o in m.get("outcomes", []) or []:
                if o.get("name") != over_under:
                    continue
                pt = o.get("point")
                pr = o.get("price")
                if pt is None or pr is None:
                    continue

                pt_f = float(pt)
                pr_i = int(pr)

                if best_point is None:
                    best_point, best_price = pt_f, pr_i
                    continue

                if over_under == "Over":
                    if pt_f < best_point:
                        best_point, best_price = pt_f, pr_i
                    elif pt_f == best_point and pr_i > (best_price or -10_000):
                        best_price = pr_i
                else:
                    if pt_f > best_point:
                        best_point, best_price = pt_f, pr_i
                    elif pt_f == best_point and pr_i > (best_price or -10_000):
                        best_price = pr_i

    label = ("o" if over_under == "Over" else "u") + _fmt_total(best_point)
    return label, _american_to_str(best_price)


def _open_spread(team: str, open_book: Optional[Dict[str, Any]]) -> Tuple[str, str]:
    if not open_book:
        return "—", "—"

    for m in open_book.get("markets", []) or []:
        if m.get("key") != "spreads":
            continue
        for o in m.get("outcomes", []) or []:
            if o.get("name") == team:
                return _fmt_spread(o.get("point")), _american_to_str(o.get("price"))

    return "—", "—"


def _open_total(over_under: str, open_book: Optional[Dict[str, Any]]) -> Tuple[str, str]:
    if not open_book:
        return "—", "—"

    for m in open_book.get("markets", []) or []:
        if m.get("key") != "totals":
            continue
        for o in m.get("outcomes", []) or []:
            if o.get("name") == over_under:
                label = ("o" if over_under == "Over" else "u") + _fmt_total(o.get("point"))
                return label, _american_to_str(o.get("price"))

    return "—", "—"


async def _fetch_odds_ncaab() -> List[Dict[str, Any]]:
    api_key = os.getenv("ODDS_API_KEY")
    if not api_key or api_key == "YOUR_ODDS_API_KEY":
        raise HTTPException(status_code=500, detail="ODDS_API_KEY is not set")

    url = f"{ODDS_API_BASE}/sports/{SPORT_KEY_NCAAB}/odds"
    params = {
        "apiKey": api_key,
        "regions": "us",
        "markets": "spreads,totals",
        "oddsFormat": "american",
        "dateFormat": "iso",
    }

    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT_SECONDS) as client:
            r = await client.get(url, params=params)
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Odds API request failed: {e}") from e

    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Odds API error: {r.status_code} {r.text}")

    data = r.json()
    if not isinstance(data, list):
        raise HTTPException(status_code=502, detail="Odds API returned unexpected payload")
    return data


@router.get("/ncaam/today")
async def edge_board_ncaam_today() -> Dict[str, Any]:
    now = time.time()
    cached = _CACHE["data"] is not None and (now - float(_CACHE["ts"])) < CACHE_TTL_SECONDS
    if cached:
        return {"rows": _CACHE["data"], "cached": True, "ttl": CACHE_TTL_SECONDS}

    events = await _fetch_odds_ncaab()
    rows: List[Dict[str, Any]] = []

    for e in events:
        away = e.get("away_team")
        home = e.get("home_team")
        if not away or not home:
            continue

        time_label = _fmt_time_et(e.get("commence_time"))
        books = e.get("bookmakers", []) or []
        open_book = _pick_open_book(books)

        # OPEN
        open_over_label, open_over_juice = _open_total("Over", open_book)
        open_under_label, open_under_juice = _open_total("Under", open_book)
        open_away_spread_label, open_away_spread_juice = _open_spread(away, open_book)
        open_home_spread_label, open_home_spread_juice = _open_spread(home, open_book)

        # BEST
        best_away_spread_label, best_away_spread_juice = _best_spread_for_team(away, books)
        best_home_spread_label, best_home_spread_juice = _best_spread_for_team(home, books)
        best_over_label, best_over_juice = _best_total("Over", books)
        best_under_label, best_under_juice = _best_total("Under", books)

        rows.append(
            {
                "id": e.get("id") or f"{away}@{home}",
                "time": time_label,
                "teamA": {"name": away, "site": "Away"},
                "teamB": {"name": home, "site": "Home"},
                "openOU": {
                    "top": {"label": open_over_label, "juice": open_over_juice},
                    "bottom": {"label": open_under_label, "juice": open_under_juice},
                },
                "openLine": {
                    "top": {"label": open_away_spread_label, "juice": open_away_spread_juice},
                    "bottom": {"label": open_home_spread_label, "juice": open_home_spread_juice},
                },
                "bestLine": {
                    "top": {"label": best_away_spread_label, "juice": best_away_spread_juice},
                    "bottom": {"label": best_home_spread_label, "juice": best_home_spread_juice},
                },
                "bestOU": {
                    "top": {"label": best_over_label, "juice": best_over_juice},
                    "bottom": {"label": best_under_label, "juice": best_under_juice},
                },
            }
        )

    _CACHE["data"] = rows
    _CACHE["ts"] = now
    return {"rows": rows, "cached": False, "ttl": CACHE_TTL_SECONDS}