"""t5213u R6 caller/ledger proofs. CERT=0. No fabricated IF mean."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.services.nfl_r6_caller.caller import (
    A_DEMO_PACKET,
    A_EXPECTED_BINDS,
    IF_TIP_PREFIX_CORRUPT,
    SPY,
    bind_a_api,
    consume_a_packet,
    locate_a_output,
    project_game,
    prove_real_mode_refuse,
    prove_ryan_cases,
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
    cutoff_from_kickoff,
    expected_c_mean,
    pin_block,
    require_full_pins,
)
from src.services.nfl_r6_caller.ledger import PairedArmLedger, make_seal_record


def _game(**overrides: object) -> dict:
    row = {
        "game_id": "SYNTHETIC_2018_W05_CTRL",
        "point_margin": {"if_mean": 3.0, "q2_mean": 1.0, "c_mean": 2.0},
        "input_hash": "a" * 64,
        "state_hash": "b" * 64,
        "config_hash": "c" * 64,
        "cutoff": cutoff_from_kickoff("2018-10-14T17:00:00Z"),
        "seed": 1,
    }
    row.update(overrides)
    return row


def _packet(**overrides: object) -> dict:
    packet = {
        "synthetic": True,
        "channel": "SYNTHETIC",
        "production_mode": False,
        "usable_by_real_mode": False,
        "if_tip": IF_TIP,
        "sim_sha256": pin_block()["sim_sha256"],
        "fw_sha256": pin_block()["fw_sha256"],
        "algorithm_tip": ALGORITHM_TIP,
        "games": [_game()],
    }
    packet.update(overrides)
    return packet


def test_pins_and_formula() -> None:
    assert IF_TIP.startswith("6ca03716")
    assert ALGORITHM_TIP.startswith("455a8e43")
    assert len(CONTRACT_27) == 27
    assert expected_c_mean(4.0, 2.0) == 3.0
    require_full_pins(_packet())


def test_real_mode_refuses_before_ledger(tmp_path: Path) -> None:
    SPY.install()
    SPY.reset()
    report = prove_real_mode_refuse()
    assert report["code"] == R6RefuseCode.REFUSE_REAL_MODE
    with pytest.raises(R6Refuse) as caught:
        refuse_real_mode("LIVE")
    assert caught.value.code == R6RefuseCode.REFUSE_REAL_MODE
    assert SPY.a_calls == 0
    assert SPY.model_calls == 0
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
        run_synthetic_e2e(
            ledger_root=tmp_path,
            a_path=tmp_path / "missing.json",
            live=False,
        )
    assert caught.value.code == R6RefuseCode.REFUSE_A_OUTPUT
    assert "fabricated" in caught.value.reason


def test_missing_pins_refuse() -> None:
    with pytest.raises(R6Refuse) as caught:
        consume_a_packet(_packet(if_tip=None))
    assert caught.value.code == R6RefuseCode.REFUSE_PIN


def test_wrong_full_if_pin_sharing_sha8_refuses() -> None:
    assert IF_TIP_PREFIX_CORRUPT.startswith(IF_TIP[:8])
    assert IF_TIP_PREFIX_CORRUPT != IF_TIP
    with pytest.raises(R6Refuse) as caught:
        consume_a_packet(_packet(if_tip=IF_TIP_PREFIX_CORRUPT))
    assert caught.value.code == R6RefuseCode.REFUSE_PIN


def test_schema_hash_as_input_or_config_refuses() -> None:
    schema = A_EXPECTED_BINDS["schema_hash"]
    with pytest.raises(R6Refuse) as caught:
        consume_a_packet(
            _packet(
                schema_hash=schema,
                games=[_game(input_hash=schema, config_hash=schema, state_hash="d" * 64)],
            )
        )
    assert caught.value.code == R6RefuseCode.REFUSE_HASH


def test_empty_state_hash_refuses() -> None:
    with pytest.raises(R6Refuse) as caught:
        consume_a_packet(_packet(games=[_game(state_hash="")]))
    assert caught.value.code == R6RefuseCode.REFUSE_HASH


def test_unparseable_kickoff_refuses() -> None:
    with pytest.raises(R6Refuse) as caught:
        consume_a_packet(_packet(games=[_game(cutoff={"kickoff_utc": "not-a-time"})]))
    assert caught.value.code == R6RefuseCode.REFUSE_CUTOFF


def test_tampered_seal_rejected_on_read_and_seal_without_overwrite(tmp_path: Path) -> None:
    proofs = prove_ryan_cases(tmp_path)
    assert proofs["tamper_read"] == R6RefuseCode.REFUSE_TAMPER
    assert proofs["tamper_seal"] == R6RefuseCode.REFUSE_TAMPER
    dest = tmp_path / "SYNTHETIC_2018_W05_KC_NE.json"
    raw = json.loads(dest.read_text(encoding="utf-8"))
    assert raw["arms"]["C"]["mean"] == 999
    assert raw["seal_id"] == "0" * 64


def test_consumes_complete_shaped_file(tmp_path: Path) -> None:
    packet = _packet()
    path = tmp_path / "a.json"
    path.write_text(json.dumps(packet), encoding="utf-8")
    result = run_synthetic_e2e(ledger_root=tmp_path / "led", a_path=path, live=False)
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


def test_formula_mismatch_refuses() -> None:
    packet = _packet(games=[_game(point_margin={"if_mean": 3.0, "q2_mean": 1.0, "c_mean": 9.0})])
    with pytest.raises(R6Refuse) as caught:
        project_game(consume_a_packet(packet)["games"][0])
    assert caught.value.code == R6RefuseCode.REFUSE_FORMULA


def test_no_hardcoded_a_demo_means() -> None:
    import src.services.nfl_r6_caller.caller as mod

    for name in ("A_DEMO_IF", "A_DEMO_Q2", "A_DEMO_C", "A_DEMO_SEED", "A_DEMO_GAME_ID"):
        assert not hasattr(mod, name)


def test_bind_a_api_does_not_invoke() -> None:
    SPY.install()
    SPY.reset()
    assert bind_a_api() == "call_r6_point_margin"
    assert SPY.a_calls == 0
    assert SPY.model_calls == 0


def test_make_seal_requires_both_arms(tmp_path: Path) -> None:
    record = make_seal_record(
        game_id="x",
        input_hash="a" * 64,
        state_hash="b" * 64,
        config_hash="c" * 64,
        cutoff=cutoff_from_kickoff("2018-10-14T17:00:00Z"),
        arms={"IF": {"status": "SEALED", "mean": 1.0}},
        refusals=[],
        manifest_id="m",
        synthetic=True,
    )
    led = PairedArmLedger(tmp_path)
    with pytest.raises(R6Refuse) as inner:
        led.seal(record)
    assert inner.value.code == R6RefuseCode.REFUSE_PARTIAL
    assert not (tmp_path / "x.json").exists()


def test_artifact_demo_result_is_not_full_proof() -> None:
    assert A_DEMO_PACKET.is_file()
    raw = json.loads(
        A_DEMO_PACKET.with_name("demo_result.json").read_text(encoding="utf-8")
    )
    assert raw["packet_hash"] == A_EXPECTED_BINDS["packet_hash"]
    assert raw["history_hash"] == A_EXPECTED_BINDS["history_hash"]
    assert raw["schema_hash"] != raw["packet_hash"]
    with pytest.raises(R6Refuse):
        consume_a_packet(raw)
