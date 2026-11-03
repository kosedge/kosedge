"""Typed evidence-manifest refuse. Not ACCEPT. Not READY_FOR_REVIEW. CERT=0."""

from __future__ import annotations

from typing import Any, Dict, Optional


class RefuseClass:
    INCOMPLETE = "INCOMPLETE"
    EXTRA = "EXTRA"
    TYPE = "TYPE"
    STALE = "STALE"
    HASH_MUTATED = "HASH_MUTATED"
    WRONG_PROFILE_IDENTITY = "WRONG_PROFILE_IDENTITY"
    WRONG_COUNT = "WRONG_COUNT"
    NONFINITE = "NONFINITE"
    SAVED_OUTPUT_ONLY = "SAVED_OUTPUT_ONLY"
    IMPORT_ONLY = "IMPORT_ONLY"
    REAL_MODE = "REAL_MODE"
    CAPABILITY = "CAPABILITY"
    CHANNEL = "CHANNEL"
    CUTOFF = "CUTOFF"
    PAIRED_ARM = "PAIRED_ARM"
    WRITE_TAMPER = "WRITE_TAMPER"
    CONSUMER = "CONSUMER"
    WORKER_HANDOFF = "WORKER_HANDOFF"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    SPY = "SPY"
    FORBIDDEN_CALL = "FORBIDDEN_CALL"
    MISSING_CONTEXT = "MISSING_CONTEXT"
    COMMAND = "COMMAND"
    EXIT = "EXIT"


class EvidenceGateRefuse(ValueError):
    """Fail-closed evidence gate. Does not mint ALLOW objects."""

    def __init__(
        self,
        reason: str,
        *,
        refuse_class: str,
        detail: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.reason = reason
        self.refuse_class = refuse_class
        self.detail = dict(detail or {})
        self.ready_for_review = False
        self.accepted = False
        self.partial = False
        super().__init__(f"EVIDENCE GATE REFUSE [{refuse_class}] {reason}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": False,
            "refuse_class": self.refuse_class,
            "reason": self.reason,
            "detail": dict(self.detail),
            "ready_for_review": False,
            "accepted": False,
            "partial": False,
            "cert": 0,
        }
