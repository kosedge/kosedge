"""Immutable prediction identity for the IF/HF/MIF ledger."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


def canonical_payload_digest(payload: Mapping[str, Any] | None) -> str:
    blob = json.dumps(
        payload or {},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def make_prediction_id(
    *,
    layer: str,
    forecast_label: str,
    game_id: str,
    as_of_ts: str,
    capture_id: str,
    schema_version: str,
    payload: Mapping[str, Any] | None = None,
) -> str:
    """Stable identity. Same inputs → same id; store refuses a second write."""
    parts = [
        str(layer).strip(),
        str(forecast_label).strip(),
        str(game_id).strip(),
        str(as_of_ts).strip(),
        str(capture_id).strip(),
        str(schema_version).strip(),
        canonical_payload_digest(payload),
    ]
    if not all(parts):
        raise ValueError("all prediction_id components required")
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return f"hl_{digest[:32]}"
