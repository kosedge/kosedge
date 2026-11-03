"""NFL_JOINT_CONTRACT_V1 literal-law tests. Synthetic only. CERT=0.

Does not run inherited real-outcome tests.
Does not go through the Primary A evidence-manifest gate.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest

from src.services.nfl_joint_contract_v1.adapter import adapt_literal_law
from src.services.nfl_joint_contract_v1.constants import (
    EXPECTED_MEANS,
    EXPECTED_ML,
    EXPECTED_SPREAD,
    EXPECTED_TOTAL,
    KNOWN_SETTLEMENT_PROFILE,
    SYNTH_IDENTITY,
)
from src.services.nfl_joint_contract_v1.consume import consume_literal_law
from src.services.nfl_joint_contract_v1.freeze import require_freeze_intact
from src.services.nfl_joint_contract_v1.handoff import bind_handoff
from src.services.nfl_joint_contract_v1.oracle import partitions_from_law
from src.services.nfl_joint_contract_v1.refuse import JointContractRefuse, RefuseClass
from src.services.nfl_joint_contract_v1.run import run_literal_law_command
from src.services.nfl_joint_contract_v1.settlement import require_known_settlement
from src.services.nfl_joint_contract_v1.spy import (
    FORBIDDEN_CALL_ATTEMPTS,
    OutcomeReadSpy,
    run_spy_positive_control,
)

REPO = Path(__file__).resolve().parents[3]


@pytest.fixture(autouse=True)
def _reset_forbidden() -> Any:
    FORBIDDEN_CALL_ATTEMPTS.clear()
    yield
    FORBIDDEN_CALL_ATTEMPTS.clear()


def _refuse_class(exc: JointContractRefuse) -> str:
    return exc.refuse_class


def test_freeze_receipt_intact() -> None:
    receipt = require_freeze_intact(REPO)
    assert receipt["oracle_hash"] == "5480da107cd39e3a352a4ccb0059a6b3d7593d81b51ec7b0dab51e6a4721a3e0"
    assert receipt["schema_hash"] == "d541b593d7f612a1ad151f9701147d699116c0ac523dd2e342fc991b35c4ddf2"
    assert receipt["code_hash"] == "2e385e934bc08390a5949f82e40841a776358ef9d09d1d4fd66774706fa92561"
    assert receipt["receipt_hash"] == "8af1d54bb3f4c7ec25a99a95e7273f7d9e6f1ff8c4b23e2b04764ea29c32f91c"
    assert receipt["ready_for_review"] is False
    assert receipt["self_accept"] is False
    assert receipt["cert"] == 0


def test_oracle_partitions_sum_to_one() -> None:
    got = partitions_from_law()
    assert abs((got["ml"]["home_win"] + got["ml"]["away_win"] + got["ml"]["tie"]) - 1.0) < 1e-12
    assert abs((got["spread"]["cover"] + got["spread"]["push"] + got["spread"]["loss"]) - 1.0) < 1e-12
    assert abs((got["total"]["over"] + got["total"]["push"] + got["total"]["under"]) - 1.0) < 1e-12
    assert got["ml"]["home_win"] == EXPECTED_ML["home_win"]
    assert got["ml"]["away_win"] == EXPECTED_ML["away_win"]
    assert got["ml"]["tie"] == EXPECTED_ML["tie"]
    assert got["means"]["margin"] == EXPECTED_MEANS["margin"]
    assert got["means"]["total"] == EXPECTED_MEANS["total"]
    assert got["spread"]["cover"] == EXPECTED_SPREAD["cover"]
    assert got["spread"]["push"] == EXPECTED_SPREAD["push"]
    assert got["spread"]["loss"] == EXPECTED_SPREAD["loss"]
    assert got["total"]["over"] == EXPECTED_TOTAL["over"]
    assert got["total"]["push"] == EXPECTED_TOTAL["push"]
    assert got["total"]["under"] == EXPECTED_TOTAL["under"]


def test_ties_are_not_away_wins() -> None:
    got = partitions_from_law()
    assert got["ml"]["tie"] == 0.25
    assert got["ml"]["away_win"] == 0.25
    assert got["ml"]["tie"] != 0
    assert got["ml"]["away_win"] != got["ml"]["home_win"] + got["ml"]["tie"]


def test_adapter_positive() -> None:
    spy = OutcomeReadSpy()
    adapted = adapt_literal_law(root=REPO, outcome_spy=spy)
    assert adapted["ok"] is True
    assert adapted["fitted"] is False
    assert adapted["ready_for_review"] is False
    assert adapted["self_accept"] is False
    assert adapted["cert"] == 0
    assert adapted["identity"] == dict(SYNTH_IDENTITY)
    assert adapted["capability"]["bits"] == ["JOINT_LITERAL_LAW"]
    assert adapted["settlement"]["actionable"] is False
    assert adapted["settlement"]["fair_odds"] is None
    assert adapted["settlement"]["ev"] is None
    assert adapted["partitions"]["ml"]["tie"] == 0.25
    assert spy.reads == 0


def test_consume_and_handoff() -> None:
    spy = OutcomeReadSpy()
    adapted = adapt_literal_law(root=REPO, outcome_spy=spy)
    consumed = consume_literal_law(adapted, root=REPO, outcome_spy=spy)
    handoff = bind_handoff(consumed)
    assert consumed["consumed"] is True
    assert handoff["not_a_pass"] is True
    assert handoff["mocked_release"] is False
    assert handoff["state"] == "QUIESCENT"
    assert handoff["ready_for_review"] is False
    assert spy.reads == 0


def test_unknown_settlement_refuses_and_does_not_mint() -> None:
    spy = OutcomeReadSpy()
    with pytest.raises(JointContractRefuse) as exc:
        adapt_literal_law(
            root=REPO,
            settlement_profile="UNKNOWN",
            outcome_spy=spy,
        )
    assert _refuse_class(exc.value) == RefuseClass.SETTLEMENT
    assert exc.value.detail.get("settled_p") is None
    assert exc.value.detail.get("fair_odds") is None
    assert exc.value.detail.get("ev") is None
    assert exc.value.detail.get("actionable") is False
    assert spy.reads == 0
    assert FORBIDDEN_CALL_ATTEMPTS == []


@pytest.mark.parametrize("profile", [None, "", "DEV_IF437", "CENSORED_NORMAL_686"])
def test_unknown_or_foreign_settlement_refuses(profile: object) -> None:
    spy = OutcomeReadSpy()
    with pytest.raises(JointContractRefuse) as exc:
        require_known_settlement(profile)
    assert _refuse_class(exc.value) in {RefuseClass.SETTLEMENT, RefuseClass.TYPE}
    with pytest.raises(JointContractRefuse):
        adapt_literal_law(root=REPO, settlement_profile=profile, outcome_spy=spy)  # type: ignore[arg-type]
    assert spy.reads == 0


def test_real_mode_refuses_before_readers() -> None:
    spy = OutcomeReadSpy()
    with pytest.raises(JointContractRefuse) as exc:
        adapt_literal_law(root=REPO, data_label="REAL", outcome_spy=spy)
    assert _refuse_class(exc.value) == RefuseClass.REAL_MODE
    assert spy.reads == 0
    assert FORBIDDEN_CALL_ATTEMPTS == []


def test_if_r6_and_686_capability_refused() -> None:
    spy = OutcomeReadSpy()
    with pytest.raises(JointContractRefuse) as exc:
        adapt_literal_law(
            root=REPO,
            requested_output="IF_R6_POINT_MEANS",
            outcome_spy=spy,
        )
    assert _refuse_class(exc.value) == RefuseClass.CAPABILITY
    with pytest.raises(JointContractRefuse) as exc686:
        adapt_literal_law(
            root=REPO,
            requested_output="CENSORED_NORMAL_686",
            outcome_spy=spy,
        )
    assert _refuse_class(exc686.value) == RefuseClass.CAPABILITY
    assert spy.reads == 0


def test_denied_consumer_refused() -> None:
    spy = OutcomeReadSpy()
    adapted = adapt_literal_law(root=REPO, outcome_spy=spy)
    with pytest.raises(JointContractRefuse) as exc:
        consume_literal_law(adapted, consumer="fair_lines_api", root=REPO, outcome_spy=spy)
    assert _refuse_class(exc.value) == RefuseClass.CAPABILITY
    assert spy.reads == 0


def test_spy_positive_control_fires() -> None:
    result = run_spy_positive_control()
    assert result["spy_fired"] is True
    assert result["reads"] >= 1
    assert FORBIDDEN_CALL_ATTEMPTS == []


def test_integrated_command(tmp_path: Path) -> None:
    result = run_literal_law_command(dest_dir=tmp_path / "out", root=REPO)
    assert result["status"] == "GATED_OK_AWAITING_CHIEF"
    assert result["ready_for_review"] is False
    assert result["self_accept"] is False
    assert result["accepted"] is False
    assert result["cert"] == 0
    assert result["not_integrated_through_evidence_gate"] is True
    assert result["handoff"]["not_a_pass"] is True
    assert result["spy_positive_control"]["spy_fired"] is True
    assert result["partitions"]["means"]["margin"] == 1.5
    assert result["partitions"]["means"]["total"] == 44.5


def test_cli_exit_zero(tmp_path: Path) -> None:
    from src.services.nfl_joint_contract_v1.run import main

    assert main([str(tmp_path / "cli")]) == 0


def test_identity_mutation_refused() -> None:
    spy = OutcomeReadSpy()
    adapted = adapt_literal_law(root=REPO, outcome_spy=spy)
    mutated = copy.deepcopy(adapted)
    mutated["identity"]["game_id"] = "2024_01_KC_BUF"
    with pytest.raises(JointContractRefuse) as exc:
        consume_literal_law(mutated, root=REPO, outcome_spy=spy)
    assert _refuse_class(exc.value) == RefuseClass.IDENTITY
    assert spy.reads == 0
