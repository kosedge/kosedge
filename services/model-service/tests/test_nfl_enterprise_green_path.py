"""t4359u local fair-line path — fail-closed, overlays off, schedule off."""

from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

import pytest

from src.services.nfl_enterprise_green_path import (
    CERT_STATUS_NOT_CERTIFIED,
    DISCLOSURE,
    FIXTURE_CLASS_ENGINEERING,
    GATE_MATRIX_SHA8,
    IFB_SCOPE_SHA8,
    REASON_MISSING,
    REASON_SILENT_DEFAULT,
    REASON_T7_NEUTRAL,
    REASON_UNKNOWN_HFA,
    REASON_UNKNOWN_INJURY_ZERO,
    SPEC_ID,
    SPEC_VERSION,
    FailClosed,
    demo_home_card,
    fingerprint,
    run_local_fair_line,
    run_local_slate,
    run_local_week,
    spec_sha256,
    validate_game_card,
    week6_boundary_slate,
    weekly_pipeline_schedule_enabled,
)
from src.services.nfl_epa_authority import overlays_must_stay_off
from src.services.nfl_regression_diagnose import LOCKED_SCORING

WORKFLOW = (
    Path(__file__).resolve().parents[3]
    / ".github"
    / "workflows"
    / "nfl-weekly-operate.yml"
)
SPEC = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "nfl"
    / "NFL_MODEL_SPEC_t4359u_v1.md"
)


def test_schedule_stays_disabled_by_default() -> None:
    assert weekly_pipeline_schedule_enabled() is False
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "schedule:" in text
    # Cron remains commented. Dispatch-only.
    assert "# schedule:" in text
    assert 'cron: "30 12 * * 2"' in text
    enabled_cron = [
        line
        for line in text.splitlines()
        if line.strip().startswith("cron:") and not line.lstrip().startswith("#")
    ]
    assert enabled_cron == []


def test_overlays_remain_off() -> None:
    assert overlays_must_stay_off(force_overlays_off=True, unlock_overlays=False) is True
    assert overlays_must_stay_off(completed_reg_season=16, force_overlays_off=True) is True


def test_demo_home_card_is_deterministic() -> None:
    a = run_local_fair_line(demo_home_card())
    b = run_local_fair_line(demo_home_card())
    assert a["status"] == "READY"
    assert b["status"] == "READY"
    assert a["fingerprint"] == b["fingerprint"]
    assert a["fair_spread_home"] == b["fair_spread_home"]
    assert a["fair_total"] == b["fair_total"]
    assert a["home_win_prob"] == b["home_win_prob"]
    assert a["spec_id"] == SPEC_ID
    assert a["spec_version"] == SPEC_VERSION
    assert a["spec_sha256"] == spec_sha256()
    assert a["overlays_off"] is True
    assert a["injury_status"] == "OVERLAY_OFF_UNAVAILABLE"
    assert a["unknown_injury_treated_as_zero"] is False
    assert a["injury_applied"] is False
    assert a["hfa_status"] == "LOCKED_HOME_1_05"
    assert a["hfa_points"] == LOCKED_SCORING["home_field_points"]
    assert a["schedule_enabled"] is False
    assert a["publication"] == "NFL_NO_GO"
    assert a["reason_codes"] == []
    assert a["ifb_candidate"] is False
    assert a["injury_model_none_by_design"] is False
    assert a["cert_status_spread"] == CERT_STATUS_NOT_CERTIFIED
    assert a["cert_status_total"] == CERT_STATUS_NOT_CERTIFIED
    assert a["cert_status_ml"] == CERT_STATUS_NOT_CERTIFIED
    assert a["markets_certified_separately"] == GATE_MATRIX_SHA8
    assert a["ifb_scope_sha8"] == IFB_SCOPE_SHA8
    assert a["total_play_enabled"] is False
    assert a["total_product_claim"] is False
    assert a["fixture_class"] == FIXTURE_CLASS_ENGINEERING
    assert a["no_holdout_tuning"] is True
    assert a["independent_repro"] == "MISSING"
    assert a["week_cap_null_postgres"] == "NOT_EVIDENCED"
    assert a["disclosure"] == DISCLOSURE
    assert "do not account for injuries" in a["disclosure"].lower()
    assert a["coming_soon"] is True
    assert a["market_blend"] is False
    assert a["totals_calibration"] is False
    assert a["fair_spread_home"] is not None
    assert a["fair_total"] is not None
    assert 0.0 < float(a["home_win_prob"]) < 1.0
    assert float(a["home_win_prob"]) + float(a["away_win_prob"]) == pytest.approx(1.0)
    assert a["strength"]["home"]["strength_source"] == "packaged_epa_prior"
    body = deepcopy(a)
    body.pop("fingerprint")
    assert a["fingerprint"] == fingerprint(body)


def test_missing_required_input_blocks() -> None:
    card = demo_home_card()
    del card["kickoff_utc"]
    out = run_local_fair_line(card)
    assert out["status"] == "BLOCKED"
    assert REASON_MISSING in out["reason_codes"]
    assert out["reason_codes"]
    assert out["markets"] is None
    assert out["ifb_candidate"] is False
    assert out["cert_status_spread"] == CERT_STATUS_NOT_CERTIFIED


def test_unknown_hfa_blocks() -> None:
    card = demo_home_card()
    card["site_class"] = "UNKNOWN"
    out = run_local_fair_line(card)
    assert out["status"] == "BLOCKED"
    assert REASON_UNKNOWN_HFA in out["reason_codes"]
    assert out["markets"] is None


def test_neutral_site_is_t7_blocked_not_invented() -> None:
    card = demo_home_card()
    card["site_class"] = "NEUTRAL"
    out = run_local_fair_line(card)
    assert out["status"] == "BLOCKED"
    assert REASON_T7_NEUTRAL in out["reason_codes"]
    assert out["markets"] is None


def test_silent_rest_seven_refused() -> None:
    card = demo_home_card()
    del card["rest_days_home_source"]
    out = run_local_fair_line(card)
    assert out["status"] == "BLOCKED"
    assert REASON_SILENT_DEFAULT in out["reason_codes"]


def test_silent_index_one_refused() -> None:
    card = demo_home_card()
    card["offense_index_home"] = 1.0
    card["defense_index_home"] = 1.0
    out = run_local_fair_line(card)
    assert out["status"] == "BLOCKED"
    assert REASON_SILENT_DEFAULT in out["reason_codes"]


def test_unknown_injury_zero_refused() -> None:
    card = demo_home_card()
    card["injury_nowcast_impact_home"] = 0.0
    out = run_local_fair_line(card)
    assert out["status"] == "BLOCKED"
    assert REASON_UNKNOWN_INJURY_ZERO in out["reason_codes"]
    assert out["reason_codes"]


def test_injury_zero_even_explicit_is_fail_closed_not_ifb() -> None:
    card = demo_home_card()
    card["injury_impact"] = 0.0
    card["injury_impact_source"] = "explicit_named_value"
    out = run_local_fair_line(card)
    assert out["status"] == "BLOCKED"
    assert REASON_UNKNOWN_INJURY_ZERO in out["reason_codes"]
    assert out["ifb_candidate"] is False
    assert out["injury_model_none_by_design"] is False


def test_unlock_overlays_refused() -> None:
    card = demo_home_card()
    card["unlock_overlays"] = True
    out = run_local_fair_line(card)
    assert out["status"] == "BLOCKED"


def test_explicit_strength_round_trip() -> None:
    card = demo_home_card()
    gated = validate_game_card(card)
    card["offense_index_home"] = gated["home"]["offense_index"]
    card["defense_index_home"] = gated["home"]["defense_index"]
    card["offense_index_away"] = gated["away"]["offense_index"]
    card["defense_index_away"] = gated["away"]["defense_index"]
    card["offense_index_home_source"] = "explicit_named_value"
    card["defense_index_home_source"] = "explicit_named_value"
    card["offense_index_away_source"] = "explicit_named_value"
    card["defense_index_away_source"] = "explicit_named_value"
    out = run_local_fair_line(card)
    assert out["status"] == "READY"
    assert out["strength"]["home"]["strength_source"] == "explicit"


def test_slate_blocks_do_not_invent_neighbors() -> None:
    good = demo_home_card()
    bad = demo_home_card()
    bad["game_id"] = "t4359u-BAD"
    bad["site_class"] = "UNKNOWN"
    slate = run_local_slate([good, bad])
    assert slate["n_ready"] == 1
    assert slate["n_blocked"] == 1
    assert slate["rows"][0]["status"] == "READY"
    assert slate["rows"][1]["status"] == "BLOCKED"
    assert slate["schedule_enabled"] is False
    assert slate["publication"] == "NFL_NO_GO"


def test_spec_file_is_versioned() -> None:
    text = SPEC.read_text(encoding="utf-8")
    assert SPEC_ID in text
    assert SPEC_VERSION in text
    assert "Do not reopen or rerun accepted W4–W6 seals" in text or "does **not** reopen" in text
    assert "T7" in text
    assert "ADD141" in text
    assert "Not the IFB candidate" in text or "not the IFB candidate" in text
    assert "41effd43" in text
    assert "6f1a95b9" in text
    assert "test_nfl_week_cap_bind.py" in text
    assert "NOT EVIDENCED" in text
    assert "MISSING" in text
    assert "ENGINEERING FIXTURE" in text
    assert "TOTAL_PLAY" in text
    assert "no_holdout_tuning" in text
    assert "non-empty" in text
    sha = spec_sha256()
    assert len(sha) == 64


def test_schedule_env_refuses_local_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NFL_WEEKLY_PIPELINE_SCHEDULE_ENABLED", "true")
    with pytest.raises(FailClosed) as exc:
        validate_game_card(demo_home_card())
    assert exc.value.reason == "SCHEDULE_REFUSED"


def test_demo_receipt_is_json_serializable() -> None:
    out = run_local_fair_line(demo_home_card())
    json.dumps(out)


def test_t7_expectation_stays_frozen() -> None:
    """t4366u: do not pick A or B until Ryan authorizes after the IMV packet."""
    text = SPEC.read_text(encoding="utf-8")
    assert "This spec does not pick A or B." in text
    assert (
        "| `NEUTRAL` | Refuse. Reason `T7_BLOCKED_NEUTRAL_SITE`. No invented 0.0 HFA |"
        in text
    )
    assert REASON_T7_NEUTRAL == "T7_BLOCKED_NEUTRAL_SITE"


def test_overview_null_week_assertion_untouched() -> None:
    """Frozen overview/SQL null-week bind. Do not edit that test for t4366u."""
    week_cap = (
        Path(__file__).resolve().parent / "test_nfl_week_cap_bind.py"
    ).read_text(encoding="utf-8")
    assert "def test_prior_season_null_week_cap_sql_is_typed() -> None:" in week_cap
    assert "CAST(:week_cap AS int) IS NULL" in week_cap
    assert "params[\"week_cap\"] is None" in week_cap


def test_week6_manual_pipeline_home_ready_t7_and_null_week_block() -> None:
    slate = run_local_week(week6_boundary_slate())
    assert slate["schedule_enabled"] is False
    assert slate["pipeline"] == "local_weekly_manual"
    assert slate["n_ready"] == 2
    assert slate["n_blocked"] == 3
    by_id = {row.get("game_id"): row for row in slate["rows"]}
    assert by_id["t4359u-DEMO-KC@BUF"]["status"] == "READY"
    assert by_id["t4366u-BOUNDARY-GB@DET"]["status"] == "READY"
    assert by_id["t4366u-T7-NEUTRAL-XXX"]["reason_codes"] == [REASON_T7_NEUTRAL]
    assert by_id["t4366u-NULL-WEEK-NO@GO"]["reason_codes"] == [REASON_MISSING]
    assert by_id["t4366u-NO-EPA-ZZ@BUF"]["status"] == "BLOCKED"
    assert by_id["t4366u-NO-EPA-ZZ@BUF"]["reason_codes"]
    assert slate["t7_status"] == "FROZEN_PENDING_RYAN_AFTER_IMV_PACKET"
    assert slate["fixture_class"] == FIXTURE_CLASS_ENGINEERING
    assert slate["ifb_candidate"] is False
    for row in slate["rows"]:
        if row["status"] == "READY":
            assert row["reason_codes"] == []
        else:
            assert row["reason_codes"]
    again = run_local_week(week6_boundary_slate())
    assert again["fingerprint"] == slate["fingerprint"]


def test_explicit_null_week_does_not_inherit_from_slate() -> None:
    card = demo_home_card()
    card["game_id"] = "t4366u-NULL-WEEK-CARD"
    card["week"] = None
    slate = run_local_week({"season": 2026, "week": 6, "cards": [card]})
    assert slate["n_ready"] == 0
    assert slate["rows"][0]["reason_codes"] == [REASON_MISSING]
    assert slate["rows"][0]["reason_codes"]
