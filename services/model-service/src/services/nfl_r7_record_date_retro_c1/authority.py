"""Approved authority + persistent exclusive claim. CERT=0.

ENV flags never grant. REAL issue + every REAL reader unconditionally HOLD
until a Root-approved grant digest exists (none posted).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping

from src.services.nfl_r7_record_date_retro_c1.context import context_hash
from src.services.nfl_r7_record_date_retro_c1.custody import (
    PHASE_CLAIMED,
    PHASE_FAILED,
    PHASE_FORECASTS_SEALED,
    PHASE_SCORED,
    PHASE_SPENT,
    PersistentCustody,
)
from src.services.nfl_r7_record_date_retro_c1.grant import refuse_real_without_root_grant
from src.services.nfl_r7_record_date_retro_c1.pins import (
    ARCHIVED_R5_CLAIM,
    CERT,
    CHANNEL_SYNTHETIC,
    COS_ACCEPT,
    PACKAGE,
    PROFILE,
    WORKER_A_ID,
)
from src.services.nfl_r7_record_date_retro_c1.refuse import RetroHold, RetroRefuse

INPUT_SYNTHETIC = "SYNTHETIC"
INPUT_REAL = "REAL"
READER_ROLES = frozenset({"feature", "history", "outcome", "model"})
ENV_GRANT_NAMES = (
    "ENABLE",
    "REAL",
    "GO",
    "R7_REAL",
    "R7_ENABLE",
    "ALLOW_FIXTURE",
    "ALLOW_REAL",
    "RETRO_C1_GO",
    "RETRO_C1_REAL",
)

# Back-compat aliases for existing tests.
STATUS_ISSUED = PHASE_CLAIMED
STATUS_SPENT = PHASE_SPENT
STATUS_FAILED = PHASE_FAILED


def env_grant_hits(environ_keys: list[str] | tuple[str, ...] | None = None) -> tuple[str, ...]:
    keys = list(environ_keys) if environ_keys is not None else list(os.environ.keys())
    return tuple(key for key in keys if key in ENV_GRANT_NAMES or key.endswith("_ENABLE") or key.endswith("_REAL_GO"))


class AuthorityRegistry:
    def __init__(self, store_dir: Path | None = None) -> None:
        if store_dir is None:
            raise RetroRefuse("persistent custody store_dir is required (in-memory registry refused)")
        self.custody = PersistentCustody(Path(store_dir))
        self.env_hits = env_grant_hits()
        self.env_grants = False

    def get(self, claim_id: str) -> dict[str, Any] | None:
        return self.custody.load(claim_id)

    def issue_synthetic_claim(
        self,
        *,
        context: Mapping[str, Any],
        claim_id: str | None = None,
    ) -> dict[str, Any]:
        digest = context_hash(context) if "context_hash" not in context else str(context["context_hash"])
        cid = str(claim_id or f"SYNTHETIC_RETRO_C1_{digest[:16]}")
        if cid == ARCHIVED_R5_CLAIM:
            raise RetroRefuse("archived R5 consumed claim cannot be issued or reused")
        return self.custody.issue(
            cid,
            {
                "context_hash": digest,
                "input_class": INPUT_SYNTHETIC,
                "package": PACKAGE,
                "profile": PROFILE,
                "cert": CERT,
                "cos_accept": COS_ACCEPT,
                "issued_by": WORKER_A_ID,
                "real_go_present": False,
                "env_grant": False,
                "channel": CHANNEL_SYNTHETIC,
            },
        )

    def issue_real_claim(self, *args: Any, **kwargs: Any) -> None:
        refuse_real_without_root_grant(grant=kwargs.get("grant"))

    def require_before_reader(
        self,
        *,
        claim_id: str | None,
        context_hash_expected: str | None,
        reader_role: str,
        requested_class: str,
    ) -> dict[str, Any]:
        if reader_role not in READER_ROLES:
            raise RetroRefuse(f"unknown reader_role {reader_role!r}")
        if requested_class == INPUT_REAL:
            raise RetroHold(
                f"{reader_role} REAL reader unconditionally HOLD — no Root-approved grant/context"
            )
        if not claim_id or not context_hash_expected:
            raise RetroRefuse(f"{reader_role} refused: absent claim/context")
        if claim_id == ARCHIVED_R5_CLAIM:
            raise RetroRefuse("archived R5 consumed claim cannot license this reader")
        row = self.custody.refuse_if_terminal_or_foreign(claim_id)
        if row["context_hash"] != context_hash_expected:
            raise RetroRefuse(f"{reader_role} refused: context hash mismatch")
        if row["input_class"] != INPUT_SYNTHETIC:
            raise RetroRefuse(f"{reader_role} refused: claim input_class is not SYNTHETIC")
        if requested_class != INPUT_SYNTHETIC:
            raise RetroRefuse(f"{reader_role} refused: synthetic claim cannot license {requested_class}")
        phase = row["phase"]
        if reader_role == "outcome" and phase not in {PHASE_FORECASTS_SEALED, PHASE_SCORED}:
            raise RetroRefuse(f"outcome unread until FORECASTS_SEALED, phase={phase}")
        if reader_role in {"feature", "history", "model"} and phase != PHASE_CLAIMED:
            raise RetroRefuse(f"{reader_role} only during CLAIMED, phase={phase}")
        return dict(row)

    def spend(self, claim_id: str) -> dict[str, Any]:
        return self.custody.spend(claim_id)

    def fail(self, claim_id: str, *, reason: str) -> dict[str, Any]:
        return self.custody.fail(claim_id, reason=reason)
