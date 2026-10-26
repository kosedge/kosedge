"""t4359u local fair-line path — fail-closed, overlays off, schedule off."""

from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

import pytest

from src.services.nfl_enterprise_green_path import (
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
    spec_sha256,
    validate_game_card,
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
    assert out["markets"] is None


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
