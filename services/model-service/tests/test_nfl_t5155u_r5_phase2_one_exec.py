"""t5155u / t5160u loader-boundary proofs. Synthetic only. CERT=0."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from src.services.nfl_t5107u.cohort_enforcement import OutcomeReadSpy
from src.services.nfl_t5107u.evaluator import BOOT_B, BOOT_SEED, MIN_N_REPORT
from src.services.nfl_t5107u.last_played_cohort import SCHEDULE_PATH
from src.services.nfl_t5107u.one_run import STATUS_BOUND, STATUS_CONSUMED, bind_one_run, load_one_run
from src.services.nfl_t5107u.r5_496_freeze import freeze_q2_history_sources
from src.services.nfl_t5107u.r5_phase2_one_exec import (
    CANDIDATE_COMPLETED_SHA256,
    FORECASTS_SHA256,
    IDENTITY_FREEZE_SHA256,
    INTERSECTION_BYTES_SHA256,
    OWNER_T5160U,
    PROTOCOL_DEVIATION_PATH,
    Q2_COMPLETED_SHA256,
    Q2_HISTORY_SHA256,
    REG496_IDENTITY_SHA256,
    SUPERSEDED_COS_ONE_DEV_ORDER,
    Phase2OneExecRefuse,
    bind_phase2_one_exec_fixture,
    mark_test_synthetic,
    load_committed_forecasts,
    load_completed_forecasts,
    run_phase2_one_exec,
    runner_code_hashes,
    runner_code_sha256,
    runner_input_sha256,
    runner_spec_sha256,
    schedule_outcome_loader,
    synthetic_outcome_loader,
)
from src.services.nfl_t5107u.recon_driver import sha256_file, sha256_text
from src.services.nfl_t5107u.verify_integrate import FOCUSED_TESTS, strip_pytest_elapsed

ROOT = Path(__file__).resolve().parents[3]
PHASE2_TEST = ROOT / "services/model-service/tests/test_nfl_t5155u_r5_phase2_one_exec.py"
CLI = ROOT / "scripts/nfl/run_nfl_t5155u_r5_phase2_one_exec.py"
VERIFY = ROOT / "services/model-service/src/services/nfl_t5107u/verify_integrate.py"


def _cli_main():
    spec = importlib.util.spec_from_file_location("phase2_cli_r2", CLI)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.main


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
    assert Q2_HISTORY_SHA256.startswith("07bbc340")


def test_committed_forecasts_never_regenerated():
    payload = load_committed_forecasts(ROOT)
    assert sha256_file(ROOT / "data/ops/nfl-t5155u-r5-496-freeze/FORECASTS_DEV_R5_496.json") == (
        FORECASTS_SHA256
    )
    assert payload["n_if_finite"] == 496
    assert payload["n_q2_hold"] == 496
    assert payload["n_candidate_finite"] == 0


def test_completed_q2_candidate_pins_copy_if496():
    payload = load_completed_forecasts(ROOT)
    assert payload["if_forecasts_sha256"] == FORECASTS_SHA256
    assert payload["if_regenerated"] is False
    assert payload["n_q2_finite"] == 496
    assert payload["n_q2_hold"] == 0
    assert payload["n_candidate_finite"] == 496
    assert payload["initial_prior_2013"] is None
    assert payload["candidate"] == "0.5*IF+0.5*Q2"
    assert sha256_file(ROOT / "data/ops/nfl-t5157u-r5-history-id/Q2_COMPLETED_FREEZE.json") == (
        Q2_COMPLETED_SHA256
    )
    assert sha256_file(
        ROOT / "data/ops/nfl-t5157u-r5-history-id/CANDIDATE_COMPLETED_FREEZE.json"
    ) == CANDIDATE_COMPLETED_SHA256
    assert sha256_file(ROOT / "data/ops/nfl-t5157u-r5-history-id/IDENTITY_FREEZE.json") == (
        IDENTITY_FREEZE_SHA256
    )


@pytest.mark.parametrize("invoke", [False, True])
def test_unbound_spy_refuses_zero_reads(invoke):
    spy = OutcomeReadSpy(lambda: {"2020_02_CIN_CLE": {"home_score": 40, "away_score": 0}})
    with pytest.raises(Phase2OneExecRefuse, match="unbound outcome_loader / invoke"):
        run_phase2_one_exec(
            root=ROOT,
            outcome_loader=spy,
            invoke_outcome_after_gates=invoke,
            write=False,
        )
    assert spy.reads == 0


@pytest.mark.parametrize("invoke", [False, True])
def test_unbound_bare_callable_refuses_zero_reads(invoke):
    reads = {"n": 0}

    def bare():
        reads["n"] += 1
        return {"2020_02_CIN_CLE": {"home_score": 40, "away_score": 0}}

    with pytest.raises(Phase2OneExecRefuse, match="unbound outcome_loader / invoke"):
        run_phase2_one_exec(
            root=ROOT,
            outcome_loader=bare,
            invoke_outcome_after_gates=invoke,
            write=False,
        )
    assert reads["n"] == 0


def test_unbound_invoke_without_loader_refuses():
    with pytest.raises(Phase2OneExecRefuse, match="unbound outcome_loader / invoke"):
        run_phase2_one_exec(
            root=ROOT,
            invoke_outcome_after_gates=True,
            write=False,
        )


def test_phase2_refusal_reads_zero_target_labels():
    receipt = run_phase2_one_exec(root=ROOT, write=False)
    assert receipt["outcome_loader_reads"] == 0
    assert receipt["scored"] is None
    assert receipt["q2"] == "COMPLETED"
    assert receipt["candidate"] == "COMPLETED"
    assert receipt["forecasts_sha256"] == FORECASTS_SHA256
    assert receipt["q2_completed_sha256"] == Q2_COMPLETED_SHA256
    assert receipt["candidate_completed_sha256"] == CANDIDATE_COMPLETED_SHA256
    assert receipt["identity_freeze_sha256"] == IDENTITY_FREEZE_SHA256
    assert receipt["n_q2_finite"] == 496
    assert receipt["n_candidate_finite"] == 496
    assert receipt["cos_bind"] is False
    assert receipt["score_flag"] is False
    assert receipt["stop"] == "STOP_AWAITING_ALEX_COMPLETED_CANDIDATE_PREFLIGHT"
    assert receipt["q2_history_sha256"].startswith("07bbc340")
    assert receipt["freeze_manifest_sha256"].startswith("36f051c4")
    assert receipt["runner_code_sha256"] == runner_code_sha256(ROOT)
    assert set(receipt["runner_code_hashes"]) == set(runner_code_hashes(ROOT))
    assert receipt["owner_t5160u"] == OWNER_T5160U
    assert receipt["superseded_cos_one_dev_order"] == SUPERSEDED_COS_ONE_DEV_ORDER
    assert receipt["protocol_deviation_path"] == PROTOCOL_DEVIATION_PATH
    assert receipt["one_run_bind_id"] is None
    assert receipt["one_run_status"] is None


def test_phase2_positive_invokes_loader_once_if_only_and_market96(tmp_path):
    bind_phase2_one_exec_fixture(path=tmp_path / "ONE_RUN.json", root=ROOT)
    loader = OutcomeReadSpy(synthetic_outcome_loader(root=ROOT))
    receipt = run_phase2_one_exec(
        root=ROOT,
        outcome_loader=loader,
        cos_bind_path=tmp_path / "ONE_RUN.json",
        score_flag=True,
        write=False,
    )
    assert loader.reads == 1
    assert receipt["outcome_loader_reads"] == 1
    scored = receipt["scored"]
    assert scored["q2"] == "COMPLETED"
    assert scored["candidate"] == "COMPLETED"
    assert scored["regenerated_forecasts"] is False
    assert scored["forecasts_sha256"] == FORECASTS_SHA256
    assert scored["q2_completed_sha256"] == Q2_COMPLETED_SHA256
    assert scored["candidate_completed_sha256"] == CANDIDATE_COMPLETED_SHA256
    for name, n in (("full496", 496), ("old437", 437), ("new59", 59)):
        body = scored["if_only"][name]
        assert body["n"] == n
        assert body["q2"] == "COMPLETED"
        assert body["candidate"] == "COMPLETED"
        assert body["mae_q2"] == pytest.approx(body["mae_q2"])
        assert body["mae_candidate"] == pytest.approx(body["mae_candidate"])
        assert body["rmse_q2"] >= 0
        assert body["rmse_candidate"] >= 0
        assert body["mae_if"] == pytest.approx(body["mae_if"])
        assert body["rmse_if"] >= 0
        assert isinstance(body["bias_if"], float)
        assert isinstance(body["bias_q2"], float)
        assert isinstance(body["bias_candidate"], float)
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
    assert market["q2"] == "COMPLETED"
    assert market["candidate"] == "COMPLETED"
    assert isinstance(market["mean_signed_diff_candidate_vs_market"], float)
    assert market["bootstrap_game_candidate"]["B"] == BOOT_B
    assert sha256_file(ROOT / "data/ops/nfl-t5155u-r5-496-freeze/FORECASTS_DEV_R5_496.json") == (
        FORECASTS_SHA256
    )
    assert receipt["cos_bind"] is True
    assert receipt["runner_code_sha256"] == runner_code_sha256(ROOT)
    assert receipt["owner_t5160u"] == OWNER_T5160U
    assert receipt["superseded_cos_one_dev_order"] == SUPERSEDED_COS_ONE_DEV_ORDER


def test_phase2_command_does_not_live_score():
    source = CLI.read_text(encoding="utf-8")
    assert "invoke_outcome_after_gates=False" in source
    assert "invoke_outcome_after_gates=True" not in source
    assert "--cos-bind" in source
    assert "unbound --score refused" in source
    assert any(path.endswith("test_nfl_t5155u_r5_phase2_one_exec.py") for path in FOCUSED_TESTS)
    assert "in 4.86s" not in strip_pytest_elapsed("8 passed in 4.86s")


def test_focused_tests_do_not_call_real_schedule_loader():
    test_src = PHASE2_TEST.read_text(encoding="utf-8")
    pos = test_src.split("def test_phase2_positive_invokes_loader_once", 1)[1]
    pos = pos.split("\ndef test_", 1)[0]
    assert "schedule_outcome_loader" not in pos
    assert "synthetic_outcome_loader" in pos
    command_fn = VERIFY.read_text(encoding="utf-8").split("def run_one_command", 1)[1]
    assert "schedule_outcome_loader" not in command_fn
    assert "invoke_outcome_after_gates=True" not in command_fn


def _count_schedule_opens(monkeypatch) -> list[str]:
    opens: list[str] = []
    real_open = Path.open

    def spy_open(self: Path, *args, **kwargs):
        text = self.as_posix()
        if SCHEDULE_PATH.split("/")[-1] in text or "schedule_results_2020_2023" in text:
            opens.append(text)
        return real_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", spy_open)
    return opens


def test_direct_real_loader_refuses_without_claimed_bind_zero_reads(monkeypatch):
    opens = _count_schedule_opens(monkeypatch)
    monkeypatch.setenv("T5157U_ALLOW_REAL_LOADER", "1")
    monkeypatch.delenv("T5151U_SKIP_NESTED_TESTS", raising=False)
    with pytest.raises(Phase2OneExecRefuse, match="claimed bind"):
        schedule_outcome_loader(ROOT)
    assert opens == []


def test_nested_env_cannot_authorize_real_loader(monkeypatch):
    opens = _count_schedule_opens(monkeypatch)
    monkeypatch.setenv("T5151U_SKIP_NESTED_TESTS", "1")
    monkeypatch.setenv("T5157U_ALLOW_REAL_LOADER", "1")
    with pytest.raises(Phase2OneExecRefuse, match="claimed bind"):
        schedule_outcome_loader(ROOT, claimed_bind={"status": "IN_PROGRESS", "bind_id": "x"})
    assert opens == []


def test_forged_claimed_bind_without_record_zero_reads(tmp_path, monkeypatch):
    opens = _count_schedule_opens(monkeypatch)
    with pytest.raises(Phase2OneExecRefuse, match="claimed bind|missing one-run"):
        schedule_outcome_loader(
            ROOT,
            claimed_bind={"status": "IN_PROGRESS", "bind_id": "forged"},
            bind_path=tmp_path / "ONE_RUN.json",
        )
    assert opens == []


def test_unclaimed_matching_bind_refuses_real_loader_zero_reads(tmp_path, monkeypatch):
    opens = _count_schedule_opens(monkeypatch)
    bind = bind_phase2_one_exec_fixture(path=tmp_path / "ONE_RUN.json", root=ROOT)
    assert bind["status"] == STATUS_BOUND
    with pytest.raises(Phase2OneExecRefuse, match="not claimed"):
        schedule_outcome_loader(
            ROOT,
            claimed_bind=bind,
            bind_path=tmp_path / "ONE_RUN.json",
        )
    assert opens == []


def test_unbound_default_api_zero_real_schedule_reads(monkeypatch):
    calls: list[object] = []

    def boom(*_a, **_k):
        calls.append(1)
        raise AssertionError("real schedule_outcome_loader must not run unbound")

    monkeypatch.setattr(
        "src.services.nfl_t5107u.r5_phase2_one_exec.schedule_outcome_loader",
        boom,
    )
    receipt = run_phase2_one_exec(root=ROOT, write=False)
    assert receipt["outcome_loader_reads"] == 0
    assert receipt["scored"] is None
    assert receipt["cos_bind"] is False
    assert receipt["owner_t5160u"] == OWNER_T5160U
    assert calls == []


def test_positive_synthetic_does_not_call_real_schedule_loader(tmp_path, monkeypatch):
    calls: list[object] = []

    def boom(*_a, **_k):
        calls.append(1)
        raise AssertionError("positive API hook must stay synthetic")

    monkeypatch.setattr(
        "src.services.nfl_t5107u.r5_phase2_one_exec.schedule_outcome_loader",
        boom,
    )
    bind_phase2_one_exec_fixture(path=tmp_path / "ONE_RUN.json", root=ROOT)
    loader = OutcomeReadSpy(synthetic_outcome_loader(root=ROOT))
    receipt = run_phase2_one_exec(
        root=ROOT,
        outcome_loader=loader,
        cos_bind_path=tmp_path / "ONE_RUN.json",
        score_flag=True,
        write=False,
    )
    assert loader.reads == 1
    assert receipt["outcome_loader_reads"] == 1
    assert receipt["scored"]["if_only"]["full496"]["n"] == 496
    assert calls == []


def test_positive_without_labels_refuses(tmp_path):
    bind_phase2_one_exec_fixture(path=tmp_path / "ONE_RUN.json", root=ROOT)
    spy = mark_test_synthetic(OutcomeReadSpy(lambda: {}))
    with pytest.raises(Phase2OneExecRefuse, match="zero target labels"):
        run_phase2_one_exec(
            root=ROOT,
            outcome_loader=spy,
            cos_bind_path=tmp_path / "ONE_RUN.json",
            score_flag=True,
            write=False,
        )
    assert spy.reads == 1


def test_bound_unmarked_caller_loader_refuses_zero_reads(tmp_path):
    bind = bind_phase2_one_exec_fixture(path=tmp_path / "ONE_RUN.json", root=ROOT)
    spy = OutcomeReadSpy(lambda: {"2020_02_CIN_CLE": {"home_score": 40, "away_score": 0}})
    with pytest.raises(Phase2OneExecRefuse, match="test-only synthetic marker"):
        run_phase2_one_exec(
            root=ROOT,
            outcome_loader=spy,
            cos_bind_path=tmp_path / "ONE_RUN.json",
            score_flag=True,
            write=False,
        )
    assert spy.reads == 0
    assert load_one_run(tmp_path / "ONE_RUN.json")["status"] == bind["status"] == STATUS_BOUND


def test_unbound_score_refuses_zero_reads():
    spy = OutcomeReadSpy(synthetic_outcome_loader(root=ROOT))
    with pytest.raises(Phase2OneExecRefuse, match="unbound --score"):
        run_phase2_one_exec(
            root=ROOT,
            outcome_loader=spy,
            score_flag=True,
            write=False,
        )
    assert spy.reads == 0


def test_cli_unbound_score_refuses_zero_reads(capsys):
    main = _cli_main()
    assert main(["--score"]) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["refused"] is True
    assert payload["outcome_loader_reads"] == 0
    assert main(["--eval"]) == 2
    assert main(["--cos-bind", "/tmp/no-bind.json"]) == 2


def test_cos_bind_pin_mismatch_refuses_zero_reads(tmp_path):
    bind_one_run(
        effective_spec_sha256="1" * 64,
        code_sha256="2" * 64,
        input_sha256="3" * 64,
        forecast_sha256=FORECASTS_SHA256,
        cohort_sha256=REG496_IDENTITY_SHA256,
        alex_go_id="ALEX_RETURN_42069EF6",
        path=tmp_path / "ONE_RUN.json",
    )
    with pytest.raises(Phase2OneExecRefuse, match="cos-bind refused"):
        run_phase2_one_exec(
            root=ROOT,
            cos_bind_path=tmp_path / "ONE_RUN.json",
            score_flag=True,
            write=False,
        )
    assert load_one_run(tmp_path / "ONE_RUN.json")["status"] == STATUS_BOUND


def test_cos_bind_fixture_claims_once_then_refuses_second(tmp_path):
    bind = bind_phase2_one_exec_fixture(path=tmp_path / "ONE_RUN.json", root=ROOT)
    assert bind["forecast_sha256"] == FORECASTS_SHA256
    assert bind["code_sha256"] == runner_code_sha256(ROOT)
    assert bind["input_sha256"] == runner_input_sha256()
    assert bind["effective_spec_sha256"] == runner_spec_sha256()
    spy = OutcomeReadSpy(synthetic_outcome_loader(root=ROOT))
    receipt = run_phase2_one_exec(
        root=ROOT,
        outcome_loader=spy,
        cos_bind_path=tmp_path / "ONE_RUN.json",
        score_flag=True,
        write=False,
    )
    assert spy.reads == 1
    assert receipt["outcome_loader_reads"] == 1
    assert receipt["cos_bind"] is True
    assert receipt["score_flag"] is True
    assert receipt["q2"] == "COMPLETED"
    assert receipt["candidate"] == "COMPLETED"
    assert receipt["one_run_bind_id"] == bind["bind_id"]
    assert receipt["one_run_status"] == STATUS_CONSUMED
    assert receipt["runner_code_sha256"] == runner_code_sha256(ROOT)
    assert receipt["hashes"]["runner_code_sha256"] == receipt["runner_code_sha256"]
    assert receipt["scored"]["if_only"]["full496"]["n"] == 496
    assert receipt["scored"]["market96"]["n"] == 96
    assert receipt["scored"]["q2"] == "COMPLETED"
    assert load_one_run(tmp_path / "ONE_RUN.json")["status"] == STATUS_CONSUMED

    spy2 = OutcomeReadSpy(synthetic_outcome_loader(root=ROOT))
    with pytest.raises(Phase2OneExecRefuse, match="cos-bind refused"):
        run_phase2_one_exec(
            root=ROOT,
            outcome_loader=spy2,
            cos_bind_path=tmp_path / "ONE_RUN.json",
            score_flag=True,
            write=False,
        )
    assert spy2.reads == 0
