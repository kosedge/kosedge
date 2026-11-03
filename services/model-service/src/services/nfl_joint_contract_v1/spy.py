"""Spy controls. Refuse paths must leave loader/network/DB/job at zero. CERT=0."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Mapping

from src.services.nfl_joint_contract_v1.refuse import JointContractRefuse, RefuseClass

FORBIDDEN_CALL_ATTEMPTS: List[str] = []


class OutcomeReadSpy:
    """Counts target-outcome / loader reads. Must stay 0 on refuse."""

    def __init__(
        self, fn: Callable[[], Mapping[str, Mapping[str, Any]]] | None = None
    ) -> None:
        self.reads = 0
        self.ids_returned: list[str] = []
        self._fn = fn

    def __call__(self) -> Mapping[str, Mapping[str, Any]]:
        self.reads += 1
        FORBIDDEN_CALL_ATTEMPTS.append("outcome_loader")
        loaded = self._fn() if self._fn is not None else {}
        self.ids_returned = list(loaded)
        return loaded


class ForbiddenSurfaceSpy:
    def __init__(self) -> None:
        self.calls: List[str] = []

    def note(self, name: str) -> None:
        self.calls.append(name)
        FORBIDDEN_CALL_ATTEMPTS.append(name)

    @property
    def count(self) -> int:
        return len(self.calls)


def assert_zero_forbidden_on_refusal(
    *,
    outcome_spy: OutcomeReadSpy | None = None,
    surface: ForbiddenSurfaceSpy | None = None,
) -> None:
    if outcome_spy is not None and int(getattr(outcome_spy, "reads", 0) or 0) != 0:
        raise JointContractRefuse(
            "target-outcome / loader was read on refusal",
            refuse_class=RefuseClass.SPY,
        )
    if surface is not None and surface.count != 0:
        raise JointContractRefuse(
            f"forbidden surface spy fired on refusal ({surface.calls})",
            refuse_class=RefuseClass.SPY,
        )
    if FORBIDDEN_CALL_ATTEMPTS:
        raise JointContractRefuse(
            f"forbidden_call_attempts={list(FORBIDDEN_CALL_ATTEMPTS)} on refusal",
            refuse_class=RefuseClass.FORBIDDEN_CALL,
        )


def run_spy_positive_control() -> Dict[str, Any]:
    """Prove the spy fires. A zero-only spy is not a control."""
    FORBIDDEN_CALL_ATTEMPTS.clear()
    spy = OutcomeReadSpy()
    surface = ForbiddenSurfaceSpy()
    spy()
    surface.note("joint_literal_instrumentation_probe")
    if spy.reads < 1 or surface.count < 1 or not FORBIDDEN_CALL_ATTEMPTS:
        raise JointContractRefuse(
            "spy-positive control failed — spy did not fire",
            refuse_class=RefuseClass.SPY,
        )
    reads = spy.reads
    notes = surface.count
    attempts = list(FORBIDDEN_CALL_ATTEMPTS)
    FORBIDDEN_CALL_ATTEMPTS.clear()
    return {
        "ran": True,
        "spy_fired": True,
        "reads": reads,
        "surface_notes": notes,
        "forbidden_call_attempts": len(attempts),
        "evidence_label": "EXECUTED_HERE",
    }
