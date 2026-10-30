"""Immutable prediction identity — DDL unique key, no payload hash."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Tuple

from src.services.nfl_handicap_ledger.schema import (
    LEDGER_SCHEMA_VERSION,
    HandicapLedgerReject,
)


def parse_ledger_ts(value: Any) -> datetime:
    if value is None:
        raise HandicapLedgerReject("timestamp missing (no impute)")
    raw = str(value).strip()
    if not raw:
        raise HandicapLedgerReject("timestamp empty (no impute)")
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise HandicapLedgerReject(f"timestamp unparseable: {value!r}") from exc
    if dt.tzinfo is None:
        raise HandicapLedgerReject(
            "naive timestamp rejected (no impute to UTC); offset or Z required"
        )
    return dt


def canonicalize_as_of_ts(value: Any) -> str:
    """UTC instant string matching timestamptz identity (N3)."""
    dt = parse_ledger_ts(value).astimezone(timezone.utc).replace(microsecond=0)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

# Matches ddl_clear_a.sql uq_nfl_handicap_forecast_ledger_identity.
BUSINESS_IDENTITY_FIELDS = (
    "layer",
    "forecast_label",
    "game_id",
    "as_of_ts",
    "capture_id",
    "schema_version",
)


def business_identity_key(
    *,
    layer: str,
    forecast_label: str,
    game_id: str,
    as_of_ts: str,
    capture_id: str,
    schema_version: str,
) -> Tuple[str, str, str, str, str, str]:
    return (
        str(layer).strip(),
        str(forecast_label).strip(),
        str(game_id).strip(),
        canonicalize_as_of_ts(as_of_ts),
        str(capture_id).strip(),
        str(schema_version).strip(),
    )


def make_prediction_id(
    *,
    layer: str,
    forecast_label: str,
    game_id: str,
    as_of_ts: str,
    capture_id: str,
    schema_version: str = LEDGER_SCHEMA_VERSION,
    payload: Any = None,  # ignored — payload hash would allow logical overwrite (F4)
) -> str:
    """Identity = DDL unique key. Same business key ⇒ same id; store rejects dup."""
    del payload
    parts = business_identity_key(
        layer=layer,
        forecast_label=forecast_label,
        game_id=game_id,
        as_of_ts=as_of_ts,
        capture_id=capture_id,
        schema_version=schema_version,
    )
    if not all(parts):
        raise HandicapLedgerReject("all prediction_id components required (no impute)")
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return f"hl_{digest[:32]}"
