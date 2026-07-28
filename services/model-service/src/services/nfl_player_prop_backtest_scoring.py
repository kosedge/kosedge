from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

from .nfl_player_projection_engine import evaluate_prop_edge

"""Pure scoring functions for the player-prop-vs-market benchmark
(data/ops/nfl-player-prop-vegas-benchmark/compute_benchmark.py).

Kept here, in the production service package, rather than inside the
analysis script -- the exact same reasoning as
data/ops/nfl-matchup-engine-backtest/backtest_matchup_engine.py importing
`baseline_projection_from_features` instead of reimplementing it: these
functions decide what "the model favored a side" and "did that side win"
mean, so they need to be covered by this project's normal pytest suite
(services/model-service/tests/), not hidden inside a one-off script no test
suite ever imports.

This module answers a different, harder question than
`baseline_projection_from_features`'s own MAE-vs-truth validation: given a
REAL market closing line and price, would betting the side the model
favored have been profitable/well-calibrated -- not just "was the model's
mean close to the truth". It reuses `evaluate_prop_edge()` (the same
production function already used for the live prop-edge board) to get the
model's implied probability and edge, rather than re-deriving American-odds
math a second time.
"""


def model_favored_side(model_mean: float, line: float) -> str:
    """Which side of a real market line the model's mean favors. A mean
    that lands EXACTLY on the line has no favored side -- flagged as
    "push_no_side" rather than arbitrarily defaulting to over, since a real
    bettor would have no edge-driven reason to pick either side here."""
    if model_mean > line:
        return "over"
    if model_mean < line:
        return "under"
    return "push_no_side"


def grade_actual_outcome(actual: float, line: float) -> str:
    """Which side of the line the REAL outcome landed on. "push" (line
    exactly matched) is a real, if rare, possibility for whole-number lines
    like receptions -- must be handled explicitly, not silently folded into
    a win or loss."""
    if actual > line:
        return "over"
    if actual < line:
        return "under"
    return "push"


def classify_conviction(model_mean: float, line: float, model_std: float, high_conviction_z: float = 0.5) -> str:
    """"High conviction" means the model's mean deviates from the market
    line by at least `high_conviction_z` of the model's own std -- i.e. the
    model itself thinks this is a real, non-marginal disagreement with the
    market, not just noise. Uses the same std floor (0.65) as
    `evaluate_prop_edge` so the two functions can never disagree about how
    "confident" a given deviation is."""
    bounded_std = max(0.65, float(model_std))
    z = abs(float(model_mean) - float(line)) / bounded_std
    return "high" if z >= high_conviction_z else "low"


@dataclass(frozen=True)
class PropBetGrade:
    side: str  # "over" | "under" | "push_no_side"
    outcome: str  # "win" | "loss" | "push"
    conviction: str  # "high" | "low"
    edge: Optional[float]
    model_implied_prob: float
    market_implied_prob: Optional[float]


def _market_implied_prob(price: Optional[int]) -> Optional[float]:
    if price is None:
        return None
    price = int(price)
    if price < 0:
        return abs(price) / (abs(price) + 100.0)
    return 100.0 / (price + 100.0)


def grade_prop_bet(
    *,
    model_mean: float,
    model_std: float,
    line: float,
    actual: float,
    market_over_price: Optional[int] = None,
    market_under_price: Optional[int] = None,
    high_conviction_z: float = 0.5,
) -> PropBetGrade:
    """Grade betting the model-favored side of one real (player, stat,
    line) at the real closing price against the real outcome. This is the
    CLV-style comparison this project's game-level model already has
    (`data/ops/nfl-clv-benchmark-report.json`) and the player-prop side has
    never had -- deliberately distinct from MAE-vs-truth: a projection can
    be quite accurate on average yet still lose money if its mean rarely
    strays far enough from the market line to clear the vig, and vice
    versa."""
    side = model_favored_side(model_mean, line)
    conviction = classify_conviction(model_mean, line, model_std, high_conviction_z)
    actual_side = grade_actual_outcome(actual, line)

    if side == "push_no_side" or actual_side == "push":
        outcome = "push"
    elif actual_side == side:
        outcome = "win"
    else:
        outcome = "loss"

    edge_result = evaluate_prop_edge(
        model_mean=model_mean,
        model_std=model_std,
        line=line,
        market_over_price=market_over_price,
        market_under_price=market_under_price,
    )

    if side == "over":
        edge = edge_result["edge_over"]
        model_prob = edge_result["over_prob"]
        market_prob = _market_implied_prob(market_over_price)
    elif side == "under":
        edge = edge_result["edge_under"]
        model_prob = edge_result["under_prob"]
        market_prob = _market_implied_prob(market_under_price)
    else:
        edge = None
        model_prob = 0.5
        market_prob = None

    return PropBetGrade(
        side=side,
        outcome=outcome,
        conviction=conviction,
        edge=edge,
        model_implied_prob=model_prob,
        market_implied_prob=market_prob,
    )


def edge_call_correct(edge: Optional[float], outcome: str) -> Optional[bool]:
    """Was a genuine positive-edge call (the model believes it has an edge
    on the side it favored, vs. the market's own implied probability)
    directionally validated by the real outcome? Returns None (not
    "False") when there's nothing to validate -- no market price to derive
    an edge from, the bet pushed, or the model claimed no edge at all on
    this side -- so callers can cleanly exclude "not applicable" rows from
    a hit-rate calculation instead of accidentally counting them as
    misses."""
    if edge is None or outcome == "push":
        return None
    if edge <= 0:
        return None
    return outcome == "win"


def summarize_grades(grades: Sequence[PropBetGrade]) -> Dict[str, Any]:
    """Pure aggregation: win rate (overall + by conviction tier) and
    edge-call accuracy for a batch of already-computed grades. Pushes are
    excluded from win-rate denominators (a push is neither a win nor a
    loss for either side), matching standard sportsbook accounting."""

    def _win_rate(rows: List[PropBetGrade]) -> Optional[Dict[str, Any]]:
        decided = [g for g in rows if g.outcome in ("win", "loss")]
        if not decided:
            return None
        wins = sum(1 for g in decided if g.outcome == "win")
        return {"n": len(decided), "wins": wins, "win_rate": round(wins / len(decided), 4)}

    decided_all = [g for g in grades if g.outcome in ("win", "loss")]
    high = [g for g in decided_all if g.conviction == "high"]
    low = [g for g in decided_all if g.conviction == "low"]

    edge_checks = [edge_call_correct(g.edge, g.outcome) for g in grades]
    edge_checks = [c for c in edge_checks if c is not None]

    return {
        "n_total": len(grades),
        "n_pushes": sum(1 for g in grades if g.outcome == "push"),
        "overall": _win_rate(decided_all),
        "high_conviction": _win_rate(high),
        "low_conviction": _win_rate(low),
        "edge_call_accuracy": (
            {"n": len(edge_checks), "correct": sum(edge_checks), "accuracy": round(sum(edge_checks) / len(edge_checks), 4)}
            if edge_checks
            else None
        ),
    }
