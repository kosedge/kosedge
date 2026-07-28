"""Market-residual prop edge model (enterprise research path).

Flat z/edge PLAY tags failed confirm holdouts. The durable +EV path is to
model residuals of (model_fair − market_close) against graded outcomes with
nested unused holdouts — not to re-tag PLAY from contaminated batches.

This module provides:
- Residual feature extraction from graded prop records
- A simple ridge-style residual corrector (frozen coefficients)
- Evaluation helpers for pre-registered holdout windows

Stake promotion remains gated by `PLAY_STAKE_ELIGIBLE` in the edge policy;
this module never flips that flag.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence


RESIDUAL_MODEL_VERSION = "prop-market-residual-v1"

# Frozen mild correctors fit conceptually as: adjusted_edge = edge + β·(fair−line)
# Tuned conservatively; production refreshes via fit_residual_corrector().
FROZEN_RESIDUAL_BETA: Dict[str, float] = {
    "pass_yds": 0.08,
    "rush_yds": 0.10,
    "rec_yds": 0.12,
    "receptions": 0.06,
    "anytime_td": 0.0,
}


@dataclass(frozen=True)
class ResidualCorrector:
    market_key: str
    beta: float
    sample_size: int
    source: str
    version: str = RESIDUAL_MODEL_VERSION


def frozen_residual_corrector(market_key: str) -> ResidualCorrector:
    mk = str(market_key or "")
    return ResidualCorrector(
        market_key=mk,
        beta=float(FROZEN_RESIDUAL_BETA.get(mk, 0.0)),
        sample_size=0,
        source="frozen",
    )


def fit_residual_corrector(
    points: Sequence[Mapping[str, Any]],
    *,
    market_key: str,
    min_sample_size: int = 120,
) -> ResidualCorrector:
    """Fit β in residual_actual ≈ β · (model_mean − market_line) via OLS."""
    xs: List[float] = []
    ys: List[float] = []
    for p in points:
        try:
            model_mean = float(p["model_mean"])
            market_line = float(p["market_line"])
            actual = float(p["actual"])
        except (KeyError, TypeError, ValueError):
            continue
        xs.append(model_mean - market_line)
        ys.append(actual - market_line)
    n = len(xs)
    if n < min_sample_size:
        return ResidualCorrector(
            market_key=market_key,
            beta=float(FROZEN_RESIDUAL_BETA.get(market_key, 0.0)),
            sample_size=n,
            source="frozen_fallback",
        )
    # Ridge toward 0 with λ=25 to avoid overfit on noisy props.
    xx = sum(x * x for x in xs) + 25.0
    xy = sum(x * y for x, y in zip(xs, ys))
    beta = max(-0.35, min(0.35, xy / xx if xx else 0.0))
    return ResidualCorrector(
        market_key=market_key,
        beta=float(beta),
        sample_size=n,
        source="fit",
    )


def apply_residual_correction(
    *,
    model_mean: float,
    market_line: float,
    corrector: ResidualCorrector,
) -> float:
    """Return adjusted model mean pulled toward residual-implied fair."""
    gap = float(model_mean) - float(market_line)
    return float(model_mean) + (float(corrector.beta) * gap)


def residual_holdout_metrics(
    points: Sequence[Mapping[str, Any]],
    *,
    corrector: ResidualCorrector,
    side_key: str = "side",
) -> Dict[str, Any]:
    """Grade ATS-style: bet model side of residual-adjusted fair vs close."""
    wins = 0
    losses = 0
    pushes = 0
    for p in points:
        try:
            model_mean = float(p["model_mean"])
            market_line = float(p["market_line"])
            actual = float(p["actual"])
        except (KeyError, TypeError, ValueError):
            continue
        adj = apply_residual_correction(
            model_mean=model_mean, market_line=market_line, corrector=corrector
        )
        # Bet Over if adjusted fair > line, else Under.
        side = "over" if adj > market_line else "under"
        if abs(actual - market_line) < 1e-9:
            pushes += 1
            continue
        hit = (actual > market_line) if side == "over" else (actual < market_line)
        if hit:
            wins += 1
        else:
            losses += 1
    decided = wins + losses
    hit_rate = (wins / decided) if decided else None
    return {
        "market_key": corrector.market_key,
        "version": corrector.version,
        "n": decided + pushes,
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "hit_rate": hit_rate,
        "beta": corrector.beta,
        "source": corrector.source,
        "promote_ready": bool(decided >= 80 and hit_rate is not None and hit_rate >= 0.54),
    }
