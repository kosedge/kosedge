"""B2-PACE-v1 challenger — KenPom AdjEM × PIT tempo + game HCA.

Atomic unit correction only:
  points/100 AdjEM differential → game points via PIT expected possessions.

Immutable candidate ID: B2-PACE-v1
Method stamp: kenpom_adjem_pit_tempo_plus_game_hca_v1

Frozen contract (Phase 2.7A — immutable under this candidate ID):
  adjem_diff = clip(home_adjem - away_adjem, ±30)
  possessions = (home_adjt + away_adjt) / 2
  margin = clip(adjem_diff * possessions / 100 + 2.8696, ±28)

HCA and clips are pinned. weights_path / custom HCA cannot change behavior:
mismatch is refused (no silent fallback). Non-finite AdjEM/AdjT/HCA fail closed.

This module does NOT replace the incumbent B2/C0 engine (`fair_b2.compute_fair_b2`).
It never writes product board / kei_lines paths. Materialize remains on incumbent.
"""

from __future__ import annotations

import math
from typing import Optional

import polars as pl

from ncaam_lab.protocol import (
    ADJEM_DIFF_CLIP,
    ContinuityState,
    DEFAULT_HCA,
    PROTOCOL_VERSION,
    SPREAD_CLIP,
    UNCERTAINTY_SIGMA_PRIOR,
    UNCERTAINTY_SIGMA_UNKNOWN,
)

# Immutable identifiers — do not reuse ordinals from research notes ("C3").
CANDIDATE_ID = "B2-PACE-v1"
METHOD_ID = "kenpom_adjem_pit_tempo_plus_game_hca_v1"
RESEARCH_ALIAS = "C3"  # diagnostic label only; not a production ID

# Incumbent identity (unchanged historical B2/C0).
INCUMBENT_CANDIDATE_ID = "B2-C0-v1"
INCUMBENT_METHOD_ID = "kenpom_adjem_plus_hca_v1"

# Output columns are explicitly namespaced so challenger cannot silently
# overwrite incumbent fair_spread_home.
FAIR_COL = "fair_spread_home_b2_pace_v1"
METHOD_COL = "fair_spread_method_b2_pace_v1"
CANDIDATE_COL = "fair_candidate_id_b2_pace_v1"
HCA_COL = "hca_applied_b2_pace_v1"
ELIGIBLE_COL = "b2_pace_v1_eligible"
EXPECTED_POSS_COL = "expected_possessions_b2_pace_v1"
RAW_MARGIN_COL = "raw_home_margin_b2_pace_v1"

# Frozen contract pins (must match protocol defaults; refuse runtime mismatch).
FROZEN_HCA = float(DEFAULT_HCA)  # 2.8696
FROZEN_ADJEM_DIFF_CLIP = float(ADJEM_DIFF_CLIP)  # 30.0
FROZEN_SPREAD_CLIP = float(SPREAD_CLIP)  # 28.0


def _is_finite_number(value: object) -> bool:
    if value is None:
        return False
    try:
        return math.isfinite(float(value))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False


def _resolve_frozen_hca(*, hca: Optional[float] = None, weights_path=None) -> float:
    """Pin HCA=2.8696 for B2-PACE-v1. Refuse mismatch / weights / non-finite.

    No silent fallback: an explicit weights_path never loads alternate HCA, and a
    custom hca that differs from the frozen contract is an error (not ignored).
    """
    if weights_path is not None:
        raise ValueError(
            f"{CANDIDATE_ID} refuses weights_path; HCA is frozen at {FROZEN_HCA} "
            "(no silent load / fallback)"
        )
    if hca is not None:
        if not _is_finite_number(hca):
            raise ValueError(
                f"{CANDIDATE_ID} refuses non-finite hca={hca!r}; "
                f"frozen contract requires hca={FROZEN_HCA}"
            )
        if float(hca) != FROZEN_HCA:
            raise ValueError(
                f"{CANDIDATE_ID} refuses HCA mismatch: got {float(hca)!r}, "
                f"frozen={FROZEN_HCA}"
            )
    return FROZEN_HCA


def scalar_fair_home_margin(
    *,
    adjem_home: Optional[float],
    adjem_away: Optional[float],
    adjt_home: Optional[float],
    adjt_away: Optional[float],
    hca: Optional[float] = None,
) -> Optional[float]:
    """Pure scalar formula for tests / audit.

    Sign convention (proven by tests): return value is predicted home margin
    in points (positive ⇒ home wins by that many points), matching incumbent B2
    `fair_spread_home`.

    Under B2-PACE-v1, ``hca`` must be omitted or exactly equal FROZEN_HCA (2.8696).
    Non-finite AdjEM/AdjT → None (fail closed). Non-finite / mismatched HCA → raise.
    """
    frozen_hca = _resolve_frozen_hca(hca=hca, weights_path=None)

    if adjem_home is None or adjem_away is None:
        return None
    if adjt_home is None or adjt_away is None:
        return None
    if not all(
        _is_finite_number(v) for v in (adjem_home, adjem_away, adjt_home, adjt_away)
    ):
        return None
    if float(adjt_home) <= 0 or float(adjt_away) <= 0:
        return None

    adjem_diff = max(
        -FROZEN_ADJEM_DIFF_CLIP,
        min(FROZEN_ADJEM_DIFF_CLIP, float(adjem_home) - float(adjem_away)),
    )
    expected_possessions = (float(adjt_home) + float(adjt_away)) / 2.0
    if not math.isfinite(expected_possessions):
        return None
    raw = adjem_diff * (expected_possessions / 100.0) + frozen_hca
    if not math.isfinite(raw):
        return None
    return max(-FROZEN_SPREAD_CLIP, min(FROZEN_SPREAD_CLIP, raw))


def compute_fair_b2_pace_v1(
    games: pl.DataFrame,
    *,
    hca: Optional[float] = None,
    weights_path=None,
) -> pl.DataFrame:
    """Attach B2-PACE-v1 fair margin columns (namespaced; incumbent untouched).

    Fail-closed when any of home/away AdjEM, home/away AdjT, or valid PIT as-of
    timestamps are missing/invalid/non-finite. Never substitutes national-average
    tempo, fitted β, market-implied tempo, or post-tip / SETTLED ratings.

    HCA is immutable under this candidate ID: ``weights_path`` is refused;
    custom ``hca`` must match FROZEN_HCA or the call raises.
    """
    frozen_hca = _resolve_frozen_hca(hca=hca, weights_path=weights_path)

    def _finite_col(name: str) -> pl.Expr:
        if name not in games.columns:
            return pl.lit(False)
        return pl.col(name).is_not_null() & pl.col(name).is_finite()

    has_adjem_home = _finite_col("adjem_home")
    has_adjem_away = _finite_col("adjem_away")
    has_adjt_home = _finite_col("adjt_home")
    has_adjt_away = _finite_col("adjt_away")
    if "adjt_home" in games.columns and "adjt_away" in games.columns:
        adjt_valid = (
            has_adjt_home
            & has_adjt_away
            & (pl.col("adjt_home") > 0)
            & (pl.col("adjt_away") > 0)
        )
    else:
        adjt_valid = pl.lit(False)

    # Valid PIT/as-of: both timestamps present and ≤ tip (no post-tip leakage).
    if "kenpom_as_of_home" in games.columns and "tip_date" in games.columns:
        pit_home_ok = pl.col("kenpom_as_of_home").is_not_null() & (
            pl.col("kenpom_as_of_home") <= pl.col("tip_date")
        )
    else:
        pit_home_ok = pl.lit(False)
    if "kenpom_as_of_away" in games.columns and "tip_date" in games.columns:
        pit_away_ok = pl.col("kenpom_as_of_away").is_not_null() & (
            pl.col("kenpom_as_of_away") <= pl.col("tip_date")
        )
    else:
        pit_away_ok = pl.lit(False)
    pit_ok = pit_home_ok & pit_away_ok

    # Continuity honesty (PRIOR/UNKNOWN only; SETTLED forbidden).
    # PRIOR still requires finite AdjEM (non-finite ratings are not PRIOR).
    continuity = (
        pl.when(has_adjem_home & has_adjem_away & pit_ok)
        .then(pl.lit(ContinuityState.PRIOR.value))
        .otherwise(pl.lit(ContinuityState.UNKNOWN.value))
    )
    sigma = (
        pl.when(continuity == ContinuityState.PRIOR.value)
        .then(pl.lit(UNCERTAINTY_SIGMA_PRIOR))
        .otherwise(pl.lit(UNCERTAINTY_SIGMA_UNKNOWN))
    )

    eligible = has_adjem_home & has_adjem_away & adjt_valid & pit_ok

    if "adjem_home" in games.columns and "adjem_away" in games.columns:
        adjem_diff = (pl.col("adjem_home") - pl.col("adjem_away")).clip(
            -FROZEN_ADJEM_DIFF_CLIP, FROZEN_ADJEM_DIFF_CLIP
        )
    else:
        adjem_diff = pl.lit(None).cast(pl.Float64)

    if "adjt_home" in games.columns and "adjt_away" in games.columns:
        expected_poss = (pl.col("adjt_home") + pl.col("adjt_away")) / 2.0
    else:
        expected_poss = pl.lit(None).cast(pl.Float64)

    raw_margin = adjem_diff * (expected_poss / 100.0) + frozen_hca
    fair = (
        pl.when(eligible)
        .then(raw_margin.clip(-FROZEN_SPREAD_CLIP, FROZEN_SPREAD_CLIP))
        .otherwise(None)
    )

    # Do not touch incumbent fair_spread_home / fair_spread_method columns.
    return games.with_columns(
        [
            continuity.alias("continuity_state_b2_pace_v1"),
            sigma.alias("uncertainty_sigma_b2_pace_v1"),
            eligible.alias(ELIGIBLE_COL),
            expected_poss.alias(EXPECTED_POSS_COL),
            pl.when(eligible).then(raw_margin).otherwise(None).alias(RAW_MARGIN_COL),
            fair.alias(FAIR_COL),
            pl.lit(frozen_hca).alias(HCA_COL),
            pl.when(eligible).then(pl.lit(METHOD_ID)).otherwise(None).alias(METHOD_COL),
            pl.when(eligible)
            .then(pl.lit(CANDIDATE_ID))
            .otherwise(None)
            .alias(CANDIDATE_COL),
            pl.lit(PROTOCOL_VERSION).alias("protocol_version_b2_pace_v1"),
            pl.lit(None).cast(pl.Float64).alias("fair_ml_home_b2_pace_v1"),
            pl.lit("omitted_no_silent_spread_to_ml").alias("fair_ml_method_b2_pace_v1"),
        ]
    )


def select_fair_candidate(
    games: pl.DataFrame,
    candidate_id: str,
) -> pl.DataFrame:
    """Explicit candidate selection into working column `selected_fair_spread_home`.

    No defaulting: caller must pass an explicit candidate_id.
    Incumbent remains the only path used by materialize_lab_fair.
    """
    if candidate_id in (INCUMBENT_CANDIDATE_ID, INCUMBENT_METHOD_ID, "B2", "C0"):
        if "fair_spread_home" not in games.columns:
            raise ValueError("incumbent fair_spread_home missing; run compute_fair_b2 first")
        return games.with_columns(
            [
                pl.col("fair_spread_home").alias("selected_fair_spread_home"),
                pl.lit(INCUMBENT_CANDIDATE_ID).alias("selected_fair_candidate_id"),
            ]
        )
    if candidate_id in (CANDIDATE_ID, METHOD_ID, RESEARCH_ALIAS):
        if FAIR_COL not in games.columns:
            raise ValueError(f"{FAIR_COL} missing; run compute_fair_b2_pace_v1 first")
        return games.with_columns(
            [
                pl.col(FAIR_COL).alias("selected_fair_spread_home"),
                pl.lit(CANDIDATE_ID).alias("selected_fair_candidate_id"),
            ]
        )
    raise ValueError(
        f"unknown fair candidate_id={candidate_id!r}; "
        f"allowed={{'{INCUMBENT_CANDIDATE_ID}','{CANDIDATE_ID}'}}"
    )
