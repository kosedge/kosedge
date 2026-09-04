"""B2 fair engine — KenPom AdjEM + HCA with PRIOR/UNKNOWN continuity honesty.

Does not emit fair ML from spread (no silent spread→ML).
Fair total only when AdjOE/AdjDE/AdjT all present (stated method).
Never tags continuity_state=SETTLED (portal model = DATA GAP).
"""

from __future__ import annotations

from typing import Optional

import polars as pl

from ncaam_lab.protocol import (
    ADJEM_DIFF_CLIP,
    ContinuityState,
    DEFAULT_HCA,
    FAIR_TOTAL_METHOD,
    PROTOCOL_VERSION,
    SPREAD_CLIP,
    UNCERTAINTY_SIGMA_PRIOR,
    UNCERTAINTY_SIGMA_UNKNOWN,
)


def _load_hca(weights_path) -> float:
    if weights_path is None:
        return DEFAULT_HCA
    try:
        import json
        from pathlib import Path

        p = Path(weights_path)
        if not p.exists():
            return DEFAULT_HCA
        with open(p, encoding="utf-8") as f:
            w = json.load(f)
        return float(w.get("home_court", DEFAULT_HCA))
    except Exception:
        return DEFAULT_HCA


def compute_fair_b2(
    games: pl.DataFrame,
    *,
    hca: Optional[float] = None,
    weights_path=None,
) -> pl.DataFrame:
    """Attach fair_spread_home (+ optional fair_total) and continuity honesty fields."""
    if hca is None:
        hca = _load_hca(weights_path)

    # Continuity: PRIOR when both sides have as-of AdjEM ≤ tip; else UNKNOWN.
    # SETTLED forbidden.
    has_home = pl.col("adjem_home").is_not_null() if "adjem_home" in games.columns else pl.lit(False)
    has_away = pl.col("adjem_away").is_not_null() if "adjem_away" in games.columns else pl.lit(False)
    asof_ok = pl.lit(True)
    if "kenpom_as_of_home" in games.columns and "tip_date" in games.columns:
        asof_ok = asof_ok & pl.col("kenpom_as_of_home").is_not_null() & (
            pl.col("kenpom_as_of_home") <= pl.col("tip_date")
        )
    if "kenpom_as_of_away" in games.columns and "tip_date" in games.columns:
        asof_ok = asof_ok & pl.col("kenpom_as_of_away").is_not_null() & (
            pl.col("kenpom_as_of_away") <= pl.col("tip_date")
        )

    continuity = (
        pl.when(has_home & has_away & asof_ok)
        .then(pl.lit(ContinuityState.PRIOR.value))
        .otherwise(pl.lit(ContinuityState.UNKNOWN.value))
    )
    sigma = (
        pl.when(continuity == ContinuityState.PRIOR.value)
        .then(pl.lit(UNCERTAINTY_SIGMA_PRIOR))
        .otherwise(pl.lit(UNCERTAINTY_SIGMA_UNKNOWN))
    )

    # Fair spread only when both AdjEM present; else null (fail-closed on ratings).
    adjem_diff = (
        pl.col("adjem_home") - pl.col("adjem_away")
    ).clip(-ADJEM_DIFF_CLIP, ADJEM_DIFF_CLIP)
    raw_spread = adjem_diff + float(hca)
    fair_spread = (
        pl.when(has_home & has_away)
        .then(raw_spread.clip(-SPREAD_CLIP, SPREAD_CLIP))
        .otherwise(None)
    )

    out = games.with_columns(
        [
            continuity.alias("continuity_state"),
            sigma.alias("uncertainty_sigma"),
            fair_spread.alias("fair_spread_home"),
            pl.lit(float(hca)).alias("hca_applied"),
            pl.lit("kenpom_adjem_plus_hca_v1").alias("fair_spread_method"),
            pl.lit(PROTOCOL_VERSION).alias("protocol_version"),
            # Explicit: no silent ML
            pl.lit(None).cast(pl.Float64).alias("fair_ml_home"),
            pl.lit("omitted_no_silent_spread_to_ml").alias("fair_ml_method"),
        ]
    )

    # Fair total — only when all four-factor inputs present
    total_cols = ("adjoe_home", "adjde_home", "adjt_home", "adjoe_away", "adjde_away", "adjt_away")
    if all(c in out.columns for c in total_cols):
        all_present = (
            pl.col("adjoe_home").is_not_null()
            & pl.col("adjde_home").is_not_null()
            & pl.col("adjt_home").is_not_null()
            & pl.col("adjoe_away").is_not_null()
            & pl.col("adjde_away").is_not_null()
            & pl.col("adjt_away").is_not_null()
        )
        pace = (pl.col("adjt_home") + pl.col("adjt_away")) / 2.0
        pts_per_100 = (
            pl.col("adjoe_home")
            + pl.col("adjde_away")
            + pl.col("adjoe_away")
            + pl.col("adjde_home")
        )
        fair_total = pace / 100.0 * pts_per_100 / 2.0
        out = out.with_columns(
            [
                pl.when(all_present).then(fair_total).otherwise(None).alias("fair_total"),
                pl.when(all_present)
                .then(pl.lit(FAIR_TOTAL_METHOD))
                .otherwise(pl.lit(None))
                .alias("fair_total_method"),
            ]
        )
    else:
        out = out.with_columns(
            [
                pl.lit(None).cast(pl.Float64).alias("fair_total"),
                pl.lit(None).cast(pl.Utf8).alias("fair_total_method"),
            ]
        )

    return out
