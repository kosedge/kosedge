"""Bounded MLB probability / totals calibration (walk-forward safe).

The shared NFL-era total clamp (24–66) previously destroyed MLB MAE at larger
n. This module keeps MLB calibrators inside baseball-native ranges.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

MLB_TOTAL_MIN = 5.0
MLB_TOTAL_MAX = 14.5
MLB_SLOPE_MIN = 0.75
MLB_SLOPE_MAX = 1.25
MLB_INTERCEPT_MIN = -3.5
MLB_INTERCEPT_MAX = 3.5
MLB_MIN_FIT_SAMPLE = 20


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def build_prob_calibrator(
    training_points: Sequence[Mapping[str, Any]],
    *,
    bins: int = 12,
    prior_strength: float = 8.0,
) -> Dict[str, Any]:
    bucket_count = max(4, min(20, int(bins)))
    buckets: List[List[Mapping[str, Any]]] = [[] for _ in range(bucket_count)]
    for point in training_points:
        prob = _clamp(float(point["fg_home_win_prob"]), 0.0, 1.0)
        idx = min(bucket_count - 1, int(prob * bucket_count))
        buckets[idx].append(point)
    mapping: List[float] = []
    prior = 0.5
    for bucket in buckets:
        if not bucket:
            mapping.append(prior)
            continue
        wins = sum(1.0 if x["home_team_won"] else 0.0 for x in bucket)
        calibrated = (wins + prior_strength * prior) / (len(bucket) + prior_strength)
        mapping.append(_clamp(calibrated, 0.01, 0.99))
    return {
        "bins": bucket_count,
        "mapping": mapping,
        "training_sample_size": len(training_points),
        "sport": "mlb",
    }


def apply_prob_calibrator(prob: float, calibrator: Mapping[str, Any]) -> float:
    p = _clamp(float(prob), 0.0, 1.0)
    bins = int(calibrator.get("bins") or 1)
    mapping = calibrator.get("mapping") or []
    if bins <= 0 or not isinstance(mapping, list) or not mapping:
        return p
    idx = min(bins - 1, int(p * bins))
    try:
        out = float(mapping[idx])
    except (TypeError, ValueError, IndexError):
        return p
    return _clamp(out, 0.01, 0.99)


def fit_total_calibrator(
    training_points: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    pairs: List[Tuple[float, float]] = []
    for point in training_points:
        pred = _to_float(point.get("fg_total_mean"))
        actual = _to_float(point.get("final_total_runs"))
        if pred is None or actual is None:
            continue
        pairs.append((float(pred), float(actual)))
    if len(pairs) < MLB_MIN_FIT_SAMPLE:
        return {
            "slope": 1.0,
            "intercept": 0.0,
            "eligible": False,
            "sample_size": len(pairs),
            "sport": "mlb",
        }

    x_vals = [pred for pred, _actual in pairs]
    y_vals = [actual for _pred, actual in pairs]
    x_mean = sum(x_vals) / len(pairs)
    y_mean = sum(y_vals) / len(pairs)
    var_x = sum((x - x_mean) ** 2 for x in x_vals)
    cov_xy = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_vals, y_vals))
    slope = cov_xy / var_x if var_x > 1e-9 else 1.0
    slope = _clamp(slope, MLB_SLOPE_MIN, MLB_SLOPE_MAX)
    intercept = y_mean - (slope * x_mean)
    intercept = _clamp(intercept, MLB_INTERCEPT_MIN, MLB_INTERCEPT_MAX)
    return {
        "slope": float(slope),
        "intercept": float(intercept),
        "eligible": True,
        "sample_size": len(pairs),
        "sport": "mlb",
        "pred_mean": round(x_mean, 4),
        "actual_mean": round(y_mean, 4),
    }


def apply_total_calibrator(total: float, calibrator: Mapping[str, Any]) -> float:
    if not calibrator or not calibrator.get("eligible", True):
        return _clamp(float(total), MLB_TOTAL_MIN, MLB_TOTAL_MAX)
    slope = float(calibrator.get("slope") or 1.0)
    intercept = float(calibrator.get("intercept") or 0.0)
    adjusted = (slope * float(total)) + intercept
    return _clamp(adjusted, MLB_TOTAL_MIN, MLB_TOTAL_MAX)


def summarize_calibration(points: Sequence[Mapping[str, Any]]) -> Dict[str, Optional[float]]:
    if not points:
        return {
            "sample_size": 0.0,
            "brier_ml": None,
            "mae_total_runs": None,
            "calendar_days_covered": 0.0,
            "last_game_date": None,
        }
    probs = [float(x["fg_home_win_prob"]) for x in points]
    actual = [1.0 if x["home_team_won"] else 0.0 for x in points]
    totals_pred = [float(x["fg_total_mean"]) for x in points]
    totals_actual = [float(x["final_total_runs"]) for x in points]
    brier = sum((p - a) ** 2 for p, a in zip(probs, actual)) / len(points)
    mae_total = sum(abs(p - a) for p, a in zip(totals_pred, totals_actual)) / len(points)
    game_dates = sorted({str(x["game_date"]) for x in points if x.get("game_date") is not None})
    return {
        "sample_size": float(len(points)),
        "brier_ml": round(brier, 6),
        "mae_total_runs": round(mae_total, 4),
        "calendar_days_covered": float(len(game_dates)),
        "last_game_date": (game_dates[-1] if game_dates else None),
    }
