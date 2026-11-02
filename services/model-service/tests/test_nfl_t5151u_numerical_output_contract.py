"""t5153u Package B — numerical output contract on published artifacts.

Normal validators consume immutable DEV437 / matched72 / REG496 bytes.
Synthetic fixtures exist only as explicit helpers and must be refused.
No real EVAL. CERT=0.
"""

from __future__ import annotations

import copy
import json
import math
from pathlib import Path

import pytest

from src.services.nfl_t5107u.cohort_enforcement import expected_profile_ids
from src.services.nfl_t5107u.eval_result_contract import (
    DEV437_RESULT_PATH,
    DEV437_RESULT_SHA256,
    DEV_IF437_BY_SEASON,
    DEV_IF437_N,
    DEV_MARKET72_BY_SEASON,
    DEV_MARKET72_N,
    INTERVAL_CONTRACT,
    MARKET72_RESULT_PATH,
    MARKET72_RESULT_SHA256,
    PROFILE_DEV_IF437,
    PROFILE_DEV_MARKET72,
    PROFILE_FEATURE_RECON_REG496,
    REG496_BY_SEASON,
    REG496_N,
    EvalResultContractRefuse,
    apply_eval_result_contract,
    join_market72_from_if437,
    refuse_synthetic_flag,
    validate_dev_if437,
    validate_eval_result_contract,
    validate_feature_recon_reg496,
    validate_market72_consistency,
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
DEV437_ARTIFACT = ROOT / DEV437_RESULT_PATH
MARKET72_ARTIFACT = ROOT / MARKET72_RESULT_PATH


def _reg_ids() -> list[str]:
    return expected_profile_ids(PROFILE_FEATURE_RECON_REG496, ROOT)


def _if437_ids() -> list[str]:
    return expected_profile_ids(PROFILE_DEV_IF437, ROOT)


def _market72_ids() -> list[str]:
    return expected_profile_ids(PROFILE_DEV_MARKET72, ROOT)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _if437() -> dict:
    return _load(DEV437_ARTIFACT)


def _market72_joined() -> dict:
    return join_market72_from_if437(_if437(), _load(MARKET72_ARTIFACT), expected_ids=_market72_ids())


def test_interval_contract_is_frozen_market72():
    assert INTERVAL_CONTRACT["B"] == 10000
    assert INTERVAL_CONTRACT["seed"] == 20261101
    assert INTERVAL_CONTRACT["rerun_intervals"] is False


def test_valid_original_496_437_72_artifacts_pass():
    assert sha256_file(REG_ARTIFACT) == FEATURE_RECON_REG496_ARTIFACT_SHA256
    assert sha256_file(DEV437_ARTIFACT) == DEV437_RESULT_SHA256
    assert sha256_file(MARKET72_ARTIFACT) == MARKET72_RESULT_SHA256
    recon = validate_profile_output(
        PROFILE_FEATURE_RECON_REG496, _load(REG_ARTIFACT), expected_ids=_reg_ids()
    )
    if437 = validate_profile_output(PROFILE_DEV_IF437, _if437(), expected_ids=_if437_ids())
    market72 = validate_profile_output(
        PROFILE_DEV_MARKET72, _market72_joined(), expected_ids=_market72_ids()
    )
    assert recon["ok"] is True
    assert recon["n"] == REG496_N
    assert recon["n_by_season"] == REG496_BY_SEASON
    assert if437["ok"] is True
    assert if437["n"] == DEV_IF437_N
    assert if437["n_by_season"] == DEV_IF437_BY_SEASON
    assert if437["market_unavailable"] is True
    assert market72["ok"] is True
    assert market72["n"] == DEV_MARKET72_N
    assert market72["n_by_season"] == DEV_MARKET72_BY_SEASON
    assert market72["joined_row_sha256"]


def test_feature_recon_reg496_lineage_and_completeness():
    payload = _load(REG_ARTIFACT)
    result = validate_feature_recon_reg496(payload, expected_ids=_reg_ids())
    assert result["ok"] is True
    assert result["invented_metrics"] is False
    assert result["w18_2021_retained"] == 16
    assert result["joined_row_sha256"]


def test_feature_recon_invented_metrics_fail():
    payload = dict(_load(REG_ARTIFACT))
    payload["mae_challenger"] = 3.14
    with pytest.raises(EvalResultContractRefuse, match="invented metric"):
        validate_feature_recon_reg496(payload, expected_ids=_reg_ids())


def test_feature_recon_inconsistent_counts_fail():
    payload = dict(_load(REG_ARTIFACT))
    payload["n"] = 495
    with pytest.raises(EvalResultContractRefuse, match="n=495"):
        validate_feature_recon_reg496(payload, expected_ids=_reg_ids())


def test_original_502_fails_reg_numerical_profile():
    assert sha256_file(ORIGINAL_502) == ORIGINAL_502_SHA256
    payload = _load(ORIGINAL_502)
    assert payload["n_complete_27"] == 502
    with pytest.raises(EvalResultContractRefuse, match="n=502 != 496"):
        validate_feature_recon_reg496(payload, expected_ids=_reg_ids())
    with pytest.raises(EvalResultContractRefuse, match="n=502 != 496"):
        validate_profile_output(PROFILE_FEATURE_RECON_REG496, payload, expected_ids=_reg_ids())


def test_dev_if437_published_marks_market_unavailable():
    payload = _if437()
    result = validate_dev_if437(payload, expected_ids=_if437_ids())
    assert result["market_unavailable"] is True
    assert result["cannot_satisfy_profile"] == PROFILE_DEV_MARKET72
    with pytest.raises(EvalResultContractRefuse, match="cannot satisfy|market unavailable|IF-only"):
        validate_eval_result_contract(payload)
    with pytest.raises(EvalResultContractRefuse, match="DEV_MARKET72|unavailable"):
        validate_profile_output(PROFILE_DEV_MARKET72, payload, expected_ids=_market72_ids())


def test_dev_if437_missing_unavailable_flag_fails():
    payload = dict(_if437())
    payload["market"] = {"status": "READY"}
    payload["market_unavailable"] = False
    payload["market_status"] = "READY"
    with pytest.raises(EvalResultContractRefuse, match="market unavailable"):
        validate_dev_if437(payload, expected_ids=_if437_ids())


def test_dev_market72_published_join_passes():
    payload = _market72_joined()
    result = validate_market72_consistency(payload, expected_ids=_market72_ids())
    assert result["ok"] is True
    stamped = apply_eval_result_contract(dict(payload))
    assert stamped["eval_result_contract"].endswith("v2")
    assert stamped["eval_result_sides"] == ["if", "market"]


def test_full_cohorts_plus_two_numerical_rows_fail():
    if437 = dict(_if437())
    if437["games"] = list(if437["games"][:2])
    if437["n"] = 2
    if437["n_by_season"] = {"2020": 1, "2021": 1}
    if437["game_ids"] = [row["game_id"] for row in if437["games"]]
    with pytest.raises(EvalResultContractRefuse, match="n=2 != profile expected 437|cohort IDs disagree"):
        validate_profile_output(PROFILE_DEV_IF437, if437, expected_ids=_if437_ids())

    joined = _market72_joined()
    slim = dict(joined)
    slim["games"] = list(joined["games"][:2])
    slim["n"] = 2
    slim["n_by_season"] = {"2020": 1, "2021": 1}
    slim["game_ids"] = [row["game_id"] for row in slim["games"]]
    with pytest.raises(EvalResultContractRefuse, match="n=2 != profile expected 72|cohort IDs disagree"):
        validate_profile_output(PROFILE_DEV_MARKET72, slim, expected_ids=_market72_ids())


def test_forged_synthetic_flag_fails_even_on_real_bytes():
    if437 = dict(_if437())
    if437["synthetic"] = True
    with pytest.raises(EvalResultContractRefuse, match="synthetic=true refused"):
        refuse_synthetic_flag(if437, label=PROFILE_DEV_IF437)
    with pytest.raises(EvalResultContractRefuse, match="synthetic=true refused"):
        validate_profile_output(PROFILE_DEV_IF437, if437, expected_ids=_if437_ids())

    market = dict(_load(MARKET72_ARTIFACT))
    market["synthetic"] = True
    with pytest.raises(EvalResultContractRefuse, match="synthetic=true refused"):
        join_market72_from_if437(_if437(), market, expected_ids=_market72_ids())

    recon = dict(_load(REG_ARTIFACT))
    recon["synthetic"] = True
    with pytest.raises(EvalResultContractRefuse, match="synthetic=true refused"):
        validate_profile_output(PROFILE_FEATURE_RECON_REG496, recon, expected_ids=_reg_ids())


def test_synthetic_helpers_are_refused_by_normal_validators():
    with pytest.raises(EvalResultContractRefuse, match="synthetic=true refused"):
        validate_dev_if437(build_synthetic_if437_result(), expected_ids=_if437_ids())
    with pytest.raises(EvalResultContractRefuse, match="synthetic=true refused"):
        validate_profile_output(
            PROFILE_DEV_MARKET72,
            build_synthetic_market72_result(),
            expected_ids=_market72_ids(),
        )


def test_mutated_real_metric_fails_and_does_not_rewrite():
    payload = dict(_if437())
    recorded = payload["mae_challenger"]
    payload["mae_challenger"] = recorded + 0.5
    with pytest.raises(EvalResultContractRefuse, match="inconsistent with saved rows"):
        validate_profile_output(PROFILE_DEV_IF437, payload, expected_ids=_if437_ids())
    assert payload["mae_challenger"] == recorded + 0.5

    market = _market72_joined()
    recorded_m = market["mae_market"]
    market["mae_market"] = recorded_m + 1.0
    with pytest.raises(EvalResultContractRefuse, match="inconsistent with saved rows"):
        validate_profile_output(PROFILE_DEV_MARKET72, market, expected_ids=_market72_ids())
    assert market["mae_market"] == recorded_m + 1.0


def test_missing_interval_field_fails():
    payload = copy.deepcopy(_if437())
    del payload["bootstrap_game"]["point"]
    with pytest.raises(EvalResultContractRefuse, match="requires point"):
        validate_profile_output(PROFILE_DEV_IF437, payload, expected_ids=_if437_ids())
    payload = copy.deepcopy(_if437())
    del payload["bootstrap_season_week"]
    with pytest.raises(EvalResultContractRefuse, match="missing IF-only fields|missing from result"):
        validate_profile_output(PROFILE_DEV_IF437, payload, expected_ids=_if437_ids())
    market = copy.deepcopy(_market72_joined())
    del market["bootstrap_game_vs_market"]["ci95"]
    with pytest.raises(EvalResultContractRefuse, match="requires ci95"):
        validate_profile_output(PROFILE_DEV_MARKET72, market, expected_ids=_market72_ids())


def test_missing_candidate_vs_market_fields_fail():
    payload = _market72_joined()
    row = dict(payload["games"][0])
    for key in ("m_market", "err_market", "L_market", "signed_diff_vs_market"):
        row.pop(key, None)
    payload["games"][0] = row
    with pytest.raises(EvalResultContractRefuse, match="missing candidate-vs-market"):
        validate_profile_output(PROFILE_DEV_MARKET72, payload, expected_ids=_market72_ids())


def test_null_nan_infinity_fail():
    payload = dict(_if437())
    payload["mae_if"] = None
    with pytest.raises(EvalResultContractRefuse, match="null"):
        validate_profile_output(PROFILE_DEV_IF437, payload, expected_ids=_if437_ids())
    payload = dict(_if437())
    payload["rmse_if"] = math.nan
    with pytest.raises(EvalResultContractRefuse, match="NaN"):
        validate_profile_output(PROFILE_DEV_IF437, payload, expected_ids=_if437_ids())
    payload = dict(_if437())
    payload["bias_challenger"] = math.inf
    with pytest.raises(EvalResultContractRefuse, match="not finite"):
        validate_profile_output(PROFILE_DEV_IF437, payload, expected_ids=_if437_ids())


def test_inconsistent_counts_fail():
    payload = dict(_if437())
    payload["n"] = payload["n"] + 1
    with pytest.raises(EvalResultContractRefuse, match="inconsistent counts"):
        validate_profile_output(PROFILE_DEV_IF437, payload, expected_ids=_if437_ids())


def test_interval_metadata_ordered_labeled_frozen():
    payload = copy.deepcopy(_if437())
    payload["bootstrap_game"]["ci95"] = [0.2, -0.2]
    with pytest.raises(EvalResultContractRefuse, match="not ordered"):
        validate_profile_output(PROFILE_DEV_IF437, payload, expected_ids=_if437_ids())
    payload = copy.deepcopy(_market72_joined())
    payload["bootstrap_game_vs_market"]["B"] = 999
    with pytest.raises(EvalResultContractRefuse, match="B is frozen"):
        validate_profile_output(PROFILE_DEV_MARKET72, payload, expected_ids=_market72_ids())
    payload = copy.deepcopy(_if437())
    payload["bootstrap_season_week"]["unit"] = "game"
    with pytest.raises(EvalResultContractRefuse, match="mislabeled unit"):
        validate_profile_output(PROFILE_DEV_IF437, payload, expected_ids=_if437_ids())


def test_payload_flag_cannot_disable_expected_ids():
    payload = dict(_if437())
    payload["synthetic"] = True
    payload["enforce_profile_n"] = False
    with pytest.raises(EvalResultContractRefuse, match="synthetic=true refused"):
        validate_profile_output(PROFILE_DEV_IF437, payload, expected_ids=_if437_ids()[:2])
    with pytest.raises(EvalResultContractRefuse, match="requires declared profile IDs"):
        validate_profile_output(PROFILE_DEV_IF437, _if437())


def test_profile_season_constants():
    assert DEV_IF437_BY_SEASON == {"2020": 210, "2021": 227}
    assert DEV_MARKET72_BY_SEASON == {"2020": 35, "2021": 37}
    assert not set(WILDCARD_2020_W18) & set(_load(REG_ARTIFACT)["game_ids"])
