"""t5151u Package A — cohort enforcement proofs. Identity only. No EVAL."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.services.nfl_t5107u.cohort_enforcement import (
    DEV_IF437_IDENTITY_SHA256,
    DEV_MARKET72_FILE_SHA256,
    DEV_MARKET72_IDENTITY_SHA256,
    FEATURE_RECON_REG496_ARTIFACT_PATH,
    FEATURE_RECON_REG496_ARTIFACT_SHA256,
    ORIGINAL_502_PATH,
    ORIGINAL_502_SHA256,
    PROFILE_DEV_IF437,
    PROFILE_DEV_MARKET72,
    PROFILE_FEATURE_RECON_REG496,
    REG496_IDENTITY_SHA256,
    TASK_MANIFEST_REL,
    TASK_MANIFEST_SHA256,
    CohortEnforcementRefuse,
    OutcomeReadSpy,
    check_cohort_before_feature_output_finalization,
    check_cohort_before_target_outcome_loading,
    expected_profile_ids,
    load_artifact_game_ids,
    load_frozen_manifest,
    sha256_file,
)
from src.services.nfl_t5107u.last_played_cohort import assert_original_502_bytes
from src.services.nfl_t5107u.metric_cohorts import WILDCARD_2020_W18

ROOT = Path(__file__).resolve().parents[3]
REG_ARTIFACT = ROOT / FEATURE_RECON_REG496_ARTIFACT_PATH
ORIGINAL_502 = ROOT / ORIGINAL_502_PATH


def _reg_ids() -> list[str]:
    return expected_profile_ids(PROFILE_FEATURE_RECON_REG496, ROOT)


def _if437_ids() -> list[str]:
    return expected_profile_ids(PROFILE_DEV_IF437, ROOT)


def _market72_ids() -> list[str]:
    return expected_profile_ids(PROFILE_DEV_MARKET72, ROOT)


def test_manifest_frozen_before_verification_not_from_output():
    manifest = load_frozen_manifest(ROOT)
    assert manifest["frozen_before_verification"] is True
    assert manifest["allowed_list_source"] == "this_manifest_not_output_under_check"
    assert sha256_file(ROOT / TASK_MANIFEST_REL) == TASK_MANIFEST_SHA256
    assert manifest["authoritative_reg_schedule"]["sha256"].startswith("08533423")
    # Allowed REG IDs are schedule order, not the 496 output list under check.
    artifact_first = load_artifact_game_ids(REG_ARTIFACT)[0]
    manifest_first = manifest["profiles"][PROFILE_FEATURE_RECON_REG496]["game_ids"][0]
    assert artifact_first == "2020_02_CIN_CLE"
    assert manifest_first == "2020_02_ATL_DAL"
    assert set(load_artifact_game_ids(REG_ARTIFACT)) == set(_reg_ids())


def test_old_502_fails_reg_profile():
    assert_original_502_bytes(ROOT)
    assert sha256_file(ORIGINAL_502) == ORIGINAL_502_SHA256
    ids_502 = load_artifact_game_ids(ORIGINAL_502)
    assert len(ids_502) == 502
    assert set(WILDCARD_2020_W18) <= set(ids_502)
    with pytest.raises(CohortEnforcementRefuse, match="n=502 != expected 496"):
        check_cohort_before_feature_output_finalization(
            PROFILE_FEATURE_RECON_REG496, ids_502, root=ROOT
        )


def test_corrected_496_passes_reg():
    ids = load_artifact_game_ids(REG_ARTIFACT)
    assert sha256_file(REG_ARTIFACT) == FEATURE_RECON_REG496_ARTIFACT_SHA256
    result = check_cohort_before_feature_output_finalization(
        PROFILE_FEATURE_RECON_REG496,
        ids,
        candidate_bytes_sha=sha256_file(REG_ARTIFACT),
        expected_bytes_sha=FEATURE_RECON_REG496_ARTIFACT_SHA256,
        root=ROOT,
    )
    assert result["ok"] is True
    assert result["n"] == 496
    assert result["n_by_season"] == {"2020": 240, "2021": 256}
    assert result["identity_sha256"] == REG496_IDENTITY_SHA256
    assert result["limitations"]["publication_timestamp_status"] == "unverified"
    assert result["limitations"]["fit_label"] == "RETRO_FIT"
    assert result["limitations"]["production_causal_claim"] is False


def test_2021_reg_week_18_retained():
    ids = _reg_ids()
    w18 = [gid for gid in ids if gid.startswith("2021_18_")]
    assert len(w18) == 16
    assert "2021_18_DAL_PHI" in w18
    assert "2021_18_KC_DEN" in w18
    assert not any(gid.startswith("2020_18_") for gid in ids)
    check_cohort_before_feature_output_finalization(
        PROFILE_FEATURE_RECON_REG496, ids, root=ROOT
    )


def test_mismatched_arm_ids_fail():
    ids = _reg_ids()
    swapped = list(ids)
    swapped[0] = "2020_18_BAL_TEN"
    with pytest.raises(CohortEnforcementRefuse, match="requested arm|exact set mismatch|Wild Card"):
        check_cohort_before_feature_output_finalization(
            PROFILE_FEATURE_RECON_REG496,
            ids,
            requested_arm_ids={PROFILE_FEATURE_RECON_REG496: swapped},
            root=ROOT,
        )
    joined_wrong = ids[:-1] + ["2020_18_CHI_NO"]
    with pytest.raises(CohortEnforcementRefuse, match="joined|exact set mismatch|Wild Card"):
        check_cohort_before_feature_output_finalization(
            PROFILE_FEATURE_RECON_REG496,
            ids,
            joined_ids=joined_wrong,
            root=ROOT,
        )


def test_changed_frozen_bytes_fail_before_outcome_loader(tmp_path: Path):
    """Safe copy only — originals must stay untouched."""
    original = REG_ARTIFACT.read_bytes()
    assert sha256_file(REG_ARTIFACT) == FEATURE_RECON_REG496_ARTIFACT_SHA256
    copy = tmp_path / "REG496_MUTATED.json"
    mutated = bytearray(original)
    mutated[0] = mutated[0] ^ 0x01
    copy.write_bytes(bytes(mutated))
    spy = OutcomeReadSpy(lambda: {"2020_02_ATL_DAL": {"home_score": 1}})
    with pytest.raises(CohortEnforcementRefuse, match="changed frozen bytes"):
        check_cohort_before_target_outcome_loading(
            PROFILE_FEATURE_RECON_REG496,
            load_artifact_game_ids(REG_ARTIFACT),
            frozen_bytes_sha=sha256_file(copy),
            expected_bytes_sha=FEATURE_RECON_REG496_ARTIFACT_SHA256,
            outcome_loader=spy,
            root=ROOT,
        )
    assert spy.reads == 0
    assert spy.ids_returned == []
    assert sha256_file(REG_ARTIFACT) == FEATURE_RECON_REG496_ARTIFACT_SHA256
    assert ORIGINAL_502.read_bytes()  # original 502 still readable
    assert sha256_file(ORIGINAL_502) == ORIGINAL_502_SHA256


def test_blocked_coverage_spy_zero_target_reads():
    spy = OutcomeReadSpy(lambda: {"2020_02_ATL_DAL": {"home_score": 24, "away_score": 21}})
    with pytest.raises(CohortEnforcementRefuse, match="blocked coverage"):
        check_cohort_before_target_outcome_loading(
            PROFILE_FEATURE_RECON_REG496,
            _reg_ids(),
            coverage_blocked=True,
            outcome_loader=spy,
            root=ROOT,
        )
    assert spy.reads == 0
    assert spy.ids_returned == []


def test_positive_accepted_437_and_72_still_pass():
    if437 = _if437_ids()
    market72 = _market72_ids()
    r437 = check_cohort_before_feature_output_finalization(
        PROFILE_DEV_IF437, if437, joined_ids=if437, root=ROOT
    )
    r72 = check_cohort_before_feature_output_finalization(
        PROFILE_DEV_MARKET72, market72, joined_ids=market72, root=ROOT
    )
    assert r437["n"] == 437
    assert r437["n_by_season"] == {"2020": 210, "2021": 227}
    assert r437["identity_sha256"] == DEV_IF437_IDENTITY_SHA256
    assert r72["n"] == 72
    assert r72["n_by_season"] == {"2020": 35, "2021": 37}
    assert r72["identity_sha256"] == DEV_MARKET72_IDENTITY_SHA256
    accepted72 = ROOT / "data/ops/nfl-t5151u-cohort-enforcement/ACCEPTED_DEV_MARKET72_IDS.json"
    assert sha256_file(accepted72) == DEV_MARKET72_FILE_SHA256
    gate = check_cohort_before_target_outcome_loading(
        PROFILE_DEV_IF437,
        if437,
        frozen_bytes_sha=DEV_IF437_IDENTITY_SHA256,
        expected_bytes_sha=DEV_IF437_IDENTITY_SHA256,
        outcome_loader=OutcomeReadSpy(),
        root=ROOT,
    )
    assert gate["outcome_loader_invoked"] is False


def test_uniqueness_extras_missing_duplicates():
    ids = _market72_ids()
    duplicated = [ids[0]] + ids[1:-1] + [ids[0]]
    with pytest.raises(CohortEnforcementRefuse, match="duplicate"):
        check_cohort_before_feature_output_finalization(
            PROFILE_DEV_MARKET72, duplicated, root=ROOT
        )
    extra = list(ids)
    extra[0] = "2020_02_ZZZ_YYY"
    with pytest.raises(CohortEnforcementRefuse, match="exact set mismatch"):
        check_cohort_before_feature_output_finalization(
            PROFILE_DEV_MARKET72, extra, root=ROOT
        )
    with pytest.raises(CohortEnforcementRefuse, match="n=71 != expected 72|exact set mismatch"):
        check_cohort_before_feature_output_finalization(
            PROFILE_DEV_MARKET72, ids[1:], root=ROOT
        )


def test_forbid_substitution_496_437_94_72():
    with pytest.raises(CohortEnforcementRefuse, match="substitution"):
        check_cohort_before_feature_output_finalization(
            PROFILE_FEATURE_RECON_REG496, _if437_ids(), root=ROOT
        )
    with pytest.raises(CohortEnforcementRefuse, match="substitution"):
        check_cohort_before_feature_output_finalization(
            PROFILE_DEV_IF437, _reg_ids(), root=ROOT
        )
    with pytest.raises(CohortEnforcementRefuse, match="substitution|94"):
        check_cohort_before_feature_output_finalization(
            PROFILE_DEV_MARKET72, _if437_ids(), root=ROOT
        )
    fake94 = [f"2020_02_FAKE_{i:02d}" for i in range(94)]
    with pytest.raises(CohortEnforcementRefuse, match="94"):
        check_cohort_before_feature_output_finalization(
            PROFILE_DEV_MARKET72, fake94, root=ROOT
        )


def test_matching_sample_requested_and_joined_pass():
    ids = _market72_ids()
    result = check_cohort_before_feature_output_finalization(
        PROFILE_DEV_MARKET72,
        ids,
        requested_arm_ids={PROFILE_DEV_MARKET72: ids},
        joined_ids=ids,
        root=ROOT,
    )
    assert result["ok"] is True
    assert result["limitations"]["publication_timestamp_status"] == "unverified"


def test_original_502_preserved_historical():
    assert_original_502_bytes(ROOT)
    payload = json.loads(ORIGINAL_502.read_text(encoding="utf-8"))
    assert payload["n_complete_27"] == 502
    manifest = load_frozen_manifest(ROOT)
    assert manifest["original_502_preserved"]["historical_only"] is True
    assert manifest["original_502_preserved"]["sha256"] == ORIGINAL_502_SHA256
