"""t4850u EVAL_ONLY — W8 diagnostic path. No public delivery. No E1."""

from __future__ import annotations

import pytest

from src.services.nfl_offline_if_caller import (
    REJECT_THROUGH_W8,
    evaluate_caller,
)
from src.services.nfl_offline_if_eval_w8 import (
    BYE_ROLLING_AS_OF,
    PANEL_SHA256,
    REJECT_PUBLICATION,
    REJECT_TNF,
    SUPPORTED_GAMES,
    TARGET_WEEK,
    TNF_GAME_ID,
    EvalW8Reject,
    _eligibility_row,
    history_w1_w7,
    load_panel,
    load_schedule,
    publication_controls,
    refuse_public_delivery,
    rest_days_from_schedule,
    rest_days_from_schedule_utc,
    run_eval_slate,
    verify_rest_days,
)


def test_panel_pin_and_no_tnf_in_ratings():
    panel = load_panel()
    assert panel["as_of_week"] == 7
    assert panel["2025_prior_used"] is False
    assert PANEL_SHA256.startswith("340a06dd")
    for team, row in panel["teams"].items():
        assert int(row["rolling_as_of_week"]) < TARGET_WEEK
        assert int(row["as_of_week"]) == 7
    for bye, week in BYE_ROLLING_AS_OF.items():
        assert panel["teams"][bye]["rolling_as_of_week"] == week


def test_lar_alias_and_tnf_excluded():
    panel = load_panel()
    schedule = load_schedule()
    by_id = {g["game_id"]: g for g in schedule["games"]}
    elig = _eligibility_row(
        game_id="2026-W08-LAC@LAR",
        schedule_game=by_id["2026-W08-LAC@LAR"],
        panel=panel,
    )
    assert elig["panel_home"] == "LA"
    assert elig["home_team"] == "LAR"
    assert elig["away_rolling_as_of"] == 6
    with pytest.raises(EvalW8Reject) as exc:
        _eligibility_row(
            game_id=TNF_GAME_ID,
            schedule_game=by_id[TNF_GAME_ID],
            panel=panel,
        )
    assert exc.value.code == REJECT_TNF


def test_history_is_w1_w7_only():
    hist = history_w1_w7(load_schedule())
    assert all(row["week"] <= 7 for row in hist)
    assert all(row["game_id"] != TNF_GAME_ID for row in hist)
    assert any(row["week"] == 7 for row in hist)


def test_publication_controls_refuse_public_delivery():
    packet = {
        "e1_admissible": False,
        "scoring_admissible": False,
        "public_delivery": False,
        "forecast_class": "DIAGNOSTIC",
    }
    controls = refuse_public_delivery(packet)
    assert controls["enabled"] is False
    assert controls["public_delivery"] is False
    assert controls["free_public"] == "REFUSED"
    assert controls["betting"] == "BLOCKED"
    assert controls["coming_soon"] == "ON"
    assert controls["cert"] == 0
    assert controls["paid_edge_language"] is False
    with pytest.raises(EvalW8Reject) as exc:
        publication_controls({**packet, "public_delivery": True})
    assert exc.value.code == REJECT_PUBLICATION


def test_operational_w8_and_w9_path_untouched():
    result = evaluate_caller(write=False)
    assert result.status == "BLOCKED"
    assert REJECT_THROUGH_W8 in result.codes
    assert result.e1_admissible is False


def test_eval_slate_invokes_13_diagnostic_only():
    artifacts = run_eval_slate(write=False)
    packet = artifacts["packet"]
    assert packet["n_supported"] == 13
    assert packet["n_invoked"] == 13
    assert packet["e1_admissible"] is False
    assert packet["public_delivery"] is False
    assert packet["publication_controls"]["enabled"] is False
    assert packet["tnf_excluded"] == TNF_GAME_ID
    assert packet["operational_path"]["blocked"] is True
    games = {row["game_id"] for row in artifacts["results"] if row.get("independent_fair_invoked")}
    assert games == set(SUPPORTED_GAMES)
    assert TNF_GAME_ID not in games
    for row in artifacts["results"]:
        if row.get("independent_fair_invoked"):
            assert row["market_blend"] == 0
            assert row["forecast_class"] == "DIAGNOSTIC"
            assert row["e1_admissible"] is False
            assert row["rating_week"] == 7
            assert row["target_week"] == 8
    rest_flags = [
        row["rest"]["status"]
        for row in artifacts["eligibility"]
        if row.get("status") == "SUPPORTED"
    ]
    assert rest_flags and all(flag == "VERIFY_AT_CONSUME" for flag in rest_flags)
    assert artifacts["findings"]["readiness_4_coherence"]["joint_st_ml"] == "INSUFFICIENT"


PHI_WAS_KICK = "2026-11-02T01:20:00.000Z"  # Sunday 21:20 ET
CHI_SEA_KICK = "2026-11-03T01:15:00.000Z"  # Monday 20:15 ET


def test_phi_was_sunday_et_not_utc_monday():
    rest = verify_rest_days(PHI_WAS_KICK)
    assert rest["dow_et"] == 6
    assert rest["dow_utc"] == 0
    assert rest["utc_et_dow_mismatch"] is True
    assert rest["status"] == "VERIFY_AT_CONSUME"
    assert rest["rest_days_home"] == 7.0
    assert rest["rest_days_away"] == 7.0
    assert rest["rest_days_utc_heuristic"] == 6.0
    assert rest["heuristic_inverted_if_utc"] is True
    assert rest_days_from_schedule(PHI_WAS_KICK) == 7.0
    assert rest_days_from_schedule_utc(PHI_WAS_KICK) == 6.0


def test_chi_sea_monday_et_not_utc_tuesday():
    rest = verify_rest_days(CHI_SEA_KICK)
    assert rest["dow_et"] == 0
    assert rest["dow_utc"] == 1
    assert rest["utc_et_dow_mismatch"] is True
    assert rest["status"] == "VERIFY_AT_CONSUME"
    assert rest["rest_days_home"] == 6.0
    assert rest["rest_days_away"] == 6.0
    assert rest["rest_days_utc_heuristic"] == 7.0
    assert rest["heuristic_inverted_if_utc"] is True
    assert rest_days_from_schedule(CHI_SEA_KICK) == 6.0
    assert rest_days_from_schedule_utc(CHI_SEA_KICK) == 7.0


def test_w8_eligibility_rest_uses_et_and_keeps_verify_on_mismatch():
    panel = load_panel()
    schedule = load_schedule()
    by_id = {g["game_id"]: g for g in schedule["games"]}
    phi = _eligibility_row(
        game_id="2026-W08-PHI@WAS",
        schedule_game=by_id["2026-W08-PHI@WAS"],
        panel=panel,
    )
    chi = _eligibility_row(
        game_id="2026-W08-CHI@SEA",
        schedule_game=by_id["2026-W08-CHI@SEA"],
        panel=panel,
    )
    assert phi["rest"]["rest_days_home"] == 7.0
    assert chi["rest"]["rest_days_home"] == 6.0
    assert phi["rest"]["utc_et_dow_mismatch"] is True
    assert chi["rest"]["utc_et_dow_mismatch"] is True
    assert phi["rest"]["status"] == "VERIFY_AT_CONSUME"
    assert chi["rest"]["status"] == "VERIFY_AT_CONSUME"
    ari = _eligibility_row(
        game_id="2026-W08-ARI@DAL",
        schedule_game=by_id["2026-W08-ARI@DAL"],
        panel=panel,
    )
    assert ari["rest"]["utc_et_dow_mismatch"] is False
    assert ari["rest"]["rest_days_home"] == 7.0
    assert ari["rest"]["status"] == "VERIFY_AT_CONSUME"
