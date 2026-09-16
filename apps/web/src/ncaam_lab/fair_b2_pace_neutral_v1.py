"""B2-PACE-NEUTRAL-v1 research challenger — pace unit correction + gated HCA.

Immutable candidate ID: B2-PACE-NEUTRAL-v1
Method stamp: kenpom_adjem_pit_tempo_gated_hca_v1

Atomic difference vs frozen B2-PACE-v1:
  - confirmed_home     → HCA = 2.8696 (identical to B2-PACE-v1)
  - confirmed_neutral  → HCA = 0.0
  - unknown / missing  → fail closed (no fair)

Pace scaling, AdjEM clips (±30), final margin clips (±28), PIT AdjT requirements,
and PRIOR/UNKNOWN continuity rules are identical to B2-PACE-v1.

Hard locks:
  - Does NOT mutate B2-PACE-v1 / fair_b2_pace_v1.py under its candidate ID
  - Does NOT replace incumbent materialize path
  - Does NOT read sealed holdout, Test-A, or pocket frames
  - Research-only; not promoted; not production default
"""

from __future__ import annotations

import math
from typing import Optional

import polars as pl

from ncaam_lab.fair_b2_pace_v1 import (
    FROZEN_ADJEM_DIFF_CLIP,
    FROZEN_HCA,
    FROZEN_SPREAD_CLIP,
    CANDIDATE_ID as PACE_CANDIDATE_ID,
    METHOD_ID as PACE_METHOD_ID,
    _is_finite_number,
)
from ncaam_lab.neutral_site_identity import (
    VENUE_STATUS_HOME,
    VENUE_STATUS_NEUTRAL,
    VENUE_STATUS_UNKNOWN,
)
from ncaam_lab.protocol import (
    ContinuityState,
    PROTOCOL_VERSION,
    UNCERTAINTY_SIGMA_PRIOR,
    UNCERTAINTY_SIGMA_UNKNOWN,
)

CANDIDATE_ID = "B2-PACE-NEUTRAL-v1"
METHOD_ID = "kenpom_adjem_pit_tempo_gated_hca_v1"
PARENT_CANDIDATE_ID = PACE_CANDIDATE_ID
PARENT_METHOD_ID = PACE_METHOD_ID

FAIR_COL = "fair_spread_home_b2_pace_neutral_v1"
METHOD_COL = "fair_spread_method_b2_pace_neutral_v1"
CANDIDATE_COL = "fair_candidate_id_b2_pace_neutral_v1"
HCA_COL = "hca_applied_b2_pace_neutral_v1"
ELIGIBLE_COL = "b2_pace_neutral_v1_eligible"
EXPECTED_POSS_COL = "expected_possessions_b2_pace_neutral_v1"
RAW_MARGIN_COL = "raw_home_margin_b2_pace_neutral_v1"
VENUE_STATUS_COL = "venue_status_b2_pace_neutral_v1"

FROZEN_HCA_HOME = float(FROZEN_HCA)  # 2.8696
FROZEN_HCA_NEUTRAL = 0.0


def resolve_hca_for_venue_status(venue_status: Optional[str]) -> Optional[float]:
    """Return frozen HCA for confirmed statuses; None ⇒ fail closed."""
    if venue_status == VENUE_STATUS_HOME:
        return FROZEN_HCA_HOME
    if venue_status == VENUE_STATUS_NEUTRAL:
        return FROZEN_HCA_NEUTRAL
    return None


def scalar_fair_home_margin(
    *,
    adjem_home: Optional[float],
    adjem_away: Optional[float],
    adjt_home: Optional[float],
    adjt_away: Optional[float],
    venue_status: Optional[str],
) -> Optional[float]:
    """Pure scalar formula. Unknown venue / non-finite inputs → None."""
    hca = resolve_hca_for_venue_status(venue_status)
    if hca is None:
        return None
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
    raw = adjem_diff * (expected_possessions / 100.0) + float(hca)
    if not math.isfinite(raw):
        return None
    return max(-FROZEN_SPREAD_CLIP, min(FROZEN_SPREAD_CLIP, raw))


def compute_fair_b2_pace_neutral_v1(games: pl.DataFrame) -> pl.DataFrame:
    """Attach B2-PACE-NEUTRAL-v1 columns. Requires ``venue_status`` on input.

    Call ``neutral_site_identity.attach_venue_status`` first. Does not mutate
    incumbent or B2-PACE-v1 columns.
    """
    if "venue_status" not in games.columns:
        raise ValueError(
            f"{CANDIDATE_ID} requires venue_status column; "
            "run attach_venue_status first (fail-closed)"
        )

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

    venue_ok = pl.col("venue_status").is_in(
        [VENUE_STATUS_HOME, VENUE_STATUS_NEUTRAL]
    )

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

    eligible = has_adjem_home & has_adjem_away & adjt_valid & pit_ok & venue_ok

    hca_expr = (
        pl.when(pl.col("venue_status") == VENUE_STATUS_NEUTRAL)
        .then(pl.lit(FROZEN_HCA_NEUTRAL))
        .when(pl.col("venue_status") == VENUE_STATUS_HOME)
        .then(pl.lit(FROZEN_HCA_HOME))
        .otherwise(None)
    )

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

    raw_margin = adjem_diff * (expected_poss / 100.0) + hca_expr
    fair = (
        pl.when(eligible)
        .then(raw_margin.clip(-FROZEN_SPREAD_CLIP, FROZEN_SPREAD_CLIP))
        .otherwise(None)
    )

    return games.with_columns(
        [
            continuity.alias("continuity_state_b2_pace_neutral_v1"),
            sigma.alias("uncertainty_sigma_b2_pace_neutral_v1"),
            eligible.alias(ELIGIBLE_COL),
            expected_poss.alias(EXPECTED_POSS_COL),
            pl.when(eligible).then(raw_margin).otherwise(None).alias(RAW_MARGIN_COL),
            fair.alias(FAIR_COL),
            pl.when(eligible).then(hca_expr).otherwise(None).alias(HCA_COL),
            pl.col("venue_status").alias(VENUE_STATUS_COL),
            pl.when(eligible).then(pl.lit(METHOD_ID)).otherwise(None).alias(METHOD_COL),
            pl.when(eligible)
            .then(pl.lit(CANDIDATE_ID))
            .otherwise(None)
            .alias(CANDIDATE_COL),
            pl.lit(PROTOCOL_VERSION).alias("protocol_version_b2_pace_neutral_v1"),
            pl.lit(None).cast(pl.Float64).alias("fair_ml_home_b2_pace_neutral_v1"),
            pl.lit("omitted_no_silent_spread_to_ml").alias(
                "fair_ml_method_b2_pace_neutral_v1"
            ),
            pl.lit(False).alias("production_default_b2_pace_neutral_v1"),
            pl.lit(False).alias("promoted_b2_pace_neutral_v1"),
        ]
    )


def assert_parent_immutability_pins() -> None:
    """Guard: parent B2-PACE-v1 frozen pins must remain unchanged."""
    if PARENT_CANDIDATE_ID != "B2-PACE-v1":
        raise AssertionError(PARENT_CANDIDATE_ID)
    if abs(FROZEN_HCA_HOME - 2.8696) > 1e-12:
        raise AssertionError(FROZEN_HCA_HOME)
    if FROZEN_HCA_NEUTRAL != 0.0:
        raise AssertionError(FROZEN_HCA_NEUTRAL)
    if VENUE_STATUS_UNKNOWN != "unknown":
        raise AssertionError(VENUE_STATUS_UNKNOWN)
