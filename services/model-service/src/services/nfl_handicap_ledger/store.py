"""Append-only IF/HF/MIF ledger. Validated writes only; never overwrite."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple, Union

from src.services.nfl_handicap_ledger.identity import business_identity_key
from src.services.nfl_handicap_ledger.schema import (
    L0_LAYER,
    L1_LAYER,
    L4_LAYER,
    LEDGER_SCHEMA_VERSION,
    HandicapLedgerEnvelope,
    HandicapLedgerReject,
)
from src.services.nfl_handicap_ledger.validate import (
    envelope_from_row,
    validate_envelope,
    validate_l0_row,
    validate_l1_row,
    validate_l4_row,
)

BizKey = Tuple[str, str, str, str, str, str]


def _utc_now() -> str:
    # NON_BLOCKING default (F6): created_at is write-time metadata, not as-of identity.
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _biz_from_row(row: Mapping[str, Any]) -> Optional[BizKey]:
    layer = str(row.get("layer") or "").strip()
    forecast_label = str(row.get("forecast_label") or "").strip()
    game_id = str(row.get("game_id") or "").strip()
    as_of_ts = str(row.get("as_of_ts") or "").strip()
    capture_id = str(row.get("capture_id") or "").strip()
    schema_version = str(row.get("schema_version") or LEDGER_SCHEMA_VERSION).strip()
    if not all((layer, forecast_label, game_id, as_of_ts, capture_id, schema_version)):
        return None
    return business_identity_key(
        layer=layer,
        forecast_label=forecast_label,
        game_id=game_id,
        as_of_ts=as_of_ts,
        capture_id=capture_id,
        schema_version=schema_version,
    )


class AppendOnlyHandicapLedger:
    """In-memory + optional JSONL store. Append only; duplicate id/biz ⇒ reject."""

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = Path(path) if path is not None else None
        self._rows: List[Dict[str, Any]] = []
        self._ids: Dict[str, Dict[str, Any]] = {}
        self._biz: Dict[BizKey, str] = {}
        if self.path is not None and self.path.exists():
            self._load_jsonl(self.path)

    def _load_jsonl(self, path: Path) -> None:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise HandicapLedgerReject("JSONL load REJECT non-object row")
            layer = str(row.get("layer") or "").strip()
            forecast_label = str(row.get("forecast_label") or "").strip()
            decision_ts = str(row.get("decision_ts") or "").strip()
            if not layer or not forecast_label or not decision_ts:
                raise HandicapLedgerReject(
                    "JSONL load REJECT missing layer/forecast_label/decision_ts"
                )
            if layer == L1_LAYER:
                validate_l1_row(row, decision_ts=decision_ts)
            elif layer == L0_LAYER:
                validate_l0_row(row)
            elif layer == L4_LAYER:
                validate_l4_row(row, decision_ts=decision_ts)
            else:
                raise HandicapLedgerReject(f"JSONL load REJECT unknown layer: {layer!r}")
            env = envelope_from_row(
                row,
                layer=layer,
                forecast_label=forecast_label,
                decision_ts=decision_ts,
            )
            derived = env.prediction_id
            stored = str(row.get("prediction_id") or "").strip()
            if not stored:
                raise HandicapLedgerReject("JSONL load REJECT missing prediction_id")
            if stored != derived:
                raise HandicapLedgerReject(
                    f"JSONL load REJECT forged prediction_id {stored} != {derived}"
                )
            if derived in self._ids:
                raise HandicapLedgerReject(
                    f"JSONL load REJECT duplicate prediction_id {derived} (no last-wins)"
                )
            biz = _biz_from_row(env.to_dict())
            if biz is not None and biz in self._biz:
                raise HandicapLedgerReject(
                    "JSONL load REJECT duplicate business identity (no last-wins)"
                )
            payload = env.to_dict()
            self._ids[derived] = payload
            if biz is not None:
                self._biz[biz] = derived
            self._rows.append(payload)

    def __len__(self) -> int:
        return len(self._rows)

    def rows(self) -> List[Dict[str, Any]]:
        return list(self._rows)

    def get(self, prediction_id: str) -> Optional[Dict[str, Any]]:
        return self._ids.get(prediction_id)

    def has_prediction_id(self, prediction_id: str) -> bool:
        return prediction_id in self._ids

    def has_business_identity(self, biz: BizKey) -> bool:
        return biz in self._biz

    def _check_unique(self, payload: Dict[str, Any]) -> None:
        pid = str(payload.get("prediction_id") or "").strip()
        if not pid:
            raise HandicapLedgerReject("append REJECT missing prediction_id (no impute)")
        if pid in self._ids:
            raise HandicapLedgerReject(
                f"append REJECT prediction_id already exists ({pid}); never overwrite"
            )
        biz = _biz_from_row(payload)
        if biz is not None and biz in self._biz:
            raise HandicapLedgerReject(
                "append REJECT business identity already exists; never overwrite"
            )

    def _write(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        # created_at default is NON_BLOCKING write metadata (F6 residual), not as-of.
        if not payload.get("created_at"):
            payload["created_at"] = _utc_now()
        pid = str(payload["prediction_id"])
        self._ids[pid] = payload
        biz = _biz_from_row(payload)
        if biz is not None:
            self._biz[biz] = pid
        self._rows.append(payload)
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(payload, sort_keys=True, default=str) + "\n")
        return payload

    def append(self, row: Union[HandicapLedgerEnvelope, Dict[str, Any]]) -> Dict[str, Any]:
        """Validated-only append. Raw attacker ids are re-derived or rejected."""
        if isinstance(row, HandicapLedgerEnvelope):
            return self.append_many([row])[0]
        if not isinstance(row, dict):
            raise HandicapLedgerReject("append REJECT unvalidated row")
        layer = row.get("layer")
        forecast_label = row.get("forecast_label")
        decision_ts = row.get("decision_ts")
        if not layer or not forecast_label or not decision_ts:
            raise HandicapLedgerReject(
                "append REJECT unvalidated row (need layer, forecast_label, decision_ts)"
            )
        return self.append_layer(
            row,
            layer=str(layer),
            forecast_label=str(forecast_label),
            decision_ts=str(decision_ts),
        )

    def append_many(self, envelopes: Iterable[HandicapLedgerEnvelope]) -> List[Dict[str, Any]]:
        prepared: List[Dict[str, Any]] = []
        seen_ids: set[str] = set()
        seen_biz: set[BizKey] = set()
        for env in envelopes:
            if not isinstance(env, HandicapLedgerEnvelope):
                raise HandicapLedgerReject("append_many REJECT unvalidated row")
            validated = validate_envelope(env)
            payload = validated.to_dict()
            pid = str(payload.get("prediction_id") or "").strip()
            biz = _biz_from_row(payload)
            if not pid:
                raise HandicapLedgerReject("append REJECT missing prediction_id (no impute)")
            if pid in self._ids or pid in seen_ids:
                raise HandicapLedgerReject(
                    f"append REJECT duplicate prediction_id ({pid}); never overwrite"
                )
            if biz is not None and (biz in self._biz or biz in seen_biz):
                raise HandicapLedgerReject(
                    "append REJECT duplicate business identity; never overwrite"
                )
            seen_ids.add(pid)
            if biz is not None:
                seen_biz.add(biz)
            prepared.append(payload)
        snapshot_rows = list(self._rows)
        snapshot_ids = dict(self._ids)
        snapshot_biz = dict(self._biz)
        snapshot_bytes = (
            self.path.read_bytes() if self.path is not None and self.path.exists() else None
        )
        written: List[Dict[str, Any]] = []
        try:
            for payload in prepared:
                written.append(self._write(payload))
        except Exception:
            self._rows = snapshot_rows
            self._ids = snapshot_ids
            self._biz = snapshot_biz
            if self.path is not None:
                if snapshot_bytes is None:
                    if self.path.exists():
                        self.path.unlink()
                else:
                    self.path.write_bytes(snapshot_bytes)
            raise
        return written

    def append_layer(
        self,
        raw: Dict[str, Any],
        *,
        layer: str,
        forecast_label: str,
        decision_ts: str,
    ) -> Dict[str, Any]:
        if layer == L1_LAYER:
            validate_l1_row(raw, decision_ts=decision_ts)
        elif layer == L0_LAYER:
            validate_l0_row(raw)
        elif layer == L4_LAYER:
            validate_l4_row(raw, decision_ts=decision_ts)
        else:
            raise HandicapLedgerReject(f"unknown layer: {layer!r}")
        env = envelope_from_row(
            raw,
            layer=layer,
            forecast_label=forecast_label,
            decision_ts=decision_ts,
        )
        return self.append_many([env])[0]
