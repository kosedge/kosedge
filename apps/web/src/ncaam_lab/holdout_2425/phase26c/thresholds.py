"""Phase 2.6C — predeclared feature-only representativeness thresholds.

FROZEN BEFORE viewing slice results. Bump threshold_version if changed.
"""

from __future__ import annotations

from typing import Any, Dict

THRESHOLD_VERSION = "phase26c_feature_only_v1"

ABS_COVERAGE_GAP_PP_MATERIAL = 10.0
SMD_MATERIAL = 0.10
SMD_CLEARLY_MATERIAL = 0.20
SYNTHETIC_CLOSE_HOUR_UTC = 22

POWER_CONF_SHORT = frozenset({"ACC", "B10", "B12", "BE", "SEC", "P12"})

TIP_HOUR_BANDS_UTC = (
    ("early_utc_0_15", range(0, 16)),
    ("afternoon_utc_16_19", range(16, 20)),
    ("primetime_utc_20_23", range(20, 24)),
)

ADJM_GAP_BINS = (
    ("gap_lt_-20", None, -20.0),
    ("gap_-20_-10", -20.0, -10.0),
    ("gap_-10_-5", -10.0, -5.0),
    ("gap_-5_0", -5.0, 0.0),
    ("gap_0_5", 0.0, 5.0),
    ("gap_5_10", 5.0, 10.0),
    ("gap_10_20", 10.0, 20.0),
    ("gap_gte_20", 20.0, None),
)

ADJT_BINS = (
    ("pace_lt_65", None, 65.0),
    ("pace_65_68", 65.0, 68.0),
    ("pace_68_71", 68.0, 71.0),
    ("pace_71_74", 71.0, 74.0),
    ("pace_gte_74", 74.0, None),
)

SPREAD_MAG_BINS = (
    ("spread_0_3", 0.0, 3.0),
    ("spread_3_7", 3.0, 7.0),
    ("spread_7_12", 7.0, 12.0),
    ("spread_12_20", 12.0, 20.0),
    ("spread_gte_20", 20.0, None),
)

ALLOWED_CONCLUSIONS = frozenset(
    {
        "REPRESENTATIVE_ON_AUDITED_FEATURES",
        "MATERIAL_SELECTION_DETECTED",
        "INCONCLUSIVE_DUE_TO_MISSING_FEATURES",
    }
)

ESPN_REJECT_TAXONOMY = (
    "confirmed_non_di_opponent",
    "exhibition_or_scrimmage",
    "duplicate_schedule_event",
    "cancelled_or_non_final",
    "b7_team_missing",
    "b7_alias_missing",
    "ambiguous_identity",
    "malformed_source_record",
    "other_explicit_reason",
)

EXPECTED_ESPN_REJECT_COUNT = 530
EXPECTED_TIMESTAMP_DISHONEST_COUNT = 2006
EXPECTED_DUPLICATE_CONFLICT_COUNT = 153


def frozen_threshold_receipt() -> Dict[str, Any]:
    return {
        "threshold_version": THRESHOLD_VERSION,
        "frozen_before_slice_results": True,
        "abs_coverage_gap_pp_material": ABS_COVERAGE_GAP_PP_MATERIAL,
        "smd_material": SMD_MATERIAL,
        "smd_clearly_material": SMD_CLEARLY_MATERIAL,
        "power_conf_short": sorted(POWER_CONF_SHORT),
        "synthetic_close_hour_utc": SYNTHETIC_CLOSE_HOUR_UTC,
        "allowed_conclusions": sorted(ALLOWED_CONCLUSIONS),
        "espn_reject_taxonomy": list(ESPN_REJECT_TAXONOMY),
        "justification": (
            "Material selection flagged when |coverage_included − coverage_reference| ≥ 10pp "
            "or |SMD| ≥ 0.10 for numeric features; |SMD| ≥ 0.20 is clearly material. "
            "Thresholds chosen a priori to detect systematic 22:00 UTC timestamp selection "
            "without outcome inspection."
        ),
        "scores_omitted": True,
        "outcomes_omitted": True,
        "candidate_predictions_omitted": True,
    }
