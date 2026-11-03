"""Typed refuse for NFL_JOINT_CONTRACT_V1. Not ACCEPT. CERT=0."""

from __future__ import annotations

from typing import Any, Dict, Optional


class RefuseClass:
    INCOMPLETE = "INCOMPLETE"
    TYPE = "TYPE"
    HASH_MUTATED = "HASH_MUTATED"
    SETTLEMENT = "SETTLEMENT"
    IDENTITY = "IDENTITY"
    NONFINITE = "NONFINITE"
    PARTITION = "PARTITION"
    REAL_MODE = "REAL_MODE"
    ACTIONABLE = "ACTIONABLE"
    SPY = "SPY"
    FORBIDDEN_CALL = "FORBIDDEN_CALL"
    FREEZE = "FREEZE"
    CAPABILITY = "CAPABILITY"


class JointContractRefuse(ValueError):
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
        self.self_accept = False
        super().__init__(f"JOINT CONTRACT REFUSE [{refuse_class}] {reason}")
