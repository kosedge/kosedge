"""Append-only IF/HF/MIF ledger. Existing prediction_id rows are never overwritten."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from src.services.nfl_handicap_ledger.schema import (
    L0_LAYER,
    L1_LAYER,
    L4_LAYER,
    HandicapLedgerEnvelope,
    HandicapLedgerReject,
)
from src.services.nfl_handicap_ledger.validate import (
    envelope_from_row,
    validate_l0_row,
    validate_l1_row,
    validate_l4_row,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


class AppendOnlyHandicapLedger:
    """In-memory + optional JSONL store. Append only; duplicate id ⇒ reject."""

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = Path(path) if path is not None else None
        self._rows: List[Dict[str, Any]] = []
        self._ids: Dict[str, Dict[str, Any]] = {}
        if self.path is not None and self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                pid = str(row.get("prediction_id") or "")
                if pid:
                    self._ids[pid] = row
                self._rows.append(row)

    def __len__(self) -> int:
        return len(self._rows)

    def rows(self) -> List[Dict[str, Any]]:
        return list(self._rows)

    def get(self, prediction_id: str) -> Optional[Dict[str, Any]]:
        return self._ids.get(prediction_id)

    def append(self, row: Union[HandicapLedgerEnvelope, Dict[str, Any]]) -> Dict[str, Any]:
        if isinstance(row, HandicapLedgerEnvelope):
            payload = row.to_dict()
        else:
            payload = dict(row)
        pid = str(payload.get("prediction_id") or "").strip()
        if not pid:
            raise HandicapLedgerReject("append REJECT missing prediction_id (no impute)")
        if pid in self._ids:
            raise HandicapLedgerReject(
                f"append REJECT prediction_id already exists ({pid}); never overwrite"
            )
        if not payload.get("created_at"):
            payload["created_at"] = _utc_now()
        self._ids[pid] = payload
        self._rows.append(payload)
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(payload, sort_keys=True, default=str) + "\n")
        return payload

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
        return self.append(env)
