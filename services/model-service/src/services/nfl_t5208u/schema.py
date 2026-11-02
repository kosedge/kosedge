"""R6 schema: CONTRACT_27 + envelope metadata. No invented fields."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from src.services.nfl_t5208u.pins import (
    CELL_META_FIELDS,
    CONTRACT_27,
    C_FORMULA,
    ENVELOPE_FIELDS,
    OUTPUT_KIND,
    SCHEMA_ID,
)


def schema_document() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "output_kind": OUTPUT_KIND,
        "c_formula": C_FORMULA,
        "contract_27": list(CONTRACT_27),
        "n_contract_27": len(CONTRACT_27),
        "envelope_fields": list(ENVELOPE_FIELDS),
        "cell_meta_fields": list(CELL_META_FIELDS),
        "notes": [
            "CONTRACT_27 is the literal tuple from recon_contract.py@455a8e43.",
            "No injury/QB/news/weather/travel/KAV unless already in the 27.",
            "No market inputs. POINT_MARGIN only.",
        ],
    }


def schema_hash(document: Mapping[str, Any] | None = None) -> str:
    payload = document if document is not None else schema_document()
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def assert_contract_27_exact(fields: list[str] | tuple[str, ...]) -> None:
    if tuple(fields) != CONTRACT_27:
        raise ValueError(
            "CONTRACT_27 freeze failed: got "
            f"{tuple(fields)!r} != {CONTRACT_27!r}"
        )
