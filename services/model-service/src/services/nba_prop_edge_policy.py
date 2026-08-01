"""NBA prop edge policy — research-only until holdout clears.

Never invents edges without a joined book line. PLAY is not stake-eligible.
Role-collapse Under refusal ports the NFL props lesson (low means ≠ edge).
"""

from __future__ import annotations

import math
from typing import Any, Dict, Optional, Tuple

from src.services.nba_player_prop_projection import NBA_PROP_MARKETS

PLAY_STAKE_ELIGIBLE = False
POLICY_VERSION = "nba_props_phase3_research_v1"

PLAY_ABS_Z = 0.55
PLAY_ABS_EDGE = 0.040
WATCH_ABS_Z = 0.30
WATCH_ABS_EDGE = 0.025
SIZE_DOWN_ABS_Z = 1.25

MAX_ABS_MEAN_GAP = {
    "pts": 12.0,
    "reb": 5.0,
    "ast": 4.0,
    "threes": 2.0,
}

ROLE_COLLAPSE_RAW_FRAC = 0.55
ROLE_COLLAPSE_MIN_LINE = {
    "pts": 14.0,
    "reb": 5.5,
    "ast": 4.5,
    "threes": 1.5,
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
    over_raw = american_to_implied_prob(over_price)
    under_raw = american_to_implied_prob(under_price)
    if over_raw is None or under_raw is None:
        return over_raw, under_raw, None
    total = over_raw + under_raw
    if total <= 1e-9:
        return over_raw, under_raw, None
    return over_raw / total, under_raw / total, round(max(0.0, total - 1.0), 4)


def _role_collapse_under(
    *,
    market_key: str,
    model_mean: float,
    line: float,
) -> bool:
    min_line = ROLE_COLLAPSE_MIN_LINE.get(market_key)
    if min_line is None or line < min_line:
        return False
    return model_mean < (ROLE_COLLAPSE_RAW_FRAC * line)


def evaluate_nba_prop_edge(
    *,
    market_key: str,
    model_mean: float,
    model_std: float,
    line: Optional[float],
    over_price: Optional[int] = None,
    under_price: Optional[int] = None,
    sample_games: int = 0,
    projection_source: str = "stub_rates",
) -> Dict[str, Any]:
    """Return probs, edges, and research tag. stake_eligible always False."""
    mk = str(market_key or "").strip().lower()
    if mk not in NBA_PROP_MARKETS:
        return {
            "tag": "PASS",
            "reason": "unsupported_market",
            "stake_eligible": False,
            "policy_version": POLICY_VERSION,
        }

    mean = float(model_mean)
    std = max(0.35, float(model_std))
    if line is None:
        return {
            "tag": "PASS",
            "reason": "no_market_line",
            "stake_eligible": False,
            "policy_version": POLICY_VERSION,
            "model_mean": mean,
            "model_std": std,
            "over_prob": None,
            "under_prob": None,
            "edge_over": None,
            "edge_under": None,
            "market_joined": False,
        }

    line_f = float(line)
    z = (mean - line_f) / std
    # P(X > line) under normal; continuity soft-handle for threes
    over_prob = 1.0 - _normal_cdf((line_f + 0.5 - mean) / std) if mk == "threes" else 1.0 - _normal_cdf(
        (line_f - mean) / std
    )
    over_prob = _clamp(over_prob, 0.02, 0.98)
    under_prob = 1.0 - over_prob

    fair_over_mkt, fair_under_mkt, vig = devig_two_way(over_price, under_price)
    if fair_over_mkt is not None and fair_under_mkt is not None:
        edge_over = over_prob - fair_over_mkt
        edge_under = under_prob - fair_under_mkt
    else:
        edge_over = over_prob - 0.5
        edge_under = under_prob - 0.5

    abs_gap = abs(mean - line_f)
    max_gap = MAX_ABS_MEAN_GAP.get(mk, 8.0)
    collapse = _role_collapse_under(market_key=mk, model_mean=mean, line=line_f)

    tag = "PASS"
    reason = "below_band"
    side = None
    if collapse:
        tag = "PASS"
        reason = "model_role_collapse"
    elif abs_gap > max_gap:
        tag = "PASS"
        reason = "mean_gap_too_large"
    elif sample_games < 3:
        tag = "PASS"
        reason = "thin_sample"
    elif abs(z) >= SIZE_DOWN_ABS_Z:
        tag = "PASS"
        reason = "extreme_z_size_down"
    else:
        prefer_over = edge_over >= edge_under
        best_edge = edge_over if prefer_over else edge_under
        best_z = z if prefer_over else -z
        if best_z >= PLAY_ABS_Z and best_edge >= PLAY_ABS_EDGE:
            tag = "PLAY"
            side = "OVER" if prefer_over else "UNDER"
            reason = "research_highlight"
        elif best_z >= WATCH_ABS_Z and best_edge >= WATCH_ABS_EDGE:
            tag = "WATCH"
            side = "OVER" if prefer_over else "UNDER"
            reason = "watch_band"

    return {
        "tag": tag,
        "tag_side": side,
        "reason": reason,
        "stake_eligible": False,
        "policy_version": POLICY_VERSION,
        "market_joined": True,
        "model_mean": round(mean, 3),
        "model_std": round(std, 3),
        "line": line_f,
        "z": round(z, 3),
        "over_prob": round(over_prob, 4),
        "under_prob": round(under_prob, 4),
        "fair_over_price": fair_price_from_prob(over_prob),
        "fair_under_price": fair_price_from_prob(under_prob),
        "market_over_price": over_price,
        "market_under_price": under_price,
        "edge_over": round(edge_over, 4),
        "edge_under": round(edge_under, 4),
        "vig_pct": vig,
        "projection_source": projection_source,
        "sample_games": sample_games,
    }


def ou_balance_report(rows: list) -> Dict[str, Any]:
    """Board-level Over/Under PLAY balance diagnostic."""
    play = [r for r in rows if str((r.get("diagnostics") or {}).get("tag") or r.get("tag") or "") == "PLAY"]
    over_n = sum(1 for r in play if str((r.get("diagnostics") or {}).get("tag_side") or r.get("tag_side") or "") == "OVER")
    under_n = sum(1 for r in play if str((r.get("diagnostics") or {}).get("tag_side") or r.get("tag_side") or "") == "UNDER")
    total = over_n + under_n
    under_pct = (under_n / total) if total else None
    return {
        "play_n": total,
        "play_over": over_n,
        "play_under": under_n,
        "play_under_pct": None if under_pct is None else round(under_pct, 3),
        "balanced": under_pct is None or (0.25 <= under_pct <= 0.75),
    }
