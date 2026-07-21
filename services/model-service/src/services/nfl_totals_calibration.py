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
    """Fit affine calibrator actual ≈ slope * pred + intercept.

    Critical: after clamping slope, recompute intercept from training means so the
    calibrator remains mean-preserving. Clamping intercept independently (old
    behavior) could push calibrated means *down* when the model was already low
    (e.g. slope=0.8, intercept capped at +8 → 0.8*42+8=41.6).
    """
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
            "signed_bias_pre": None,
            "signed_bias_post": None,
            "eligible": False,
            "mean_preserved": True,
        }

    x_vals = [float(point["pred_total"]) for point in valid_points]
    y_vals = [float(point["actual_total"]) for point in valid_points]
    half_life_days = max(30.0, _env_float("NFL_TOTALS_CALIBRATION_HALF_LIFE_DAYS", 180.0))
    weights: List[float] = []
    for point in valid_points:
        explicit = _to_float(point.get("weight"))
        if explicit is not None and explicit > 0:
            weights.append(float(explicit))
            continue
        days_ago = _to_float(point.get("days_ago"))
        if days_ago is None:
            weights.append(1.0)
        else:
            weights.append(0.5 ** (max(0.0, float(days_ago)) / half_life_days))
    weight_sum = sum(weights) or float(sample_size)
    x_mean = sum(w * x for w, x in zip(weights, x_vals)) / weight_sum
    y_mean = sum(w * y for w, y in zip(weights, y_vals)) / weight_sum
    var_x = sum(w * (x - x_mean) ** 2 for w, x in zip(weights, x_vals))
    cov_xy = sum(w * (x - x_mean) * (y - y_mean) for w, x, y in zip(weights, x_vals, y_vals))
    raw_slope = (cov_xy / var_x) if var_x > 1e-9 else 1.0
    affine_slope = max(float(slope_min), min(float(slope_max), float(raw_slope)))
    affine_intercept = y_mean - (affine_slope * x_mean)
    intercept_clamped = False
    if abs(affine_intercept) > float(intercept_abs_max):
        affine_intercept = max(-float(intercept_abs_max), min(float(intercept_abs_max), affine_intercept))
        intercept_clamped = True
    affine_cal = [(affine_slope * x) + affine_intercept for x in x_vals]
    recenter = 0.0
    affine_mean = sum(w * c for w, c in zip(weights, affine_cal)) / weight_sum
    if intercept_clamped and abs(affine_mean - y_mean) > 0.05:
        recenter = y_mean - affine_mean
        affine_cal = [c + recenter for c in affine_cal]
        affine_intercept = affine_intercept + recenter

    # Pure level-shift candidate: dominant NFL totals failure mode is mean bias,
    # not slope. Prefer this when MAE is within epsilon of affine (more stable).
    #
    # When the generative prior was raised (e.g. 43.5 → 45.3), historical
    # pred_totals still embed the old prior. Subtract that prior delta from the
    # level intercept so we do not double-count the lift on newly simulated games.
    prior_now = _env_float("NFL_FRAMEWORK_PRIOR_TOTAL_POINTS", 45.3)
    # After 2023–2025 re-sim under the raised prior, reference matches live prior
    # so prior_delta=0 and transition shrink no longer fires.
    prior_ref = _env_float("NFL_TOTALS_CALIBRATION_PRIOR_REFERENCE", 45.3)
    prior_delta = float(prior_now) - float(prior_ref)
    level_slope = 1.0
    level_intercept = (y_mean - x_mean) - prior_delta
    if abs(level_intercept) > float(intercept_abs_max):
        level_intercept = max(-float(intercept_abs_max), min(float(intercept_abs_max), level_intercept))
    level_cal = [x + level_intercept for x in x_vals]

    def _mae(preds: List[float]) -> float:
        return sum(abs(p - y) for p, y in zip(preds, y_vals)) / sample_size

    affine_mae = _mae(affine_cal)
    level_mae = _mae(level_cal)
    raw_mean_bias = abs(y_mean - x_mean)
    # Prefer level-shift when the error is clearly a mean bias (typical O/U miss),
    # even if prior-delta adjustment slightly worsens in-sample historical MAE.
    # Also prefer level when affine slope is clamped to the bound — a raw slope of
    # 4.0 clamped to 1.25 + large negative intercept is unstable on live boards.
    slope_at_bound = (
        abs(float(affine_slope) - float(slope_min)) < 1e-9
        or abs(float(affine_slope) - float(slope_max)) < 1e-9
    )
    prefer_level = (
        level_mae <= (affine_mae + 0.05)
        or raw_mean_bias >= 1.5
        or slope_at_bound
    )
    if prefer_level:
        slope, intercept, calibrated, mode = level_slope, level_intercept, level_cal, "level_shift"
        calibrated_mae = level_mae
    else:
        slope, intercept, calibrated, mode = affine_slope, affine_intercept, affine_cal, "affine"
        calibrated_mae = affine_mae

    base_mae = sum(abs(x - y) for x, y in zip(x_vals, y_vals)) / sample_size
    signed_bias_pre = sum(x - y for x, y in zip(x_vals, y_vals)) / sample_size
    signed_bias_post = sum(c - y for c, y in zip(calibrated, y_vals)) / sample_size
    return {
        "sample_size": sample_size,
        "slope": round(slope, 6),
        "intercept": round(intercept, 6),
        "raw_slope": round(float(raw_slope), 6),
        "fit_mode": mode,
        "slope_clamped": bool(slope_at_bound),
        "pred_mean": round(x_mean, 4),
        "actual_mean": round(y_mean, 4),
        "base_mae": round(base_mae, 4),
        "calibrated_mae": round(calibrated_mae, 4),
        "mae_improvement": round(base_mae - calibrated_mae, 4),
        "signed_bias_pre": round(signed_bias_pre, 4),
        "signed_bias_post": round(signed_bias_post, 4),
        "eligible": True,
        "mean_preserved": abs(signed_bias_post) <= max(0.15, abs(signed_bias_pre) * 0.25 + 0.05),
        "intercept_clamped": bool(intercept_clamped),
        "recenter_applied": round(recenter, 4),
        "affine_mae": round(affine_mae, 4),
        "level_shift_mae": round(level_mae, 4),
        "half_life_days": round(half_life_days, 1),
        "prior_now": round(prior_now, 4),
        "prior_reference": round(prior_ref, 4),
        "prior_delta_removed": round(prior_delta, 4),
    }


def resolve_totals_level_shift_shrink(calibration: Dict[str, Any]) -> float:
    """Shrink final level correction during prior-transition windows.

    After raising the generative prior (e.g. 43.5 → 45.3), historical fits still
    carry a residual intercept even after prior_delta removal. Applying that
    intercept at full strength on newly simulated boards double-counts the lift
    and floods Overs. Shrink until PRIOR_REFERENCE catches up via re-simmed history.
    """
    explicit = os.getenv("NFL_TOTALS_LEVEL_SHIFT_SHRINK")
    if explicit is not None:
        try:
            return max(0.0, min(1.0, float(explicit)))
        except ValueError:
            pass
    prior_delta = _to_float(calibration.get("prior_delta_removed")) or 0.0
    if prior_delta > 0.05:
        return max(
            0.0,
            min(1.0, _env_float("NFL_TOTALS_LEVEL_SHIFT_SHRINK_DEFAULT_WITH_PRIOR_DELTA", 0.50)),
        )
    return 1.0


def resolve_effective_totals_intercept(
    calibration: Dict[str, Any],
    *,
    slate_pre_mean: Optional[float] = None,
) -> Dict[str, Any]:
    """Resolve the intercept actually applied on a live slate.

    When slate_pre_mean is provided, subtract generative lift already present in
    the new prior/sim stack relative to (train_pred_mean + prior_delta). For a
    level-shift fit this yields intercept_eff ≈ actual_mean - slate_pre_mean,
    i.e. only close the remaining gap — never re-apply a stale historical lift.
    """
    intercept = _to_float(calibration.get("intercept"))
    if intercept is None:
        return {
            "intercept_fit": None,
            "intercept_effective": None,
            "generative_extra": None,
            "shrink": 1.0,
            "slate_pre_mean": slate_pre_mean,
        }
    pred_mean = _to_float(calibration.get("pred_mean"))
    prior_delta = _to_float(calibration.get("prior_delta_removed")) or 0.0
    generative_extra = 0.0
    intercept_eff = float(intercept)
    fit_mode = str(calibration.get("fit_mode") or "")
    if (
        fit_mode == "level_shift"
        and slate_pre_mean is not None
        and pred_mean is not None
    ):
        expected_after_prior = float(pred_mean) + float(prior_delta)
        generative_extra = float(slate_pre_mean) - expected_after_prior
        if intercept_eff >= 0.0:
            intercept_eff = max(0.0, intercept_eff - max(0.0, generative_extra))
        else:
            intercept_eff = min(0.0, intercept_eff - min(0.0, generative_extra))
    shrink = resolve_totals_level_shift_shrink(calibration)
    intercept_eff *= shrink
    return {
        "intercept_fit": round(float(intercept), 6),
        "intercept_effective": round(float(intercept_eff), 6),
        "generative_extra": round(float(generative_extra), 4),
        "shrink": round(float(shrink), 4),
        "slate_pre_mean": round(float(slate_pre_mean), 4) if slate_pre_mean is not None else None,
    }


def apply_totals_calibration(
    total_mean: Optional[float],
    calibration: Dict[str, Any],
    *,
    slate_pre_mean: Optional[float] = None,
    return_meta: bool = False,
) -> Any:
    value = _to_float(total_mean)
    if value is None:
        return (None, {"applied": False, "reason": "missing_total"}) if return_meta else None
    if not bool(calibration.get("eligible", True)):
        meta = {"applied": False, "reason": "ineligible", "pre_calibration_total": value}
        return (value, meta) if return_meta else value
    slope = _to_float(calibration.get("slope"))
    intercept = _to_float(calibration.get("intercept"))
    if slope is None or intercept is None:
        meta = {"applied": False, "reason": "missing_fit", "pre_calibration_total": value}
        return (value, meta) if return_meta else value
    sample_size = int(calibration.get("sample_size") or 0)
    min_sample = max(20, int(_env_float("NFL_TOTALS_CALIBRATION_MIN_SAMPLE", 80.0)))
    if sample_size and sample_size < min_sample:
        meta = {"applied": False, "reason": "insufficient_sample", "pre_calibration_total": value}
        return (value, meta) if return_meta else value
    floor = _env_float("NFL_TOTALS_CALIBRATION_MIN_TOTAL", 24.0)
    ceiling = _env_float("NFL_TOTALS_CALIBRATION_MAX_TOTAL", 66.0)

    intercept_meta = resolve_effective_totals_intercept(
        calibration, slate_pre_mean=slate_pre_mean
    )
    intercept_eff = intercept_meta.get("intercept_effective")
    if intercept_eff is None:
        intercept_eff = float(intercept)
    fit_mode = str(calibration.get("fit_mode") or "")
    shrink = float(intercept_meta.get("shrink") or 1.0)
    if fit_mode == "level_shift":
        raw = float(value) + float(intercept_eff)
    else:
        # Shrink the affine correction toward identity so prior transitions
        # cannot yank the board by a stale intercept.
        raw_full = (float(slope) * float(value)) + float(intercept)
        raw = float(value) + shrink * (raw_full - float(value))
    calibrated = max(floor, min(ceiling, raw))
    meta = {
        "applied": abs(float(calibrated) - float(value)) > 1e-9,
        "pre_calibration_total": round(float(value), 4),
        "calibrated_total": round(float(calibrated), 4),
        "delta": round(float(calibrated) - float(value), 4),
        "fit_mode": fit_mode or None,
        "slope": float(slope),
        **intercept_meta,
    }
    return (calibrated, meta) if return_meta else calibrated


def fetch_nfl_totals_calibration(
    session: Any,
    *,
    model_version: str,
    lookback_days: int,
) -> Dict[str, Any]:
    """Fit totals calibrator on pre-calibration predictions when available.

    Prefers audit.pre_calibration_total (post-supervised, pre-final-cal), then
    diagnostics base_total (MC+market-blend), then stored total_mean.
    """
    rows = session.execute(
        text(
            """
            SELECT
              mo.game_id,
              COALESCE(
                NULLIF(lp.projection->'audit'->>'pre_calibration_total', '')::double precision,
                NULLIF(
                  lp.projection->'diagnostics'->'totals_calibration'->>'base_total',
                  ''
                )::double precision,
                lp.total_mean
              ) AS pred_total,
              mo.final_total_points AS actual_total,
              GREATEST(0, (CURRENT_DATE - g.game_date::date))::double precision AS days_ago,
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
                mp.projection,
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

    slope_min = _env_float("NFL_TOTALS_CALIBRATION_SLOPE_MIN", 0.85)
    slope_max = _env_float("NFL_TOTALS_CALIBRATION_SLOPE_MAX", 1.25)
    # Wide enough that mean-preserving intercept for ~3pt level bias is not destroyed.
    intercept_abs_max = _env_float("NFL_TOTALS_CALIBRATION_INTERCEPT_ABS_MAX", 18.0)
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
