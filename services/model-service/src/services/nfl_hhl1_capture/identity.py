"""Immutable event identity for H-HL-1 L1 rows.

capture_id = sha256(canonical_json(payload) ‖ source_id ‖ source_published_at ‖ captured_at)
source_snapshot_id = sha256 of raw source bytes (hex) — accepted, not fetched.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from src.services.nfl_hhl1_capture.constants import (
    DECISION_OFFSET_BEFORE_KICKOFF_MINUTES,
    PROTOCOL_SHA256,
)
from src.services.nfl_hhl1_capture.schema import Hhl1Reject, Hhl1RejectCode

# Protocol §5.2 uses U+2016 DOUBLE VERTICAL LINE as the identity delimiter.
IDENTITY_DELIMITER = "\u2016"

_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")
_TEAM = re.compile(r"^[A-Z]{2,3}$")


def canonical_json(obj: Any) -> str:
    """Deterministic JSON: sorted keys, no whitespace, no NaN."""
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def is_sha256_hex(value: Any) -> bool:
    return isinstance(value, str) and bool(_SHA256_HEX.fullmatch(value))


def is_team_code(value: Any) -> bool:
    return isinstance(value, str) and bool(_TEAM.fullmatch(value))


def parse_utc(value: Any, *, field: str) -> datetime:
    if value is None:
        raise Hhl1Reject(Hhl1RejectCode.PROVENANCE_INCOMPLETE, f"{field} missing (no impute)")
    raw = str(value).strip()
    if not raw:
        raise Hhl1Reject(Hhl1RejectCode.PROVENANCE_INCOMPLETE, f"{field} empty (no impute)")
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise Hhl1Reject(
            Hhl1RejectCode.SCHEMA_MISMATCH, f"{field} unparseable: {value!r}"
        ) from exc
    if dt.tzinfo is None:
        raise Hhl1Reject(
            Hhl1RejectCode.SCHEMA_MISMATCH,
            f"{field} naive timestamp rejected (no impute to UTC)",
        )
    return dt.astimezone(timezone.utc)


def canonicalize_utc(value: Any, *, field: str) -> str:
    dt = parse_utc(value, field=field).replace(microsecond=0)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def expected_decision_ts(kickoff_ts: Any) -> str:
    """kickoff − 90 minutes (provisional R3). Does not invent a rating window."""
    kickoff = parse_utc(kickoff_ts, field="kickoff_ts")
    decision = kickoff - timedelta(minutes=DECISION_OFFSET_BEFORE_KICKOFF_MINUTES)
    return decision.replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def make_capture_id(
    *,
    payload: Mapping[str, Any],
    source_id: str,
    source_published_at: str,
    captured_at: str,
) -> str:
    """Immutable capture identity. payload must not include capture_id."""
    if "capture_id" in payload:
        raise Hhl1Reject(
            Hhl1RejectCode.IDENTITY_MISMATCH,
            "identity payload must not contain capture_id (circular)",
        )
    blob = IDENTITY_DELIMITER.join(
        (
            canonical_json(dict(payload)),
            str(source_id),
            canonicalize_utc(source_published_at, field="source_published_at"),
            canonicalize_utc(captured_at, field="captured_at"),
        )
    )
    return sha256_hex(blob.encode("utf-8"))


def make_baseline_ref_sha(player_ids: Any, *, team: str) -> str:
    """Hash a supplied starter list. Does not select or fetch players."""
    if not isinstance(player_ids, (list, tuple)):
        raise Hhl1Reject(
            Hhl1RejectCode.SCHEMA_MISMATCH,
            "player_ids must be a list to hash (no impute)",
        )
    ordered = sorted(str(p) for p in player_ids)
    return sha256_hex(canonical_json({"team": team, "player_ids": ordered}).encode("utf-8"))


def make_source_snapshot_id(raw_bytes: bytes) -> str:
    """sha256 of caller-supplied raw bytes. Does not fetch those bytes."""
    if not raw_bytes:
        raise Hhl1Reject(
            Hhl1RejectCode.PROVENANCE_INCOMPLETE,
            "raw source bytes empty (no impute)",
        )
    return sha256_hex(raw_bytes)


def require_protocol_sha(value: Any) -> str:
    raw = str(value or "").strip().lower()
    if raw in {PROTOCOL_SHA256, PROTOCOL_SHA256[:8]}:
        return PROTOCOL_SHA256
    raise Hhl1Reject(
        Hhl1RejectCode.PROVENANCE_INCOMPLETE,
        f"protocol_sha must be {PROTOCOL_SHA256[:8]} (got {value!r})",
    )
