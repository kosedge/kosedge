"""Stake close for NFL PLAY tags: DraftKings, then FanDuel, then consensus.

Best-of-books is a shop number. PLAY must grade the line a subscriber can
actually bet at DK or FD.
"""

from __future__ import annotations

from typing import Any, Optional, Tuple

STAKE_BOOKS = ("draftkings", "fanduel")


def _f(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if out != out:
        return None
    return out


def stake_close_spread(
    *,
    draftkings: Any = None,
    fanduel: Any = None,
    consensus: Any = None,
    best: Any = None,
) -> Tuple[Optional[float], str]:
    """Return (spread_home, book_used). Odds API sign."""
    dk = _f(draftkings)
    if dk is not None:
        return dk, "draftkings"
    fd = _f(fanduel)
    if fd is not None:
        return fd, "fanduel"
    cons = _f(consensus)
    if cons is not None:
        return cons, "consensus"
    b = _f(best)
    if b is not None:
        return b, "best"
    return None, ""
