"""t5153u Package C — real-artifact command wiring, spies, R1 hashes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.services.nfl_t5107u.cohort_enforcement import (
    DEV_IF437_IDENTITY_SHA256,
    FEATURE_RECON_REG496_ARTIFACT_PATH as A_REG_PATH,
    FEATURE_RECON_REG496_ARTIFACT_SHA256 as A_REG_SHA,
    REG496_IDENTITY_SHA256,
    CohortEnforcementRefuse,
    check_cohort_before_feature_output_finalization,
    check_cohort_before_target_outcome_loading,
    expected_profile_ids,
)
from src.services.nfl_t5107u.eval_result_contract import (
    DEV437_RESULT_PATH,
    DEV437_RESULT_SHA256,
    MARKET72_RESULT_PATH,
    MARKET72_RESULT_SHA256,
    PROFILE_DEV_IF437,
    PROFILE_DEV_MARKET72,
    PROFILE_FEATURE_RECON_REG496,
    EvalResultContractRefuse,
    join_market72_from_if437,
)
from src.services.nfl_t5107u.last_played_cohort import ORIGINAL_502_PATH, ORIGINAL_502_SHA256
from src.services.nfl_t5107u.recon_driver import sha256_file
from src.services.nfl_t5107u.verify_integrate import (
    FEATURE_RECON_REG496_ARTIFACT_PATH,
    FEATURE_RECON_REG496_ARTIFACT_SHA256,
    PROTECTED_ORIGINALS,
    CohortHooks,
    OutcomeReadSpy,
    build_receipt,
    build_synthetic_if437_result,
    build_synthetic_market72_result,
    guarded_finalize_feature_output,
    hash_file_list,
    repo_relative_posix,
    require_cohort_hooks,
    run_scoped_research_verify,
    try_load_cohort_module,
    verify_pinned_artifacts,
)

ROOT = Path(__file__).resolve().parents[3]


def _load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def _reg_ids() -> list[str]:
    return expected_profile_ids(PROFILE_FEATURE_RECON_REG496, ROOT)


def _if437_ids() -> list[str]:
    return expected_profile_ids(PROFILE_DEV_IF437, ROOT)


def _market72_ids() -> list[str]:
    return expected_profile_ids(PROFILE_DEV_MARKET72, ROOT)


def _a_hooks() -> CohortHooks:
    return require_cohort_hooks()


def _if437_payload() -> dict:
    return _load(DEV437_RESULT_PATH)


def _market72_joined() -> dict:
    return join_market72_from_if437(
        _if437_payload(), _load(MARKET72_RESULT_PATH), expected_ids=_market72_ids()
    )


def test_pinned_real_496_437_72_and_502_bytes():
    pins = verify_pinned_artifacts(ROOT)
    names = {row["name"]: row for row in pins["checks"]}
    assert names["FEATURE_RECON_REG496"]["ok"] is True
    assert names["ORIGINAL_502_HISTORICAL"]["ok"] is True
    assert names["DEV437_RESULT_66c3bde1"]["ok"] is True
    assert names["MATCHED72_RESULT_316345fa"]["ok"] is True
    assert names["FEATURE_RECON_REG496"]["sha256"] == FEATURE_RECON_REG496_ARTIFACT_SHA256
    assert names["DEV437_RESULT_66c3bde1"]["sha256"] == DEV437_RESULT_SHA256
    assert names["MATCHED72_RESULT_316345fa"]["sha256"] == MARKET72_RESULT_SHA256
    assert names["FEATURE_RECON_REG496"]["path"] == FEATURE_RECON_REG496_ARTIFACT_PATH
    assert not names["DEV437_RESULT_66c3bde1"]["path"].startswith("/")


def test_real_437_and_72_through_scoped_caller():
    spy = OutcomeReadSpy(lambda: {"SHOULD_NOT_LOAD": {"home_score": 99}})
    hooks = _a_hooks()
    if_body = run_scoped_research_verify(
        PROFILE_DEV_IF437,
        _if437_payload(),
        _if437_ids(),
        hooks=hooks,
        outcome_loader=spy,
        joined_ids=_if437_ids(),
        candidate_bytes_sha=DEV437_RESULT_SHA256,
        expected_bytes_sha=DEV437_RESULT_SHA256,
        root=ROOT,
    )
    mkt = run_scoped_research_verify(
        PROFILE_DEV_MARKET72,
        _market72_joined(),
        _market72_ids(),
        hooks=hooks,
        outcome_loader=spy,
        joined_ids=_market72_ids(),
        candidate_bytes_sha=MARKET72_RESULT_SHA256,
        expected_bytes_sha=MARKET72_RESULT_SHA256,
        root=ROOT,
    )
    assert if_body["ok"] is True
    assert if_body["numerical"]["n"] == 437
    assert if_body["feature_gate"]["identity_sha256"] == DEV_IF437_IDENTITY_SHA256
    assert mkt["numerical"]["n"] == 72
    assert spy.reads == 0
    assert if_body["real_eval_executed"] is False


def test_scoped_caller_recon_never_reads_outcomes():
    payload = _load(FEATURE_RECON_REG496_ARTIFACT_PATH)
    spy = OutcomeReadSpy(lambda: {"2020_02_ATL_DAL": {"home_score": 24, "away_score": 21}})
    result = run_scoped_research_verify(
        PROFILE_FEATURE_RECON_REG496,
        payload,
        _reg_ids(),
        hooks=_a_hooks(),
        outcome_loader=spy,
        candidate_bytes_sha=sha256_file(ROOT / FEATURE_RECON_REG496_ARTIFACT_PATH),
        expected_bytes_sha=FEATURE_RECON_REG496_ARTIFACT_SHA256,
        root=ROOT,
    )
    assert result["ok"] is True
    assert result["real_eval_executed"] is False
    assert result["outcome_loader_reads"] == 0
    assert spy.reads == 0
    assert spy.ids_returned == []
    assert result["feature_gate"]["identity_sha256"] == REG496_IDENTITY_SHA256


def test_synthetic_positive_invokes_spy_after_gates():
    spy = OutcomeReadSpy(lambda: {"2020_02_CIN_CLE": {"home_score": 27, "away_score": 22}})
    result = run_scoped_research_verify(
        PROFILE_DEV_IF437,
        _if437_payload(),
        _if437_ids(),
        hooks=_a_hooks(),
        outcome_loader=spy,
        joined_ids=_if437_ids(),
        candidate_bytes_sha=DEV437_RESULT_SHA256,
        expected_bytes_sha=DEV437_RESULT_SHA256,
        root=ROOT,
        invoke_outcome_after_gates=True,
    )
    assert result["ok"] is True
    assert result["outcome_loader_invoked_after_gates"] is True
    assert result["outcome_loader_reads"] == 1
    assert spy.reads == 1
    assert spy.ids_returned == ["2020_02_CIN_CLE"]
    assert result["real_eval_executed"] is False


def test_byte_change_fails_before_outcome_loader():
    payload = _load(FEATURE_RECON_REG496_ARTIFACT_PATH)
    spy = OutcomeReadSpy(lambda: {"2020_02_ATL_DAL": {"home_score": 1}})
    with pytest.raises(CohortEnforcementRefuse, match="changed frozen bytes"):
        run_scoped_research_verify(
            PROFILE_FEATURE_RECON_REG496,
            payload,
            _reg_ids(),
            hooks=_a_hooks(),
            outcome_loader=spy,
            candidate_bytes_sha="deadbeef" * 8,
            expected_bytes_sha=FEATURE_RECON_REG496_ARTIFACT_SHA256,
            root=ROOT,
        )
    assert spy.reads == 0
    assert spy.ids_returned == []


def test_blocked_coverage_zero_outcomes():
    spy = OutcomeReadSpy(lambda: {"2020_02_CIN_CLE": {"home_score": 9, "away_score": 3}})
    with pytest.raises(CohortEnforcementRefuse, match="blocked coverage"):
        run_scoped_research_verify(
            PROFILE_DEV_IF437,
            _if437_payload(),
            _if437_ids(),
            hooks=_a_hooks(),
            outcome_loader=spy,
            joined_ids=_if437_ids(),
            coverage_blocked=True,
            root=ROOT,
        )
    assert spy.reads == 0
    assert spy.ids_returned == []


def test_numerical_failure_after_gates_still_zero_outcomes():
    payload = dict(_if437_payload())
    payload["mae_challenger"] = payload["mae_challenger"] + 1.0
    spy = OutcomeReadSpy(lambda: {"x": {"home_score": 1}})
    with pytest.raises(EvalResultContractRefuse, match="inconsistent"):
        run_scoped_research_verify(
            PROFILE_DEV_IF437,
            payload,
            _if437_ids(),
            hooks=_a_hooks(),
            outcome_loader=spy,
            joined_ids=_if437_ids(),
            candidate_bytes_sha=DEV437_RESULT_SHA256,
            expected_bytes_sha=DEV437_RESULT_SHA256,
            root=ROOT,
        )
    assert spy.reads == 0


def test_full_cohort_ids_with_two_numerical_rows_fail_zero_reads():
    payload = dict(_if437_payload())
    payload["games"] = list(payload["games"][:2])
    payload["n"] = 2
    payload["n_by_season"] = {"2020": 1, "2021": 1}
    payload["game_ids"] = [row["game_id"] for row in payload["games"]]
    spy = OutcomeReadSpy(lambda: {"x": {"home_score": 1}})
    with pytest.raises(EvalResultContractRefuse, match="n=2 != profile expected 437|cohort IDs disagree"):
        run_scoped_research_verify(
            PROFILE_DEV_IF437,
            payload,
            _if437_ids(),
            hooks=_a_hooks(),
            outcome_loader=spy,
            joined_ids=_if437_ids(),
            candidate_bytes_sha=DEV437_RESULT_SHA256,
            expected_bytes_sha=DEV437_RESULT_SHA256,
            root=ROOT,
        )
    assert spy.reads == 0


def test_forged_synthetic_flag_refused_on_scoped_path():
    payload = dict(_if437_payload())
    payload["synthetic"] = True
    spy = OutcomeReadSpy(lambda: {"x": {"home_score": 1}})
    with pytest.raises(EvalResultContractRefuse, match="synthetic=true refused"):
        run_scoped_research_verify(
            PROFILE_DEV_IF437,
            payload,
            _if437_ids(),
            hooks=_a_hooks(),
            outcome_loader=spy,
            joined_ids=_if437_ids(),
            root=ROOT,
        )
    assert spy.reads == 0
    with pytest.raises(EvalResultContractRefuse, match="synthetic=true refused"):
        run_scoped_research_verify(
            PROFILE_DEV_IF437,
            build_synthetic_if437_result(),
            _if437_ids(),
            hooks=_a_hooks(),
            outcome_loader=spy,
            root=ROOT,
        )
    assert spy.reads == 0


def test_guarded_finalize_writes_only_after_gate(tmp_path: Path):
    payload = _load(FEATURE_RECON_REG496_ARTIFACT_PATH)
    dest = tmp_path / "FEATURE_OUTPUT_REG496.json"
    original = (ROOT / FEATURE_RECON_REG496_ARTIFACT_PATH).read_bytes()
    result = guarded_finalize_feature_output(
        dest,
        payload,
        profile=PROFILE_FEATURE_RECON_REG496,
        candidate_ids=_reg_ids(),
        hooks=_a_hooks(),
        root=ROOT,
        candidate_bytes_sha=FEATURE_RECON_REG496_ARTIFACT_SHA256,
        expected_bytes_sha=FEATURE_RECON_REG496_ARTIFACT_SHA256,
    )
    assert result["ok"] is True
    written = json.loads(dest.read_text(encoding="utf-8"))
    assert written["finalized"] is True
    assert written["n"] == 496
    assert written["gate"]["identity_sha256"] == REG496_IDENTITY_SHA256
    assert (ROOT / FEATURE_RECON_REG496_ARTIFACT_PATH).read_bytes() == original


def test_guarded_finalize_invalid_ids_do_not_write(tmp_path: Path):
    dest = tmp_path / "SHOULD_NOT_EXIST.json"
    with pytest.raises(CohortEnforcementRefuse):
        guarded_finalize_feature_output(
            dest,
            {"n": 2},
            profile=PROFILE_DEV_IF437,
            candidate_ids=["2020_02_CIN_CLE", "2021_02_CLE_CIN"],
            hooks=_a_hooks(),
            root=ROOT,
        )
    assert dest.exists() is False


def test_guarded_finalize_refuses_protected_originals():
    original_reg = (ROOT / FEATURE_RECON_REG496_ARTIFACT_PATH).read_bytes()
    original_437 = (ROOT / DEV437_RESULT_PATH).read_bytes()
    original_72 = (ROOT / MARKET72_RESULT_PATH).read_bytes()
    original_502 = (ROOT / ORIGINAL_502_PATH).read_bytes()
    for rel in (
        FEATURE_RECON_REG496_ARTIFACT_PATH,
        DEV437_RESULT_PATH,
        MARKET72_RESULT_PATH,
        ORIGINAL_502_PATH,
    ):
        with pytest.raises((Exception,), match="protected original"):
            guarded_finalize_feature_output(
                ROOT / rel,
                {"n": 0},
                profile=PROFILE_FEATURE_RECON_REG496,
                candidate_ids=_reg_ids(),
                hooks=_a_hooks(),
                root=ROOT,
            )
    assert (ROOT / FEATURE_RECON_REG496_ARTIFACT_PATH).read_bytes() == original_reg
    assert (ROOT / DEV437_RESULT_PATH).read_bytes() == original_437
    assert (ROOT / MARKET72_RESULT_PATH).read_bytes() == original_72
    assert (ROOT / ORIGINAL_502_PATH).read_bytes() == original_502
    assert sha256_file(ROOT / ORIGINAL_502_PATH) == ORIGINAL_502_SHA256
    assert FEATURE_RECON_REG496_ARTIFACT_PATH in PROTECTED_ORIGINALS


def test_hash_file_list_repo_relative_posix_cross_root(tmp_path: Path):
    rel = "data/ops/cross-root/pin.json"
    body = '{"n":437,"ok":true}\n'
    root_a = tmp_path / "alpha"
    root_b = tmp_path / "beta"
    for root in (root_a, root_b):
        dest = root / rel
        dest.parent.mkdir(parents=True)
        dest.write_text(body, encoding="utf-8")
    hashed_a = hash_file_list(root_a, [root_a / rel])
    hashed_b = hash_file_list(root_b, [root_b / rel])
    assert hashed_a["sha256"] == hashed_b["sha256"]
    assert hashed_a["files"] == [{"path": rel, "sha256": hashed_a["files"][0]["sha256"]}]
    assert hashed_b["files"][0]["path"] == rel
    assert not hashed_a["files"][0]["path"].startswith("/")
    assert repo_relative_posix(ROOT, ROOT / DEV437_RESULT_PATH) == DEV437_RESULT_PATH


def test_output_hash_excludes_interpreter_and_head():
    pins = {"ok": True, "checks": [], "errors": []}
    profiles = {
        PROFILE_FEATURE_RECON_REG496: {
            "ok": True,
            "feature_gate": {"identity_sha256": "aa"},
            "numerical": {"joined_row_sha256": "bb", "n": 496},
        },
        PROFILE_DEV_IF437: {
            "ok": True,
            "feature_gate": {"identity_sha256": "cc"},
            "numerical": {"joined_row_sha256": "dd", "n": 437},
        },
        PROFILE_DEV_MARKET72: {
            "ok": True,
            "feature_gate": {"identity_sha256": "ee"},
            "numerical": {"joined_row_sha256": "ff", "n": 72},
        },
    }
    tests = {"ok": True, "commands": [], "tests": []}
    one = build_receipt(
        root=ROOT,
        pins=pins,
        profiles=profiles,
        tests=tests,
        errors=[],
        interpreter="/abs/venv-one/bin/python",
    )
    two = build_receipt(
        root=ROOT,
        pins=pins,
        profiles=profiles,
        tests=tests,
        errors=[],
        interpreter="/other/root/bin/python",
    )
    assert one["hashes"]["output_sha256"] == two["hashes"]["output_sha256"]
    assert one["interpreter"] != two["interpreter"]
    assert one["runtime"]["tip_sha"] == two["runtime"]["tip_sha"]
    code_paths = [row["path"] for row in one["hashes"]["code"]["files"]]
    assert all(not path.startswith("/") for path in code_paths)
    assert "services/model-service/src/services/nfl_t5107u/verify_integrate.py" in code_paths
    input_paths = [row["path"] for row in one["hashes"]["input"]["files"]]
    assert DEV437_RESULT_PATH in input_paths
    assert MARKET72_RESULT_PATH in input_paths
    assert FEATURE_RECON_REG496_ARTIFACT_PATH in input_paths


def test_receipt_profile_map_keeps_each_profile_name():
    receipt = build_receipt(
        root=ROOT,
        pins={"ok": True, "checks": [], "errors": []},
        profiles={
            PROFILE_FEATURE_RECON_REG496: {"ok": True, "profile": PROFILE_FEATURE_RECON_REG496},
            PROFILE_DEV_IF437: {"ok": True, "profile": PROFILE_DEV_IF437},
            PROFILE_DEV_MARKET72: {"ok": True, "profile": PROFILE_DEV_MARKET72},
        },
        tests={"ok": True, "commands": [], "tests": []},
        errors=[],
    )
    assert receipt["profiles"] == {
        PROFILE_FEATURE_RECON_REG496: PROFILE_FEATURE_RECON_REG496,
        PROFILE_DEV_IF437: PROFILE_DEV_IF437,
        PROFILE_DEV_MARKET72: PROFILE_DEV_MARKET72,
    }
    assert receipt["verified"] is False
    assert receipt["cos_accept_scoped_sha8"] == "96908853"
    assert receipt["package_a_tip"].startswith("42ff285c")
    assert receipt["partial_plumbing_tip"].startswith("ac35ed55")
    assert receipt["partial_plumbing_not_verified"] is True
    assert receipt["owner_amend_sha8"] == "cd253f7a"
    assert receipt["alex_return_sha8"] == "7057e5a9"


def test_failure_cannot_leave_success_receipt():
    receipt = build_receipt(
        root=ROOT,
        pins={"ok": True, "checks": [], "errors": []},
        profiles={
            PROFILE_FEATURE_RECON_REG496: {"ok": True},
            PROFILE_DEV_IF437: {"ok": False, "error": "n=2"},
            PROFILE_DEV_MARKET72: {"ok": True},
        },
        tests={"ok": True, "commands": [], "tests": []},
        errors=["DEV_IF437: n=2"],
    )
    assert receipt["status"] == "FAILED"
    assert receipt["verified"] is False


def test_real_a_hooks_optional_recon_path():
    ce = try_load_cohort_module()
    assert ce is not None
    ids = ce.expected_profile_ids(PROFILE_FEATURE_RECON_REG496, ROOT)
    spy = ce.OutcomeReadSpy(lambda: {"2020_02_ATL_DAL": {"home_score": 24}})
    payload = _load(A_REG_PATH)
    result = run_scoped_research_verify(
        PROFILE_FEATURE_RECON_REG496,
        payload,
        ids,
        hooks=CohortHooks(
            before_feature_output=check_cohort_before_feature_output_finalization,
            before_target_outcome=check_cohort_before_target_outcome_loading,
            source="cohort_enforcement",
        ),
        outcome_loader=spy,
        candidate_bytes_sha=A_REG_SHA,
        expected_bytes_sha=A_REG_SHA,
        root=ROOT,
    )
    assert result["ok"] is True
    assert spy.reads == 0
    assert result["profile"] == PROFILE_FEATURE_RECON_REG496


def test_synthetic_helpers_are_not_the_normal_command_path():
    source = (ROOT / "services/model-service/src/services/nfl_t5107u/verify_integrate.py").read_text(
        encoding="utf-8"
    )
    command_fn = source.split("def run_one_command", 1)[1]
    assert "build_synthetic_if437_result" not in command_fn
    assert "build_synthetic_market72_result" not in command_fn
    assert "DEV437_RESULT_PATH" in command_fn
    assert "MARKET72_RESULT_PATH" in command_fn
    assert "join_market72_from_if437" in command_fn
    assert "refuse_synthetic_flag" in command_fn
    helper = build_synthetic_if437_result()
    assert helper["synthetic"] is True
    assert build_synthetic_market72_result()["synthetic"] is True
