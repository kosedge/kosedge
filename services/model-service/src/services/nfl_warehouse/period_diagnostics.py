"""1H / alt-line diagnostics for why a mainline side or total missed.

Not a product board. Used after the mainline holdout is green to explain
script, pace, and key-number (3/7) crossings.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

KEY_NUMBERS = (3.0, 7.0)


def _f(value: Any) -> Optional[float]:
    try:
        return float(value) if value is not None and value != "" else None
    except (TypeError, ValueError):
        return None


def _crossed_key(open_sp: Optional[float], close_sp: Optional[float]) -> List[float]:
    if open_sp is None or close_sp is None:
        return []
    crossed: List[float] = []
    lo, hi = sorted((abs(open_sp), abs(close_sp)))
    for key in KEY_NUMBERS:
        if lo < key < hi or (open_sp < 0 <= close_sp) or (close_sp < 0 <= open_sp):
            if min(open_sp, close_sp) <= key <= max(open_sp, close_sp) or min(
                -open_sp, -close_sp
            ) <= key <= max(-open_sp, -close_sp):
                crossed.append(key)
    return sorted(set(crossed))


def diagnose_mainline(
    *,
    actual_home_margin: Optional[float],
    actual_total: Optional[float],
    close_spread_home: Optional[float],
    close_total: Optional[float],
    h1_spread_home: Optional[float] = None,
    h1_total: Optional[float] = None,
    open_spread_home: Optional[float] = None,
    alt_spreads: Optional[Sequence[float]] = None,
) -> Dict[str, Any]:
    """Return research-only reasons. Empty reasons means 'no extra signal'."""
    reasons: List[str] = []
    close_sp = _f(close_spread_home)
    close_tot = _f(close_total)
    margin = _f(actual_home_margin)
    total = _f(actual_total)
    h1_sp = _f(h1_spread_home)
    h1_tot = _f(h1_total)
    open_sp = _f(open_spread_home)

    if margin is not None and close_sp is not None:
        ats = (margin + close_sp) > 0
        if not ats and h1_sp is not None:
            h1_ats = (margin + h1_sp) > 0
            if h1_ats != ats:
                reasons.append("1h_spread_disagrees_with_full_game")
        crossed = _crossed_key(open_sp, close_sp)
        if crossed:
            reasons.append("key_number_crossed:" + ",".join(f"{k:g}" for k in crossed))

    if total is not None and close_tot is not None:
        went_over = total > close_tot
        if h1_tot is not None:
            # First-half total as a pace tell vs full-game close.
            if went_over and h1_tot >= (close_tot * 0.52):
                reasons.append("1h_total_hot_vs_full_close")
            if (not went_over) and h1_tot <= (close_tot * 0.42):
                reasons.append("1h_total_cold_vs_full_close")

    alts = [_f(x) for x in (alt_spreads or []) if _f(x) is not None]
    if close_sp is not None and alts:
        if any(abs(float(a) - abs(close_sp)) <= 0.5 for a in alts if a is not None):
            reasons.append("alt_cluster_at_close")

    return {
        "reasons": reasons,
        "product": False,
        "note": "diagnostic only — do not ship a 1H/alts desk from this payload",
    }
