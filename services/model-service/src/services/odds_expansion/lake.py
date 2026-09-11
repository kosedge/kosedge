"""Odds lake field contract over existing ``odds_snapshots``.

Append-only: never overwrite a historical ``captured_at`` vintage.
OPEN / CURRENT / CLOSE are labels derived from history, not updates.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

LAKE_FIELDS: tuple[str, ...] = (
    "sport",
    "league",
    "season",
    "canonical_game_id",
    "provider_event_id",
    "book",
    "market_type",
    "side",
    "line",
    "price",
    "retrieved_at",
    "market_as_of",
    "event_start",
    "source",
)

SNAPSHOT_KINDS: tuple[str, ...] = ("OPEN", "CURRENT", "CLOSE", "HIST")


def _aware(dt: datetime | None) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def snapshot_kind_from_history(
    *,
    captured_at: datetime | None,
    first_captured_at: datetime | None,
    last_captured_at: datetime | None,
    event_start: datetime | None = None,
    is_last_pre_kickoff: bool = False,
) -> str:
    """Label a vintage. CLOSE is opt-in (``is_last_pre_kickoff``) — later work."""
    cap = _aware(captured_at)
    first = _aware(first_captured_at)
    last = _aware(last_captured_at)
    if cap is None:
        return "HIST"
    if is_last_pre_kickoff:
        return "CLOSE"
    if first is not None and cap == first:
        return "OPEN"
    if last is not None and cap == last:
        return "CURRENT"
    return "HIST"


def lake_row_from_wide_snapshot(
    *,
    sport: str,
    league: str,
    season: int | None,
    canonical_game_id: str,
    provider_event_id: str | None,
    book: str,
    market_type: str,
    retrieved_at: datetime | None,
    market_as_of: datetime | None,
    event_start: datetime | None,
    source: str | None,
    spread_home: float | None = None,
    spread_away: float | None = None,
    price_home: float | None = None,
    price_away: float | None = None,
    total_points: float | None = None,
    over_price: float | None = None,
    under_price: float | None = None,
) -> List[Dict[str, Any]]:
    """Unpivot a wide ``odds_snapshots`` row into lake side rows."""
    base = {
        "sport": sport,
        "league": league,
        "season": season,
        "canonical_game_id": canonical_game_id,
        "provider_event_id": provider_event_id,
        "book": book,
        "market_type": market_type,
        "retrieved_at": retrieved_at,
        "market_as_of": market_as_of,
        "event_start": event_start,
        "source": source,
    }
    rows: List[Dict[str, Any]] = []
    mt = (market_type or "").lower()
    if mt in {"spread", "spreads"}:
        if spread_away is not None or price_away is not None:
            rows.append({**base, "side": "away", "line": spread_away, "price": price_away})
        if spread_home is not None or price_home is not None:
            rows.append({**base, "side": "home", "line": spread_home, "price": price_home})
    elif mt in {"total", "totals"}:
        if total_points is not None or over_price is not None:
            rows.append({**base, "side": "over", "line": total_points, "price": over_price})
        if total_points is not None or under_price is not None:
            rows.append({**base, "side": "under", "line": total_points, "price": under_price})
    else:
        if price_away is not None:
            rows.append({**base, "side": "away", "line": None, "price": price_away})
        if price_home is not None:
            rows.append({**base, "side": "home", "line": None, "price": price_home})
    for row in rows:
        missing = [f for f in ("sport", "league", "canonical_game_id", "book", "market_type", "side") if not row.get(f)]
        row["_complete"] = not missing
    return rows


def assert_lake_fields(row: Mapping[str, Any]) -> List[str]:
    return [name for name in LAKE_FIELDS if name not in row]
