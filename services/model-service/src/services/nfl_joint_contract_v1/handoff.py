"""Handoff semantics for the literal-law successor. Not platform reclaim. CERT=0."""

from __future__ import annotations

from typing import Any, Mapping

from src.services.nfl_joint_contract_v1.constants import (
    CERT,
    CONTRACT_HASH,
    CONTRACT_ID,
    PACKAGE,
    TASK_ID,
)
from src.services.nfl_joint_contract_v1.refuse import JointContractRefuse, RefuseClass

HANDOFF_SCHEMA = "nfl-joint-contract-v1-handoff-v1"
HANDOFF_STATE = "QUIESCENT"
HANDOFF_KIND = "SYNTHETIC_PARTIAL"


def bind_handoff(consumed: Mapping[str, Any]) -> dict[str, Any]:
    if consumed.get("ok") is not True or consumed.get("consumed") is not True:
        raise JointContractRefuse(
            "handoff requires a consumed synthetic adapter record",
            refuse_class=RefuseClass.INCOMPLETE,
        )
    if consumed.get("ready_for_review") is True or consumed.get("self_accept") is True:
        raise JointContractRefuse(
            "handoff cannot self-stamp READY_FOR_REVIEW / self_accept",
            refuse_class=RefuseClass.ACTIONABLE,
        )
    return {
        "schema": HANDOFF_SCHEMA,
        "field": "worker_handoff",
        "package": PACKAGE,
        "contract_id": CONTRACT_ID,
        "contract_hash": CONTRACT_HASH,
        "task_id": TASK_ID,
        "state": HANDOFF_STATE,
        "release_kind": HANDOFF_KIND,
        "not_a_pass": True,
        "mocked_release": False,
        "bound": True,
        "cert": CERT,
        "ready_for_review": False,
        "self_accept": False,
        "accepted": False,
        "freeze_receipt_hash": consumed.get("freeze_receipt_hash"),
        "note": (
            "Synthetic literal-law handoff only. Not Primary A evidence-gate integration. "
            "Not platform reclaim. PLATFORM_LIMITATION of #712 is a different record."
        ),
    }
