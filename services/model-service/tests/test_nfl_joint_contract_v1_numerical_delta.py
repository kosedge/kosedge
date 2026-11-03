"""t5271u numerical delta. Additive. Historical 79-test suite stays the prior bar.

CERT=0. SYNTHETIC_ONLY. Does not run inherited real-outcome tests.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from src.services.nfl_joint_contract_v1.adapter import adapt_literal_law
from src.services.nfl_joint_contract_v1.consume import (
    NUMERICAL_SINGLE_FAULTS,
    apply_numerical_fault,
    consume_literal_law,
    run_numerical_single_faults,
)
from src.services.nfl_joint_contract_v1.refuse import JointContractRefuse, RefuseClass
from src.services.nfl_joint_contract_v1.spy import FORBIDDEN_CALL_ATTEMPTS, OutcomeReadSpy

REPO = Path(__file__).resolve().parents[3]


@pytest.fixture(autouse=True)
def _reset_forbidden() -> Any:
    FORBIDDEN_CALL_ATTEMPTS.clear()
    yield
    FORBIDDEN_CALL_ATTEMPTS.clear()


def test_adapter_positive_still_passes() -> None:
    spy = OutcomeReadSpy()
    adapted = adapt_literal_law(root=REPO, outcome_spy=spy)
    consumed = consume_literal_law(adapted, root=REPO, outcome_spy=spy)
    assert consumed["supplied_law_recomputed"] is True
    assert consumed["partitions"]["means"]["margin"] == 1.5
    assert consumed["partitions"]["n"] == 4
    assert consumed["partitions"]["weight_sum"] == 1.0
    assert consumed["outcomes"][0]["margin"] == 3
    assert spy.reads == 0


@pytest.mark.parametrize("case", [name for name, _fn in NUMERICAL_SINGLE_FAULTS])
def test_direct_consumer_refuses_numerical_single_fault(case: str) -> None:
    spy = OutcomeReadSpy()
    adapted = adapt_literal_law(root=REPO, outcome_spy=spy)
    mutated = apply_numerical_fault(adapted, case)
    with pytest.raises(JointContractRefuse):
        consume_literal_law(mutated, root=REPO, outcome_spy=spy)
    assert spy.reads == 0
    assert FORBIDDEN_CALL_ATTEMPTS == []


def test_integrated_path_refuses_numerical_single_faults(tmp_path: Path) -> None:
    from src.services.nfl_joint_contract_v1.integrate import run_joint_integrated_command

    result = run_joint_integrated_command(dest_dir=tmp_path / "int", root=REPO)
    faults = result["numerical_single_faults"]
    assert faults["ran"] is True
    assert faults["all_refused"] is True
    assert faults["n"] == len(NUMERICAL_SINGLE_FAULTS)
    names = {row["case"] for row in faults["faults"]}
    assert names == {name for name, _fn in NUMERICAL_SINGLE_FAULTS}
    assert all(row["refused"] is True and row["forbidden_calls"] == 0 for row in faults["faults"])
    assert result["receipt_head_vs_tip"]["not_silently_rebound"] is True
    assert result["historical_t5266u"]["pytest_passed"] == 79
    assert result["residuals_remain_explicit"] == [
        "PE R1",
        "PE R2",
        "PE R3",
        "PE R4",
        "PE R5",
        "Alex D-a",
        "C1",
    ]


def test_run_numerical_battery_zero_forbidden() -> None:
    spy = OutcomeReadSpy()
    adapted = adapt_literal_law(root=REPO, outcome_spy=spy)
    report = run_numerical_single_faults(adapted, root=REPO)
    assert report["all_refused"] is True
    assert report["forbidden_calls"] == 0
    assert spy.reads == 0


def test_equal_extra_home_score_alias_refuses() -> None:
    spy = OutcomeReadSpy()
    adapted = adapt_literal_law(root=REPO, outcome_spy=spy)
    mutated = apply_numerical_fault(adapted, "equal_extra_home_score")
    assert mutated["outcomes"][0]["home_score"] == mutated["outcomes"][0]["home"]
    with pytest.raises(JointContractRefuse) as exc:
        consume_literal_law(mutated, root=REPO, outcome_spy=spy)
    assert exc.value.refuse_class == RefuseClass.TYPE
    assert "extra alias" in exc.value.reason
    assert spy.reads == 0
    assert FORBIDDEN_CALL_ATTEMPTS == []
