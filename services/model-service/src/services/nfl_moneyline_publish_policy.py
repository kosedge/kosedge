"""Moneyline publish policy — derived from the same margin / win-prob model.

ML PLAY requires:
  1) spread already clears selective PLAY (spread_play_v2_cap7), and
  2) vig-aware ML EV vs offered American odds clears a stricter bar.

Never trains a disconnected ML classifier. Props remain out of scope.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

# Stricter than spread: require clear price edge after juice.
ML_MIN_EV = 0.02  # +2% EV on a 1-unit stake
POLICY_VERSION = "ml_from_spread_play_v1"


def american_to_decimal(american: float) -> float:
    a = float(american)
    if a == 0:
        return 1.0
    if a > 0:
        return 1.0 + (a / 100.0)
    return 1.0 + (100.0 / abs(a))


def american_to_implied_prob(american: float) -> float:
    a = float(american)
    if a == 0:
        return 0.5
    if a > 0:
        return 100.0 / (a + 100.0)
    return abs(a) / (abs(a) + 100.0)


def ev_per_unit(*, model_win_prob: float, american_odds: float) -> float:
    """Expected value of a 1-unit bet at American odds given model win probability."""
    p = max(0.0, min(1.0, float(model_win_prob)))
    dec = american_to_decimal(american_odds)
    profit_if_win = dec - 1.0
    return p * profit_if_win - (1.0 - p)


def publish_moneyline_tag(
    *,
    spread_tag: str,
    spread_stake_eligible: bool,
    model_win_prob: Optional[float],
    offered_american: Optional[float],
    product_gate_status: str = "YELLOW",
    min_ev: float = ML_MIN_EV,
) -> Dict[str, Any]:
    """Return ML tag. PASS unless spread PLAY + EV bar clear."""
    status = (product_gate_status or "YELLOW").upper()
    if status == "RED":
        return {
            "tag": "PASS",
            "stake_eligible": False,
            "reason": "product_gate_red",
            "policy_version": POLICY_VERSION,
        }
    if not spread_stake_eligible or str(spread_tag).upper() != "PLAY":
        return {
            "tag": "PASS",
            "stake_eligible": False,
            "reason": "spread_not_play",
            "policy_version": POLICY_VERSION,
        }
    if model_win_prob is None or offered_american is None:
        return {
            "tag": "PASS",
            "stake_eligible": False,
            "reason": "missing_ml_inputs",
            "policy_version": POLICY_VERSION,
        }
    ev = ev_per_unit(model_win_prob=model_win_prob, american_odds=offered_american)
    if ev < float(min_ev):
        return {
            "tag": "PASS",
            "stake_eligible": False,
            "reason": "ml_ev_below_bar",
            "ev": round(ev, 4),
            "min_ev": min_ev,
            "implied_prob": round(american_to_implied_prob(offered_american), 4),
            "policy_version": POLICY_VERSION,
        }
    return {
        "tag": "PLAY",
        "stake_eligible": True,
        "reason": "spread_play_and_ml_ev_cleared",
        "ev": round(ev, 4),
        "min_ev": min_ev,
        "implied_prob": round(american_to_implied_prob(offered_american), 4),
        "policy_version": POLICY_VERSION,
    }
