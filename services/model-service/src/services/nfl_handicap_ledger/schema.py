"""IF / HF / MIF ledger row contract (blueprint L0 / L1 / L4).

Three forecasts never overwrite each other:
  independent_fair · handicapped_fair · market_informed_fair

L5 never reads MIF as fair. This module is schema only — no capture.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Mapping, Optional

LEDGER_SCHEMA_VERSION = "handicap-ledger-v0-clear-a"

FORECAST_INDEPENDENT_FAIR = "independent_fair"
FORECAST_HANDICAPPED_FAIR = "handicapped_fair"
FORECAST_MARKET_INFORMED_FAIR = "market_informed_fair"
FORECAST_LABELS = frozenset(
    {
        FORECAST_INDEPENDENT_FAIR,
        FORECAST_HANDICAPPED_FAIR,
        FORECAST_MARKET_INFORMED_FAIR,
    }
)

L0_LAYER = "L0"
L1_LAYER = "L1"
L4_LAYER = "L4"
LAYER_LABELS = frozenset({L0_LAYER, L1_LAYER, L4_LAYER})

L1_ENTRY_POINTS = frozenset(
    {"efficiency", "possessions", "variance", "shape", "points"}
)

# D3(iii) required L1 identity / provenance — missing ⇒ REJECT, never impute.
L1_REQUIRED_FIELDS = (
    "capture_id",
    "as_of_ts",
    "baseline_ref",
    "registry_id",
    "source_snapshot_id",
)

L0_REQUIRED_FIELDS = (
    "game_id",
    "model_version",
    "as_of_ts",
    "capture_id",
    "baseline_personnel_ref",
    "margin_mu",
    "total_mu",
)

L4_REQUIRED_FIELDS = (
    "market_snapshot_id",
    "captured_at",
)


class HandicapLedgerReject(ValueError):
    """Fail-closed ledger / stage reject. Callers must not impute."""


@dataclass
class HandicapLedgerEnvelope:
    """Append-only prediction envelope. Identity is immutable once written."""

    prediction_id: str
    layer: str
    forecast_label: str
    game_id: str
    as_of_ts: str
    decision_ts: str
    capture_id: str
    source_snapshot_id: str
    registry_id: str
    baseline_ref: str
    model_version: str
    schema_version: str = LEDGER_SCHEMA_VERSION
    missing: bool = False
    missingness: Dict[str, bool] = field(default_factory=dict)
    payload: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "HandicapLedgerEnvelope":
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        data = {k: v for k, v in raw.items() if k in known}
        return cls(**data)  # type: ignore[arg-type]
