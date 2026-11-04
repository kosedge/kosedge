"""t5335u/t5344u followthrough metadata preflight tests. CERT=0. No kernel lock."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.services.nfl_r7_correctness_v1.followthrough_preflight import (
    B_NTBBK_TIP_HELD,
    B_NTBBK_TIP_REFUSED,
    EXACT_496,
    N_2020,
    N_2021,
    N_CONTRACT_27,
    N_NEW_59,
    N_OLD_437,
    N_SAME_96,
    N_SCHEDULE_REG,
    PBP_TIME_ROLE,
    PRIOR_MISSING_N,
    PROJECTION_SHA256,
    RAW_CUTOFF_ROLE,
    RETURN_NTBBK,
    SPEC_SHA256,
    FollowthroughRefuse,
    _scan_forbidden,
    build_candidate,
    ntbb_k_integrate_hooks,
    require_spec,
    retro_c1_hold,
    run_direct_boundary_controls,
)

REPO = Path(__file__).resolve().parents[3]


def test_spec_bind_matches_connector() -> None:
    bound = require_spec(REPO)
    assert bound["sha256"] == SPEC_SHA256
    assert bound["kernel_implemented"] is False


def test_candidate_counts_and_unknown_timing() -> None:
    cand = build_candidate(root=REPO)
    assert cand["counts"]["exact496"] == EXACT_496 == N_2020 + N_2021
    assert cand["counts"]["old437"] + cand["counts"]["new59"] == EXACT_496
    assert cand["counts"]["old437"] == N_OLD_437
    assert cand["counts"]["new59"] == N_NEW_59
    assert cand["counts"]["same96"] == N_SAME_96
    assert cand["counts"]["same96_ids_present"] is True
    assert cand["counts"]["schedule_reg_records"] == N_SCHEDULE_REG
    assert cand["counts"]["contract_27"] == N_CONTRACT_27
    assert len(cand["game_ids"]) == EXACT_496
    assert len(cand["new_59_ids"]) == N_NEW_59
    assert len(cand["same96_ids"]) == N_SAME_96
    assert len(cand["identities"]) == EXACT_496
    assert len(cand["physical_schedule_recorded_metadata_only"]) == N_SCHEDULE_REG
    assert len(cand["same96_metadata"]) == N_SAME_96
    assert len(cand["matrix_field_metadata"]) == EXACT_496
    assert cand["readiness"] == "NOT_READY"
    assert cand["kernel_implemented"] is False
    assert cand["score_bearing_payload_returned"] is False
    assert cand["packaging_revision"] is None
    assert cand["packaging_revision_claimed_as_executed"] is False
    assert cand["runtime_source_revision"]
    assert cand["missing_n"] == 1
    assert cand["missing_n_prior"] == PRIOR_MISSING_N
    assert cand["missing_n_delta"] == 1 - PRIOR_MISSING_N
    assert cand["consumed_projection"]["sha256"] == PROJECTION_SHA256
    assert cand["consumed_projection"]["sha256_match"] is True
    assert cand["consumed_projection"]["actual_clock_proof"] is False
    assert cand["spec"]["sha256"] == SPEC_SHA256
    assert all(row["actual_versus_scheduled"] == "UNKNOWN" for row in cand["targets"])
    assert all(row["played"] == "UNKNOWN" for row in cand["targets"])
    assert all(row["rest_ready"] is False for row in cand["targets"])
    assert all(row["strict_rest_ready"] is False for row in cand["targets"])
    assert all(row["score_bearing_payload"] is False for row in cand["targets"])
    assert all(row["actual_kickoff_utc"] is None for row in cand["targets"])
    assert all(row["scheduled_kickoff_utc"] is None for row in cand["targets"])
    assert all(row["available_at"] is None for row in cand["targets"])
    assert all(row["observed_at"] is None for row in cand["targets"])
    assert cand["targets"][0]["previous_week_history_pointer_eligible"] is True


def test_timestamp_role_not_seal_or_ko60() -> None:
    cand = build_candidate(root=REPO)
    audit = cand["timestamp_role"]
    assert audit["matrix_named_pregame_cutoff_equals_B1_kickoff"] == N_SAME_96
    assert audit["matrix_named_pregame_cutoff_equals_B1_true_cutoff"] == 0
    assert audit["matrix_named_pregame_cutoff_equals_actual_ko_minus_60"] == 0
    assert audit["actual_ko_minus_60_computed"] is False
    assert audit["used_as_seal"] is False
    assert audit["silently_subtracted_60"] is False
    assert audit["meaning_generalized_beyond_same96"] is False
    assert audit["role"] == RAW_CUTOFF_ROLE
    assert all(row["raw_field_named_pregame_cutoff_utc_role"] == RAW_CUTOFF_ROLE for row in cand["targets"])
    assert all(row["raw_field_named_pregame_cutoff_utc_used_as_seal"] is False for row in cand["targets"])
    assert all(row["raw_field_named_pregame_cutoff_utc_silently_subtracted_60"] is False for row in cand["targets"])
    assert all(row["pbp_start_time_raw_role"] == PBP_TIME_ROLE for row in cand["targets"])
    assert all(row["played_status_is_actual_clock_proof"] is False for row in cand["targets"])
    clocks = cand["physical_schedule_recorded_metadata_only"]
    assert all(row["actual_kickoff_utc"] is None for row in clocks)
    assert all(row["scheduled_kickoff_utc"] is None for row in clocks)
    assert all(row["available_at"] is None for row in clocks)
    assert all(row["observed_at"] is None for row in clocks)


def test_fifth_prerequisite_point_error_not_book_prices() -> None:
    cand = build_candidate(root=REPO)
    fifth = cand["fifth_prerequisite"]
    assert fifth["book_specific_offered_price_required"] is False
    assert fifth["book_specific_settlement_required"] is False
    assert fifth["price_or_line_included"] is False
    assert fifth["same96_ids_bound"] is True
    assert fifth["same96_b1_times_bound"] is True
    assert fifth["score_access"] is False
    assert fifth["forecast_authorization"] is False
    assert fifth["market_point_bind"]["digest_found"] is False
    assert fifth["market_point_bind"]["invented_prices"] is False
    assert fifth["market_point_bind"]["opener_close_label_invented"] is False
    missing_locators = [row["locator"] for row in cand["missing"]]
    assert missing_locators == [
        "frozen median-spread market-point digest for same96 POINT-ERROR"
    ]
    assert "same96 book-specific offered price/settlement" not in missing_locators
    assert all("offered-line/price" not in row["locator"] for row in cand["missing"])
    consumed = [row["status"] for row in cand["consumed_cloud_metadata"]]
    assert consumed == ["CONSUMED_VIA_STAGED_PROJECTION"] * 5


def test_ntbbk_hooks_a807af22_not_final_wait_58427() -> None:
    hooks = ntbb_k_integrate_hooks()
    assert hooks["status"] == "WAIT_RETURN58427_LOGPMF_TAIL_DELTA"
    assert hooks["return_order"] == RETURN_NTBBK
    assert hooks["return_unfreeze"] == "58427"
    assert hooks["refused_tip"] == B_NTBBK_TIP_REFUSED
    assert hooks["held_tip"] == B_NTBBK_TIP_HELD
    assert hooks["frozen_tip"] is None
    assert hooks["frozen_as_final"] is False
    assert hooks["integrated"] is False
    assert hooks["package_accepted"] is False
    assert hooks["direct_paths_open"] is True
    assert hooks["r7_model_arm"] is False
    assert hooks["package_closed_from_b_alone"] is False
    assert hooks["b_clocks_promoted"] is False
    assert hooks["producer_capability_gate"]["owner"] == "A"
    hold = retro_c1_hold()
    assert hold["implemented"] is True
    assert hold["real_exec"] is False
    assert hold["package_accepted"] is False
    cand = build_candidate(root=REPO)
    assert cand["ntbb_k_integrate"]["held_tip"].startswith("a807af22")
    assert cand["ntbb_k_integrate"]["frozen_as_final"] is False
    assert cand["ntbb_k_integrate"]["r7_model_arm"] is False
    assert cand["kernel_implemented"] is False
    assert (REPO / "services/model-service/src/services/nfl_ntbb_k_v1/law.py").is_file()


def test_score_keys_and_missing_spec_refused() -> None:
    with pytest.raises(FollowthroughRefuse, match="home_score"):
        _scan_forbidden({"home_score": 21}, where="test")
    with pytest.raises(FollowthroughRefuse, match="spec missing"):
        require_spec(Path("/tmp/no-such-r7-root"))
    controls = run_direct_boundary_controls()
    assert controls["spy_positive_control"]["spy_fired"] is True
    assert all(item["refused"] for item in controls["negatives"])
