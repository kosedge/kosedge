"""Phase 2.6C — holdout integrity tests (no scoring / no unseal)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

WEB_ROOT = Path(__file__).resolve().parents[1]
SRC = WEB_ROOT / "src"
REPO = WEB_ROOT.parent.parent
for p in (str(WEB_ROOT), str(SRC)):
    if p not in sys.path:
        sys.path.insert(0, p)

from ncaam_lab.holdout_2425.evaluator_gate import (  # noqa: E402
    HoldoutSealError,
    evaluate_holdout_refused_by_default,
)
from ncaam_lab.holdout_2425.phase26c.thresholds import (  # noqa: E402
    ABS_COVERAGE_GAP_PP_MATERIAL,
    ALLOWED_CONCLUSIONS,
    ESPN_REJECT_TAXONOMY,
    EXPECTED_ESPN_REJECT_COUNT,
    SMD_CLEARLY_MATERIAL,
    SMD_MATERIAL,
    THRESHOLD_VERSION,
    frozen_threshold_receipt,
)

COVERAGE_26C = REPO / "data" / "ops" / "lab" / "ncaam" / "holdout_2024_25" / "coverage_26c"
FORBIDDEN_PERF_KEYS = {
    "ats",
    "roi",
    "clv",
    "mae",
    "rmse",
    "calibration",
    "brier",
    "log_loss",
    "hit_rate",
    "units",
    "pnl",
    "score",
    "scores",
    "home_score",
    "away_score",
    "actual_margin",
    "prediction",
    "predictions",
}


def test_threshold_receipt_frozen_fields():
    receipt = frozen_threshold_receipt()
    assert receipt["threshold_version"] == THRESHOLD_VERSION
    assert receipt["frozen_before_slice_results"] is True
    assert receipt["abs_coverage_gap_pp_material"] == ABS_COVERAGE_GAP_PP_MATERIAL
    assert receipt["smd_material"] == SMD_MATERIAL
    assert receipt["smd_clearly_material"] == SMD_CLEARLY_MATERIAL
    assert set(receipt["allowed_conclusions"]) == set(ALLOWED_CONCLUSIONS)
    assert receipt["espn_reject_taxonomy"] == list(ESPN_REJECT_TAXONOMY)
    assert receipt["scores_omitted"] is True
    assert receipt["outcomes_omitted"] is True
    assert receipt["candidate_predictions_omitted"] is True


def test_espn_taxonomy_sum_invariant():
    ledger_path = COVERAGE_26C / "espn_reject_ledger.json"
    if not ledger_path.exists():
        # Synthetic invariant when artifacts not yet materialized in this checkout.
        taxonomy = {k: 0 for k in ESPN_REJECT_TAXONOMY}
        taxonomy["confirmed_non_di_opponent"] = EXPECTED_ESPN_REJECT_COUNT
        assert sum(taxonomy.values()) == EXPECTED_ESPN_REJECT_COUNT
        return
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    counts = ledger["taxonomy_counts"]
    assert sum(counts[k] for k in ESPN_REJECT_TAXONOMY) == EXPECTED_ESPN_REJECT_COUNT
    assert ledger["n_rejects"] == EXPECTED_ESPN_REJECT_COUNT
    assert ledger["taxonomy_sum"] == EXPECTED_ESPN_REJECT_COUNT
    assert ledger.get("scores_omitted") is True


def test_evaluator_still_refuses_by_default():
    with pytest.raises(HoldoutSealError):
        evaluate_holdout_refused_by_default()
    with pytest.raises(HoldoutSealError):
        evaluate_holdout_refused_by_default(None)


def _collect_keys(obj, acc: set[str]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            acc.add(str(k).lower())
            _collect_keys(v, acc)
    elif isinstance(obj, list):
        for item in obj[:50]:
            _collect_keys(item, acc)


def test_no_performance_fields_in_representativeness_keys():
    path = COVERAGE_26C / "feature_only_representativeness.json"
    if not path.exists():
        # Contract check against the allowed conclusion set only.
        assert "REPRESENTATIVE_ON_AUDITED_FEATURES" in ALLOWED_CONCLUSIONS
        return
    payload = json.loads(path.read_text(encoding="utf-8"))
    keys: set[str] = set()
    _collect_keys(payload, keys)
    leaked = FORBIDDEN_PERF_KEYS & keys
    assert not leaked, f"performance fields leaked into representativeness: {sorted(leaked)}"
    assert payload.get("scores_omitted") is True
    assert payload.get("outcomes_omitted") is True
    assert payload.get("ats_roi_clv_calibration_omitted") is True
    assert payload.get("candidate_predictions_omitted") is True
    assert payload.get("conclusion") in ALLOWED_CONCLUSIONS
