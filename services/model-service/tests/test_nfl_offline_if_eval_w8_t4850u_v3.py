"""t4850u v3 EVAL_ONLY re-execution. v2 remains sealed baseline."""

from __future__ import annotations

from src.services.nfl_offline_if_caller import REJECT_THROUGH_W8, evaluate_caller, sha256_file
from src.services.nfl_offline_if_eval_w8 import SUPPORTED_GAMES, TNF_GAME_ID
from src.services.nfl_offline_if_eval_w8_v2 import V1_DIR, V2_DIR
from src.services.nfl_offline_if_eval_w8_v3 import (
    REST_FIX_TIP,
    V2_INVOKE_PARENT,
    V2_PACKET_TIP,
    V3_DIR,
    run_eval_slate_v3,
)


def _assert_sealed(folder) -> None:
    for line in (folder / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        digest, rel = line.split("  ", 1)
        assert sha256_file(folder / rel) == digest


def test_v1_and_v2_packets_sealed():
    _assert_sealed(V1_DIR)
    _assert_sealed(V2_DIR)
    stdout = (V2_DIR / "INVOKE_STDOUT.txt").read_text(encoding="utf-8")
    assert f"HEAD={V2_INVOKE_PARENT}" in stdout


def test_operational_path_still_blocked():
    result = evaluate_caller(write=False)
    assert result.status == "BLOCKED"
    assert REJECT_THROUGH_W8 in result.codes


def test_v3_rerun_before_after_vs_v2():
    artifacts = run_eval_slate_v3(write=False)
    packet = artifacts["packet"]
    assert packet["n_invoked"] == 13
    assert packet["e1_admissible"] is False
    assert packet["public_delivery"] is False
    assert artifacts["manifest"]["invoke_head_matches_execution_tip"] is True
    assert artifacts["manifest"]["baseline_v2_packet_tip"] == V2_PACKET_TIP
    assert artifacts["manifest"]["rest_fix_tip"] == REST_FIX_TIP
    games = {row["game_id"] for row in artifacts["results"]}
    assert games == set(SUPPORTED_GAMES)
    assert TNF_GAME_ID not in games
    by_elig = {row["game_id"]: row for row in artifacts["eligibility"]}
    assert by_elig["2026-W08-PHI@WAS"]["rest"]["rest_days_home"] == 7.0
    assert by_elig["2026-W08-CHI@SEA"]["rest"]["rest_days_home"] == 6.0
    ba = artifacts["before_after"]
    assert ba["phi_was_changed"] is True
    assert ba["chi_sea_changed"] is True
    changed_ids = {item["game_id"] for item in ba["changed"]}
    assert "2026-W08-PHI@WAS" in changed_ids
    assert "2026-W08-CHI@SEA" in changed_ids
    for game_id in SUPPORTED_GAMES:
        if game_id in changed_ids:
            continue
        assert game_id in ba["unchanged"]
    assert artifacts["call_audit"]["passed"] is True
    assert f"HEAD={artifacts['manifest']['execution_tip']}" in artifacts["logs"]["stdout"]
    assert artifacts["manifest"]["execution_tip"] != V2_INVOKE_PARENT
