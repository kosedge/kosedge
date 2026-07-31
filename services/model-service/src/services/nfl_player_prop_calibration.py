"""Walk-forward / frozen calibration for NFL player-prop means and stds.

Vegas regrades (208 games / 3815 props) showed:
  - Blended means slightly undershoot truth (pass −2.7, rush −4.1, rec −2.1)
  - Pass stds are too tight (empirical residual ≈ 1.29× model std; 68% cov ~60%)
  - Rush means sit below closing lines while truth runs higher → fake Unders

This module applies a market-aware, mean-preserving level shift plus std
inflation before edge tagging. Coefficients default to the frozen enterprise
fit from that sample; production can refresh via DB walk-forward points.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence


CALIBRATION_VERSION = "prop-enterprise-cal-v1"

# Frozen fit on blended (60% MC / 40% baseline) means vs actuals,
# seasons 2023–2025 weeks 4–17, n≈3815 graded props (batch1+2+3).
# intercept = mean(actual − pred) so calibrated = pred + intercept.
FROZEN_MEAN_INTERCEPT: Dict[str, float] = {
    # Enterprise retune (2026-07): densified W16-17 board still showed pass
    # bias ~+5.5 vs close after volume fixes; deepen the mean pull-down and
    # keep rush/rec near truth-fit levels. Gate: pass PLAY stays research-only
    # until densified MAE ≤ 12.
    "pass_yds": -8.5,
    "rush_yds": 3.6,
    "rec_yds": 1.6,
    "receptions": 0.12,
    "anytime_td": 0.0,
}

# Inflate std so ~68% of actuals land within ±1σ of the calibrated mean.
FROZEN_STD_MULTIPLIER: Dict[str, float] = {
    "pass_yds": 1.29,
    "rush_yds": 1.10,
    "rec_yds": 1.05,
    "receptions": 1.15,
    "anytime_td": 1.0,
}

# Mild market shrink for solid roles keeps means playable vs books without
# inventing edges (pulls inflated YPA/volume toward the close). Stronger
# shrink when role confidence is weak (backup / uncertain involvement).
# IMPORTANT: callers must pass *effective* role_confidence (depth / usage-rank
# floors applied). The raw features-table involvement score has p50 ≈ 0.20 and
# must not be compared to LOW_ROLE_CONFIDENCE=0.55 or every prop looks weak.
# Stake PLAY tags remain gated separately and stay research-only until
# a pre-registered holdout confirms.
MARKET_SHRINK_BASE = 0.12
MARKET_SHRINK_LOW_ROLE = 0.30
LOW_ROLE_CONFIDENCE = 0.55
PASS_MARKET_SHRINK_BASE = 0.32
PASS_MARKET_SHRINK_MAX = 0.68

INTERCEPT_ABS_MAX: Dict[str, float] = {
    "pass_yds": 12.0,
    "rush_yds": 8.0,
    "rec_yds": 6.0,
    "receptions": 0.8,
    "anytime_td": 0.08,
}


@dataclass(frozen=True)
class PropMarketCalibration:
    market_key: str
    intercept: float
    std_multiplier: float
    sample_size: int
    source: str  # "frozen" | "walk_forward" | "identity"
    version: str = CALIBRATION_VERSION

    @property
    def eligible(self) -> bool:
        return self.source != "identity" and self.sample_size > 0


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def frozen_calibration_for(market_key: str) -> PropMarketCalibration:
    mk = str(market_key or "")
    return PropMarketCalibration(
        market_key=mk,
        intercept=float(FROZEN_MEAN_INTERCEPT.get(mk, 0.0)),
        std_multiplier=float(FROZEN_STD_MULTIPLIER.get(mk, 1.0)),
        sample_size=3815,
        source="frozen",
    )


def fit_prop_calibration_from_points(
    points: Sequence[Mapping[str, Any]],
    *,
    market_key: str,
    min_sample_size: int = 80,
) -> PropMarketCalibration:
    """Fit level-shift intercept + std multiplier from {pred, actual} points."""
    valid = []
    for p in points:
        try:
            pred = float(p["pred"])
            actual = float(p["actual"])
        except (KeyError, TypeError, ValueError):
            continue
        std = p.get("std")
        try:
            std_f = float(std) if std is not None else None
        except (TypeError, ValueError):
            std_f = None
        valid.append((pred, actual, std_f))

    n = len(valid)
    if n < int(min_sample_size):
        return PropMarketCalibration(
            market_key=market_key,
            intercept=0.0,
            std_multiplier=1.0,
            sample_size=n,
            source="identity",
        )

    residuals = [actual - pred for pred, actual, _ in valid]
    intercept = sum(residuals) / n
    abs_max = float(INTERCEPT_ABS_MAX.get(market_key, 8.0))
    intercept = _clamp(intercept, -abs_max, abs_max)

    emp_var = sum(r * r for r in residuals) / n
    emp_std = math.sqrt(max(emp_var, 1e-6))
    model_stds = [s for _, _, s in valid if s is not None and s > 0]
    if model_stds:
        mean_model_std = sum(model_stds) / len(model_stds)
        std_mult = _clamp(emp_std / max(mean_model_std, 0.65), 0.85, 2.5)
    else:
        std_mult = 1.0

    return PropMarketCalibration(
        market_key=market_key,
        intercept=round(intercept, 4),
        std_multiplier=round(std_mult, 4),
        sample_size=n,
        source="walk_forward",
    )


def apply_prop_calibration(
    *,
    model_mean: float,
    model_std: float,
    market_key: str,
    calibration: Optional[PropMarketCalibration] = None,
    market_line: Optional[float] = None,
    role_confidence: Optional[float] = None,
) -> Dict[str, Any]:
    """Truth level-shift + std inflate + optional mild market shrink."""
    cal = calibration or frozen_calibration_for(market_key)
    mean = float(model_mean) + float(cal.intercept)
    std = max(0.65, float(model_std) * float(cal.std_multiplier))

    shrink = 0.0
    if market_line is not None and math.isfinite(float(market_line)):
        role = float(role_confidence) if role_confidence is not None else 0.7
        if market_key == "pass_yds":
            shrink = MARKET_SHRINK_LOW_ROLE if role < LOW_ROLE_CONFIDENCE else PASS_MARKET_SHRINK_BASE
            shrink_cap = PASS_MARKET_SHRINK_MAX
        else:
            shrink = MARKET_SHRINK_LOW_ROLE if role < LOW_ROLE_CONFIDENCE else MARKET_SHRINK_BASE
            shrink_cap = 0.45
        # Large model-vs-close disagreements get a stronger pull toward the book
        # so the board stays playable without inventing a stake edge.
        gap = abs(mean - float(market_line))
        yard_markets = market_key in {"pass_yds", "rush_yds", "rec_yds"}
        if yard_markets and gap > 25.0:
            shrink = max(shrink, _clamp(0.14 + (gap - 25.0) / 70.0, 0.14, shrink_cap))
        shrink = _clamp(shrink, 0.0, shrink_cap)
        mean = ((1.0 - shrink) * mean) + (shrink * float(market_line))

    return {
        "model_mean": round(mean, 4),
        "model_std": round(std, 4),
        "calibration_version": cal.version,
        "calibration_source": cal.source,
        "calibration_intercept": cal.intercept,
        "calibration_std_multiplier": cal.std_multiplier,
        "calibration_sample_size": cal.sample_size,
        "market_shrink": round(shrink, 4),
    }


def default_calibration_bundle() -> Dict[str, PropMarketCalibration]:
    keys = ("pass_yds", "rush_yds", "rec_yds", "receptions", "anytime_td")
    return {k: frozen_calibration_for(k) for k in keys}


def load_walk_forward_prop_calibration(
    session: Any,
    *,
    season: int,
    week: int,
    lookback_seasons: Sequence[int] = (2023, 2024, 2025),
    min_sample_size: int = 80,
) -> Dict[str, PropMarketCalibration]:
    """Fit per-market calibrators from completed weeks before (season, week).

    Joins box-score / baseline means to real usage outcomes. Falls back to
    frozen enterprise coefficients when a market lacks sample.
    """
    from sqlalchemy import text

    # Prefer box-score means when present; else baseline. Walk-forward: prior weeks only.
    rows = session.execute(
        text(
            """
            WITH priors AS (
              SELECT season, week
              FROM (
                SELECT DISTINCT b.season, b.week
                FROM nfl_player_projection_baselines b
                WHERE b.season = ANY(:seasons)
                  AND (
                    b.season < :season
                    OR (b.season = :season AND b.week < :week)
                  )
                  AND b.week BETWEEN 4 AND 17
              ) x
            ),
            preds AS (
              SELECT
                b.season,
                b.week,
                b.player_id,
                b.team,
                b.pass_yards_mean AS base_pass,
                b.rush_yards_mean AS base_rush,
                b.receiving_yards_mean AS base_rec,
                b.receptions_mean AS base_receptions,
                s.pass_yards_mean AS box_pass,
                s.rush_yards_mean AS box_rush,
                s.receiving_yards_mean AS box_rec,
                s.receptions_mean AS box_receptions,
                COALESCE(
                  (s.pass_yards_dist->>'std')::float,
                  b.pass_yards_std
                ) AS pass_std,
                COALESCE(
                  (s.rush_yards_dist->>'std')::float,
                  b.rush_yards_std
                ) AS rush_std,
                COALESCE(
                  (s.receiving_yards_dist->>'std')::float,
                  b.receiving_yards_std
                ) AS rec_std,
                COALESCE(
                  (s.receptions_dist->>'std')::float,
                  b.receptions_std
                ) AS receptions_std
              FROM nfl_player_projection_baselines b
              INNER JOIN priors p ON p.season = b.season AND p.week = b.week
              LEFT JOIN nfl_player_game_box_score_sims s
                ON s.season = b.season
               AND s.week = b.week
               AND s.player_id = b.player_id
               AND s.team = b.team
              WHERE b.model_version = 'nfl-player-v1'
            )
            SELECT
              pr.season,
              pr.week,
              u.pass_yards AS actual_pass,
              u.rush_yards AS actual_rush,
              u.receiving_yards AS actual_rec,
              u.receptions AS actual_receptions,
              COALESCE(0.60 * pr.box_pass + 0.40 * pr.base_pass, pr.base_pass) AS pred_pass,
              COALESCE(0.60 * pr.box_rush + 0.40 * pr.base_rush, pr.base_rush) AS pred_rush,
              COALESCE(0.60 * pr.box_rec + 0.40 * pr.base_rec, pr.base_rec) AS pred_rec,
              COALESCE(0.60 * pr.box_receptions + 0.40 * pr.base_receptions, pr.base_receptions) AS pred_receptions,
              pr.pass_std,
              pr.rush_std,
              pr.rec_std,
              pr.receptions_std
            FROM preds pr
            INNER JOIN nfl_dp_player_usage_weekly u
              ON u.season = pr.season
             AND u.week = pr.week
             AND u.player_id = pr.player_id
             AND u.team = pr.team
            WHERE COALESCE(u.involvement_plays, 0) > 0
            """
        ),
        {
            "seasons": list(lookback_seasons),
            "season": int(season),
            "week": int(week),
        },
    ).fetchall()

    buckets: Dict[str, List[Dict[str, Any]]] = {
        "pass_yds": [],
        "rush_yds": [],
        "rec_yds": [],
        "receptions": [],
    }
    for row in rows:
        mapping = (
            ("pass_yds", row.pred_pass, row.actual_pass, row.pass_std),
            ("rush_yds", row.pred_rush, row.actual_rush, row.rush_std),
            ("rec_yds", row.pred_rec, row.actual_rec, row.rec_std),
            ("receptions", row.pred_receptions, row.actual_receptions, row.receptions_std),
        )
        for mk, pred, actual, std in mapping:
            if pred is None or actual is None:
                continue
            # Skip near-zero skill-position noise for volume markets.
            if mk in {"pass_yds", "rush_yds", "rec_yds"} and float(pred) < 1.0 and float(actual) < 1.0:
                continue
            buckets[mk].append({"pred": float(pred), "actual": float(actual), "std": std})

    out: Dict[str, PropMarketCalibration] = default_calibration_bundle()
    for mk, points in buckets.items():
        fitted = fit_prop_calibration_from_points(points, market_key=mk, min_sample_size=min_sample_size)
        if fitted.eligible:
            # Blend walk-forward with frozen for stability (50/50).
            frozen = frozen_calibration_for(mk)
            out[mk] = PropMarketCalibration(
                market_key=mk,
                intercept=round(0.5 * fitted.intercept + 0.5 * frozen.intercept, 4),
                std_multiplier=round(0.5 * fitted.std_multiplier + 0.5 * frozen.std_multiplier, 4),
                sample_size=fitted.sample_size,
                source="walk_forward",
            )
    return out
