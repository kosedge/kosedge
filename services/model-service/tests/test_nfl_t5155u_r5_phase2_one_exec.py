"""t5155u RETURN-FIX — R3 env-hash + Phase-2 one-exec proofs. CERT=0."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.services.nfl_t5107u.cohort_enforcement import OutcomeReadSpy
from src.services.nfl_t5107u.evaluator import BOOT_B, BOOT_SEED, MIN_N_REPORT
from src.services.nfl_t5107u.r5_496_freeze import freeze_q2_history_sources
from src.services.nfl_t5107u.r5_phase2_one_exec import (
    FORECASTS_SHA256,
    INTERSECTION_BYTES_SHA256,
    Phase2OneExecRefuse,
    load_committed_forecasts,
    run_phase2_one_exec,
    schedule_outcome_loader,
)
from src.services.nfl_t5107u.recon_driver import sha256_file, sha256_text
from src.services.nfl_t5107u.verify_integrate import FOCUSED_TESTS, strip_pytest_elapsed

ROOT = Path(__file__).resolve().parents[3]


def test_q2_history_env_hash_is_repo_relative_only():
    payload = freeze_q2_history_sources(ROOT)
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    assert "/tmp/" not in blob
    games = payload["score_sources"]["games_csv"]
    outcomes = payload["score_sources"]["outcomes_50bda875"]
    assert "present" not in games
    assert "present" not in outcomes
    assert games["path"].startswith("data/ops/")
    assert not games["path"].startswith("/")
    assert not outcomes["path"].startswith("/")
    assert games["sha256"].startswith("4fe1cdd7")
    assert outcomes["sha256"].startswith("50bda875")
    again = freeze_q2_history_sources(ROOT)
    assert sha256_text(json.dumps(payload, sort_keys=True, separators=(",", ":"))) == sha256_text(
        json.dumps(again, sort_keys=True, separators=(",", ":"))
    )


def test_committed_forecasts_never_regenerated():
    payload = load_committed_forecasts(ROOT)
    assert sha256_file(ROOT / "data/ops/nfl-t5155u-r5-496-freeze/FORECASTS_DEV_R5_496.json") == (
        FORECASTS_SHA256
    )
    assert payload["n_if_finite"] == 496
    assert payload["n_q2_hold"] == 496
    assert payload["n_candidate_finite"] == 0


def test_phase2_refusal_reads_zero_target_labels():
    spy = OutcomeReadSpy(lambda: {"2020_02_CIN_CLE": {"home_score": 40, "away_score": 0}})
    receipt = run_phase2_one_exec(
        root=ROOT,
        outcome_loader=spy,
        invoke_outcome_after_gates=False,
        write=False,
    )
    assert spy.reads == 0
    assert receipt["outcome_loader_reads"] == 0
    assert receipt["scored"] is None
    assert receipt["q2"] == "HOLD"
    assert receipt["forecasts_sha256"] == FORECASTS_SHA256
    assert receipt["cos_bind"] is False
    assert receipt["score_flag"] is False
    assert receipt["stop"] == "STOP_AWAITING_ALEX_RE_PREFLIGHT"


def test_phase2_positive_invokes_loader_once_if_only_and_market96():
    loader = OutcomeReadSpy(schedule_outcome_loader(ROOT))
    receipt = run_phase2_one_exec(
        root=ROOT,
        outcome_loader=loader,
        invoke_outcome_after_gates=True,
        write=False,
    )
    assert loader.reads == 1
    assert receipt["outcome_loader_reads"] == 1
    scored = receipt["scored"]
    assert scored["q2"] == "HOLD"
    assert scored["candidate"] == "HOLD"
    assert scored["regenerated_forecasts"] is False
    assert scored["forecasts_sha256"] == FORECASTS_SHA256
    for name, n in (("full496", 496), ("old437", 437), ("new59", 59)):
        body = scored["if_only"][name]
        assert body["n"] == n
        assert body["q2"] == "HOLD"
        assert body["candidate"] == "HOLD"
        assert body["mae_q2"] is None
        assert body["mae_candidate"] is None
        assert body["mae_if"] == pytest.approx(body["mae_if"])
        assert body["rmse_if"] >= 0
        assert isinstance(body["bias_if"], float)
    market = scored["market96"]
    assert market["n"] == 96
    assert market["bytes_sha256"] == INTERSECTION_BYTES_SHA256
    assert market["bytes_sha256"].startswith("072e99e0")
    assert market["bootstrap_game"]["B"] == BOOT_B == 10000
    assert market["bootstrap_game"]["seed"] == BOOT_SEED == 20261101
    assert market["bootstrap_season_week"]["B"] == BOOT_B
    assert market["n_clusters"] >= 1
    assert market["sparse_limits"]["n_lt_100"] is True
    assert market["reporting_class"] == "DESCRIPTIVE_ONLY"
    assert MIN_N_REPORT == 100
    assert market["nfl_green"] is False
    assert "GREEN" in market["n100_guidance"]
    assert sha256_file(ROOT / "data/ops/nfl-t5155u-r5-496-freeze/FORECASTS_DEV_R5_496.json") == (
        FORECASTS_SHA256
    )


def test_phase2_command_does_not_live_score():
    source = (
        ROOT / "scripts/nfl/run_nfl_t5155u_r5_phase2_one_exec.py"
    ).read_text(encoding="utf-8")
    assert "invoke_outcome_after_gates=False" in source
    assert "invoke_outcome_after_gates=True" not in source
    assert any(path.endswith("test_nfl_t5155u_r5_phase2_one_exec.py") for path in FOCUSED_TESTS)
    assert "in 4.86s" not in strip_pytest_elapsed("8 passed in 4.86s")


def test_positive_without_labels_refuses():
    spy = OutcomeReadSpy(lambda: {})
    with pytest.raises(Phase2OneExecRefuse, match="zero target labels"):
        run_phase2_one_exec(
            root=ROOT,
            outcome_loader=spy,
            invoke_outcome_after_gates=True,
            write=False,
        )
    assert spy.reads == 1
