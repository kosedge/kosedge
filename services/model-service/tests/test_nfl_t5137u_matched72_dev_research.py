"""t5137u matched72 DEV_RESEARCH persist — no EVAL, old 72 immutable."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from src.services.nfl_t5107u.dev_research import LABEL
from src.services.nfl_t5107u.dev_research_matched72 import (
    DEFAULT_DEST,
    MATCHED72_N,
    MATCHED72_PATH,
    PARENT_RECEIPT,
    REPORTING,
    SEALED_MARKET_BIAS,
    SEALED_MARKET_MAE,
    SEALED_MARKET_RMSE,
    SEALED_MATCHED72_SHA256,
    SEALED_PARENT_RECEIPT_SHA256,
    Matched72Refuse,
    build_matched72_dev_research_record,
    load_matched72_ids,
    validate_matched72_record,
)
from src.services.nfl_t5107u.metric_cohorts import DEV_METRIC_SPLIT
from src.services.nfl_t5107u.outcome_gate import (
    FIRST_CASE_FILE_SHA256,
    FIRST_CASE_GAME_ID,
    FIRST_CASE_RECORD_SHA256,
)
from src.services.nfl_t5107u.r2_market_e2e import (
    SEALED_CONSUME_SHA256,
    SEALED_MANIFEST_SHA256,
    SEALED_QUOTES_SHA256,
    MarketE2ERefuse,
    run_market_e2e,
    sha256_file,
)

ROOT = Path(__file__).resolve().parents[3]
R2A = ROOT / "data/ops/nfl-t5119u-r2-owned-coverage"
FIRST_CASE = ROOT / "data/ops/nfl-forecast-builder-t5107u/DEV_RESEARCH_t5119u_R2B.json"
DEV437 = ROOT / "data/ops/nfl-forecast-builder-t5107u/DEV_RESEARCH_t5125u_R2B2_437.json"
ONE_RUN = ROOT / "data/ops/nfl-forecast-builder-t5107u/ONE_RUN.json"
ONE_EXEC = ROOT / "data/ops/nfl-forecast-builder-t5107u/ONE_EXEC_RESULT_t5116u.json"
ONE_EXEC_MD = ROOT / "ops/CURSOR_ONE_EXEC_RESULT_t5116u.md"


def test_matched72_pin_and_not_94():
    ids = load_matched72_ids()
    assert len(ids) == MATCHED72_N
    assert len(set(ids)) == MATCHED72_N
    assert ids[0] == FIRST_CASE_GAME_ID
    assert ids[-1] == "2021_18_DAL_PHI"
    assert sha256_file(MATCHED72_PATH) == SEALED_MATCHED72_SHA256


def test_load_refuses_94_list(tmp_path: Path):
    dest = tmp_path / "ninety_four.json"
    dest.write_text(json.dumps([f"g{i}" for i in range(94)]) + "\n")
    with pytest.raises(Matched72Refuse, match="94-DEV"):
        load_matched72_ids(dest)


def test_load_refuses_wrong_n(tmp_path: Path):
    dest = tmp_path / "not72.json"
    dest.write_text(json.dumps(["2020_02_CIN_CLE"]) + "\n")
    with pytest.raises(Matched72Refuse, match="n=72"):
        load_matched72_ids(dest)


def test_explicit_dev_split_on_matched_call():
    ids = load_matched72_ids()
    record = run_market_e2e(split="dev_reg", eligible_ids=ids, emit_metrics=False)
    assert record["split"] == "dev_reg"
    assert record["eval"] is None
    assert record["eval_invoked"] is False
    assert record["eligible_n"] == 72
    assert record["joined_n"] == 72
    assert record["bind_ready"] is True


def test_refuses_overwrite_parent_receipt():
    with pytest.raises(Matched72Refuse, match="MARKET_E2E|preserved|parent"):
        build_matched72_dev_research_record(dest=PARENT_RECEIPT)


def test_refuses_overwrite_first_case():
    with pytest.raises(Matched72Refuse):
        build_matched72_dev_research_record(dest=FIRST_CASE)


def test_refuses_overwrite_dev437():
    with pytest.raises(Matched72Refuse, match="preserved|parent"):
        build_matched72_dev_research_record(dest=DEV437)


def test_run_market_e2e_refuses_parent_receipt_dest():
    with pytest.raises(MarketE2ERefuse, match="preserved"):
        run_market_e2e(
            split="dev_reg",
            eligible_ids=[FIRST_CASE_GAME_ID],
            emit_metrics=False,
            dest=PARENT_RECEIPT,
        )


def test_refuses_94_eligible_ids():
    with pytest.raises(Matched72Refuse, match="94-DEV"):
        build_matched72_dev_research_record(eligible_ids=[f"g{i}" for i in range(94)])


def test_old_receipts_and_r2a_immutable():
    assert sha256_file(PARENT_RECEIPT) == SEALED_PARENT_RECEIPT_SHA256
    assert hashlib.sha256(FIRST_CASE.read_bytes()).hexdigest() == FIRST_CASE_FILE_SHA256
    assert json.loads(FIRST_CASE.read_text())["record_sha256"] == FIRST_CASE_RECORD_SHA256
    assert hashlib.sha256(DEV437.read_bytes()).hexdigest() == (
        "66c3bde18fd6b1a4766f1001403deb68b9f625ccd00372f280f187ef95a54e50"
    )
    assert hashlib.sha256(ONE_RUN.read_bytes()).hexdigest() == (
        "96478f6b91fb12c6c9a0f3941870819cf3d9fa8da4804feecaf9650b7180cc7d"
    )
    assert hashlib.sha256(ONE_EXEC.read_bytes()).hexdigest() == (
        "913242590b43dc03f45b88ca970f39db5523e53e67983a65d599fb124adf81f6"
    )
    assert hashlib.sha256(ONE_EXEC_MD.read_bytes()).hexdigest() == (
        "be409f70ba94e48b21ad5e18a78d22f4264c70442538b4c8f2039b9695848df3"
    )
    assert sha256_file(R2A / "ADMISSIBLE_QUOTES.jsonl") == SEALED_QUOTES_SHA256
    assert sha256_file(R2A / "COVERAGE_MANIFEST.json") == SEALED_MANIFEST_SHA256
    assert sha256_file(R2A / "R2B_CONSUME.json") == SEALED_CONSUME_SHA256
    assert sha256_file(MATCHED72_PATH) == SEALED_MATCHED72_SHA256


def test_materialized_matched72_record_is_dev_reporting_reproduction():
    assert DEFAULT_DEST.is_file(), "t5137u persist must write DEV_RESEARCH_t5137u_MATCHED72.json"
    record = json.loads(DEFAULT_DEST.read_text(encoding="utf-8"))
    validate_matched72_record(record)
    assert record["label"] == LABEL
    assert record["metric_split"] == DEV_METRIC_SPLIT
    assert record["split"] == "dev_reg"
    assert record["cohort"] == "matched72"
    assert record["reporting"] == REPORTING
    assert "not independent confirmation" in record["reporting_disclosure"].lower()
    assert record["n"] == 72
    assert record["game_ids"] == load_matched72_ids()
    assert record["mae_market"] == SEALED_MARKET_MAE
    assert record["rmse_market"] == SEALED_MARKET_RMSE
    assert record["bias_market"] == SEALED_MARKET_BIAS
    assert record["mae_challenger"] is not None
    assert record["mae_if"] is not None
    assert record["mean_signed_diff_vs_if"] is not None
    assert record["mean_signed_diff_vs_market"] is not None
    assert record["delta_mae_vs_if"] is not None
    assert record["delta_mae_vs_market"] is not None
    assert record["bootstrap_game"]["B"] == 10000
    assert record["bootstrap_game"]["seed"] == 20261101
    assert record["bootstrap_season_week"]["B"] == 10000
    assert record["bootstrap_game_vs_market"]["seed"] == 20261101
    assert record["bootstrap_season_week_vs_market"]["seed"] == 20261101
    assert set(record["per_season"]) == {"2020", "2021"}
    assert record["eval"] is None
    assert record["eval_invoked"] is False
    assert record["one_run_claim"] is False
    assert record["not_normalized_94"] is True
    assert record["old_72_immutable"] is True
    assert record["parent_receipt"]["file_sha256"] == SEALED_PARENT_RECEIPT_SHA256
    assert record["g5_status"] == "DATA_COVERAGE_BLOCKED"
    # parent receipt bytes still the sealed market-only receipt
    parent = json.loads(PARENT_RECEIPT.read_text())
    assert set(parent["dev_matched_subset"]) == {
        "eligible_n",
        "joined_n",
        "bind_ready",
        "mae_market",
        "rmse_market",
        "bias_market",
    }
    assert "mae_challenger" not in parent["dev_matched_subset"]


def test_exclusive_create_refuses_second_write():
    if not DEFAULT_DEST.is_file():
        pytest.skip("matched72 record not materialized yet")
    with pytest.raises(Matched72Refuse, match="exists|exclusive"):
        build_matched72_dev_research_record(dest=DEFAULT_DEST)
