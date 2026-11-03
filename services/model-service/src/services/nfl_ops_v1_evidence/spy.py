"""Spy controls for forbidden loader / model / network / DB / job calls.

``OutcomeReadSpy`` reused from #700 tip 9d436eb1
``verify_integrate.OutcomeReadSpy``. Forbidden-call surface wraps the
#707/#706 ``chain_guard`` (tips f2c72e8b / 644c517d).
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Mapping

from src.services.nfl_fixture_assembly.assemble import FORBIDDEN_CALL_ATTEMPTS
from src.services.nfl_fixture_assembly.contract import FixtureHardRefuse
from src.services.nfl_fixture_assembly.guard import chain_guard, last_guard_report
from src.services.nfl_ops_v1_evidence.refuse import EvidenceGateRefuse, RefuseClass


class OutcomeReadSpy:
    """Counts target-outcome / loader reads. Gates must leave this at zero on refuse."""

    def __init__(
        self, fn: Callable[[], Mapping[str, Mapping[str, Any]]] | None = None
    ) -> None:
        self.reads = 0
        self.ids_returned: list[str] = []
        self._fn = fn

    def __call__(self) -> Mapping[str, Mapping[str, Any]]:
        self.reads += 1
        loaded = self._fn() if self._fn is not None else {}
        self.ids_returned = list(loaded)
        return loaded


class ForbiddenSurfaceSpy:
    """Records loader/model/network/DB/job attempts observed by this gate."""

    def __init__(self) -> None:
        self.calls: List[str] = []

    def note(self, name: str) -> None:
        self.calls.append(name)

    @property
    def count(self) -> int:
        return len(self.calls)


def assert_zero_forbidden_on_refusal(
    *,
    outcome_spy: OutcomeReadSpy,
    surface: ForbiddenSurfaceSpy | None = None,
) -> None:
    report = last_guard_report()
    if int(getattr(outcome_spy, "reads", 0) or 0) != 0:
        raise EvidenceGateRefuse(
            "target-outcome / loader was read on refusal — refuse",
            refuse_class=RefuseClass.SPY,
        )
    extra = 0 if surface is None else surface.count
    if extra != 0:
        raise EvidenceGateRefuse(
            f"forbidden surface spy fired on refusal ({surface.calls})",
            refuse_class=RefuseClass.SPY,
        )
    if int(report.get("forbidden_call_attempts") or 0) != 0:
        raise EvidenceGateRefuse(
            f"forbidden_call_attempts={report.get('forbidden_call_attempts')} on refusal",
            refuse_class=RefuseClass.FORBIDDEN_CALL,
        )


def run_spy_positive_control() -> Dict[str, Any]:
    """Prove the spy fires. A zero-only spy is not a control."""
    FORBIDDEN_CALL_ATTEMPTS.clear()
    refused = False
    reason = ""
    with chain_guard():
        try:
            import socket

            socket.getaddrinfo("example.test", 80)
        except FixtureHardRefuse as exc:
            refused = True
            reason = str(exc)
    report = last_guard_report()
    attempts = int(report.get("forbidden_call_attempts") or 0)
    if not refused or attempts < 1:
        raise EvidenceGateRefuse(
            "spy-positive control failed — spy did not fire",
            refuse_class=RefuseClass.SPY,
            detail={"refused": refused, "attempts": attempts},
        )
    FORBIDDEN_CALL_ATTEMPTS.clear()
    return {
        "ran": True,
        "spy_fired": True,
        "refused": True,
        "forbidden_call_attempts": attempts,
        "reason": reason,
        "evidence_label": "EXECUTED_HERE",
    }
