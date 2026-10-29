"""Fail-closed L0/L1/L4 validation. Missing required fields are not imputed."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional

from src.services.nfl_handicap_ledger.identity import (
    canonicalize_as_of_ts,
    make_prediction_id,
    parse_ledger_ts,
)
from src.services.nfl_handicap_ledger.schema import (
    FORECAST_HANDICAP_DELTA,
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


def is_exact_zero(value: Any) -> bool:
    """True only for numeric 0 / 0.0. Bool and other types are not zero."""
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return value == 0
    return False


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    return True


def _field_from(row: Mapping[str, Any], name: str) -> Any:
    """Read a field from the envelope or its payload. Never invent."""
    if name in row and _present(row.get(name)):
        return row.get(name)
    payload = row.get("payload")
    if isinstance(payload, Mapping) and name in payload and _present(payload.get(name)):
        return payload.get(name)
    return None


def _require_number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise HandicapLedgerReject(f"REJECT {name} must be numeric (no impute)")
    return float(value)


def validate_l1_row(
    row: Mapping[str, Any],
    *,
    decision_ts: Optional[Any] = None,
) -> Dict[str, Any]:
    """D3(iii) + 243a384e L1: missing required field or as_of > decision ⇒ REJECT."""
    missing = [name for name in L1_REQUIRED_FIELDS if not _present(_field_from(row, name))]
    # delta/uncertainty may be 0.0 — _present(0.0) is True. Missing key rejects.
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

    entry_point = str(_field_from(row, "entry_point"))
    if entry_point not in L1_ENTRY_POINTS:
        raise HandicapLedgerReject(f"L1 REJECT invalid entry_point: {entry_point!r}")
    _require_number(_field_from(row, "delta"), "delta")
    _require_number(_field_from(row, "uncertainty"), "uncertainty")

    label = _field_from(row, "forecast_label")
    if _present(label) and str(label) != FORECAST_HANDICAP_DELTA:
        raise HandicapLedgerReject(
            "L1 REJECT forecast_label must be handicap_delta (not a fair line)"
        )
    return dict(row)


def validate_l0_row(row: Mapping[str, Any]) -> Dict[str, Any]:
    missing = [name for name in L0_REQUIRED_FIELDS if not _present(_field_from(row, name))]
    if missing:
        raise HandicapLedgerReject(
            f"L0 REJECT missing required fields {missing} (no impute)"
        )
    blend = _field_from(row, "market_blend")
    if not is_exact_zero(blend):
        raise HandicapLedgerReject(
            "L0 REJECT market_blend MUST = 0 (exact; bool/float≠0 rejected)"
        )
    for name in ("margin_mu", "total_mu", "sigma"):
        _require_number(_field_from(row, name), name)
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
    if not _present(resolved_decision):
        raise HandicapLedgerReject("L4 REJECT missing decision_ts (no impute)")
    parse_ledger_ts(captured_at)
    if parse_ledger_ts(captured_at) > parse_ledger_ts(resolved_decision):
        raise HandicapLedgerReject("L4 REJECT captured_at > decision_ts (no impute)")
    as_of_ts = _field_from(row, "as_of_ts")
    parse_ledger_ts(as_of_ts)
    if parse_ledger_ts(as_of_ts) > parse_ledger_ts(resolved_decision):
        raise HandicapLedgerReject("L4 REJECT as_of_ts > decision_ts (no impute)")
    label = _field_from(row, "forecast_label")
    if not _present(label) or str(label) != FORECAST_MARKET_INFORMED_FAIR:
        raise HandicapLedgerReject(
            "L4 REJECT forecast_label must be market_informed_fair"
        )
    return dict(row)


def _require_layer_label(layer: str, forecast_label: str) -> None:
    if layer not in LAYER_LABELS:
        raise HandicapLedgerReject(f"unknown layer: {layer!r}")
    if forecast_label not in FORECAST_LABELS:
        raise HandicapLedgerReject(f"unknown forecast_label: {forecast_label!r}")
    if layer == L0_LAYER and forecast_label != FORECAST_INDEPENDENT_FAIR:
        raise HandicapLedgerReject("L0 REJECT forecast_label must be independent_fair")
    if layer == L1_LAYER and forecast_label != FORECAST_HANDICAP_DELTA:
        raise HandicapLedgerReject(
            "L1 REJECT forecast_label must be handicap_delta (HF/MIF smear forbidden)"
        )
    if layer == L4_LAYER and forecast_label != FORECAST_MARKET_INFORMED_FAIR:
        raise HandicapLedgerReject("L4 REJECT forecast_label must be market_informed_fair")


def validate_envelope(env: HandicapLedgerEnvelope) -> HandicapLedgerEnvelope:
    """N1: public Envelope inputs take the same layer/label/ts/field gates."""
    if not isinstance(env, HandicapLedgerEnvelope):
        raise HandicapLedgerReject("envelope REJECT unvalidated row")
    _require_layer_label(env.layer, env.forecast_label)
    parse_ledger_ts(env.as_of_ts)
    parse_ledger_ts(env.decision_ts)
    row = env.to_dict()
    if env.layer == L1_LAYER:
        validate_l1_row(row, decision_ts=env.decision_ts)
    elif env.layer == L0_LAYER:
        validate_l0_row(row)
    elif env.layer == L4_LAYER:
        validate_l4_row(row, decision_ts=env.decision_ts)
    else:
        raise HandicapLedgerReject(f"unknown layer: {env.layer!r}")
    return envelope_from_row(
        row,
        layer=env.layer,
        forecast_label=env.forecast_label,
        decision_ts=env.decision_ts,
    )


def envelope_from_row(
    row: Mapping[str, Any],
    *,
    layer: str,
    forecast_label: str,
    decision_ts: str,
) -> HandicapLedgerEnvelope:
    _require_layer_label(layer, forecast_label)
    parse_ledger_ts(decision_ts)

    game_id = _field_from(row, "game_id")
    as_of_ts = _field_from(row, "as_of_ts")
    capture_id = _field_from(row, "capture_id")
    if not _present(game_id) or not _present(as_of_ts) or not _present(capture_id):
        raise HandicapLedgerReject(
            "envelope REJECT missing game_id/as_of_ts/capture_id (no impute)"
        )
    as_of_ts = canonicalize_as_of_ts(as_of_ts)

    if layer == L1_LAYER:
        baseline_ref = _field_from(row, "baseline_ref")
        source_snapshot_id = _field_from(row, "source_snapshot_id")
        registry_id = _field_from(row, "registry_id")
        if not _present(baseline_ref) or not _present(source_snapshot_id) or not _present(registry_id):
            raise HandicapLedgerReject("L1 envelope REJECT missing refs (no impute)")
    elif layer == L0_LAYER:
        baseline_ref = _field_from(row, "baseline_personnel_ref")
        if not _present(baseline_ref):
            raise HandicapLedgerReject("L0 envelope REJECT missing baseline_personnel_ref (no impute)")
        # L0 blueprint does not require these; omit rather than impute "".
        source_snapshot_id = _field_from(row, "source_snapshot_id")
        registry_id = _field_from(row, "registry_id")
    else:
        baseline_ref = _field_from(row, "baseline_ref")
        source_snapshot_id = _field_from(row, "source_snapshot_id")
        registry_id = _field_from(row, "registry_id")

    schema_version = _field_from(row, "schema_version") or LEDGER_SCHEMA_VERSION
    derived_id = make_prediction_id(
        layer=layer,
        forecast_label=forecast_label,
        game_id=str(game_id),
        as_of_ts=str(as_of_ts),
        capture_id=str(capture_id),
        schema_version=str(schema_version),
    )
    caller_id = str(row.get("prediction_id") or "").strip()
    if caller_id and caller_id != derived_id:
        raise HandicapLedgerReject(
            "append REJECT caller-chosen prediction_id does not match re-derived identity"
        )

    payload = row.get("payload") if isinstance(row.get("payload"), Mapping) else dict(row)
    return HandicapLedgerEnvelope(
        prediction_id=derived_id,
        layer=layer,
        forecast_label=forecast_label,
        game_id=str(game_id),
        as_of_ts=str(as_of_ts),
        decision_ts=str(decision_ts),
        capture_id=str(capture_id),
        source_snapshot_id=str(source_snapshot_id) if _present(source_snapshot_id) else None,
        registry_id=str(registry_id) if _present(registry_id) else None,
        baseline_ref=str(baseline_ref) if _present(baseline_ref) else None,
        model_version=str(_field_from(row, "model_version") or ""),
        schema_version=str(schema_version),
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
    forecast_label: str = FORECAST_HANDICAP_DELTA,
) -> List[Dict[str, Any]]:
    """Validate + dup-check every L1 row, then append. Any reject ⇒ no writes."""
    raw_list = list(rows)
    prepared: List[HandicapLedgerEnvelope] = []
    seen_ids = set()
    seen_biz = set()
    for raw in raw_list:
        validate_l1_row(raw, decision_ts=decision_ts)
        env = envelope_from_row(
            raw,
            layer=L1_LAYER,
            forecast_label=forecast_label,
            decision_ts=decision_ts,
        )
        biz = (
            env.layer,
            env.forecast_label,
            env.game_id,
            env.as_of_ts,
            env.capture_id,
            env.schema_version,
        )
        if store.has_prediction_id(env.prediction_id) or env.prediction_id in seen_ids:
            raise HandicapLedgerReject(
                f"L1 stage REJECT duplicate prediction_id {env.prediction_id}; no writes"
            )
        if store.has_business_identity(biz) or biz in seen_biz:
            raise HandicapLedgerReject(
                "L1 stage REJECT duplicate business identity; no writes"
            )
        seen_ids.add(env.prediction_id)
        seen_biz.add(biz)
        prepared.append(env)
    return store.append_many(prepared)
