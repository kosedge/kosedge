"""Bounded lineup / SP confidence shocks for nowcast / enterprise repricing.

When confirmed lineup quality jumps (or collapses) relative to the prior
projection stamp — or when the probable pitcher changes — nudge offense /
allowed factors inside safe clamps so moneyline / run-line / totals move
coherently without overfitting one news hit.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Dict, Optional

from .mlb_pa_feature_sharpen import compute_sp_change_shock
from .mlb_simulator import MlbGameInputs


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def normalize_pitcher_key(name: Optional[str]) -> str:
    return " ".join(str(name or "").lower().split())


def resolve_nowcast_starters(
    *,
    context_home: Optional[str],
    context_away: Optional[str],
    live_home: Optional[str] = None,
    live_away: Optional[str] = None,
    allow_clear: bool = False,
) -> Dict[str, Any]:
    """Merge context + live feed pitchers; flag SP identity changes.

    When allow_clear=True (late confirmed cards), a missing live probable clears
    the prior SP instead of COALESCE-keeping a scratched name.
    """
    prior_home = context_home
    prior_away = context_away
    if live_home:
        new_home = live_home
    elif allow_clear:
        new_home = None
    else:
        new_home = context_home
    if live_away:
        new_away = live_away
    elif allow_clear:
        new_away = None
    else:
        new_away = context_away
    home_changed = normalize_pitcher_key(prior_home) != normalize_pitcher_key(new_home)
    away_changed = normalize_pitcher_key(prior_away) != normalize_pitcher_key(new_away)
    return {
        "prior_home": prior_home,
        "prior_away": prior_away,
        "new_home": new_home,
        "new_away": new_away,
        "home_changed": home_changed,
        "away_changed": away_changed,
        "any_changed": home_changed or away_changed,
        "allow_clear": bool(allow_clear),
    }


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
    prior_starter_home: Optional[str] = None,
    prior_starter_away: Optional[str] = None,
    prior_starter_quality_home: float = 1.0,
    prior_starter_quality_away: float = 1.0,
    max_abs_shock: float = 0.08,
) -> tuple[MlbGameInputs, Dict[str, Any]]:
    """Apply lineup confidence + SP-change shocks; return (inputs, diag)."""
    prior_h = float(prior_confidence_home if prior_confidence_home is not None else inputs.lineup_confidence_home)
    prior_a = float(prior_confidence_away if prior_confidence_away is not None else inputs.lineup_confidence_away)
    shock = compute_lineup_shock(
        prior_confidence_home=prior_h,
        prior_confidence_away=prior_a,
        new_confidence_home=float(inputs.lineup_confidence_home),
        new_confidence_away=float(inputs.lineup_confidence_away),
        max_abs_shock=max_abs_shock,
    )
    sp_home = compute_sp_change_shock(
        prior_starter=prior_starter_home,
        new_starter=inputs.starter_home,
        prior_quality=prior_starter_quality_home,
        new_quality=float(inputs.starter_quality_home),
    )
    sp_away = compute_sp_change_shock(
        prior_starter=prior_starter_away,
        new_starter=inputs.starter_away,
        prior_quality=prior_starter_quality_away,
        new_quality=float(inputs.starter_quality_away),
    )
    # SP change on the home side affects away offense (facing that pitcher) via starter_quality.
    # We also nudge the changed pitcher's quality toward the new identity already on inputs,
    # and apply a tiny opposing-offense mul when SP flips.
    home_offense_mul = shock["home_offense_mul"] * (
        1.0 + _clamp((sp_away["allowed_mul"] - 1.0) * 0.65, -0.05, 0.05)
    )
    away_offense_mul = shock["away_offense_mul"] * (
        1.0 + _clamp((sp_home["allowed_mul"] - 1.0) * 0.65, -0.05, 0.05)
    )
    updated = replace(
        inputs,
        offense_home=_clamp(float(inputs.offense_home) * home_offense_mul, 0.78, 1.25),
        offense_away=_clamp(float(inputs.offense_away) * away_offense_mul, 0.78, 1.25),
        lineup_strength_index_home=_clamp(
            float(inputs.lineup_strength_index_home) * home_offense_mul,
            0.78,
            1.25,
        ),
        lineup_strength_index_away=_clamp(
            float(inputs.lineup_strength_index_away) * away_offense_mul,
            0.78,
            1.25,
        ),
        # Missing → named SP firmness bump; named → missing firmness cut.
        starter_firmness_home=_clamp(
            float(inputs.starter_firmness_home)
            + (0.10 if sp_home["changed"] and inputs.starter_home else 0.0)
            - (0.18 if sp_home["changed"] and not inputs.starter_home else 0.0),
            0.35,
            1.0,
        ),
        starter_firmness_away=_clamp(
            float(inputs.starter_firmness_away)
            + (0.10 if sp_away["changed"] and inputs.starter_away else 0.0)
            - (0.18 if sp_away["changed"] and not inputs.starter_away else 0.0),
            0.35,
            1.0,
        ),
    )
    return updated, {
        "lineup_shock": shock,
        "sp_change_shock": {
            "home": sp_home,
            "away": sp_away,
            "home_offense_mul": home_offense_mul,
            "away_offense_mul": away_offense_mul,
        },
    }
