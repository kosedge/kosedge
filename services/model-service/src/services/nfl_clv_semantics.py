"""NFL closing-line value — one definition, one sign convention.

CLV is the movement of our recommended side's market from the first captured
price (open) to the last captured price (called close) on the same market.
Positive means the market moved toward our side after the play was implied —
we got a better number than the later line (beat the close).
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional, Sequence

NFL_CLV_DEFINITION = (
    "CLV is the movement of our recommended side's market from the first "
    "captured price (open) to the last captured price (called close) on the "
    "same market. Positive means the market moved toward our side after the "
    "play was implied — we got a better number than the later line (beat the close)."
)

NFL_CLV_POPULATION = (
    "Rows are +EV vs the open snapshot only (moneyline: model win probability "
    "exceeds open implied probability on that side; total: |model − open| ≥ 1.0; "
    "spread: |model − open| ≥ 1.0 home-spread points). "
    "Not PLAY-only. Not graded-only."
)

NFL_CLV_TIMESTAMPS = (
    "Open = first legal snapshot (prefer snapshot_kind=open) and close = last "
    "snapshot strictly before kickoff (prefer snapshot_kind=close) on "
    "nfl_market_history_snapshots. Post-kickoff rows are not close."
)

# Inclusive last calendar day treated as preseason. Matches web nfl-truth-label
# and historical_replay PRESEASON_CUTOFF_BY_SEASON. REG Week 1 2026 is 2026-09-10.
NFL_PRESEASON_CUTOFF: Dict[int, date] = {
    2025: date(2025, 9, 1),
    2026: date(2026, 9, 7),
}

PUSH_EPS = 1e-12
MIN_DECIDED_FOR_TRUST = 20


def american_implied_prob(price: int) -> float:
    if price > 0:
        return 100.0 / (price + 100.0)
    return abs(price) / (abs(price) + 100.0)


def moneyline_clv(*, open_price: int, close_price: int) -> float:
    """close_imp − open_imp on the same side. Positive = beat the later line."""
    return american_implied_prob(close_price) - american_implied_prob(open_price)


def total_clv(*, side: str, open_total: float, close_total: float) -> float:
    """Over: close − open. Under: open − close. Positive = market moved toward us."""
    token = side.strip().lower()
    if token == "over":
        return close_total - open_total
    if token == "under":
        return open_total - close_total
    raise ValueError(f"total side must be over or under, got {side!r}")


def spread_clv(*, side: str, open_spread_home: float, close_spread_home: float) -> float:
    """Odds API: more negative = home more favored. Home: open − close. Away: close − open."""
    token = side.strip().lower()
    if token == "home":
        return open_spread_home - close_spread_home
    if token == "away":
        return close_spread_home - open_spread_home
    raise ValueError(f"spread side must be home or away, got {side!r}")


def classify_clv(value: float, eps: float = PUSH_EPS) -> str:
    if value > eps:
        return "beat"
    if value < -eps:
        return "lose"
    return "push"


def summarize_clv_values(
    values: Sequence[float],
    *,
    eps: float = PUSH_EPS,
) -> Dict[str, Any]:
    n = len(values)
    beat = sum(1 for value in values if value > eps)
    lose = sum(1 for value in values if value < -eps)
    push = n - beat - lose
    return market_summary_from_counts(
        n=n,
        beat=beat,
        push=push,
        lose=lose,
        avg_clv=(sum(values) / n) if n else None,
    )


def market_summary_from_counts(
    *,
    n: int,
    beat: int,
    push: int,
    lose: int,
    avg_clv: Optional[float],
) -> Dict[str, Any]:
    decided = beat + lose
    return {
        "sample_size": n,
        "n": n,
        "avg_clv": avg_clv,
        "beat_close": beat,
        "push": push,
        "lose_close": lose,
        "decided_n": decided,
        "positive_clv": beat,
        "non_positive_clv": push + lose,
        # Share of all rows with CLV > 0. Pushes sit in the denominator.
        "positive_clv_rate": (beat / n) if n else None,
        # Share of moved lines that beat the later snapshot. Pushes excluded.
        "beat_close_rate": (beat / decided) if decided else None,
    }


def nfl_product_season(as_of: date) -> int:
    return as_of.year if as_of.month >= 3 else as_of.year - 1


def nfl_calendar_is_preseason(as_of: date) -> bool:
    season = nfl_product_season(as_of)
    cutoff = NFL_PRESEASON_CUTOFF.get(season) or date(season, 9, 7)
    return as_of <= cutoff


def assess_live_clv_trust(
    *,
    as_of: date,
    n: int,
    beat: int,
    push: int,
    lose: int,
    min_decided: int = MIN_DECIDED_FOR_TRUST,
) -> Dict[str, Any]:
    decided = beat + lose
    push_share = (push / n) if n else 1.0
    reasons: List[str] = []
    if nfl_calendar_is_preseason(as_of):
        reasons.append("preseason_no_reg_closes")
    if n <= 0:
        reasons.append("no_rows")
    elif decided < min_decided:
        reasons.append("tiny_decided_sample")
    if n > 0 and push_share >= 0.5:
        reasons.append("majority_identical_open_close")
    return {
        "trustworthy": len(reasons) == 0,
        "reasons": reasons,
        "push_share": push_share,
        "decided_n": decided,
        "min_decided": min_decided,
    }
