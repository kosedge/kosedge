"""MLB player-prop edge policy — research-only until holdout clears.

Honesty rule (non-negotiable): PLAY tags are never stake-eligible until a
pre-registered unused holdout proves positive ROI. Enterprise default keeps
PLAY_STAKE_ELIGIBLE=false regardless of local edge size.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

# Until a pre-registered MLB props holdout clears, never imply paid +EV cards.
PLAY_STAKE_ELIGIBLE = False

PLAY_ABS_EDGE = 0.055
WATCH_ABS_EDGE = 0.030


def evaluate_mlb_prop_edge(
    *,
    model_prob: float,
    market_implied_prob: Optional[float],
    market_key: str = "",
) -> Dict[str, Any]:
    """Return PLAY/WATCH/PASS tag with stake eligibility forced off."""
    if market_implied_prob is None:
        return {
            "tag": "PASS",
            "edge": None,
            "stake_eligible": False,
            "tag_reason": "missing_market",
            "market_key": market_key,
            "play_stake_eligible_policy": PLAY_STAKE_ELIGIBLE,
        }

    edge = float(model_prob) - float(market_implied_prob)
    abs_edge = abs(edge)
    if abs_edge >= PLAY_ABS_EDGE:
        tag = "PLAY"
        reason = "research_play_threshold"
    elif abs_edge >= WATCH_ABS_EDGE:
        tag = "WATCH"
        reason = "research_watch_threshold"
    else:
        tag = "PASS"
        reason = "below_watch_threshold"

    return {
        "tag": tag,
        "edge": round(edge, 5),
        "abs_edge": round(abs_edge, 5),
        "stake_eligible": False if tag == "PLAY" else False,
        "tag_reason": reason if tag != "PLAY" else "research_only_no_holdout",
        "market_key": market_key,
        "play_stake_eligible_policy": PLAY_STAKE_ELIGIBLE,
    }
