"""CLV for The Book — post market → close on our side.

Positive = market moved toward our side after post (beat the close).
Reuses NFL sign conventions from nfl_clv_semantics.
"""

from __future__ import annotations

from typing import Optional

from src.services.nfl_clv_semantics import (
    moneyline_clv,
    spread_clv,
    total_clv,
)


def compute_clv(
    *,
    market: str,
    side: str,
    post_line: Optional[float],
    post_price: Optional[float],
    close_line: Optional[float],
    close_price: Optional[float],
) -> Optional[float]:
    """CLV from post snapshot to close. None if inputs incomplete."""
    token = str(market).strip().lower()
    side_tok = str(side).strip().lower()

    if token == "spread":
        if post_line is None or close_line is None:
            return None
        # Rows store the side's line (home/away). Convert to home-spread
        # convention when side is away: away line = -home_spread.
        if side_tok == "home":
            open_home = float(post_line)
            close_home = float(close_line)
        elif side_tok == "away":
            open_home = -float(post_line)
            close_home = -float(close_line)
        else:
            # Explicit home-spread number with side token like "TCU" — treat as home.
            open_home = float(post_line)
            close_home = float(close_line)
            side_tok = "home"
        return round(spread_clv(side=side_tok, open_spread_home=open_home, close_spread_home=close_home), 4)

    if token == "total":
        if post_line is None or close_line is None:
            return None
        return round(
            total_clv(side=side_tok, open_total=float(post_line), close_total=float(close_line)),
            4,
        )

    if token == "ml":
        if post_price is None or close_price is None:
            return None
        return round(
            moneyline_clv(open_price=int(post_price), close_price=int(close_price)),
            6,
        )

    # prop: line-based when both present; side over/under preferred
    if token == "prop":
        if post_line is None or close_line is None:
            return None
        if side_tok in {"over", "under"}:
            return round(
                total_clv(side=side_tok, open_total=float(post_line), close_total=float(close_line)),
                4,
            )
        return round(float(post_line) - float(close_line), 4)

    raise ValueError(f"unsupported market for CLV: {market!r}")
