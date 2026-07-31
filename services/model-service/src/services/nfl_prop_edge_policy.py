"""Enterprise prop edge policy: de-vig mids + sparse research tags.

Holdout chain (no refit on confirmation batches):
  - Batch-4 (offset=2): locked yards PLAY FAILED (50.8% / −4.2%, n=128)
  - Batch-5 (offset=3): provisional rec |z|≥0.60 did NOT confirm
    (43.5% / −18.8%, n=23) — thin but directionally negative

Until a rule clears a pre-registered holdout, PLAY tags are research-only
(stake_eligible=False). Board must not imply a paid +EV bet card.

Policy:
  - PLAY  — research highlight (rec_yds |z|≥0.60); NOT stake-eligible
  - WATCH — informational mid-band
  - PASS  — default

Never invents edges without a joined book.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Optional, Tuple


# Research highlight markets (not stake-confirmed after batch-5).
PLAY_MARKETS = frozenset({"rec_yds"})
WATCH_MARKETS = frozenset({"pass_yds", "rush_yds", "rec_yds", "receptions"})
# Confirmation failed — keep False until a future pre-registered holdout passes.
PLAY_STAKE_ELIGIBLE = False

PLAY_ABS_Z = 0.60
PLAY_ABS_EDGE = 0.045
WATCH_ABS_Z = 0.35
WATCH_ABS_EDGE = 0.030

# Extreme z historically anti-correlated with wins — refuse stake tags.
SIZE_DOWN_ABS_Z = 1.15

MAX_ABS_MEAN_GAP = {
    "pass_yds": 45.0,
    "rush_yds": 18.0,
    "rec_yds": 18.0,
    "receptions": 2.2,
    "anytime_td": 0.30,
}

# After props materializer applies depth / usage-rank floors, role_confidence
# is on the starter-probability scale (WR1 ≈ 0.88). Raw involvement scores
# (~0.20) must be floored before reaching this gate — see
# effective_skill_role_confidence(). Still allow None (unknown) through.
MIN_ROLE_CONFIDENCE_PLAY = 0.50
MIN_AVAILABILITY_CONFIDENCE_PLAY = 0.50

# Refuse Under tags when the *raw* (pre-shrink) mean implies role collapse
# vs the book. Live 2025 W17: featured WR1s raw ≈ line − 14 yd; PLAY Unders
# were the residual just inside MAX_ABS_MEAN_GAP — model failure, not edge.
ROLE_COLLAPSE_RAW_FRAC = 0.55
ROLE_COLLAPSE_MIN_LINE = {
    "pass_yds": 180.0,
    "rush_yds": 25.0,
    "rec_yds": 25.0,
    "receptions": 3.5,
}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def american_to_implied_prob(price: Optional[int]) -> Optional[float]:
    if price is None:
        return None
    try:
        american = float(price)
    except (TypeError, ValueError):
        return None
    if american == 0:
        return None
    if american < 0:
        return abs(american) / (abs(american) + 100.0)
    return 100.0 / (american + 100.0)


def fair_price_from_prob(prob: float) -> int:
    p = _clamp(float(prob), 0.001, 0.999)
    if p >= 0.5:
        return int(round(-(100.0 * p) / (1.0 - p)))
    return int(round((100.0 * (1.0 - p)) / p))


def _normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def devig_two_way(
    over_price: Optional[int],
    under_price: Optional[int],
) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """Multiplicative vig removal → (fair_over, fair_under, vig_pct)."""
    over_raw = american_to_implied_prob(over_price)
    under_raw = american_to_implied_prob(under_price)
    if over_raw is None or under_raw is None:
        return over_raw, under_raw, None
    total = over_raw + under_raw
    if total <= 1e-9:
        return over_raw, under_raw, None
    fair_over = over_raw / total
    fair_under = under_raw / total
    vig = max(0.0, total - 1.0)
    return fair_over, fair_under, round(vig, 4)


def anytime_td_prob_from_td_mean(total_tds_mean: float) -> float:
    """Poisson P(X >= 1) from expected total TDs."""
    mu = max(0.0, float(total_tds_mean))
    return _clamp(1.0 - math.exp(-mu), 0.01, 0.95)


def evaluate_prop_edge(
    *,
    model_mean: float,
    model_std: float,
    line: float,
    market_over_price: Optional[int],
    market_under_price: Optional[int],
    market_key: str = "",
    position: str = "",
    role_confidence: Optional[float] = None,
    availability_confidence: Optional[float] = None,
    raw_model_mean: Optional[float] = None,
) -> Dict[str, Any]:
    """Model CDF vs de-vigged market mid, plus PLAY/WATCH/PASS tag."""
    bounded_std = max(0.65, float(model_std))
    z_over = (float(model_mean) - float(line)) / bounded_std
    over_prob = _clamp(_normal_cdf(z_over), 0.01, 0.99)
    under_prob = _clamp(1.0 - over_prob, 0.01, 0.99)

    market_over_raw = american_to_implied_prob(market_over_price)
    market_under_raw = american_to_implied_prob(market_under_price)
    fair_mkt_over, fair_mkt_under, vig = devig_two_way(market_over_price, market_under_price)

    market_over_ref = fair_mkt_over if fair_mkt_over is not None else market_over_raw
    market_under_ref = fair_mkt_under if fair_mkt_under is not None else market_under_raw

    edge_over = (over_prob - market_over_ref) if market_over_ref is not None else None
    edge_under = (under_prob - market_under_ref) if market_under_ref is not None else None

    both_sides = market_over_ref is not None and market_under_ref is not None
    confidence = _clamp((abs(z_over) / 2.6) + (0.30 if both_sides else 0.0), 0.05, 0.99)

    tag_payload = classify_prop_tag(
        market_key=market_key,
        position=position,
        z_over=z_over,
        edge_over=edge_over,
        edge_under=edge_under,
        market_joined=both_sides or market_over_ref is not None or market_under_ref is not None,
        model_mean=float(model_mean),
        line=float(line),
        role_confidence=role_confidence,
        availability_confidence=availability_confidence,
        raw_model_mean=raw_model_mean,
    )

    return {
        "over_prob": round(over_prob, 4),
        "under_prob": round(under_prob, 4),
        "fair_over_price": fair_price_from_prob(over_prob),
        "fair_under_price": fair_price_from_prob(under_prob),
        "edge_over": round(edge_over, 4) if edge_over is not None else None,
        "edge_under": round(edge_under, 4) if edge_under is not None else None,
        "confidence": round(confidence, 4),
        "z_over": round(z_over, 4),
        "market_vig": vig,
        "market_over_fair": round(fair_mkt_over, 4) if fair_mkt_over is not None else None,
        "market_under_fair": round(fair_mkt_under, 4) if fair_mkt_under is not None else None,
        **tag_payload,
    }


def _favored_side(
    edge_over: Optional[float],
    edge_under: Optional[float],
) -> Tuple[Optional[str], float]:
    side: Optional[str] = None
    edge_mag = 0.0
    if edge_over is not None and edge_under is not None:
        if edge_over >= edge_under and edge_over > 0:
            side, edge_mag = "Over", float(edge_over)
        elif edge_under > edge_over and edge_under > 0:
            side, edge_mag = "Under", float(edge_under)
    elif edge_over is not None and edge_over > 0:
        side, edge_mag = "Over", float(edge_over)
    elif edge_under is not None and edge_under > 0:
        side, edge_mag = "Under", float(edge_under)
    return side, edge_mag


def _role_collapse_under(
    *,
    market_key: str,
    line: Optional[float],
    raw_model_mean: Optional[float],
    side: Optional[str],
) -> bool:
    """True when Under favor is driven by a collapsed raw projection vs book."""
    if side != "Under" or line is None or raw_model_mean is None:
        return False
    min_line = ROLE_COLLAPSE_MIN_LINE.get(str(market_key or ""))
    if min_line is None:
        return False
    line_f = float(line)
    raw_f = float(raw_model_mean)
    if line_f < float(min_line) or line_f <= 0.0:
        return False
    return raw_f < (ROLE_COLLAPSE_RAW_FRAC * line_f)


def classify_prop_tag(
    *,
    market_key: str,
    position: str,
    z_over: float,
    edge_over: Optional[float],
    edge_under: Optional[float],
    market_joined: bool,
    model_mean: Optional[float] = None,
    line: Optional[float] = None,
    role_confidence: Optional[float] = None,
    availability_confidence: Optional[float] = None,
    raw_model_mean: Optional[float] = None,
) -> Dict[str, Any]:
    """Selective staking tags grounded in calibrated Vegas cuts."""
    if not market_joined:
        return {
            "tag": "PASS",
            "tag_side": None,
            "tag_action": None,
            "size_down": False,
            "stake_eligible": False,
            "tag_reason": "no_market",
        }

    mk = str(market_key or "")

    if model_mean is not None and line is not None:
        gap = abs(float(model_mean) - float(line))
        max_gap = MAX_ABS_MEAN_GAP.get(mk)
        if max_gap is not None and gap > max_gap:
            return {
                "tag": "PASS",
                "tag_side": None,
                "tag_action": None,
                "size_down": False,
                "stake_eligible": False,
                "tag_reason": "model_market_disagreement",
            }

    abs_z = abs(float(z_over))
    side, edge_mag = _favored_side(edge_over, edge_under)

    if side is None or edge_mag < WATCH_ABS_EDGE or abs_z < WATCH_ABS_Z:
        return {
            "tag": "PASS",
            "tag_side": None,
            "tag_action": None,
            "size_down": False,
            "stake_eligible": False,
            "tag_reason": "below_watch_floor",
        }

    if _role_collapse_under(
        market_key=mk,
        line=line,
        raw_model_mean=raw_model_mean,
        side=side,
    ):
        return {
            "tag": "PASS",
            "tag_side": None,
            "tag_action": None,
            "size_down": False,
            "stake_eligible": False,
            "tag_reason": "model_role_collapse",
        }

    size_down = abs_z >= SIZE_DOWN_ABS_Z
    if size_down:
        return {
            "tag": "WATCH",
            "tag_side": side,
            "tag_action": side,
            "size_down": True,
            "stake_eligible": False,
            "tag_reason": "extreme_z_watch_only",
        }

    role_ok = role_confidence is None or float(role_confidence) >= MIN_ROLE_CONFIDENCE_PLAY
    avail_ok = (
        availability_confidence is None
        or float(availability_confidence) >= MIN_AVAILABILITY_CONFIDENCE_PLAY
    )

    if (
        mk in PLAY_MARKETS
        and abs_z >= PLAY_ABS_Z
        and edge_mag >= PLAY_ABS_EDGE
        and role_ok
        and avail_ok
    ):
        return {
            "tag": "PLAY",
            "tag_side": side,
            "tag_action": side,
            "size_down": False,
            "stake_eligible": bool(PLAY_STAKE_ELIGIBLE),
            "tag_reason": "rec_yds_research_unconfirmed",
        }

    if mk in WATCH_MARKETS:
        reason = "watch_band"
        if mk == "rush_yds" and abs_z >= 0.50 and edge_mag >= 0.040:
            reason = "rush_watch_only_holdout"
        elif mk == "pass_yds" and abs_z >= 0.50 and edge_mag >= 0.040:
            reason = "pass_watch_only_holdout"
        elif mk == "rec_yds" and abs_z >= 0.50 and edge_mag >= 0.040:
            reason = "rec_watch_below_play_z"
        elif not role_ok:
            reason = "watch_low_role_confidence"
        elif not avail_ok:
            reason = "watch_low_availability"
        return {
            "tag": "WATCH",
            "tag_side": side,
            "tag_action": side,
            "size_down": False,
            "stake_eligible": False,
            "tag_reason": reason,
        }

    return {
        "tag": "PASS",
        "tag_side": None,
        "tag_action": None,
        "size_down": False,
        "stake_eligible": False,
        "tag_reason": "below_play_floor",
    }
