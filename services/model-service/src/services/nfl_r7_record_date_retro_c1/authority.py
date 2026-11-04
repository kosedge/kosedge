"""Approved authority registry + atomic claim/context. CERT=0.

ENV flags never grant real access. Synthetic claims cannot license real input.
Spent/failed claims cannot reset/rebind/retry. Archived R5 claim cannot reuse.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any, Mapping

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

STATUS_ISSUED = "ISSUED"
STATUS_SPENT = "SPENT"
STATUS_FAILED = "FAILED"
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


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def context_hash(payload: Mapping[str, Any]) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def env_grant_hits(environ_keys: list[str] | tuple[str, ...] | None = None) -> tuple[str, ...]:
    """Name-only. Never reads values. Hits do not grant."""
    keys = list(environ_keys) if environ_keys is not None else list(os.environ.keys())
    return tuple(key for key in keys if key in ENV_GRANT_NAMES or key.endswith("_ENABLE") or key.endswith("_REAL_GO"))


class AuthorityRegistry:
    def __init__(self) -> None:
        self._claims: dict[str, dict[str, Any]] = {}
        self.env_hits = env_grant_hits()
        self.env_grants = False

    def get(self, claim_id: str) -> dict[str, Any] | None:
        row = self._claims.get(claim_id)
        return dict(row) if row else None

    def issue_synthetic_claim(
        self,
        *,
        context: Mapping[str, Any],
        claim_id: str | None = None,
    ) -> dict[str, Any]:
        cid = str(claim_id or f"SYNTHETIC_RETRO_C1_{context_hash(context)[:16]}")
        if cid == ARCHIVED_R5_CLAIM:
            raise RetroRefuse("archived R5 consumed claim cannot be issued or reused")
        if cid in self._claims:
            raise RetroRefuse(f"claim already exists and cannot rebind: {cid}")
        digest = context_hash(context)
        row = {
            "claim_id": cid,
            "context_hash": digest,
            "input_class": INPUT_SYNTHETIC,
            "status": STATUS_ISSUED,
            "phase": "SYNTHETIC_FIXTURE",
            "package": PACKAGE,
            "profile": PROFILE,
            "cert": CERT,
            "cos_accept": COS_ACCEPT,
            "issued_by": WORKER_A_ID,
            "issued_utc": _utc_now(),
            "real_go_present": False,
            "env_grant": False,
            "channel": CHANNEL_SYNTHETIC,
        }
        self._claims[cid] = row
        return dict(row)

    def issue_real_claim(self, *args: Any, **kwargs: Any) -> None:
        raise RetroHold("real GO/claim mint refused — no placeholder GO; DATA_HOLD")

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
                f"{reader_role} real read refused — no matching real GO/context (ENV-independent)"
            )
        if not claim_id or not context_hash_expected:
            raise RetroRefuse(f"{reader_role} refused: absent claim/context")
        if claim_id == ARCHIVED_R5_CLAIM:
            raise RetroRefuse("archived R5 consumed claim cannot license this reader")
        row = self._claims.get(claim_id)
        if row is None:
            raise RetroRefuse(f"{reader_role} refused: claim not in registry")
        if row["status"] == STATUS_SPENT:
            raise RetroRefuse(f"{reader_role} refused: spent claim cannot retry {claim_id}")
        if row["status"] == STATUS_FAILED:
            raise RetroRefuse(f"{reader_role} refused: failed claim cannot reset {claim_id}")
        if row["status"] != STATUS_ISSUED:
            raise RetroRefuse(f"{reader_role} refused: claim status {row['status']}")
        if row["context_hash"] != context_hash_expected:
            raise RetroRefuse(f"{reader_role} refused: context hash mismatch")
        if row["input_class"] != INPUT_SYNTHETIC:
            raise RetroRefuse(f"{reader_role} refused: claim input_class is not SYNTHETIC")
        if requested_class != INPUT_SYNTHETIC:
            raise RetroRefuse(f"{reader_role} refused: synthetic claim cannot license {requested_class}")
        return dict(row)

    def spend(self, claim_id: str) -> dict[str, Any]:
        row = self._claims.get(claim_id)
        if row is None:
            raise RetroRefuse("cannot spend unknown claim")
        if row["status"] != STATUS_ISSUED:
            raise RetroRefuse(f"cannot spend claim status={row['status']}")
        row["status"] = STATUS_SPENT
        row["spent_utc"] = _utc_now()
        return dict(row)

    def fail(self, claim_id: str, *, reason: str) -> dict[str, Any]:
        row = self._claims.get(claim_id)
        if row is None:
            raise RetroRefuse("cannot fail unknown claim")
        if row["status"] == STATUS_SPENT:
            raise RetroRefuse("spent claim cannot be rebound to FAILED")
        row["status"] = STATUS_FAILED
        row["failed_utc"] = _utc_now()
        row["fail_reason"] = reason
        return dict(row)
