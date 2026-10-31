"""t4838u — offline Independent Fair caller (synthetic negatives + dry-run).

No admissible E1 labels. No 2026 W8 invention. No sportsbook. IF(blend=0).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.services.nfl_offline_if_caller import (
    ASOF_BOUNDARY_SHA8,
    ASOF_MODULE_SHA256,
    CALLER_MODE_OPERATIONAL,
    CONTRACT_SHA8,
    FORECAST_CLASS_WIRING_ONLY,
    IF_SOURCE_PIN_SHA256,
    IF_SOURCE_PIN_SHA8,
    REJECT_ASOF,
    REJECT_CUTOFF,
    REJECT_E1,
    REJECT_HISTORY,
    REJECT_HL,
    REJECT_INPUTS,
    REJECT_SOURCE_PIN,
    REJECT_SPORTSBOOK,
    REJECT_TARGET_ID,
    REJECT_THROUGH_W8,
    OfflineIfCallerReject,
    OfflineIfRequest,
    build_contract_inputs,
    enforce_asof_and_history,
    evaluate_caller,
    invoke_independent_fair,
    lineage_pins,
    synthetic_wiring_request,
    verify_asof_module,
    verify_source_pin,
    wiring_probe,
)
from src.services.nfl_pregame_asof import (
    IF_MATCHUP_PREGAME_FROM_SQL,
    IF_MATCHUP_ROLLING_JOIN_HOME,
    PINNED_IF_MATCHUP_JOIN_HOME,
)


def _accept_file(path: Path, *, accept: bool) -> Path:
    payload = {
        "status": "DATA_ACCEPT" if accept else "DATA_PARTIAL",
        "data_accept": accept,
        "note": "synthetic test flag only",
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _operational(req: OfflineIfRequest) -> OfflineIfRequest:
    req.mode = CALLER_MODE_OPERATIONAL
    return req


def test_lineages_are_reported_distinct():
    pins = lineage_pins()
    assert pins["source_only"]["sha8"] == IF_SOURCE_PIN_SHA8
    assert pins["source_only"]["status"] == "SOURCE_ONLY"
    assert pins["source_only"]["ratified"] == "75d1b695"
    assert pins["as_of"]["sha8"] == ASOF_BOUNDARY_SHA8
    assert pins["as_of"]["status"] == "PASS_ASOF_BOUNDARY"
    assert pins["as_of"]["distinct_from_source_pin_52d9e909"] is True
    assert pins["as_of"]["sha8"] != pins["source_only"]["sha8"]
    assert pins["contract"]["sha8"] == CONTRACT_SHA8
    assert pins["contract"]["pass_contract_sha8"] == "1a53bbd3"
    assert pins["w8"]["status"] == "DATA_PARTIAL"
    assert pins["w8"]["invent_w8"] is False


def test_source_and_asof_pins_match_disk():
    assert verify_source_pin() == IF_SOURCE_PIN_SHA256
    assert verify_asof_module() == ASOF_MODULE_SHA256
    assert IF_SOURCE_PIN_SHA256 != ASOF_MODULE_SHA256


def test_through_w8_accept_missing_fail_closed(tmp_path: Path):
    req = _operational(synthetic_wiring_request())
    with pytest.raises(OfflineIfCallerReject) as exc:
        invoke_independent_fair(req, through_w8_path=tmp_path / "missing.json")
    assert exc.value.code == REJECT_THROUGH_W8


def test_through_w8_partial_is_not_accept(tmp_path: Path):
    path = _accept_file(tmp_path / "w8.json", accept=False)
    req = _operational(synthetic_wiring_request())
    with pytest.raises(OfflineIfCallerReject) as exc:
        invoke_independent_fair(req, through_w8_path=path)
    assert exc.value.code == REJECT_THROUGH_W8


def test_missing_target_game_id_fail_closed():
    from src.services.nfl_offline_if_caller import require_target_identifiers

    req = synthetic_wiring_request()
    req.game_id = ""
    with pytest.raises(OfflineIfCallerReject) as exc:
        require_target_identifiers(req)
    assert exc.value.code == REJECT_TARGET_ID


def test_missing_forecast_cutoff_fail_closed():
    req = synthetic_wiring_request()
    req.forecast_cutoff_ts = ""
    with pytest.raises(OfflineIfCallerReject) as exc:
        enforce_asof_and_history(req)
    assert exc.value.code == REJECT_CUTOFF


def test_naive_forecast_cutoff_fail_closed():
    req = synthetic_wiring_request()
    req.forecast_cutoff_ts = "2099-11-01T00:00:00"
    with pytest.raises(OfflineIfCallerReject) as exc:
        enforce_asof_and_history(req)
    assert exc.value.code == REJECT_CUTOFF


def test_same_week_rating_is_leakage():
    req = synthetic_wiring_request()
    req.rating_week = 9
    with pytest.raises(OfflineIfCallerReject) as exc:
        enforce_asof_and_history(req)
    assert exc.value.code == REJECT_ASOF
    assert "same-week" in exc.value.message or "not < target_week" in exc.value.message


def test_unavailable_history_fail_closed():
    req = synthetic_wiring_request()
    req.available_rating_weeks = (4, 5, 6, 7)
    with pytest.raises(OfflineIfCallerReject) as exc:
        enforce_asof_and_history(req)
    assert exc.value.code == REJECT_HISTORY


def test_target_game_cannot_enter_history():
    req = synthetic_wiring_request()
    req.history_games = req.history_games + (
        {
            "week": 9,
            "game_id": req.game_id,
            "game_date": "2099-11-01",
            "kickoff_ts": "2099-11-01T17:00:00Z",
        },
    )
    with pytest.raises(OfflineIfCallerReject) as exc:
        enforce_asof_and_history(req)
    assert exc.value.code == REJECT_ASOF


def test_incomplete_required_field_fail_closed():
    req = synthetic_wiring_request()
    efficiency = dict(req.efficiency)
    del efficiency["home_off_epa_5g"]
    req.efficiency = efficiency
    with pytest.raises(OfflineIfCallerReject) as exc:
        build_contract_inputs(req)
    assert exc.value.code == REJECT_INPUTS


def test_non_finite_required_field_fail_closed():
    req = synthetic_wiring_request()
    efficiency = dict(req.efficiency)
    efficiency["away_pass_rate_5g"] = float("nan")
    req.efficiency = efficiency
    with pytest.raises(OfflineIfCallerReject) as exc:
        build_contract_inputs(req)
    assert exc.value.code == REJECT_INPUTS


def test_unapproved_hl_fail_closed():
    req = synthetic_wiring_request()
    req.extra = {"injury_nowcast_impact_home": 0.4}
    with pytest.raises(OfflineIfCallerReject) as exc:
        build_contract_inputs(req)
    assert exc.value.code == REJECT_HL


def test_kav_and_travel_are_unapproved_hl():
    req = synthetic_wiring_request()
    req.efficiency = dict(req.efficiency, home_kav_net_5g=0.12)
    with pytest.raises(OfflineIfCallerReject) as exc:
        build_contract_inputs(req)
    assert exc.value.code == REJECT_HL


def test_sportsbook_forbidden():
    req = synthetic_wiring_request()
    req.extra = {"market_spread_home": -3.5, "market_total": 44.5}
    with pytest.raises(OfflineIfCallerReject) as exc:
        build_contract_inputs(req)
    assert exc.value.code == REJECT_SPORTSBOOK


def test_source_pin_mismatch_fail_closed(tmp_path: Path):
    fake = tmp_path / "nfl_simulator.py"
    fake.write_text("not-the-source-pin\n", encoding="utf-8")
    with pytest.raises(OfflineIfCallerReject) as exc:
        verify_source_pin(simulator_path=fake)
    assert exc.value.code == REJECT_SOURCE_PIN


def test_week1_target_fail_closed():
    req = synthetic_wiring_request()
    req.matchup_week = 1
    req.rating_week = None
    req.available_rating_weeks = ()
    with pytest.raises(OfflineIfCallerReject) as exc:
        enforce_asof_and_history(req)
    assert exc.value.code == REJECT_TARGET_ID


def test_wiring_probe_is_if_blend_zero_and_not_e1():
    probe = wiring_probe()
    assert probe["market_blend"] == 0
    assert probe["independent_fair_invoked"] is True
    assert probe["forecast_class"] == FORECAST_CLASS_WIRING_ONLY
    assert probe["e1"] is False
    assert probe["e1_admissible"] is False
    assert probe["e1_label"] is None
    assert probe["scoring_admissible"] is False
    assert probe["matchup_season"] == 2099
    assert probe["digest"]
    again = wiring_probe()
    assert again["digest"] == probe["digest"]
    assert again["margin_mu"] == probe["margin_mu"]
    assert again["total_mu"] == probe["total_mu"]


def test_evaluate_is_blocked_without_w8_accept(tmp_path: Path):
    result = evaluate_caller(through_w8_path=tmp_path / "absent.json", write=False)
    assert result.status == "BLOCKED"
    assert result.blocked is True
    assert result.e1_admissible is False
    assert REJECT_THROUGH_W8 in result.codes
    assert result.wiring is not None
    assert result.wiring["forecast_class"] == FORECAST_CLASS_WIRING_ONLY
    from src.services.nfl_offline_if_caller import remaining_owner_e1_clear_conditions

    remaining = [item["id"] for item in remaining_owner_e1_clear_conditions()]
    assert "W8_DATA_READY" in remaining
    assert "IMV_THROUGH_W8_DATA_ACCEPT" in remaining
    assert "OWNER_E1_CLEAR" in remaining


def test_operational_invoke_still_not_e1_when_w8_accept_forced(tmp_path: Path):
    """Even a forced ACCEPT file cannot label the invoke as E1."""
    path = _accept_file(tmp_path / "w8.json", accept=True)
    req = _operational(synthetic_wiring_request())
    payload = invoke_independent_fair(req, through_w8_path=path)
    assert payload["e1_admissible"] is False
    assert payload["e1"] is False
    assert payload["forecast_class"] == "NONE"
    assert payload["market_blend"] == 0
    payload["e1_admissible"] = True
    with pytest.raises(OfflineIfCallerReject) as exc:
        from src.services.nfl_offline_if_caller import _forbid_e1_label

        _forbid_e1_label(payload)
    assert exc.value.code == REJECT_E1


def test_asof_sql_is_lagged_not_pin_same_week():
    assert PINNED_IF_MATCHUP_JOIN_HOME != IF_MATCHUP_ROLLING_JOIN_HOME
    assert "h.week = (s.week - 1)" in IF_MATCHUP_ROLLING_JOIN_HOME
    assert "h.week = s.week" in PINNED_IF_MATCHUP_JOIN_HOME
    assert IF_MATCHUP_ROLLING_JOIN_HOME in IF_MATCHUP_PREGAME_FROM_SQL
    assert "g.game_date >= s.game_date" in IF_MATCHUP_PREGAME_FROM_SQL


def test_executed_sql_week_w_gets_w_minus_1_and_target_row_cannot_enter():
    import sqlite3

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE nfl_dp_schedules (
          season INT, week INT, game_id TEXT, game_date TEXT,
          home_team TEXT, away_team TEXT,
          home_score INT, away_score INT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE nfl_dp_team_rolling_features_weekly (
          season INT, week INT, team TEXT, off_epa_per_play_5g REAL
        )
        """
    )
    conn.executemany(
        "INSERT INTO nfl_dp_schedules VALUES (?,?,?,?,?,?,?,?)",
        [
            (2099, 8, "G-W8", "2099-10-25", "SYN", "OPP", 21, 17),
            (2099, 9, "G-W9", "2099-11-01", "SYN", "OPP", None, None),
        ],
    )
    conn.executemany(
        "INSERT INTO nfl_dp_team_rolling_features_weekly VALUES (?,?,?,?)",
        [
            (2099, 8, "SYN", 0.10),
            (2099, 9, "SYN", 0.99),
            (2099, 8, "OPP", -0.02),
        ],
    )
    sql = f"""
        SELECT s.week, s.game_id, h.week AS home_rating_week,
               h.off_epa_per_play_5g AS home_off_epa_5g
        {IF_MATCHUP_PREGAME_FROM_SQL}
    """
    rows = {int(r["week"]): dict(r) for r in conn.execute(sql, {"season": 2099})}
    assert rows[9]["home_rating_week"] == 8
    assert rows[9]["home_off_epa_5g"] == 0.10
    assert rows[9]["home_off_epa_5g"] != 0.99
    assert rows[8]["home_rating_week"] is None
    conn.close()
