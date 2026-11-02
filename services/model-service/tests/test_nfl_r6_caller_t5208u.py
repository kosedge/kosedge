"""t5208u R6 caller/ledger proofs. CERT=0. No fabricated IF mean."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.services.nfl_r6_caller.caller import (
    consume_a_packet,
    locate_a_output,
    project_game,
    prove_real_mode_refuse,
    prove_seal_refuses,
    refuse_real_mode,
    run_synthetic_e2e,
    seal_projected,
)
from src.services.nfl_r6_caller.contract import (
    ALGORITHM_TIP,
    CONTRACT_27,
    IF_TIP,
    R6Refuse,
    R6RefuseCode,
    expected_c_mean,
)
from src.services.nfl_r6_caller.ledger import PairedArmLedger, make_seal_record


def test_pins_and_formula() -> None:
    assert IF_TIP.startswith("6ca03716")
    assert ALGORITHM_TIP.startswith("455a8e43")
    assert len(CONTRACT_27) == 27
    assert expected_c_mean(4.0, 2.0) == 3.0


def test_real_mode_refuses_before_ledger(tmp_path: Path) -> None:
    report = prove_real_mode_refuse()
    assert report["code"] == R6RefuseCode.REFUSE_REAL_MODE
    with pytest.raises(R6Refuse) as caught:
        refuse_real_mode("LIVE")
    assert caught.value.code == R6RefuseCode.REFUSE_REAL_MODE
    assert not list(tmp_path.glob("*.json"))


def test_dup_race_partial(tmp_path: Path) -> None:
    proofs = prove_seal_refuses(tmp_path)
    assert proofs["duplicate"] == R6RefuseCode.REFUSE_DUPLICATE
    assert proofs["race"] == R6RefuseCode.REFUSE_RACE
    assert proofs["partial_write"] == R6RefuseCode.REFUSE_PARTIAL
    assert proofs["leftover_tmp"] == R6RefuseCode.REFUSE_PARTIAL
    assert not (tmp_path / "2026_99_R6_PARTIAL.json").exists()


def test_absent_a_does_not_invent_if(tmp_path: Path) -> None:
    assert locate_a_output(tmp_path / "missing.json") is None
    with pytest.raises(R6Refuse) as caught:
        run_synthetic_e2e(ledger_root=tmp_path, a_path=tmp_path / "missing.json")
    assert caught.value.code == R6RefuseCode.REFUSE_A_OUTPUT
    assert "fabricated" in caught.value.reason


def test_consumes_actual_a_shaped_file(tmp_path: Path) -> None:
    """Only when a file is supplied — values are the file's, not invented by B."""
    packet = {
        "synthetic": True,
        "channel": "SYNTHETIC",
        "production_mode": False,
        "usable_by_real_mode": False,
        "if_tip": IF_TIP,
        "algorithm_tip": ALGORITHM_TIP,
        "contract_27": list(CONTRACT_27),
        "games": [
            {
                "game_id": "2026_99_R6_SYN",
                "point_margin": {"if_mean": 3.0, "q2_mean": 1.0, "c_mean": 2.0},
                "input_hash": "a" * 64,
                "state_hash": "b" * 64,
                "config_hash": "c" * 64,
                "cutoff": {"kickoff_ts": "2026-11-08T18:00:00Z"},
            }
        ],
    }
    path = tmp_path / "a.json"
    path.write_text(json.dumps(packet), encoding="utf-8")
    result = run_synthetic_e2e(ledger_root=tmp_path / "led", a_path=path)
    assert result["status"] == "OK"
    assert result["sealed"][0]["arms"]["IF"]["mean"] == 3.0
    assert result["sealed"][0]["arms"]["C"]["mean"] == 2.0
    again = PairedArmLedger(tmp_path / "led")
    with pytest.raises(R6Refuse) as caught:
        seal_projected(
            again,
            project_game(packet["games"][0]),
            manifest_id="again",
        )
    assert caught.value.code == R6RefuseCode.REFUSE_DUPLICATE


def test_formula_mismatch_refuses(tmp_path: Path) -> None:
    packet = {
        "synthetic": True,
        "channel": "SYNTHETIC",
        "production_mode": False,
        "games": [
            {
                "game_id": "2026_99_BAD_C",
                "point_margin": {"if_mean": 3.0, "q2_mean": 1.0, "c_mean": 9.0},
            }
        ],
    }
    with pytest.raises(R6Refuse) as caught:
        project_game(consume_a_packet(packet)["games"][0])
    assert caught.value.code == R6RefuseCode.REFUSE_FORMULA


def test_make_seal_requires_both_arms(tmp_path: Path) -> None:
    record = make_seal_record(
        game_id="x",
        input_hash="0" * 64,
        state_hash="0" * 64,
        config_hash="0" * 64,
        cutoff={},
        arms={"IF": {"status": "SEALED"}},
        refusals=[],
        manifest_id="m",
        synthetic=True,
    )
    led = PairedArmLedger(tmp_path)
    with pytest.raises(R6Refuse) as inner:
        led.seal(record)
    assert inner.value.code == R6RefuseCode.REFUSE_PARTIAL
    assert not (tmp_path / "x.json").exists()
