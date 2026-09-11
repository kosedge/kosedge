"""Market-driven event discovery — no current-week window.

Provider catalog → bookmakers → markets → ingest iff a verified
spread / total / moneyline exists. Kickoff may be weeks or months away.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

# Same sports as tasks.SPORT_MAP / web SPORT_KEY_MAP.
EXPANSION_SPORT_KEYS: tuple[str, ...] = (
    "americanfootball_ncaaf",
    "americanfootball_nfl",
    "basketball_nba",
    "basketball_ncaab",
    "baseball_mlb",
    "icehockey_nhl",
    "basketball_wnba",
)

MAINLINE_MARKET_KEYS = frozenset({"h2h", "spreads", "totals", "moneyline", "spread", "total"})


def _parse_iso(raw: Any) -> Optional[datetime]:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _outcomes(market: Mapping[str, Any]) -> Sequence[Mapping[str, Any]]:
    raw = market.get("outcomes")
    if not isinstance(raw, list):
        return ()
    return [o for o in raw if isinstance(o, Mapping)]


def _market_has_verified_quote(market: Mapping[str, Any]) -> bool:
    key = str(market.get("key") or "").strip().lower()
    if key not in MAINLINE_MARKET_KEYS:
        return False
    priced = 0
    for outcome in _outcomes(market):
        price = outcome.get("price")
        if price is None:
            continue
        try:
            float(price)
        except (TypeError, ValueError):
            continue
        # Spreads/totals need a line; ML is price-only.
        if key in {"spreads", "totals", "spread", "total"}:
            point = outcome.get("point")
            if point is None:
                continue
            try:
                float(point)
            except (TypeError, ValueError):
                continue
        priced += 1
    return priced >= 1


def event_has_verified_mainline(event: Mapping[str, Any] | None) -> bool:
    """True when at least one book posted a real spread, total, or ML."""
    if not isinstance(event, Mapping):
        return False
    books = event.get("bookmakers")
    if not isinstance(books, list) or not books:
        return False
    for book in books:
        if not isinstance(book, Mapping):
            continue
        if not str(book.get("key") or "").strip():
            continue
        markets = book.get("markets")
        if not isinstance(markets, list):
            continue
        for market in markets:
            if isinstance(market, Mapping) and _market_has_verified_quote(market):
                return True
    return False


def should_ingest_event(
    event: Mapping[str, Any] | None,
    *,
    now: Optional[datetime] = None,
) -> bool:
    """Ingest when a verified mainline exists. No current-week / days-ahead cap.

    ``now`` is accepted for call-site symmetry and future live-game gates.
    It must not be used to drop far-future kickoffs.
    """
    del now  # explicit: clock must not week-filter
    if not isinstance(event, Mapping):
        return False
    if not str(event.get("id") or "").strip():
        return False
    if not str(event.get("home_team") or "").strip():
        return False
    if not str(event.get("away_team") or "").strip():
        return False
    if _parse_iso(event.get("commence_time")) is None:
        return False
    return event_has_verified_mainline(event)


def filter_ingestible_events(
    events: Iterable[Mapping[str, Any] | None],
    *,
    now: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """Keep verified-book events only. Never drop because kickoff is far away."""
    kept: List[Dict[str, Any]] = []
    for event in events:
        if should_ingest_event(event, now=now) and isinstance(event, Mapping):
            kept.append(dict(event))
    return kept


def catalog_coverage(
    catalog_events: Iterable[Mapping[str, Any] | None],
    odds_events: Iterable[Mapping[str, Any] | None],
    *,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Compare cheap ``/events`` catalog to ``/odds`` payload.

    Catalog IDs without verified books are **coverage**, not ingest.
    """
    clock = now or datetime.now(timezone.utc)
    if clock.tzinfo is None:
        clock = clock.replace(tzinfo=timezone.utc)

    catalog_ids: List[str] = []
    future_catalog = 0
    for event in catalog_events:
        if not isinstance(event, Mapping):
            continue
        eid = str(event.get("id") or "").strip()
        if not eid:
            continue
        catalog_ids.append(eid)
        start = _parse_iso(event.get("commence_time"))
        if start is not None and start > clock:
            future_catalog += 1

    odds_ids: List[str] = []
    ingestible = 0
    far_future_ingested = 0
    for event in odds_events:
        if not isinstance(event, Mapping):
            continue
        eid = str(event.get("id") or "").strip()
        if eid:
            odds_ids.append(eid)
        if should_ingest_event(event, now=clock):
            ingestible += 1
            start = _parse_iso(event.get("commence_time"))
            if start is not None and (start - clock).days > 7:
                far_future_ingested += 1

    catalog_set = set(catalog_ids)
    odds_set = set(odds_ids)
    return {
        "catalog_events": len(catalog_ids),
        "odds_events": len(odds_ids),
        "ingestible_events": ingestible,
        "future_catalog_events": future_catalog,
        "far_future_ingested": far_future_ingested,
        "catalog_missing_odds": len(catalog_set - odds_set),
        "odds_not_in_catalog": len(odds_set - catalog_set),
        "week_filter": None,
        "horizon": "all_available",
    }
