"""t4850u v2 EVAL_ONLY — Alex RO HARD-gap close. No public delivery. No E1."""

from __future__ import annotations

from src.services.nfl_offline_if_caller import REJECT_THROUGH_W8, evaluate_caller, sha256_file
from src.services.nfl_offline_if_eval_w8 import SUPPORTED_GAMES, TNF_GAME_ID
from src.services.nfl_offline_if_eval_w8_v2 import (
    PARENT_TIP,
    PARENT_TIP_FULL,
    V1_DIR,
    capture_cli,
    render_unresolved_md,
    run_eval_slate_v2,
)
from src.services.nfl_offline_if_eval_w8_v2 import (
    test_6_1_missing_field as induced_missing_field,
)
from src.services.nfl_offline_if_eval_w8_v2 import (
    test_6_3_pin_mismatch as pin_asof_mismatch,
)


def test_v1_packet_sealed_untouched():
    sha_file = V1_DIR / "SHA256SUMS"
    assert sha_file.is_file()
    for line in sha_file.read_text(encoding="utf-8").splitlines():
        digest, rel = line.split("  ", 1)
        assert sha256_file(V1_DIR / rel) == digest


def test_6_1_induced_missing_field_rejects():
    result = induced_missing_field()
    assert result["passed"] is True
    assert result["imputed"] is False
    assert result["exit_code"] == 2
    assert result["field"] == "home_off_epa_5g"
    assert "home_off_epa_5g" in result["message"]


def test_6_3_pin_asof_mismatch_rejects():
    result = pin_asof_mismatch()
    assert result["passed"] is True
    assert result["exit_code"] == 3
    assert all(case["rejected"] for case in result["cases"])


def test_operational_w8_and_w9_path_still_blocked():
    result = evaluate_caller(write=False)
    assert result.status == "BLOCKED"
    assert REJECT_THROUGH_W8 in result.codes
    assert result.e1_admissible is False


def test_eval_slate_v2_has_ml_and_reconciled_unresolved():
    artifacts = run_eval_slate_v2(write=False)
    packet = artifacts["packet"]
    assert packet["n_invoked"] == 13
    assert packet["e1_admissible"] is False
    assert packet["scoring_admissible_now"] is False
    assert packet["public_delivery"] is False
    assert packet["parent_v1_tip"] == PARENT_TIP
    assert PARENT_TIP in artifacts["manifest"]["commits_in_packet"]
    assert PARENT_TIP_FULL in artifacts["manifest"]["commits_in_packet"]
    assert artifacts["manifest"]["cmd"]
    assert artifacts["manifest"]["run_id"].startswith("eval-w8-t4850u-v2-")
    assert artifacts["call_audit"]["passed"] is True
    assert artifacts["call_audit"]["odds_calls"] == 0
    assert artifacts["call_audit"]["railway_calls"] == 0
    assert artifacts["call_audit"]["hl_adjustments"] == 0
    games = {row["game_id"] for row in artifacts["results"]}
    assert games == set(SUPPORTED_GAMES)
    assert TNF_GAME_ID not in games
    for row in artifacts["results"]:
        assert row["market_blend"] == 0
        assert row["forecast_class"] == "DIAGNOSTIC"
        assert row["home_win_prob"] is not None
        assert row["away_win_prob"] is not None
        assert row["fair_home_ml"] is not None
        assert row["fair_away_ml"] is not None
        assert row["ml_null_reason"] is None
        assert row["scoring_admissible_now"] is False
    unresolved = artifacts["unresolved"]
    assert unresolved["scoring_admissible_now"] is False
    assert unresolved["e1_admissible"] is False
    assert unresolved["invocation_failures"] == []
    assert unresolved["evidence_gaps"]
    md = render_unresolved_md(unresolved)
    for gap in unresolved["evidence_gaps"]:
        assert gap["id"] in md
    assert artifacts["logs"]["stdout"]
    assert "RUN_ID=" in artifacts["logs"]["stdout"]
    assert artifacts["findings"]["readiness_4_coherence"]["joint_st_ml"] == "INSUFFICIENT"


def test_cli_fail_closed_exits():
    one = capture_cli("--test-6-1-missing-field")
    assert one["exit_code"] == 2
    assert "home_off_epa_5g" in one["stdout"]
    three = capture_cli("--test-6-3-pin-mismatch")
    assert three["exit_code"] == 3
    assert "source_pin" in three["stdout"]
