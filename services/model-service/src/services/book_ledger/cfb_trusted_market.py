"""CFB trusted-market guard (Python port of apps/web/lib/cfb-trusted-market.ts)."""

from __future__ import annotations

from typing import Any, Dict, Literal, Optional

OUTLIER_VS_OPEN_PTS = 3.5
ABSURD_VS_KEI_PTS = 12.0
SINGLE_BOOK_ABSURD_PTS = 8.0

PLAY_EDGE_PTS = 4.0
LEAN_EDGE_PTS = 2.5
# Totals PLAY sits until unused close holdout greens + Ryan/CoS flip.
# See docs/CFB_TOTALS_PLAY_SIT.md — mirror of CFB_TOTALS_PLAY_ELIGIBLE.
TOTALS_PLAY_ELIGIBLE = False

CfbEdgeMarket = Literal["spread", "total"]
CfbEdgeTag = Literal["PLAY", "LEAN", "PASS"]


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


def cfb_edge_tag(
    abs_edge: Optional[float],
    market: CfbEdgeMarket = "spread",
) -> CfbEdgeTag:
    """Port of apps/web/lib/cfb-trusted-market.ts `cfbEdgeTag`."""
    if abs_edge is None:
        return "PASS"
    try:
        e = abs(float(abs_edge))
    except (TypeError, ValueError):
        return "PASS"
    if e != e:  # NaN
        return "PASS"
    if e >= PLAY_EDGE_PTS:
        if market == "total" and not TOTALS_PLAY_ELIGIBLE:
            return "PASS"
        return "PLAY"
    if e >= LEAN_EDGE_PTS:
        return "LEAN"
    return "PASS"


def cfb_publish_tag_from_edge(
    abs_edge: Optional[float],
    market: CfbEdgeMarket = "spread",
) -> CfbEdgeTag:
    """Publish ≡ display after totals PLAY sit remap."""
    return cfb_edge_tag(abs_edge, market)
