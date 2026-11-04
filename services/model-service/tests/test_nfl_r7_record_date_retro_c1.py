"""R7_RECORD_DATE_RETRO_C1 tests. CERT=0. Synthetic fixtures only."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.services.nfl_r7_correctness_v1.consume_ntbb_k import consume_ntbb_k
from src.services.nfl_r7_record_date_retro_c1.authority import AuthorityRegistry
from src.services.nfl_r7_record_date_retro_c1.fixtures import (
    ALIAS_SCHEDULE,
    POSTPONE_SCHEDULE,
    SYNTHETIC_TARGET,
    TIE_SCHEDULE,
    synthetic_history,
    synthetic_schedule,
)
from src.services.nfl_r7_record_date_retro_c1.history_filter import filter_history_for_target
from src.services.nfl_r7_record_date_retro_c1.identity import bind_identity_pointers
from src.services.nfl_r7_record_date_retro_c1.pins import (
    ARCHIVED_R5_CLAIM,
    IDENTITY_SHA256,
    N_2020_21,
    N_HISTORY_2013_19,
    N_IDENTITY,
    N_TARGET,
    SPEC_SHA256,
)
from src.services.nfl_r7_record_date_retro_c1.produce import run_preflight
from src.services.nfl_r7_record_date_retro_c1.refuse import RetroHold, RetroRefuse
from src.services.nfl_r7_record_date_retro_c1.rest import project_recorded_date_rest

REPO = Path(__file__).resolve().parents[3]


def test_identity_2320_no_scores() -> None:
    bound = bind_identity_pointers(REPO)
    assert bound["n"] == N_IDENTITY == N_HISTORY_2013_19 + N_2020_21
    assert bound["sha256"] == IDENTITY_SHA256
    assert bound["scores_opened"] is False
    assert bound["week_number_reg_proxy"] is False
    assert bound["eval_2017_reopened"] is False


def test_recorded_date_rest_calendar_asymmetry_bye_alias() -> None:
    got = project_recorded_date_rest(target=SYNTHETIC_TARGET, schedule=synthetic_schedule())
    assert got["home"]["calendar_days"] == 13  # 2018-10-13 minus 2018-09-30
    assert got["away"]["calendar_days"] == 16  # 2018-10-13 minus 2018-09-27
    assert got["asymmetric"] is True
    assert got["used_default_seven"] is False
    assert got["claimed_actual_clock"] is False
    alias = project_recorded_date_rest(
        target={"game_id": "SYNTHETIC_2018_W06_LAC_LAR", "season": 2018, "home": "LAC", "away": "LAR",
                "recorded_game_date": "2018-10-13"},
        schedule=ALIAS_SCHEDULE,
    )
    assert alias["home"]["predecessor_game_id"] == "SYNTHETIC_2018_W01_SD_MIA"
    assert alias["away"]["predecessor_game_id"] == "SYNTHETIC_2018_W02_STL_BUF"
    postponed = project_recorded_date_rest(
        target={"game_id": "SYNTHETIC_2018_W03_LAC_DEN", "season": 2018, "home": "DEN", "away": "LAC",
                "recorded_game_date": "2018-09-30"},
        schedule=POSTPONE_SCHEDULE,
    )
    assert postponed["away"]["calendar_days"] == 7
    assert postponed["away"]["predecessor_game_id"] == "SYNTHETIC_2018_W02_LAC_KC"


def test_week1_equal_date_and_own_game_refused() -> None:
    with pytest.raises(RetroRefuse, match="missing prior"):
        project_recorded_date_rest(
            target={"game_id": "SYNTHETIC_2018_W01_LAC_MIA", "season": 2018, "home": "LAC", "away": "MIA",
                    "recorded_game_date": "2018-09-09"},
            schedule=synthetic_schedule(),
        )
    with pytest.raises(RetroRefuse, match="equal latest"):
        project_recorded_date_rest(
            target={"game_id": "SYNTHETIC_2018_W02_LAC_KC", "season": 2018, "home": "LAC", "away": "KC",
                    "recorded_game_date": "2018-09-16"},
            schedule=TIE_SCHEDULE,
        )


def test_history_filter_drops_same_week_and_target() -> None:
    hist = filter_history_for_target(
        synthetic_history(),
        target_season=2018,
        target_week=6,
        target_game_id="SYNTHETIC_2018_W06_LAC_LAR",
        nominal_kickoff_utc="2018-10-14T00:25:00Z",
    )
    kept = {row["game_id"] for row in hist["rows"]}
    assert "SYNTHETIC_2018_W06_LAC_LAR" not in kept
    assert "SYNTHETIC_2018_W06_SAMEWEEK_LAC_DEN" not in kept
    assert "SYNTHETIC_2018_W04_LAC_SF" in kept
    assert hist["n_kept"] >= 1


def test_authority_synthetic_not_real_or_r5_or_spent() -> None:
    reg = AuthorityRegistry()
    claim = reg.issue_synthetic_claim(context={"demo": True})
    ok = reg.require_before_reader(
        claim_id=claim["claim_id"],
        context_hash_expected=claim["context_hash"],
        reader_role="model",
        requested_class="SYNTHETIC",
    )
    assert ok["status"] == "ISSUED"
    with pytest.raises(RetroHold):
        reg.require_before_reader(
            claim_id=claim["claim_id"],
            context_hash_expected=claim["context_hash"],
            reader_role="model",
            requested_class="REAL",
        )
    with pytest.raises(RetroRefuse, match="R5"):
        reg.issue_synthetic_claim(context={"x": 1}, claim_id=ARCHIVED_R5_CLAIM)
    reg.spend(claim["claim_id"])
    with pytest.raises(RetroRefuse, match="spent"):
        reg.require_before_reader(
            claim_id=claim["claim_id"],
            context_hash_expected=claim["context_hash"],
            reader_role="history",
            requested_class="SYNTHETIC",
        )


def test_guarded_preflight_synthetic_executor() -> None:
    receipt = run_preflight(root=REPO)
    assert receipt["ok"] is True
    assert receipt["ready_for_real_exec"] is False
    assert receipt["identity"]["n"] == N_IDENTITY
    assert receipt["rest_recomputed_496"]["matched"] == N_TARGET
    assert receipt["strict_live_unchanged"] is True
    assert receipt["synthetic_executor"]["model_called"] is True
    assert receipt["synthetic_executor"]["claim_status"] == "SPENT"
    assert receipt["pins"]["spec"]["sha256"] == SPEC_SHA256
    assert receipt["invalid_paths"]["absent_claim"]["outcome_reads"] == 0
    assert receipt["invalid_paths"]["real_request"]["model_called"] is False
    assert receipt["invalid_paths"]["r5_reuse"]["refused"] is True
    assert receipt["invalid_paths"]["spent_retry"]["refused"] is True
    assert receipt["ntbb_k_integrated"] is False
    assert receipt["kernel_frozen_from_d0bb6bef"] is False
    schema = receipt["real_data_projection_schema"]
    assert schema["authorized_now"] is False
    assert schema["scores_opened"] is False
    assert "ROOT_CLAIM" in schema["executable_command_when_root_authorizes"]


def test_ntbbk_freeze_corrected_tip_not_d0bb6bef() -> None:
    bound = consume_ntbb_k(root=REPO)
    assert bound["frozen_tip"].startswith("a807af22")
    assert bound["refused_tip"].startswith("d0bb6bef")
    assert bound["r7_model_arm"] is False
    assert bound["package_closed_from_b_alone"] is False
    assert bound["b_clocks_promoted"] is False
    assert bound["kernel_sha256"] == "ee80029149e410da7c3add0f74f2e8b1c3568c96a4542d820bbf4c9369996aa7"
