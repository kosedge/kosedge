"""Four-layer provenance + failure codes (Phase 1).

RAW → DERIVED → ADJUSTED → MODELED

Opponent adjustment is ADJUSTED unless a genuinely fitted model is involved.
MODELED is reserved for estimated/fitted outputs and is not produced here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Layer(str, Enum):
    RAW = "RAW"
    DERIVED = "DERIVED"
    ADJUSTED = "ADJUSTED"
    MODELED = "MODELED"


class Status(str, Enum):
    OK = "OK"
    THIN = "THIN"
    PRIOR_ONLY = "PRIOR_ONLY"
    PARTIAL = "PARTIAL"
    DATA_INSUFFICIENT = "DATA_INSUFFICIENT"
    EXCLUDED_GAME = "EXCLUDED_GAME"
    OMIT = "OMIT"


# Sample floors from #569. Thin labels — never silent fills.
THIN_PLAYS_STD = 80
THIN_GAMES_STD = 2
THIN_PASS_SPLIT = 40
THIN_RUSH_SPLIT = 40
THIN_ST_PLAYS = 40
THIN_ST_GAME = 8
THIN_DRIVES_GAME = 4
THIN_OPPORTUNITIES_STD = 8
CLOCK_NULL_MAX = 0.02
SCORE_DIFF_NULL_MAX = 0.05
EPA_NULL_PARTIAL = 0.01


@dataclass
class Component:
    """One published (or refused) measurement cell."""

    id: str
    value: Optional[float]
    unit: str
    layer: Layer
    status: Status
    n: int = 0
    missing_fields: List[str] = field(default_factory=list)
    notes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "value": self.value,
            "unit": self.unit,
            "layer": self.layer.value,
            "status": self.status.value,
            "n": int(self.n),
            "missing_fields": list(self.missing_fields),
            "notes": dict(self.notes),
            "production_promote": False,
        }


def derived(
    metric_id: str,
    value: Optional[float],
    *,
    unit: str,
    n: int,
    thin_n: Optional[int] = None,
    missing_fields: Optional[List[str]] = None,
    notes: Optional[Dict[str, Any]] = None,
    partial: bool = False,
    required: bool = True,
) -> Component:
    """Publish a DERIVED cell or refuse it. Never fills a missing mean."""
    miss = list(missing_fields or [])
    extra = dict(notes or {})
    if value is None or (required and n <= 0):
        return Component(
            id=metric_id,
            value=None,
            unit=unit,
            layer=Layer.DERIVED,
            status=Status.DATA_INSUFFICIENT if required else Status.OMIT,
            n=int(n),
            missing_fields=miss,
            notes=extra,
        )
    if partial:
        status = Status.PARTIAL
    elif thin_n is not None and n < thin_n:
        status = Status.THIN
    else:
        status = Status.OK
    return Component(
        id=metric_id,
        value=float(value),
        unit=unit,
        layer=Layer.DERIVED,
        status=status,
        n=int(n),
        missing_fields=miss,
        notes=extra,
    )


def adjusted(
    metric_id: str,
    value: Optional[float],
    *,
    unit: str,
    n: int,
    notes: Optional[Dict[str, Any]] = None,
    missing_fields: Optional[List[str]] = None,
) -> Component:
    if value is None or n <= 0:
        return Component(
            id=metric_id,
            value=None,
            unit=unit,
            layer=Layer.ADJUSTED,
            status=Status.DATA_INSUFFICIENT,
            n=int(n),
            missing_fields=list(missing_fields or []),
            notes=dict(notes or {}),
        )
    return Component(
        id=metric_id,
        value=float(value),
        unit=unit,
        layer=Layer.ADJUSTED,
        status=Status.OK if n >= THIN_GAMES_STD else Status.THIN,
        n=int(n),
        missing_fields=list(missing_fields or []),
        notes=dict(notes or {}),
    )


def omitted(metric_id: str, *, unit: str, reason: str) -> Component:
    return Component(
        id=metric_id,
        value=None,
        unit=unit,
        layer=Layer.DERIVED,
        status=Status.OMIT,
        n=0,
        missing_fields=[],
        notes={"reason": reason, "do_not_impute": True},
    )


def modeled_forbidden(metric_id: str, *, unit: str = "epa_per_play") -> Component:
    """Phase 1 must not emit MODELED cells."""
    return Component(
        id=metric_id,
        value=None,
        unit=unit,
        layer=Layer.MODELED,
        status=Status.OMIT,
        n=0,
        notes={
            "reason": "MODELED reserved for fitted estimators; not Phase 1",
            "see": "docs/ratings/KE_FOOTBALL_V1_PROVENANCE_AMEND_2026-09-15.md",
        },
    )


def modeled(
    metric_id: str,
    value: Optional[float],
    *,
    unit: str,
    n: int,
    notes: Optional[Dict[str, Any]] = None,
    missing_fields: Optional[List[str]] = None,
    thin_n: Optional[int] = None,
) -> Component:
    """Publish a MODELED cell. Never fills a missing mean. Not a production promote."""
    extra = dict(notes or {})
    extra.setdefault("production_promote", False)
    if value is None or n <= 0:
        return Component(
            id=metric_id,
            value=None,
            unit=unit,
            layer=Layer.MODELED,
            status=Status.DATA_INSUFFICIENT,
            n=int(n),
            missing_fields=list(missing_fields or []),
            notes=extra,
        )
    status = Status.THIN if (thin_n is not None and n < thin_n) else Status.OK
    return Component(
        id=metric_id,
        value=float(value),
        unit=unit,
        layer=Layer.MODELED,
        status=status,
        n=int(n),
        missing_fields=list(missing_fields or []),
        notes=extra,
    )
