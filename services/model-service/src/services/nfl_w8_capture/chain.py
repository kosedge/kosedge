"""AC-5: hash-chained append-only evidence log."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from src.services.nfl_w8_capture.constants import CHAIN_GENESIS


def _canonical(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_hex(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def genesis_sha() -> str:
    return sha256_hex(CHAIN_GENESIS.encode("utf-8"))


@dataclass
class ChainLog:
    path: Path
    entries: list[dict[str, Any]]
    sealed: bool = False

    @property
    def head(self) -> str:
        if not self.entries:
            return genesis_sha()
        return str(self.entries[-1]["entry_sha256"])


def open_log(path: Path) -> ChainLog:
    entries: list[dict[str, Any]] = []
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            entries.append(json.loads(line))
    return ChainLog(path=path, entries=entries, sealed=any(e.get("event") == "SEAL" for e in entries))


def append_event(
    log: ChainLog,
    *,
    event: str,
    ts_utc: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    if log.sealed and event not in {"CUSTODIAN_RECEIPT", "VERIFY"}:
        raise ValueError("AC-7: evidence log is sealed; only custodian receipt or verify may append")
    if event == "SEAL":
        log.sealed = True
    body = {
        "seq": len(log.entries) + 1,
        "ts_utc": ts_utc,
        "event": event,
        "payload": payload,
        "prev_sha256": log.head,
    }
    entry_sha = sha256_hex(_canonical(body))
    body["entry_sha256"] = entry_sha
    log.entries.append(body)
    log.path.parent.mkdir(parents=True, exist_ok=True)
    with log.path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(body, sort_keys=True) + "\n")
    return body


def verify_chain(log: ChainLog) -> Optional[str]:
    prev = genesis_sha()
    for idx, entry in enumerate(log.entries, start=1):
        expected_seq = idx
        if int(entry.get("seq") or 0) != expected_seq:
            return f"chain_seq_break_at_{idx}"
        if entry.get("prev_sha256") != prev:
            return f"chain_prev_break_at_{idx}"
        body = {k: v for k, v in entry.items() if k != "entry_sha256"}
        if sha256_hex(_canonical(body)) != entry.get("entry_sha256"):
            return f"chain_entry_tamper_at_{idx}"
        prev = entry["entry_sha256"]
    return None
