"""t5151u Package C wiring — scoped caller + spies. Synthetic only."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.services.nfl_t5107u.eval_result_contract import (
    PROFILE_DEV_IF437,
    PROFILE_DEV_MARKET72,
    PROFILE_FEATURE_RECON_REG496,
    EvalResultContractRefuse,
)
from src.services.nfl_t5107u.verify_integrate import (
    FEATURE_RECON_REG496_ARTIFACT_PATH,
    FEATURE_RECON_REG496_ARTIFACT_SHA256,
    CohortHooks,
    OutcomeReadSpy,
    build_receipt,
    build_synthetic_if437_result,
    build_synthetic_market72_result,
    run_scoped_research_verify,
    sha256_file,
    try_load_cohort_module,
    verify_pinned_artifacts,
)

ROOT = Path(__file__).resolve().parents[3]


class _Refuse(ValueError):
    pass


def _pass_hooks() -> CohortHooks:
    def feature(profile, candidate_ids, **kwargs):
        return {"ok": True, "gate": "before_feature_output_finalization", "profile": profile, "n": len(candidate_ids)}

    def outcome(profile, candidate_ids, **kwargs):
        loader = kwargs.get("outcome_loader")
        if loader is not None and getattr(loader, "reads", 0) not in (None, 0):
            raise _Refuse("outcome loader already read")
        if kwargs.get("coverage_blocked"):
            raise _Refuse("blocked coverage — refuse before target-outcome loading")
        if (
            kwargs.get("frozen_bytes_sha")
            and kwargs.get("expected_bytes_sha")
            and kwargs["frozen_bytes_sha"] != kwargs["expected_bytes_sha"]
        ):
            raise _Refuse("changed frozen bytes — refuse before target-outcome loading")
        return {
            "ok": True,
            "gate": "before_target_outcome_loading",
            "profile": profile,
            "outcome_loader_invoked": False,
        }

    return CohortHooks(before_feature_output=feature, before_target_outcome=outcome, source="test")


def test_pinned_reg496_and_502_bytes():
    pins = verify_pinned_artifacts(ROOT)
    names = {row["name"]: row for row in pins["checks"]}
    assert names["FEATURE_RECON_REG496"]["ok"] is True
    assert names["ORIGINAL_502_HISTORICAL"]["ok"] is True
    assert names["FEATURE_RECON_REG496"]["sha256"] == FEATURE_RECON_REG496_ARTIFACT_SHA256


def test_scoped_caller_recon_never_reads_outcomes():
    payload = json.loads((ROOT / FEATURE_RECON_REG496_ARTIFACT_PATH).read_text(encoding="utf-8"))
    spy = OutcomeReadSpy(lambda: {"2020_02_ATL_DAL": {"home_score": 24, "away_score": 21}})
    result = run_scoped_research_verify(
        PROFILE_FEATURE_RECON_REG496,
        payload,
        payload["game_ids"],
        hooks=_pass_hooks(),
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


def test_byte_change_fails_before_outcome_loader():
    payload = json.loads((ROOT / FEATURE_RECON_REG496_ARTIFACT_PATH).read_text(encoding="utf-8"))
    spy = OutcomeReadSpy(lambda: {"2020_02_ATL_DAL": {"home_score": 1}})
    with pytest.raises(_Refuse, match="changed frozen bytes"):
        run_scoped_research_verify(
            PROFILE_FEATURE_RECON_REG496,
            payload,
            payload["game_ids"],
            hooks=_pass_hooks(),
            outcome_loader=spy,
            candidate_bytes_sha="deadbeef" * 8,
            expected_bytes_sha=FEATURE_RECON_REG496_ARTIFACT_SHA256,
            root=ROOT,
        )
    assert spy.reads == 0
    assert spy.ids_returned == []


def test_blocked_coverage_zero_outcomes():
    payload = build_synthetic_if437_result()
    spy = OutcomeReadSpy(lambda: {"2020_02_CIN_CLE": {"home_score": 9, "away_score": 3}})
    with pytest.raises(_Refuse, match="blocked coverage"):
        run_scoped_research_verify(
            PROFILE_DEV_IF437,
            payload,
            payload["game_ids"],
            hooks=_pass_hooks(),
            outcome_loader=spy,
            coverage_blocked=True,
        )
    assert spy.reads == 0
    assert spy.ids_returned == []


def test_numerical_failure_after_gates_still_zero_outcomes():
    payload = build_synthetic_market72_result()
    payload["mae_market"] = payload["mae_market"] + 1.0
    spy = OutcomeReadSpy(lambda: {"x": {"home_score": 1}})
    with pytest.raises(EvalResultContractRefuse, match="inconsistent"):
        run_scoped_research_verify(
            PROFILE_DEV_MARKET72,
            payload,
            payload["game_ids"],
            hooks=_pass_hooks(),
            outcome_loader=spy,
        )
    assert spy.reads == 0


def test_if437_and_market72_synthetic_through_caller():
    spy = OutcomeReadSpy()
    if_body = run_scoped_research_verify(
        PROFILE_DEV_IF437,
        build_synthetic_if437_result(),
        ["2020_02_CIN_CLE", "2021_02_CLE_CIN"],
        hooks=_pass_hooks(),
        outcome_loader=spy,
    )
    mkt = run_scoped_research_verify(
        PROFILE_DEV_MARKET72,
        build_synthetic_market72_result(),
        ["2020_02_CIN_CLE", "2021_03_CLE_CIN"],
        hooks=_pass_hooks(),
        outcome_loader=spy,
    )
    assert if_body["numerical"]["market_unavailable"] is True
    assert mkt["numerical"]["ok"] is True
    assert spy.reads == 0


def test_real_a_hooks_optional():
    ce = try_load_cohort_module()
    if ce is None:
        pytest.skip("Package A not landed in this worktree")
    ids = ce.expected_profile_ids(PROFILE_FEATURE_RECON_REG496, ROOT)
    spy = ce.OutcomeReadSpy(lambda: {"2020_02_ATL_DAL": {"home_score": 24}})
    payload = json.loads((ROOT / FEATURE_RECON_REG496_ARTIFACT_PATH).read_text(encoding="utf-8"))
    result = run_scoped_research_verify(
        PROFILE_FEATURE_RECON_REG496,
        payload,
        ids,
        hooks=CohortHooks(
            before_feature_output=ce.check_cohort_before_feature_output_finalization,
            before_target_outcome=ce.check_cohort_before_target_outcome_loading,
            source="cohort_enforcement",
        ),
        outcome_loader=spy,
        candidate_bytes_sha=FEATURE_RECON_REG496_ARTIFACT_SHA256,
        expected_bytes_sha=FEATURE_RECON_REG496_ARTIFACT_SHA256,
        root=ROOT,
    )
    assert result["ok"] is True
    assert spy.reads == 0
    assert result["profile"] == PROFILE_FEATURE_RECON_REG496
    assert result["feature_gate"]["identity_sha256"] == (
        "6429f8596a1b605a9f1dc8aec21d81fc4454ff25e985dc77e691ec29d489c640"
    )


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
    assert result["profile"] == PROFILE_FEATURE_RECON_REG496
    assert result["feature_gate"]["identity_sha256"] == (
        "6429f8596a1b605a9f1dc8aec21d81fc4454ff25e985dc77e691ec29d489c640"
    )


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
