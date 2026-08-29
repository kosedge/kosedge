"""CFB trusted-market guard (Python port of apps/web/lib/cfb-trusted-market.ts)."""

from __future__ import annotations

from typing import Any, Dict, Optional

OUTLIER_VS_OPEN_PTS = 3.5
ABSURD_VS_KEI_PTS = 12.0
SINGLE_BOOK_ABSURD_PTS = 8.0


def _f(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def trust_cfb_market(
    *,
    kei: Any,
    best: Any = None,
    open_line: Any = None,
    book_count: Optional[int] = None,
) -> Dict[str, Any]:
    kei_n = _f(kei)
    best_n = _f(best)
    open_n = _f(open_line)
    books = book_count
    if books is None:
        books = 2 if (best_n is not None and open_n is not None and best_n != open_n) else 1

    if kei_n is None:
        return {"trusted": False, "market": None, "reason": "no_kei"}
    if best_n is None and open_n is None:
        return {"trusted": False, "market": None, "reason": "no_market"}

    candidate = best_n if best_n is not None else open_n
    reason = "best"
    if best_n is not None and open_n is not None and abs(best_n - open_n) >= OUTLIER_VS_OPEN_PTS:
        candidate = open_n
        reason = "best_outlier_vs_open"

    if candidate is None:
        return {"trusted": False, "market": None, "reason": "no_candidate"}

    gap = abs(candidate - kei_n)
    if gap >= ABSURD_VS_KEI_PTS:
        return {"trusted": False, "market": None, "reason": "absurd_vs_kei"}
    if books < 2 and gap >= SINGLE_BOOK_ABSURD_PTS:
        return {"trusted": False, "market": None, "reason": "single_book_outlier"}

    return {"trusted": True, "market": candidate, "reason": reason}
