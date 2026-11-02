"""t5165u reporting addendum proofs. Does not invoke one-exec. CERT=0."""

from __future__ import annotations

from pathlib import Path

from src.services.nfl_t5107u.evaluator import BOOT_B, BOOT_SEED
from src.services.nfl_t5107u.r5_reporting_addendum import (
    EXEC_BIND_ID,
    EXEC_ONE_RUN_PATH,
    EXEC_ONE_RUN_SHA256,
    EXEC_RECEIPT_PATH,
    EXEC_RECEIPT_SHA256,
    build_reporting_addendum,
)
from src.services.nfl_t5107u.recon_driver import sha256_file

ROOT = Path(__file__).resolve().parents[3]
PHASE2 = ROOT / "services/model-service/src/services/nfl_t5107u/r5_phase2_one_exec.py"
REPORT = ROOT / "services/model-service/src/services/nfl_t5107u/r5_reporting_addendum.py"


def test_exec_artifacts_untouched():
    assert sha256_file(ROOT / EXEC_RECEIPT_PATH) == EXEC_RECEIPT_SHA256
    assert sha256_file(ROOT / EXEC_ONE_RUN_PATH) == EXEC_ONE_RUN_SHA256


def test_reporting_module_does_not_invoke_one_exec():
    src = REPORT.read_text(encoding="utf-8")
    assert "run_phase2_one_exec" not in src
    assert "schedule_outcome_loader" not in src
    assert "bind_one_run" not in src
    assert "claim_one_run" not in src
    assert "complete_one_run" not in src


def test_reporting_addendum_reconstructs_join_and_cites_exec():
    report = build_reporting_addendum(root=ROOT, write=False)
    assert report["new_scientific_look"] is False
    assert report["kind"] == "reporting_reconstruction"
    assert report["joined_n"] == 496
    assert report["joined_not_persisted_at_exec"] is True
    assert report["exec_bind_id"] == EXEC_BIND_ID
    assert report["exec_receipt_sha256"] == EXEC_RECEIPT_SHA256
    assert report["consistency"]["old_plus_new"] == 496
    assert report["consistency"]["mae_if_matches_exec_receipt"] is True
    for name, n in (("full496", 496), ("old437", 437), ("new59", 59)):
        body = report["if_q2_candidate"][name]
        assert body["n"] == n
        assert body["finite"] is True
        assert body["n_clusters"] >= 1
        assert "per_season" in body
        assert set(body["per_season"]) == {"2020", "2021"}
        boot = body["candidate_minus_if"]["bootstrap_game"]
        assert boot["B"] == BOOT_B == 10000
        assert boot["seed"] == BOOT_SEED == 20261101
        assert body["cited_exec_overall"]["path"] == EXEC_RECEIPT_PATH
        assert body["cited_exec_overall"]["sha256"] == EXEC_RECEIPT_SHA256
        assert body["cited_exec_overall"]["n"] == n
    market = report["market96"]
    assert market["n"] == 96
    assert market["reporting_class"] == "DESCRIPTIVE_ONLY"
    assert market["sparse_limits"]["n_lt_100"] is True
    assert market["nfl_green"] is False
    assert "mae_if" in market["per_season"]["2020"]
    assert market["candidate_minus_if_market96"]["bootstrap_game"]["B"] == BOOT_B
    cited = market["cited_from_exec_receipt"]
    assert cited["sha256"] == EXEC_RECEIPT_SHA256
    assert cited["bootstrap_game"]["B"] == BOOT_B
    assert "code_sha256" in report["hashes"]
    assert "input_sha256" in report["hashes"]
    assert "join_sha256" in report["hashes"]
    assert "output_sha256" in report["hashes"]
    assert sha256_file(ROOT / EXEC_RECEIPT_PATH) == EXEC_RECEIPT_SHA256
    assert sha256_file(ROOT / EXEC_ONE_RUN_PATH) == EXEC_ONE_RUN_SHA256
    assert PHASE2.is_file()
