"""t5155u combine — pin Worker A freeze into B Phase 1. CERT=0. No Cos bind."""

from __future__ import annotations

from pathlib import Path

from src.services.nfl_t5107u.cohort_enforcement import OutcomeReadSpy
from src.services.nfl_t5107u.market_arm_freeze import (
    INTERSECTION_BYTES_SHA256,
    INTERSECTION_N,
    build_market_arm_freeze,
)
from src.services.nfl_t5107u.verify_integrate import (
    A_CANDIDATE_COMPLETED_SHA256,
    A_FORECASTS_SHA256,
    A_HISTORY_STAMP,
    A_HISTORY_TIP,
    A_IDENTITY_FREEZE_SHA256,
    A_MANIFEST_SHA256,
    A_Q2_COMPLETED_SHA256,
    FOCUSED_TESTS,
    REG496_IDENTITY_SHA256,
    REG496_SHA256,
    WORKER_A_COMMAND,
    WORKER_A_STAMP,
    WORKER_A_TIP,
    bind_worker_a_forecast_freeze,
    bind_worker_a_history_id,
)

ROOT = Path(__file__).resolve().parents[3]


def test_worker_a_bind_pins_hold_and_phase2_readiness_only():
    spy = OutcomeReadSpy(lambda: {"2020_02_CIN_CLE": {"home_score": 40, "away_score": 0}})
    bound = bind_worker_a_forecast_freeze(ROOT, outcome_loader=spy)
    assert bound["ok"] is True
    assert bound["status"] == "PINNED"
    assert bound["tip"] == WORKER_A_TIP
    assert bound["stamp"] == WORKER_A_STAMP
    assert bound["command"] == WORKER_A_COMMAND
    assert bound["identity_sha256"] == REG496_IDENTITY_SHA256
    assert bound["feature_json_sha256"] == REG496_SHA256
    assert bound["forecasts_sha256"] == A_FORECASTS_SHA256
    assert bound["freeze_manifest_sha256"] == A_MANIFEST_SHA256
    assert bound["n_if_finite"] == 496
    assert bound["n_q2_hold"] == 496
    assert bound["n_candidate_finite"] == 0
    assert bound["q2"]["status"] == "HOLD"
    assert bound["q2"]["hold_q2"] is True
    assert bound["q2"]["invented_q2"] is False
    assert bound["q2"]["years_unproven"] == [2013, 2014, 2015, 2016, 2017, 2018, 2019]
    assert "2013" in bound["q2"]["reason"] or "UNPROVEN" in bound["q2"]["reason"]
    assert bound["common437"] == {"n_common": 437, "n_replayed": 437, "n_blocker": 0}
    assert bound["phase2_positive_path"]["status"] == "READINESS_ONLY"
    assert bound["phase2_positive_path"]["executed"] is False
    assert bound["phase2_positive_path"]["cos_bind"] is False
    assert bound["phase2_positive_path"]["score_flag"] is False
    assert bound["phase2_positive_path"]["target_scoring_loader"] is False
    assert bound["phase2_positive_path"]["one_dev_diagnostic"] is False
    assert bound["phase2_positive_path"]["invoke_outcome_after_gates"] is False
    assert bound["phase2_positive_path"]["invoke_outcome_after_gates_available"] is True
    assert bound["cos_bind"] is False
    assert bound["scoring"] is None
    assert bound["eval"] is None
    assert bound["scoring_refuse"]["outcome_loader_reads"] == 0
    assert spy.reads == 0
    assert spy.ids_returned == []


def test_market_intersection_bytes_survive_worker_a_pin():
    bound = bind_worker_a_forecast_freeze(ROOT)
    payload = build_market_arm_freeze(root=ROOT, worker_a=bound)
    assert payload["intersection"]["n"] == INTERSECTION_N == 96
    assert payload["intersection"]["bytes_sha256"] == INTERSECTION_BYTES_SHA256
    assert payload["intersection"]["bytes_sha256"].startswith("072e99e0")
    assert payload["worker_a_forecast_freeze"]["status"] == "PINNED"
    assert payload["worker_a_forecast_freeze"]["q2"]["status"] == "HOLD"
    assert payload["scoring"] is None


def test_worker_a_history_id_completed_pins():
    spy = OutcomeReadSpy(lambda: {"2020_02_CIN_CLE": {"home_score": 40, "away_score": 0}})
    bound = bind_worker_a_history_id(ROOT, outcome_loader=spy)
    assert bound["ok"] is True
    assert bound["status"] == "COMPLETED"
    assert bound["tip"] == A_HISTORY_TIP
    assert bound["stamp"] == A_HISTORY_STAMP
    assert bound["if_forecasts_sha256"] == A_FORECASTS_SHA256
    assert bound["q2_completed_sha256"] == A_Q2_COMPLETED_SHA256
    assert bound["candidate_completed_sha256"] == A_CANDIDATE_COMPLETED_SHA256
    assert bound["identity_freeze_sha256"] == A_IDENTITY_FREEZE_SHA256
    assert bound["n_q2_finite"] == 496
    assert bound["n_candidate_finite"] == 496
    assert bound["n_q2_hold"] == 0
    assert bound["q2"] == "COMPLETED"
    assert bound["candidate"] == "COMPLETED"
    assert bound["initial_prior_2013"] is None
    assert bound["end_season_carry"] == 0.5
    assert bound["cos_bind"] is False
    assert bound["scoring"] is None
    assert spy.reads == 0


def test_one_command_does_not_score_or_bind_cos():
    source = (
        ROOT / "services/model-service/src/services/nfl_t5107u/verify_integrate.py"
    ).read_text(encoding="utf-8")
    command_fn = source.split("def run_one_command", 1)[1]
    assert "bind_worker_a_forecast_freeze" in command_fn
    assert "bind_worker_a_history_id" in command_fn
    assert "invoke_outcome_after_gates=True" not in command_fn
    assert "--score" not in command_fn
    assert "run_phase1_freeze" not in command_fn
    assert any(path.endswith("test_nfl_t5155u_r5_496_freeze.py") for path in FOCUSED_TESTS)
    assert any(path.endswith("test_nfl_t5155u_r5_combine.py") for path in FOCUSED_TESTS)
    assert any(path.endswith("test_nfl_t5157u_r5_history_id.py") for path in FOCUSED_TESTS)
