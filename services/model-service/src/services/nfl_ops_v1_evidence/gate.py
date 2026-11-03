"""Executable evidence-manifest gates on the synthetic caller path.

``gate_before_consume`` runs after produce_fixture_chain and BEFORE
consume_fixture_chain / any data reader.
``gate_before_final_receipt`` runs before any receipt write or READY_FOR_REVIEW.
Neither function mints ALLOW objects. CERT=0.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional

from src.services.nfl_ops_v1_evidence.constants import STAGE_PRE_CONSUME, STAGE_PRE_RECEIPT
from src.services.nfl_ops_v1_evidence.refuse import EvidenceGateRefuse, RefuseClass
from src.services.nfl_ops_v1_evidence.spy import (
    ForbiddenSurfaceSpy,
    OutcomeReadSpy,
    assert_zero_forbidden_on_refusal,
)
from src.services.nfl_ops_v1_evidence.validate import validate_manifest


def gate_before_consume(
    manifest: Mapping[str, Any],
    *,
    chain_payload: Optional[Mapping[str, Any]] = None,
    outcome_spy: Optional[OutcomeReadSpy] = None,
    surface: Optional[ForbiddenSurfaceSpy] = None,
) -> dict[str, Any]:
    spy = outcome_spy if outcome_spy is not None else OutcomeReadSpy()
    try:
        if getattr(spy, "reads", 0) not in (None, 0):
            raise EvidenceGateRefuse(
                "outcome loader already read — refuse (join-before-gate)",
                refuse_class=RefuseClass.SPY,
            )
        return validate_manifest(
            manifest, stage=STAGE_PRE_CONSUME, chain_payload=chain_payload
        )
    except Exception:
        assert_zero_forbidden_on_refusal(outcome_spy=spy, surface=surface)
        raise


def gate_before_final_receipt(
    manifest: Mapping[str, Any],
    *,
    chain_payload: Optional[Mapping[str, Any]] = None,
    outcome_spy: Optional[OutcomeReadSpy] = None,
    surface: Optional[ForbiddenSurfaceSpy] = None,
) -> dict[str, Any]:
    spy = outcome_spy if outcome_spy is not None else OutcomeReadSpy()
    try:
        if getattr(spy, "reads", 0) not in (None, 0):
            raise EvidenceGateRefuse(
                "outcome loader already read — refuse (join-before-receipt)",
                refuse_class=RefuseClass.SPY,
            )
        return validate_manifest(
            manifest, stage=STAGE_PRE_RECEIPT, chain_payload=chain_payload
        )
    except Exception:
        assert_zero_forbidden_on_refusal(outcome_spy=spy, surface=surface)
        raise


def assert_ready_for_review_allowed(
    manifest: Mapping[str, Any],
    *,
    chain_payload: Optional[Mapping[str, Any]] = None,
    chief_verified: bool = False,
    outcome_spy: Optional[OutcomeReadSpy] = None,
) -> dict[str, Any]:
    """Chief-only stamp. Passing logs are not self-acceptance."""
    gated = gate_before_final_receipt(
        manifest, chain_payload=chain_payload, outcome_spy=outcome_spy
    )
    if not chief_verified:
        raise EvidenceGateRefuse(
            "READY_FOR_REVIEW requires Chief verification — not self-stamped",
            refuse_class=RefuseClass.READY_FOR_REVIEW,
        )
    return gated


def stamp_ready_for_review(
    manifest: Mapping[str, Any],
    *,
    chain_payload: Optional[Mapping[str, Any]] = None,
    chief_verified: bool = False,
    outcome_spy: Optional[OutcomeReadSpy] = None,
) -> dict[str, Any]:
    gated = assert_ready_for_review_allowed(
        manifest,
        chain_payload=chain_payload,
        chief_verified=chief_verified,
        outcome_spy=outcome_spy,
    )
    out = dict(gated)
    out["ready_for_review"] = True
    out["accepted"] = False
    out["cert"] = 0
    return out
