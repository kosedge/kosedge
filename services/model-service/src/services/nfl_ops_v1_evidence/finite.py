"""Finite-number gate.

Utility reused from #700 tip 9d436eb1
``eval_result_contract.require_finite`` (copied, not imported — that module
pulls real-outcome profiles we must not execute tonight).
"""

from __future__ import annotations

import math
from typing import Any

from src.services.nfl_ops_v1_evidence.refuse import EvidenceGateRefuse, RefuseClass


def require_finite(value: Any, name: str) -> float:
    if value is None:
        raise EvidenceGateRefuse(
            f"{name} is null — refuse",
            refuse_class=RefuseClass.NONFINITE,
        )
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EvidenceGateRefuse(
            f"{name} is not numeric — refuse (got {type(value).__name__})",
            refuse_class=RefuseClass.NONFINITE,
        )
    number = float(value)
    if math.isnan(number):
        raise EvidenceGateRefuse(f"{name} is NaN — refuse", refuse_class=RefuseClass.NONFINITE)
    if not math.isfinite(number):
        raise EvidenceGateRefuse(
            f"{name} is not finite — refuse",
            refuse_class=RefuseClass.NONFINITE,
        )
    return number


def require_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise EvidenceGateRefuse(
            f"{name} must be int (not bool/float/str; got {type(value).__name__})",
            refuse_class=RefuseClass.TYPE,
        )
    return value


def require_bool(value: Any, name: str) -> bool:
    if type(value) is not bool:
        raise EvidenceGateRefuse(
            f"{name} must be boolean (got {type(value).__name__})",
            refuse_class=RefuseClass.TYPE,
        )
    return value


def require_str(value: Any, name: str, *, nonempty: bool = True) -> str:
    if type(value) is not str:
        raise EvidenceGateRefuse(
            f"{name} must be str (got {type(value).__name__})",
            refuse_class=RefuseClass.TYPE,
        )
    if nonempty and not value:
        raise EvidenceGateRefuse(
            f"{name} empty — refuse",
            refuse_class=RefuseClass.INCOMPLETE,
        )
    return value
