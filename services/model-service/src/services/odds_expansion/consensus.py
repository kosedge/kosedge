"""Multi-book consensus — never a KEI / Fair stand-in.

Best formula for *product* math stays UNKNOWN (MARKET_ODDS audit).
This helper is inventory + isolation only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from statistics import median
from typing import Any, Iterable, List, Optional, Sequence


@dataclass(frozen=True)
class BookQuote:
    book: str
    line: Optional[float]
    price: Optional[float]
    market_as_of: Optional[datetime]
    market_type: str = "spread"


@dataclass(frozen=True)
class ConsensusResult:
    best_line: Optional[float]
    best_book: Optional[str]
    consensus_line: Optional[float]
    book_count: int
    isolated_count: int
    dispersion: Optional[float]
    freshness: Optional[datetime]
    isolated_books: tuple[str, ...] = field(default_factory=tuple)
    stale_books: tuple[str, ...] = field(default_factory=tuple)
    reason: str = "ok"


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _finite(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    if n != n:  # NaN
        return None
    return n


def _iqr(values: Sequence[float]) -> Optional[float]:
    if len(values) < 2:
        return 0.0 if values else None
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2 == 0:
        lower = ordered[:mid]
        upper = ordered[mid:]
    else:
        lower = ordered[:mid]
        upper = ordered[mid + 1 :]
    if not lower or not upper:
        return 0.0
    q1 = median(lower)
    q3 = median(upper)
    return float(q3 - q1)


def isolate_rogue_or_stale(
    quotes: Iterable[BookQuote],
    *,
    now: Optional[datetime] = None,
    stale_after: timedelta = timedelta(hours=6),
    iqr_fence: float = 2.5,
) -> tuple[List[BookQuote], List[BookQuote], List[BookQuote]]:
    """Return (kept, rogue, stale). Stale never wins Best/consensus."""
    clock = now or datetime.now(timezone.utc)
    clock = _aware(clock)
    fresh: List[BookQuote] = []
    stale: List[BookQuote] = []
    for quote in quotes:
        if not quote.book or _finite(quote.line) is None:
            continue
        as_of = quote.market_as_of
        if as_of is None:
            stale.append(quote)
            continue
        if clock - _aware(as_of) > stale_after:
            stale.append(quote)
            continue
        fresh.append(quote)

    if len(fresh) < 3:
        return fresh, [], stale

    lines = [_finite(q.line) for q in fresh]
    nums = [n for n in lines if n is not None]
    if not nums:
        return fresh, [], stale
    mid = float(median(nums))
    # MAD is robust to a single junk book; raw IQR is not.
    abs_dev = [abs(n - mid) for n in nums]
    mad = float(median(abs_dev))
    spread = _iqr(nums) or 0.0
    fence = max(1.0, iqr_fence * mad if mad > 0 else spread * iqr_fence)
    kept: List[BookQuote] = []
    rogue: List[BookQuote] = []
    for quote in fresh:
        line = _finite(quote.line)
        if line is None:
            continue
        if abs(line - mid) > fence:
            rogue.append(quote)
        else:
            kept.append(quote)
    return kept, rogue, stale


def multi_book_consensus(
    quotes: Iterable[BookQuote],
    *,
    now: Optional[datetime] = None,
    prefer_home_negative_spread: bool = True,
) -> ConsensusResult:
    """Median consensus + shop-side best among non-isolated books."""
    pool = [q for q in quotes if q.book]
    if not pool:
        return ConsensusResult(
            best_line=None,
            best_book=None,
            consensus_line=None,
            book_count=0,
            isolated_count=0,
            dispersion=None,
            freshness=None,
            reason="no_quotes",
        )

    kept, rogue, stale = isolate_rogue_or_stale(pool, now=now)
    isolated = rogue + stale
    working = kept if kept else [q for q in pool if _finite(q.line) is not None]
    lines = [_finite(q.line) for q in working]
    nums = [n for n in lines if n is not None]
    if not nums:
        return ConsensusResult(
            best_line=None,
            best_book=None,
            consensus_line=None,
            book_count=0,
            isolated_count=len(isolated),
            dispersion=None,
            freshness=None,
            isolated_books=tuple(q.book for q in rogue),
            stale_books=tuple(q.book for q in stale),
            reason="no_lines",
        )

    cons = float(median(nums))
    # Shop-side best: more points for the listed side.
    # Spreads: more positive away / more negative home — caller passes signed line.
    if prefer_home_negative_spread and all(
        (q.market_type or "").lower() in {"spread", "spreads"} for q in working
    ):
        best_quote = min(working, key=lambda q: (_finite(q.line) is None, _finite(q.line)))
    else:
        best_quote = max(working, key=lambda q: (_finite(q.line) or float("-inf")))

    as_ofs = [q.market_as_of for q in working if q.market_as_of is not None]
    freshness = max((_aware(a) for a in as_ofs), default=None)

    return ConsensusResult(
        best_line=_finite(best_quote.line),
        best_book=best_quote.book,
        consensus_line=cons,
        book_count=len(working),
        isolated_count=len(isolated),
        dispersion=_iqr(nums),
        freshness=freshness,
        isolated_books=tuple(q.book for q in rogue),
        stale_books=tuple(q.book for q in stale),
        reason="ok",
    )
