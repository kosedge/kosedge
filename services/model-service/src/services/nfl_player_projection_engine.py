from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _normal_cdf(x: float) -> float:
    # Deterministic normal CDF approximation via erf.
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def fair_price_from_prob(prob: float) -> int:
    p = _clamp(prob, 0.001, 0.999)
    if p >= 0.5:
        return int(round(-(100.0 * p) / (1.0 - p)))
    return int(round((100.0 * (1.0 - p)) / p))


@dataclass(frozen=True)
class PlayerFeatureInputs:
    position: str
    snap_proxy: float
    route_proxy: float
    target_proxy: float
    rush_share: float
    red_zone_share: float
    qb_dropback_factor: float
    qb_pressure_factor: float
    team_pace_factor: float
    team_pass_rate_factor: float
    availability_confidence: float
    role_confidence: float


def baseline_projection_from_features(inputs: PlayerFeatureInputs) -> Dict[str, Any]:
    position = (inputs.position or "").upper()
    volume_signal = _clamp(
        (0.32 * inputs.snap_proxy)
        + (0.28 * inputs.route_proxy)
        + (0.22 * inputs.target_proxy)
        + (0.18 * inputs.rush_share),
        0.01,
        0.98,
    )
    role_factor = _clamp(0.55 + (0.45 * inputs.role_confidence), 0.35, 1.0)
    availability_factor = _clamp(0.45 + (0.55 * inputs.availability_confidence), 0.35, 1.0)
    pace_factor = _clamp(inputs.team_pace_factor, 0.78, 1.22)
    pass_factor = _clamp(inputs.team_pass_rate_factor, 0.78, 1.22)

    attempts_mean = 0.0
    carries_mean = 0.0
    targets_mean = 0.0
    pass_yards_mean = 0.0
    rush_yards_mean = 0.0
    receiving_yards_mean = 0.0
    receptions_mean = 0.0
    pass_tds_mean = 0.0
    rush_tds_mean = 0.0
    rec_tds_mean = 0.0

    if position == "QB":
        attempts_mean = 20.0 + (25.0 * volume_signal * pass_factor * pace_factor)
        completion_rate = _clamp(0.60 + (0.05 * inputs.target_proxy) - (0.03 * inputs.qb_pressure_factor), 0.50, 0.74)
        yards_per_attempt = _clamp(6.2 + (1.1 * inputs.target_proxy) - (0.6 * inputs.qb_pressure_factor), 5.0, 9.2)
        pass_yards_mean = attempts_mean * yards_per_attempt
        carries_mean = _clamp(1.2 + (4.0 * inputs.rush_share), 0.0, 10.0)
        rush_yards_mean = carries_mean * _clamp(4.6 - (0.7 * inputs.qb_pressure_factor), 2.6, 6.2)
        pass_tds_mean = _clamp((pass_yards_mean / 115.0) * (0.72 + (0.32 * inputs.red_zone_share)), 0.15, 3.8)
        rush_tds_mean = _clamp(carries_mean * inputs.red_zone_share * 0.12, 0.0, 1.2)
        receptions_mean = 0.0
        receiving_yards_mean = 0.0
    elif position in {"RB", "FB"}:
        carries_mean = _clamp(2.0 + (20.0 * inputs.rush_share * pace_factor), 0.0, 29.0)
        targets_mean = _clamp(0.8 + (7.0 * inputs.target_proxy * pass_factor), 0.0, 13.0)
        rush_yards_mean = carries_mean * _clamp(3.7 + (0.9 * volume_signal), 2.6, 6.3)
        receptions_mean = targets_mean * _clamp(0.62 + (0.16 * inputs.route_proxy), 0.40, 0.92)
        receiving_yards_mean = receptions_mean * _clamp(6.0 + (2.8 * inputs.target_proxy), 4.2, 13.5)
        rush_tds_mean = _clamp(carries_mean * inputs.red_zone_share * 0.16, 0.0, 1.7)
        rec_tds_mean = _clamp(receptions_mean * inputs.red_zone_share * 0.08, 0.0, 1.2)
    else:
        targets_mean = _clamp(1.2 + (11.5 * inputs.target_proxy * pass_factor), 0.0, 17.5)
        receptions_mean = targets_mean * _clamp(0.56 + (0.28 * inputs.route_proxy), 0.38, 0.93)
        receiving_yards_mean = receptions_mean * _clamp(8.4 + (4.2 * volume_signal), 5.5, 20.0)
        carries_mean = _clamp(2.0 * inputs.rush_share, 0.0, 4.0)
        rush_yards_mean = carries_mean * _clamp(5.0 + (0.8 * volume_signal), 3.0, 8.0)
        rec_tds_mean = _clamp(receptions_mean * inputs.red_zone_share * 0.14, 0.0, 1.7)
        rush_tds_mean = _clamp(carries_mean * inputs.red_zone_share * 0.08, 0.0, 0.7)

    # Availability and role confidence reduce all outcomes in a deterministic, bounded manner.
    confidence_scale = _clamp((0.65 * availability_factor) + (0.35 * role_factor), 0.30, 1.0)
    pass_yards_mean *= confidence_scale
    rush_yards_mean *= confidence_scale
    receiving_yards_mean *= confidence_scale
    receptions_mean *= confidence_scale
    carries_mean *= confidence_scale
    attempts_mean *= confidence_scale
    pass_tds_mean *= confidence_scale
    rush_tds_mean *= confidence_scale
    rec_tds_mean *= confidence_scale

    pass_yards_std = max(3.0, pass_yards_mean * 0.22)
    rush_yards_std = max(2.2, rush_yards_mean * 0.31)
    receiving_yards_std = max(2.2, receiving_yards_mean * 0.33)
    receptions_std = max(0.4, receptions_mean * 0.29)
    attempts_std = max(0.8, attempts_mean * 0.18)
    carries_std = max(0.6, carries_mean * 0.24)
    targets_std = max(0.5, targets_mean * 0.26)

    anytime_td_prob = _clamp(1.0 - math.exp(-(rush_tds_mean + rec_tds_mean)), 0.005, 0.92)
    total_td_mean = pass_tds_mean + rush_tds_mean + rec_tds_mean
    outcome_floor = {
        "pass_yards": max(0.0, pass_yards_mean - (1.05 * pass_yards_std)),
        "rush_yards": max(0.0, rush_yards_mean - (0.95 * rush_yards_std)),
        "receiving_yards": max(0.0, receiving_yards_mean - (0.95 * receiving_yards_std)),
        "receptions": max(0.0, receptions_mean - (0.9 * receptions_std)),
        "touchdowns": max(0.0, total_td_mean * 0.35),
    }
    outcome_median = {
        "pass_yards": pass_yards_mean,
        "rush_yards": rush_yards_mean,
        "receiving_yards": receiving_yards_mean,
        "receptions": receptions_mean,
        "touchdowns": total_td_mean,
    }
    outcome_ceiling = {
        "pass_yards": pass_yards_mean + (1.15 * pass_yards_std),
        "rush_yards": rush_yards_mean + (1.15 * rush_yards_std),
        "receiving_yards": receiving_yards_mean + (1.25 * receiving_yards_std),
        "receptions": receptions_mean + (1.2 * receptions_std),
        "touchdowns": min(4.0, total_td_mean * 1.9 + 0.25),
    }
    return {
        "attempts_mean": round(attempts_mean, 3),
        "attempts_std": round(attempts_std, 3),
        "carries_mean": round(carries_mean, 3),
        "carries_std": round(carries_std, 3),
        "targets_mean": round(targets_mean, 3),
        "targets_std": round(targets_std, 3),
        "completions_mean": round(receptions_mean if position == "QB" else 0.0, 3),
        "pass_yards_mean": round(pass_yards_mean, 3),
        "pass_yards_std": round(pass_yards_std, 3),
        "rush_yards_mean": round(rush_yards_mean, 3),
        "rush_yards_std": round(rush_yards_std, 3),
        "receiving_yards_mean": round(receiving_yards_mean, 3),
        "receiving_yards_std": round(receiving_yards_std, 3),
        "receptions_mean": round(receptions_mean, 3),
        "receptions_std": round(receptions_std, 3),
        "pass_tds_mean": round(pass_tds_mean, 3),
        "rush_tds_mean": round(rush_tds_mean, 3),
        "rec_tds_mean": round(rec_tds_mean, 3),
        "anytime_td_prob": round(anytime_td_prob, 4),
        "floor_outcome": outcome_floor,
        "median_outcome": outcome_median,
        "ceiling_outcome": outcome_ceiling,
        "uncertainty": {
            "confidence_scale": round(confidence_scale, 4),
            "volume_signal": round(volume_signal, 4),
            "availability_factor": round(availability_factor, 4),
            "role_factor": round(role_factor, 4),
        },
    }


def evaluate_prop_edge(*, model_mean: float, model_std: float, line: float, market_over_price: int | None, market_under_price: int | None) -> Dict[str, Any]:
    bounded_std = max(0.65, float(model_std))
    z_over = (float(model_mean) - float(line)) / bounded_std
    over_prob = _clamp(_normal_cdf(z_over), 0.01, 0.99)
    under_prob = _clamp(1.0 - over_prob, 0.01, 0.99)

    market_over_prob = None
    market_under_prob = None
    if market_over_price is not None:
        market_over_prob = (abs(market_over_price) / (abs(market_over_price) + 100.0)) if market_over_price < 0 else (100.0 / (market_over_price + 100.0))
    if market_under_price is not None:
        market_under_prob = (abs(market_under_price) / (abs(market_under_price) + 100.0)) if market_under_price < 0 else (100.0 / (market_under_price + 100.0))

    edge_over = over_prob - market_over_prob if market_over_prob is not None else None
    edge_under = under_prob - market_under_prob if market_under_prob is not None else None
    confidence = _clamp((abs(z_over) / 2.6) + (0.30 if market_over_prob is not None and market_under_prob is not None else 0.0), 0.05, 0.99)
    return {
        "over_prob": round(over_prob, 4),
        "under_prob": round(under_prob, 4),
        "fair_over_price": fair_price_from_prob(over_prob),
        "fair_under_price": fair_price_from_prob(under_prob),
        "edge_over": round(edge_over, 4) if edge_over is not None else None,
        "edge_under": round(edge_under, 4) if edge_under is not None else None,
        "confidence": round(confidence, 4),
    }


def fantasy_points_from_projection(*, scoring_profile: str, pass_yards: float, pass_tds: float, rush_yards: float, rush_tds: float, receiving_yards: float, receptions: float, rec_tds: float) -> float:
    profile = scoring_profile.strip().lower()
    ppr_bonus = 0.0
    if profile == "half_ppr":
        ppr_bonus = 0.5
    elif profile == "ppr":
        ppr_bonus = 1.0
    return round(
        (pass_yards / 25.0)
        + (pass_tds * 4.0)
        + (rush_yards / 10.0)
        + (rush_tds * 6.0)
        + (receiving_yards / 10.0)
        + (receptions * ppr_bonus)
        + (rec_tds * 6.0),
        4,
    )
