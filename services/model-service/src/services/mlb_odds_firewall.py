"""DK-first odds firewall for MLB CLV / consensus / densify.

Historical and live MLB pricing should prefer DraftKings when present, then
FanDuel, then remaining US books. Alternate run lines outside the canonical
±1.5 band are excluded from CLV / closing-line aggregation unless explicitly
allowed.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

MLB_CANONICAL_RUN_LINE_ABS = 1.5
MLB_CANONICAL_RUN_LINE_MAX = 2.5

# Higher rank = preferred. Unknown books get 0.
BOOK_PRIORITY: Dict[str, int] = {
    "draftkings": 100,
    "fanduel": 80,
    "betmgm": 60,
    "williamhill_us": 55,
    "caesars": 55,
    "pointsbetus": 40,
    "betrivers": 35,
    "bovada": 20,
    "betonlineag": 15,
    "lowvig": 10,
    "mybookieag": 5,
}

DEFAULT_DENSIFY_BOOKS = "draftkings,fanduel"
DEFAULT_PREFERRED_BOOK = "draftkings"


def normalize_book_code(raw: Any) -> str:
    return str(raw or "").strip().lower()


def book_priority(book_code: Any) -> int:
    return int(BOOK_PRIORITY.get(normalize_book_code(book_code), 0))


def is_canonical_mlb_run_line(point: Optional[float]) -> bool:
    if point is None:
        return False
    try:
        value = abs(float(point))
    except (TypeError, ValueError):
        return False
    return value <= MLB_CANONICAL_RUN_LINE_MAX + 1e-9


def is_standard_run_line(point: Optional[float]) -> bool:
    if point is None:
        return False
    try:
        value = abs(float(point))
    except (TypeError, ValueError):
        return False
    return abs(value - MLB_CANONICAL_RUN_LINE_ABS) < 1e-9


def select_preferred_book_row(
    rows: Sequence[Mapping[str, Any]],
    *,
    book_key: str = "book_code",
    preferred_book: str = DEFAULT_PREFERRED_BOOK,
) -> Optional[Mapping[str, Any]]:
    """Pick the best row by DK-first priority, with preferred_book override."""
    if not rows:
        return None
    preferred = normalize_book_code(preferred_book)
    ranked: List[Mapping[str, Any]] = []
    for row in rows:
        code = normalize_book_code(row.get(book_key) or row.get("sportsbook_code") or row.get("bookmaker"))
        if not code:
            continue
        ranked.append(row)
    if not ranked:
        return None

    def sort_key(row: Mapping[str, Any]) -> tuple:
        code = normalize_book_code(row.get(book_key) or row.get("sportsbook_code") or row.get("bookmaker"))
        preferred_hit = 1 if code == preferred else 0
        return (preferred_hit, book_priority(code))

    return max(ranked, key=sort_key)


def filter_spread_rows_for_firewall(
    rows: Iterable[Mapping[str, Any]],
    *,
    spread_key: str = "spread_home",
    allow_alternate: bool = False,
) -> List[Mapping[str, Any]]:
    out: List[Mapping[str, Any]] = []
    for row in rows:
        point = row.get(spread_key)
        if point is None:
            continue
        try:
            value = float(point)
        except (TypeError, ValueError):
            continue
        if allow_alternate:
            if is_canonical_mlb_run_line(value):
                out.append(row)
        elif is_standard_run_line(value) or is_canonical_mlb_run_line(value):
            # Prefer true ±1.5; still accept other canonical lines ≤2.5 when ±1.5 missing.
            out.append(row)
    # If any standard ±1.5 rows exist, drop non-standard.
    standard = [r for r in out if is_standard_run_line(r.get(spread_key))]
    return standard if standard else out


def densify_bookmakers_csv(raw: Optional[str] = None) -> str:
    tokens = [
        normalize_book_code(tok)
        for tok in str(raw or DEFAULT_DENSIFY_BOOKS).split(",")
        if normalize_book_code(tok)
    ]
    if not tokens:
        tokens = [DEFAULT_PREFERRED_BOOK]
    # Ensure preferred book is first.
    preferred = DEFAULT_PREFERRED_BOOK
    ordered = [preferred] + [t for t in tokens if t != preferred]
    # Deduplicate preserving order.
    seen = set()
    unique: List[str] = []
    for tok in ordered:
        if tok in seen:
            continue
        seen.add(tok)
        unique.append(tok)
    return ",".join(unique)


def firewall_summary(
    *,
    preferred_book: str = DEFAULT_PREFERRED_BOOK,
    books_seen: Sequence[str] = (),
    spreads_kept: int = 0,
    spreads_dropped_alt: int = 0,
) -> Dict[str, Any]:
    return {
        "preferred_book": normalize_book_code(preferred_book),
        "books_seen": [normalize_book_code(b) for b in books_seen if normalize_book_code(b)],
        "dk_first": True,
        "spreads_kept": int(spreads_kept),
        "spreads_dropped_alt": int(spreads_dropped_alt),
        "canonical_run_line_abs": MLB_CANONICAL_RUN_LINE_ABS,
        "canonical_run_line_max": MLB_CANONICAL_RUN_LINE_MAX,
    }
