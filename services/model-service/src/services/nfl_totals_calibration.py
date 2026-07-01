from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from sqlalchemy import text


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return float(default)
    try:
        return float(raw)
    except ValueError:
        return float(default)


def _fit_linear_calibration(
    points: List[Dict[str, Any]],
    *,
    min_sample_size: int,
    slope_min: float,
    slope_max: float,
    intercept_abs_max: float,
) -> Dict[str, Any]:
    valid_points = [
        point
        for point in points
        if _to_float(point.get("pred_total")) is not None and _to_float(point.get("actual_total")) is not None
    ]
    sample_size = len(valid_points)
    if sample_size < int(min_sample_size):
        return {
            "sample_size": sample_size,
            "slope": 1.0,
            "intercept": 0.0,
            "base_mae": None,
            "calibrated_mae": None,
            "mae_improvement": None,
            "eligible": False,
        }

    x_vals = [float(point["pred_total"]) for point in valid_points]
    y_vals = [float(point["actual_total"]) for point in valid_points]
    x_mean = sum(x_vals) / sample_size
    y_mean = sum(y_vals) / sample_size
    var_x = sum((x - x_mean) ** 2 for x in x_vals)
    cov_xy = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_vals, y_vals))
    slope = (cov_xy / var_x) if var_x > 1e-9 else 1.0
    slope = max(float(slope_min), min(float(slope_max), slope))
    intercept = y_mean - (slope * x_mean)
    intercept = max(-float(intercept_abs_max), min(float(intercept_abs_max), intercept))

    calibrated = [(slope * x) + intercept for x in x_vals]
    base_mae = sum(abs(x - y) for x, y in zip(x_vals, y_vals)) / sample_size
    calibrated_mae = sum(abs(c - y) for c, y in zip(calibrated, y_vals)) / sample_size
    return {
        "sample_size": sample_size,
        "slope": round(slope, 6),
        "intercept": round(intercept, 6),
        "base_mae": round(base_mae, 4),
        "calibrated_mae": round(calibrated_mae, 4),
        "mae_improvement": round(base_mae - calibrated_mae, 4),
        "eligible": True,
    }


def apply_totals_calibration(total_mean: Optional[float], calibration: Dict[str, Any]) -> Optional[float]:
    value = _to_float(total_mean)
    if value is None:
        return None
    slope = _to_float(calibration.get("slope"))
    intercept = _to_float(calibration.get("intercept"))
    if slope is None or intercept is None:
        return value
    floor = _env_float("NFL_TOTALS_CALIBRATION_MIN_TOTAL", 24.0)
    ceiling = _env_float("NFL_TOTALS_CALIBRATION_MAX_TOTAL", 66.0)
    calibrated = (float(slope) * value) + float(intercept)
    return max(floor, min(ceiling, calibrated))


def fetch_nfl_totals_calibration(
    session: Any,
    *,
    model_version: str,
    lookback_days: int,
) -> Dict[str, Any]:
    rows = session.execute(
        text(
            """
            SELECT
              mo.game_id,
              lp.total_mean AS pred_total,
              mo.final_total_points AS actual_total,
              EXISTS (
                SELECT 1
                FROM nfl_market_history_snapshots mhs
                WHERE mhs.game_id = mo.game_id
                  AND mhs.market_code = 'total'
                  AND mhs.total_points IS NOT NULL
              ) AS has_total_market_snapshot
            FROM nfl_market_outcomes mo
            JOIN games g ON g.id = mo.game_id
            JOIN LATERAL (
              SELECT
                mp.total_mean,
                mp.created_at
              FROM nfl_market_projections mp
              WHERE mp.game_id = mo.game_id
                AND mp.model_version = :model_version
                AND mp.created_at < GREATEST(
                  COALESCE(mo.completed_at, '-infinity'::timestamptz),
                  COALESCE(
                    g.start_time + INTERVAL '6 hours',
                    ((g.game_date::date + INTERVAL '1 day')::timestamptz)
                  )
                )
              ORDER BY mp.created_at DESC
              LIMIT 1
            ) lp ON TRUE
            WHERE g.game_date >= CURRENT_DATE - make_interval(days => :lookback_days)
            """
        ),
        {"model_version": model_version, "lookback_days": int(lookback_days)},
    ).fetchall()
    points = [dict(row._mapping) for row in rows]

    slope_min = _env_float("NFL_TOTALS_CALIBRATION_SLOPE_MIN", 0.8)
    slope_max = _env_float("NFL_TOTALS_CALIBRATION_SLOPE_MAX", 1.2)
    intercept_abs_max = _env_float("NFL_TOTALS_CALIBRATION_INTERCEPT_ABS_MAX", 8.0)
    min_sample_size = max(20, int(_env_float("NFL_TOTALS_CALIBRATION_MIN_SAMPLE", 80.0)))
    fit = _fit_linear_calibration(
        points,
        min_sample_size=min_sample_size,
        slope_min=min(slope_min, slope_max),
        slope_max=max(slope_min, slope_max),
        intercept_abs_max=intercept_abs_max,
    )

    total_snapshot_games = sum(1 for point in points if bool(point.get("has_total_market_snapshot")))
    snapshot_coverage = (total_snapshot_games / len(points)) if points else 0.0
    substrate_label = "historical-total-snapshots" if snapshot_coverage >= 0.5 else "normalized-total-proxy"
    return {
        **fit,
        "source": "nfl_totals_linear_calibration",
        "lookback_days": int(lookback_days),
        "market_substrate": {
            "label": substrate_label,
            "total_snapshot_coverage": round(snapshot_coverage, 4),
            "games_with_total_snapshots": total_snapshot_games,
            "games_considered": len(points),
        },
    }
