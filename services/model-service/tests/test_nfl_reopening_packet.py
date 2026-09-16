"""NFL 2026-09-16 reopening packet — integrity, leak, W-L refuse, shadow audit."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.nfl_epa_authority import NFL_2026_W1_OUTCOMES, NFL_2026_W2_SLATE
from src.services.nfl_reopening_packet import (
    ATL_GB_FILL_RUN_ID,
    PACKET_RUN_ID,
    PROD_CANDIDATE_RUN_ID,
    PROD_CANDIDATE_SHA,
    assemble_packet,
    audit_customer_view_slate,
    audit_shadow,
    authorize_candidate_row,
    build_customer_view_slate,
    build_gate1_integrity,
    build_shadow_slate,
    classify_live_leak,
    frozen_eval_w1,
    grade_predictive_validation,
    is_july31_stale,
    load_canonical_slate,
    prove_wl_refuse_holds,
    records_after_week1,
)
from src.services.nfl_regression_diagnose import LOCKED_SCORING, locked_scoring_snapshot

PUBLIC_FLAG = (
    Path(__file__).resolve().parents[3]
    / "apps"
    / "web"
    / "lib"
    / "cfb-edge-board-public.ts"
)


def test_july31_stale_filter_rejects_live_and_authorizes_only_packet_run() -> None:
    stale = {
        "key": "CLE@TB",
        "projection_created_at": "2026-07-31T06:05:49.707238Z",
        "run_id": None,
        "strength_source": "other_or_blended",
    }
    unauthorized = {
        "key": "DET@BUF",
        "projection_created_at": "2026-09-15T21:15:16.688269Z",
        "run_id": None,
        "strength_source": "packaged_epa_prior",
    }
    candidate = {
        "key": "DET@BUF",
        "projection_created_at": "2026-09-16T15:00:00Z",
        "run_id": PACKET_RUN_ID,
        "strength_source": "packaged_epa_prior",
        "personnel_overlay": False,
        "injury_overlay": False,
    }
    assert is_july31_stale(stale) is True
    assert authorize_candidate_row(stale)["authorized"] is False
    assert "july31_stale_projection" in authorize_candidate_row(stale)["reasons"]
    assert authorize_candidate_row(unauthorized)["authorized"] is False
    assert "unauthorized_partial_remat_null_run_id" in authorize_candidate_row(unauthorized)["reasons"]
    assert authorize_candidate_row(candidate)["authorized"] is True
    leak = classify_live_leak()
    assert leak["july31_cannot_enter_candidate"] is True
    assert leak["upcoming_authorized_as_candidate_n"] == 0
    assert leak["week1_july31_n"] == 16
    assert leak["candidate_filter_rejects_all_live_rows"] is True


def test_atl_pit_wl_refuse_still_holds() -> None:
    proof = prove_wl_refuse_holds()
    assert proof["passed"] is True
    assert proof["material_wl_vs_epa"] is True
    assert proof["adhoc_source"] == "packaged_epa_prior"
    assert proof["adhoc_refused_win_loss"] is True
    assert proof["missing_epa_refuse_reason"] == "packaged_epa_unavailable"
    assert abs(float(proof["wl_spread_home"]) + 7.55) < 0.05


def test_gate1_resolves_atl_pit_remat_and_keeps_reopen_fail() -> None:
    report = build_gate1_integrity()
    assert report["candidate_path"] == "PASS"
    assert report["focus_integrity"]["atl_pit_hold_resolved"] is True
    assert report["focus_integrity"]["atl_pit_remat_spread_home"] is not None
    assert report["focus_integrity"]["chi_car_remat_spread_home"] is not None
    assert report["focus_integrity"]["passed"] is True
    assert "ATL@PIT" in report["focus_integrity"]["material_wl_vs_epa_keys"]
    assert report["wl_refuse"]["passed"] is True
    assert report["july31_leak"]["july31_cannot_enter_candidate"] is True
    assert report["live_production_isolation"] == "FAIL"
    assert report["reopen_gate"] == "FAIL"
    assert report["recommendation"] == "HOLD"
    assert report["production_promote"] is False
    assert report["scoring_equation_changed"] is False
    assert locked_scoring_snapshot()["base_total_points"] == LOCKED_SCORING["base_total_points"]


def test_w2_shadow_has_every_game_and_no_absurdities() -> None:
    shadow = build_shadow_slate(weeks=(2,))
    keys = {g["key"] for g in shadow["games"]}
    expected = {f"{g['away']}@{g['home']}" for g in NFL_2026_W2_SLATE}
    assert keys == expected
    assert shadow["game_count"] == 16
    assert shadow["run_id"] == PACKET_RUN_ID
    for game in shadow["games"]:
        assert game["run_id"] == PACKET_RUN_ID
        assert game["injury_personnel_status"] == "OFF"
        assert game["strength_source"] == "packaged_epa_prior"
        assert game["data_timestamp"]["live_projection_used_as_fair"] is False
        assert game["overlays"]["personnel_margin_points"] == 0.0
        assert game["overlays"]["injuries_margin_points"] == 0.0
        assert abs(float(game["ke_fair_spread_home"])) < 20
        assert 28 < float(game["ke_fair_total"]) < 70
    audit = audit_shadow(shadow)
    assert audit["sanity"] == "PASS"
    assert not audit["absurdities"]
    assert not audit["provenance_fail"]


def test_canonical_w2_matches_locked_slate() -> None:
    canon = {(r["away"], r["home"]) for r in load_canonical_slate((2,))}
    locked = {(g["away"], g["home"]) for g in NFL_2026_W2_SLATE}
    assert canon == locked


def test_frozen_eval_does_not_fit_ats_or_change_coeffs() -> None:
    ev = frozen_eval_w1()
    assert ev["ats_fitting"] is False
    assert ev["coefficient_changes"] is False
    assert ev["n_w1"] == len(NFL_2026_W1_OUTCOMES) == 16
    assert ev["w1_oos"]["epa_margin_mae"] is not None
    assert ev["w1_oos"]["epa_total_mae"] is not None
    assert ev["w1_oos"]["wl_margin_mae"] is not None
    records = records_after_week1()
    assert records["PIT"] == "1-0"
    assert records["ATL"] == "0-1"
    assert records["CHI"] == "1-0"
    assert records["CAR"] == "0-1"


def test_packet_folds_alex_live_as_conditional_no_board_go() -> None:
    bundle = assemble_packet()
    packet = bundle["packet"]
    assert packet["research_recommendation"] == "HOLD"
    assert packet["recommendation"] == "HOLD"
    assert packet["production_promote"] is False
    assert packet["coming_soon"] is True
    assert packet["public_flags"]["NFL_EDGE_BOARD_PUBLIC_ENABLED"] is False
    assert packet["cfb"] == "separate_do_not_bless"
    assert packet["gate1"]["candidate_path"] == "PASS"
    assert packet["gate1"]["integrity"] == "PASS"
    assert packet["gate1"]["integrity_sha_status"] == "STILL_VALID"
    assert str(packet["gate1"]["integrity_sha_564"]).startswith("3ee91339")
    assert packet["gate1"]["atl_pit_epa_spread_home"] == -0.76
    assert packet["gate1"]["atl_pit_wl_spread_home"] == -7.55
    assert packet["gate1"]["board_reopen"] == "NO-GO"
    assert packet["gate1"]["reopen_gate"] == "FAIL"
    assert packet["gate2"]["sanity"] == "PASS"
    assert packet["gate2"]["alex_live_shadow"] == "PASS"
    assert packet["gate2"]["alex_live_game_count"] == 17
    assert packet["gate3"]["verdict"] == "PARTIAL"
    assert packet["gate3"]["alex_status"] == "RUN_ON_CANDIDATE"
    assert packet["gate4"]["release_spread"] == "BLOCKED"
    assert packet["gate4"]["website_verification"] == "BLOCKED"
    assert packet["alex_live"]["cited_not_recomputed"] is True
    assert packet["alex_live"]["live_git_sha"] == "153b6a884a8e"
    assert packet["system_integrity"] == "PASS"
    assert packet["predictive_validation"] == "PARTIAL"
    assert packet["current_slate_sanity_provenance"] == "PASS"
    assert packet["slate_fair_coverage"] == "16/17"
    assert packet["final"]["fair_coverage"] == "16/17"
    assert packet["final"]["w2_grades_invented"] is False
    assert packet["clear"] == "NO-GO"
    assert packet["coming_soon"] is True
    assert packet["final"]["public_paint"] is False
    assert "NFL_EDGE_BOARD_PUBLIC_ENABLED = false" in PUBLIC_FLAG.read_text(encoding="utf-8")
    assert "CFB_EDGE_BOARD_PUBLIC_ENABLED = false" in PUBLIC_FLAG.read_text(encoding="utf-8")


def test_frozen_predictive_fails_thin_n_and_floors() -> None:
    ev = frozen_eval_w1()
    grade = grade_predictive_validation(eval_report=ev)
    assert grade["tuning"] is False
    assert grade["ats_fitting"] is False
    assert grade["coefficient_changes"] is False
    assert grade["feature_additions"] is False
    assert grade["market_fitting"] is False
    assert grade["candidate_sha"] == PROD_CANDIDATE_SHA
    assert grade["n_w1"] == 16
    assert grade["can_protocol_green"] is False
    assert grade["can_protocol_yellow"] is False
    assert grade["floors"]["margin_floor_ok"] is False
    assert grade["floors"]["total_floor_ok"] is False
    assert grade["calibration"]["status"] == "N/A"
    assert grade["regression_checks"]["wl_circular_refused"]["refused"] is True
    assert float(grade["w1_oos"]["epa_margin_mae"]) > 9.5
    assert float(grade["w1_oos"]["epa_total_mae"]) > 10.5
    assert grade["verdict"] == "PARTIAL"
    assert grade["fail_closed"] is True
    assert grade["can_pass"] is False
    assert grade["w2_frozen"]["grades_invented"] is False
    assert grade["historical_oos_settled_w1"]["ran"] is True
    assert grade["historical_oos_settled_w1"]["touched_unsettled_w2"] is False
    assert grade["clear_blocks"] is True


def test_customer_view_17_uses_live_w2_and_rejects_july31_atl_gb() -> None:
    slate = build_customer_view_slate()
    keys = [g["key"] for g in slate["games"]]
    assert len(keys) == 17
    assert keys.count("ATL@GB") == 1
    w2 = [g for g in slate["games"] if g["week"] == 2]
    assert len(w2) == 16
    for game in w2:
        assert game["run_id"] == PROD_CANDIDATE_RUN_ID
        assert game["candidate_sha"] == PROD_CANDIDATE_SHA
        assert game["overlay_status"] == "OFF"
        assert game["freshness"]["july31_used_as_fair"] is False
        assert game["freshness"]["live_projection_used_as_fair"] is True
        assert game["fair_spread_home"] is not None
        assert game["fair_total"] is not None
        assert game["projected_score"]
        assert game["model_edge_spread"] is not None
        assert game["model_edge_total"] is not None
    atl = next(g for g in slate["games"] if g["key"] == "ATL@GB")
    assert atl["week"] == 3
    assert atl["run_id"] == ATL_GB_FILL_RUN_ID
    assert atl["freshness"]["july31_stale"] is True
    assert atl["freshness"]["july31_used_as_fair"] is False
    assert atl["freshness"]["live_projection_used_as_fair"] is False
    assert abs(float(atl["fair_spread_home"]) + 2.2744) < 0.01
    assert abs(float(atl["fair_total"]) - 46.0712) < 0.01
    assert abs(float(atl["fair_spread_home"]) - (-4.59)) > 1.0
    audit = audit_customer_view_slate(slate)
    assert audit["verdict"] == "PASS"
    assert audit["fair_coverage"] == "16/17"
    assert audit["ind_kc_dup_lacks_canonical_fair"] is True
    assert audit["alex_absurdity_flags_cited"] == []
    assert audit["complete_17"] is True
    assert audit["atl_gb_july31_rejected"] is True
    assert not audit["absurdities"]
    assert not audit["provenance_fail"]
