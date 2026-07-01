from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Tuple

BOOK_WEIGHTS: Dict[str, float] = {
    "pinnacle": 1.35,
    "circa": 1.30,
    "bookmaker": 1.25,
    "betonlineag": 1.15,
    "draftkings": 1.00,
    "fanduel": 1.00,
    "caesars": 0.95,
    "betmgm": 0.95,
    "espnbet": 0.90,
    "betrivers": 0.90,
}


def _book_weight(book_key: Optional[str]) -> float:
    if not book_key:
        return 0.85
    return BOOK_WEIGHTS.get(book_key.lower(), 0.85)


def book_weight(book_key: Optional[str]) -> float:
    return _book_weight(book_key)


def _trimmed(values: List[float], trim_pct: float = 0.15) -> List[float]:
    if not values:
        return []
    s = sorted(values)
    k = int(len(s) * trim_pct)
    if len(s) - 2 * k < 3:
        return s
    return s[k : len(s) - k]


def weighted_consensus(
    pairs: Iterable[Tuple[str, float]],
    *,
    trim_pct: float = 0.15,
) -> Optional[float]:
    vals = [(book, float(v)) for book, v in pairs]
    if not vals:
        return None
    trimmed_values = _trimmed([v for _, v in vals], trim_pct=trim_pct)
    trimmed_set = set(trimmed_values)
    kept = [(book, v) for book, v in vals if v in trimmed_set]
    if not kept:
        kept = vals
    w_sum = 0.0
    wx_sum = 0.0
    for book, value in kept:
        w = _book_weight(book)
        w_sum += w
        wx_sum += w * value
    if w_sum <= 0:
        return None
    return wx_sum / w_sum

