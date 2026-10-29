"""Fail-closed L0/L1/L4 validation. Missing required fields are not imputed."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional

from src.services.nfl_handicap_ledger.identity import make_prediction_id
from src.services.nfl_handicap_ledger.schema import (
    FORECAST_HANDICAPPED_FAIR,
    FORECAST_INDEPENDENT_FAIR,
    FORECAST_LABELS,
    FORECAST_MARKET_INFORMED_FAIR,
    L0_LAYER,
    L0_REQUIRED_FIELDS,
    L1_ENTRY_POINTS,
    L1_LAYER,
    L1_REQUIRED_FIELDS,
    L4_LAYER,
    L4_REQUIRED_FIELDS,
    LAYER_LABELS,
    LEDGER_SCHEMA_VERSION,
    HandicapLedgerEnvelope,
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
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    return True


def _field_from(row: Mapping[str, Any], name: str) -> Any:
    """Read a required field from the envelope or its payload. Never invent."""
    if name in row and _present(row.get(name)):
        return row.get(name)
    payload = row.get("payload")
    if isinstance(payload, Mapping) and name in payload and _present(payload.get(name)):
        return payload.get(name)
    return None


def validate_l1_row(
    row: Mapping[str, Any],
    *,
    decision_ts: Optional[Any] = None,
) -> Dict[str, Any]:
    """D3(iii): missing required L1 field or as_of_ts > decision_ts ⇒ REJECT.

    Does not impute. Stage callers must treat the exception as a hard fail.
    """
    missing = [name for name in L1_REQUIRED_FIELDS if not _present(_field_from(row, name))]
    if missing:
        raise HandicapLedgerReject(
            f"L1 REJECT missing required fields {missing} (no impute)"
        )

    as_of_ts = _field_from(row, "as_of_ts")
    resolved_decision = decision_ts if _present(decision_ts) else _field_from(row, "decision_ts")
    if not _present(resolved_decision):
        raise HandicapLedgerReject("L1 REJECT missing decision_ts (no impute)")
    if parse_ledger_ts(as_of_ts) > parse_ledger_ts(resolved_decision):
        raise HandicapLedgerReject("L1 REJECT as_of_ts > decision_ts (no impute)")

    entry_point = _field_from(row, "entry_point")
    if _present(entry_point) and str(entry_point) not in L1_ENTRY_POINTS:
        raise HandicapLedgerReject(f"L1 REJECT invalid entry_point: {entry_point!r}")

    return dict(row)


def validate_l0_row(row: Mapping[str, Any]) -> Dict[str, Any]:
    missing = [name for name in L0_REQUIRED_FIELDS if not _present(_field_from(row, name))]
    if missing:
        raise HandicapLedgerReject(
            f"L0 REJECT missing required fields {missing} (no impute)"
        )
    blend = _field_from(row, "market_blend")
    if blend is None:
        payload = row.get("payload") if isinstance(row.get("payload"), Mapping) else {}
        blend = payload.get("market_blend") if isinstance(payload, Mapping) else None
    try:
        blend_n = int(blend)
    except (TypeError, ValueError):
        raise HandicapLedgerReject("L0 REJECT market_blend MUST = 0")
    if blend_n != 0:
        raise HandicapLedgerReject("L0 REJECT market_blend MUST = 0")
    label = _field_from(row, "forecast_label")
    if _present(label) and str(label) != FORECAST_INDEPENDENT_FAIR:
        raise HandicapLedgerReject("L0 REJECT forecast_label must be independent_fair")
    return dict(row)


def validate_l4_row(row: Mapping[str, Any], *, decision_ts: Optional[Any] = None) -> Dict[str, Any]:
    missing = [name for name in L4_REQUIRED_FIELDS if not _present(_field_from(row, name))]
    if missing:
        raise HandicapLedgerReject(
            f"L4 REJECT missing required fields {missing} (no impute)"
        )
    captured_at = _field_from(row, "captured_at")
    resolved_decision = decision_ts if _present(decision_ts) else _field_from(row, "decision_ts")
    if _present(resolved_decision) and parse_ledger_ts(captured_at) > parse_ledger_ts(resolved_decision):
        raise HandicapLedgerReject("L4 REJECT captured_at > decision_ts (no impute)")
    label = str(_field_from(row, "forecast_label") or row.get("forecast_label") or "")
    if label in {FORECAST_INDEPENDENT_FAIR, "model_fair"}:
        raise HandicapLedgerReject(
            "L4/MIF REJECT: market compare / MIF must not be labeled independent_fair or model_fair"
        )
    return dict(row)


def envelope_from_row(
    row: Mapping[str, Any],
    *,
    layer: str,
    forecast_label: str,
    decision_ts: str,
) -> HandicapLedgerEnvelope:
    if layer not in LAYER_LABELS:
        raise HandicapLedgerReject(f"unknown layer: {layer!r}")
    if forecast_label not in FORECAST_LABELS:
        raise HandicapLedgerReject(f"unknown forecast_label: {forecast_label!r}")
    if forecast_label == FORECAST_MARKET_INFORMED_FAIR and layer == L0_LAYER:
        raise HandicapLedgerReject("MIF must not be stored as L0 Independent Fair")

    game_id = str(_field_from(row, "game_id") or "")
    as_of_ts = str(_field_from(row, "as_of_ts") or _field_from(row, "captured_at") or "")
    capture_id = str(_field_from(row, "capture_id") or "")
    payload = row.get("payload") if isinstance(row.get("payload"), Mapping) else dict(row)
    prediction_id = str(row.get("prediction_id") or "").strip() or make_prediction_id(
        layer=layer,
        forecast_label=forecast_label,
        game_id=game_id,
        as_of_ts=as_of_ts,
        capture_id=capture_id,
        schema_version=str(row.get("schema_version") or LEDGER_SCHEMA_VERSION),
        payload=payload,
    )
    return HandicapLedgerEnvelope(
        prediction_id=prediction_id,
        layer=layer,
        forecast_label=forecast_label,
        game_id=game_id,
        as_of_ts=as_of_ts,
        decision_ts=str(decision_ts),
        capture_id=capture_id,
        source_snapshot_id=str(_field_from(row, "source_snapshot_id") or ""),
        registry_id=str(_field_from(row, "registry_id") or ""),
        baseline_ref=str(_field_from(row, "baseline_ref") or _field_from(row, "baseline_personnel_ref") or ""),
        model_version=str(_field_from(row, "model_version") or ""),
        schema_version=str(row.get("schema_version") or LEDGER_SCHEMA_VERSION),
        missing=bool(row.get("missing", False)),
        missingness=dict(row.get("missingness") or {}),
        payload=dict(payload),
        created_at=row.get("created_at") if _present(row.get("created_at")) else None,
    )


def commit_l1_stage(
    store: Any,
    rows: Iterable[Mapping[str, Any]],
    *,
    decision_ts: str,
    forecast_label: str = FORECAST_HANDICAPPED_FAIR,
) -> List[Dict[str, Any]]:
    """Validate every L1 row, then append. Any reject fails the stage (no writes)."""
    prepared: List[HandicapLedgerEnvelope] = []
    for raw in rows:
        validate_l1_row(raw, decision_ts=decision_ts)
        prepared.append(
            envelope_from_row(
                raw,
                layer=L1_LAYER,
                forecast_label=forecast_label,
                decision_ts=decision_ts,
            )
        )
    written: List[Dict[str, Any]] = []
    for env in prepared:
        written.append(store.append(env))
    return written
