"""Immutable content hashes for the snap-share `_5g` exposure ledger."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Mapping

from src.services.nfl_snap_share_exposure_ledger.schema import (
    REJECT_TIMESTAMP_INVALID,
    ExposureLedgerReject,
)


def parse_ledger_ts(value: Any) -> datetime:
    if value is None:
        raise ExposureLedgerReject(REJECT_TIMESTAMP_INVALID, "timestamp missing (no impute)")
    raw = str(value).strip()
    if not raw:
        raise ExposureLedgerReject(REJECT_TIMESTAMP_INVALID, "timestamp empty (no impute)")
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise ExposureLedgerReject(
            REJECT_TIMESTAMP_INVALID, f"timestamp unparseable: {value!r}"
        ) from exc
    if dt.tzinfo is None:
        raise ExposureLedgerReject(
            REJECT_TIMESTAMP_INVALID,
            "naive timestamp rejected (no impute to UTC); offset or Z required",
        )
    return dt


def canonicalize_as_of_ts(value: Any) -> str:
    dt = parse_ledger_ts(value).astimezone(timezone.utc).replace(microsecond=0)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _canonical_default(value: Any) -> Any:
    raise TypeError(f"non-canonical type {type(value).__name__} (no default=str)")


def canonical_json(obj: Any) -> str:
    """Stable JSON: sorted keys, no whitespace, no type coercion."""
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
        default=_canonical_default,
    )


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def fingerprint_payload(obj: Any) -> str:
    return sha256_hex(canonical_json(obj))


def make_ledger_id(*, input_fingerprint: str, output_fingerprint: str) -> str:
    digest = sha256_hex(f"{input_fingerprint}|{output_fingerprint}")
    return f"x5g_{digest[:32]}"


def assert_as_of_not_after(*, fact_ts: str, bound_ts: str, field_name: str) -> None:
    fact = parse_ledger_ts(fact_ts)
    bound = parse_ledger_ts(bound_ts)
    if fact > bound:
        from src.services.nfl_snap_share_exposure_ledger.schema import (
            REJECT_AS_OF_VIOLATION,
        )

        raise ExposureLedgerReject(
            REJECT_AS_OF_VIOLATION,
            f"{field_name} as_of {canonicalize_as_of_ts(fact_ts)} "
            f"> bound {canonicalize_as_of_ts(bound_ts)}",
        )


def mapping_to_sorted_pairs(mapping: Mapping[str, str]) -> list[list[str]]:
    return [[str(k), str(v)] for k, v in sorted(mapping.items(), key=lambda kv: kv[0])]
