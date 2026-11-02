"""t5168u market96 MARKET schema correction. No one-exec. CERT=0."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.services.nfl_t5107u.market_arm_freeze import INTERSECTION_N
from src.services.nfl_t5107u.r5_market96_schema_correction import (
    ADDENDUM_REPORT_PATH,
    ADDENDUM_REPORT_SHA256,
    JOINED_PATH,
    JOINED_SHA256,
    OWNER_MARKET,
    Market96SchemaRefuse,
    build_market96_schema_correction,
    select_market96,
)
from src.services.nfl_t5107u.r5_reporting_addendum import (
    EXEC_ONE_RUN_PATH,
    EXEC_ONE_RUN_SHA256,
    EXEC_RECEIPT_PATH,
    EXEC_RECEIPT_SHA256,
)
from src.services.nfl_t5107u.recon_driver import sha256_file

ROOT = Path(__file__).resolve().parents[3]
CORR = ROOT / "services/model-service/src/services/nfl_t5107u/r5_market96_schema_correction.py"


def _frozen_rows() -> list[dict]:
    return json.loads((ROOT / JOINED_PATH).read_text(encoding="utf-8"))["rows"]


def test_frozen_exec_and_addendum_bytes_stand():
    assert sha256_file(ROOT / EXEC_RECEIPT_PATH) == EXEC_RECEIPT_SHA256
    assert sha256_file(ROOT / EXEC_ONE_RUN_PATH) == EXEC_ONE_RUN_SHA256
    assert sha256_file(ROOT / JOINED_PATH) == JOINED_SHA256
    assert sha256_file(ROOT / ADDENDUM_REPORT_PATH) == ADDENDUM_REPORT_SHA256


def test_correction_module_does_not_invoke_one_exec():
    src = CORR.read_text(encoding="utf-8")
    assert "run_phase2_one_exec" not in src
    assert "schedule_outcome_loader" not in src
    assert "bind_one_run" not in src
    assert "claim_one_run" not in src
    assert "complete_one_run" not in src


def test_market96_schema_matches_owner_citation():
    report = build_market96_schema_correction(root=ROOT, write=False)
    assert report["new_scientific_look"] is False
    assert report["arms"] == ["candidate", "IF", "MARKET"]
    assert report["q2_role"] == "diagnostic_only_not_market_substitute"
    market = report["market96"]
    assert market["n"] == INTERSECTION_N == 96
    assert market["mae_market"] == OWNER_MARKET["overall"]["mae_market"]
    assert market["rmse_market"] == OWNER_MARKET["overall"]["rmse_market"]
    assert market["bias_market"] == OWNER_MARKET["overall"]["bias_market"]
    for season in ("2020", "2021"):
        body = market["per_season"][season]
        exp = OWNER_MARKET[season]
        assert body["n"] == exp["n"]
        assert body["mae_market"] == exp["mae_market"]
        assert body["rmse_market"] == exp["rmse_market"]
        assert body["bias_market"] == exp["bias_market"]
        assert "mae_if" in body and "mae_candidate" in body
    assert "mae_if" in market and "mae_candidate" in market
    assert market["paired_cited_from_exec_receipt"]["sha256"] == EXEC_RECEIPT_SHA256
    assert sha256_file(ROOT / JOINED_PATH) == JOINED_SHA256
    assert sha256_file(ROOT / EXEC_RECEIPT_PATH) == EXEC_RECEIPT_SHA256


def test_missing_market_margin_fails():
    rows = _frozen_rows()
    hit = next(row for row in rows if row.get("in_market96"))
    hit.pop("market_home_margin")
    with pytest.raises(Market96SchemaRefuse, match="missing market_home_margin"):
        select_market96(rows)


def test_nonfinite_market_error_fails():
    rows = _frozen_rows()
    hit = next(row for row in rows if row.get("in_market96"))
    hit["market_home_margin"] = float("nan")
    with pytest.raises(Market96SchemaRefuse, match="nonfinite market error"):
        select_market96(rows)


def test_wrong_market_cohort_fails():
    rows = [row for row in _frozen_rows() if row.get("in_market96")][:95]
    with pytest.raises(Market96SchemaRefuse, match="wrong market cohort"):
        select_market96(rows)
