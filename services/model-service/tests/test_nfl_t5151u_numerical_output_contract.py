"""t5151u Package B — numerical output contract. Synthetic only. No real EVAL."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from src.services.nfl_t5107u.eval_result_contract import (
    DEV_IF437_BY_SEASON,
    DEV_MARKET72_BY_SEASON,
    INTERVAL_CONTRACT,
    PROFILE_DEV_IF437,
    PROFILE_DEV_MARKET72,
    PROFILE_FEATURE_RECON_REG496,
    REG496_BY_SEASON,
    REG496_N,
    EvalResultContractRefuse,
    apply_eval_result_contract,
    validate_dev_if437,
    validate_eval_result_contract,
    validate_feature_recon_reg496,
    validate_profile_output,
)
from src.services.nfl_t5107u.last_played_cohort import ORIGINAL_502_PATH, ORIGINAL_502_SHA256
from src.services.nfl_t5107u.metric_cohorts import WILDCARD_2020_W18
from src.services.nfl_t5107u.recon_driver import sha256_file
from src.services.nfl_t5107u.verify_integrate import (
    FEATURE_RECON_REG496_ARTIFACT_PATH,
    FEATURE_RECON_REG496_ARTIFACT_SHA256,
    build_synthetic_if437_result,
    build_synthetic_market72_result,
)

ROOT = Path(__file__).resolve().parents[3]
REG_ARTIFACT = ROOT / FEATURE_RECON_REG496_ARTIFACT_PATH
ORIGINAL_502 = ROOT / ORIGINAL_502_PATH


def test_interval_contract_is_frozen_market72():
    assert INTERVAL_CONTRACT["B"] == 10000
    assert INTERVAL_CONTRACT["seed"] == 20261101
    assert INTERVAL_CONTRACT["rerun_intervals"] is False


def test_feature_recon_reg496_lineage_and_completeness():
    payload = json.loads(REG_ARTIFACT.read_text(encoding="utf-8"))
    assert sha256_file(REG_ARTIFACT) == FEATURE_RECON_REG496_ARTIFACT_SHA256
    result = validate_feature_recon_reg496(payload)
    assert result["ok"] is True
    assert result["n"] == REG496_N
    assert result["n_by_season"] == REG496_BY_SEASON
    assert result["invented_metrics"] is False
    assert result["w18_2021_retained"] == 16


def test_feature_recon_invented_metrics_fail():
    payload = json.loads(REG_ARTIFACT.read_text(encoding="utf-8"))
    payload = dict(payload)
    payload["mae_challenger"] = 3.14
    with pytest.raises(EvalResultContractRefuse, match="invented metric"):
        validate_feature_recon_reg496(payload)


def test_feature_recon_inconsistent_counts_fail():
    payload = json.loads(REG_ARTIFACT.read_text(encoding="utf-8"))
    payload = dict(payload)
    payload["n"] = 495
    with pytest.raises(EvalResultContractRefuse, match="n=495"):
        validate_feature_recon_reg496(payload)


def test_original_502_fails_reg_numerical_profile():
    assert sha256_file(ORIGINAL_502) == ORIGINAL_502_SHA256
    payload = json.loads(ORIGINAL_502.read_text(encoding="utf-8"))
    assert payload["n_complete_27"] == 502
    with pytest.raises(EvalResultContractRefuse, match="n=502 != 496"):
        validate_profile_output(PROFILE_FEATURE_RECON_REG496, payload)


def test_dev_if437_positive_control_marks_market_unavailable():
    payload = build_synthetic_if437_result()
    result = validate_dev_if437(payload)
    assert result["ok"] is True
    assert result["market_unavailable"] is True
    assert result["cannot_satisfy_profile"] == PROFILE_DEV_MARKET72
    with pytest.raises(EvalResultContractRefuse, match="cannot satisfy|market unavailable|IF-only"):
        validate_eval_result_contract(payload)
    with pytest.raises(EvalResultContractRefuse, match="DEV_MARKET72|unavailable"):
        validate_profile_output(PROFILE_DEV_MARKET72, payload)


def test_dev_if437_missing_unavailable_flag_fails():
    payload = build_synthetic_if437_result()
    payload["market_unavailable"] = False
    with pytest.raises(EvalResultContractRefuse, match="market unavailable"):
        validate_dev_if437(payload)


def test_dev_market72_positive_control():
    payload = build_synthetic_market72_result()
    result = validate_profile_output(PROFILE_DEV_MARKET72, payload)
    assert result["ok"] is True
    stamped = apply_eval_result_contract(dict(payload))
    assert stamped["eval_result_contract"].endswith("v2")
    assert stamped["eval_result_sides"] == ["if", "market"]


def test_missing_candidate_vs_market_fields_fail():
    payload = build_synthetic_market72_result()
    row = dict(payload["games"][0])
    for key in ("m_market", "err_market", "L_market", "signed_diff_vs_market"):
        row.pop(key, None)
    payload["games"][0] = row
    with pytest.raises(EvalResultContractRefuse, match="missing candidate-vs-market"):
        validate_profile_output(PROFILE_DEV_MARKET72, payload)


def test_null_nan_infinity_fail():
    payload = build_synthetic_market72_result()
    payload["mae_market"] = None
    with pytest.raises(EvalResultContractRefuse, match="null|missing"):
        validate_eval_result_contract(payload)
    payload = build_synthetic_market72_result()
    payload["rmse_if"] = math.nan
    with pytest.raises(EvalResultContractRefuse, match="NaN"):
        validate_profile_output(PROFILE_DEV_MARKET72, payload)
    payload = build_synthetic_market72_result()
    payload["bias_challenger"] = math.inf
    with pytest.raises(EvalResultContractRefuse, match="not finite"):
        validate_profile_output(PROFILE_DEV_MARKET72, payload)


def test_inconsistent_counts_fail():
    payload = build_synthetic_market72_result()
    payload["n"] = payload["n"] + 1
    with pytest.raises(EvalResultContractRefuse, match="inconsistent counts"):
        validate_profile_output(PROFILE_DEV_MARKET72, payload)


def test_recompute_mismatch_never_rewrites_recorded():
    payload = build_synthetic_market72_result()
    recorded = payload["mae_challenger"]
    payload["mae_challenger"] = recorded + 0.5
    with pytest.raises(EvalResultContractRefuse, match="inconsistent with saved rows"):
        validate_profile_output(PROFILE_DEV_MARKET72, payload)
    assert payload["mae_challenger"] == recorded + 0.5


def test_interval_metadata_ordered_labeled_frozen():
    payload = build_synthetic_market72_result()
    payload["bootstrap_game"]["ci95"] = [0.2, -0.2]
    with pytest.raises(EvalResultContractRefuse, match="not ordered"):
        validate_profile_output(PROFILE_DEV_MARKET72, payload)
    payload = build_synthetic_market72_result()
    payload["bootstrap_game_vs_market"]["B"] = 999
    with pytest.raises(EvalResultContractRefuse, match="B is frozen"):
        validate_profile_output(PROFILE_DEV_MARKET72, payload)
    payload = build_synthetic_market72_result()
    payload["bootstrap_season_week"]["unit"] = "game"
    with pytest.raises(EvalResultContractRefuse, match="mislabeled unit"):
        validate_profile_output(PROFILE_DEV_MARKET72, payload)


def test_profile_season_constants():
    assert DEV_IF437_BY_SEASON == {"2020": 210, "2021": 227}
    assert DEV_MARKET72_BY_SEASON == {"2020": 35, "2021": 37}
    assert not set(WILDCARD_2020_W18) & set(
        json.loads(REG_ARTIFACT.read_text(encoding="utf-8"))["game_ids"]
    )
