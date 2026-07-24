"""Bounded lineup confidence shocks for nowcast / enterprise repricing.

When confirmed lineup quality jumps (or collapses) relative to the prior
projection stamp, nudge offense indices inside safe clamps so moneyline /
run-line / totals move coherently without overfitting one news hit.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Dict, Optional

from .mlb_simulator import MlbGameInputs


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def compute_lineup_shock(
    *,
    prior_confidence_home: float,
    prior_confidence_away: float,
    new_confidence_home: float,
    new_confidence_away: float,
    max_abs_shock: float = 0.08,
) -> Dict[str, float]:
    """Return offense multipliers from confidence deltas."""
    home_delta = float(new_confidence_home) - float(prior_confidence_home)
    away_delta = float(new_confidence_away) - float(prior_confidence_away)
    home_shock = _clamp(home_delta * 0.35, -max_abs_shock, max_abs_shock)
    away_shock = _clamp(away_delta * 0.35, -max_abs_shock, max_abs_shock)
    return {
        "home_offense_mul": 1.0 + home_shock,
        "away_offense_mul": 1.0 + away_shock,
        "home_confidence_delta": home_delta,
        "away_confidence_delta": away_delta,
        "max_abs_shock": max_abs_shock,
    }


def apply_lineup_shock(
    inputs: MlbGameInputs,
    *,
    prior_confidence_home: Optional[float] = None,
    prior_confidence_away: Optional[float] = None,
    max_abs_shock: float = 0.08,
) -> tuple[MlbGameInputs, Dict[str, Any]]:
    """Apply shock to lineup strength / offense indices; return (inputs, diag)."""
    prior_h = float(prior_confidence_home if prior_confidence_home is not None else inputs.lineup_confidence_home)
    prior_a = float(prior_confidence_away if prior_confidence_away is not None else inputs.lineup_confidence_away)
    shock = compute_lineup_shock(
        prior_confidence_home=prior_h,
        prior_confidence_away=prior_a,
        new_confidence_home=float(inputs.lineup_confidence_home),
        new_confidence_away=float(inputs.lineup_confidence_away),
        max_abs_shock=max_abs_shock,
    )
    updated = replace(
        inputs,
        offense_home=_clamp(float(inputs.offense_home) * shock["home_offense_mul"], 0.78, 1.25),
        offense_away=_clamp(float(inputs.offense_away) * shock["away_offense_mul"], 0.78, 1.25),
        lineup_strength_index_home=_clamp(
            float(inputs.lineup_strength_index_home) * shock["home_offense_mul"],
            0.78,
            1.25,
        ),
        lineup_strength_index_away=_clamp(
            float(inputs.lineup_strength_index_away) * shock["away_offense_mul"],
            0.78,
            1.25,
        ),
    )
    return updated, {"lineup_shock": shock}
