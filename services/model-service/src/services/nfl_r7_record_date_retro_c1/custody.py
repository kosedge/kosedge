"""Atomic persistent exclusive claim custody. CERT=0.

Durable phases: CLAIMED → FORECASTS_SEALED → SCORED → SPENT|FAILED.
Restart / replay / second writer (including a fresh process) refuse.
Spent/failed/R5 cannot reset or overwrite.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from src.services.nfl_r7_record_date_retro_c1.pins import ARCHIVED_R5_CLAIM, CERT
from src.services.nfl_r7_record_date_retro_c1.refuse import RetroRefuse

PHASE_CLAIMED = "CLAIMED"
PHASE_FORECASTS_SEALED = "FORECASTS_SEALED"
PHASE_SCORED = "SCORED"
PHASE_SPENT = "SPENT"
PHASE_FAILED = "FAILED"
TERMINAL = frozenset({PHASE_SPENT, PHASE_FAILED})
LEGAL = {
    PHASE_CLAIMED: {PHASE_FORECASTS_SEALED, PHASE_FAILED},
    PHASE_FORECASTS_SEALED: {PHASE_SCORED, PHASE_FAILED},
    PHASE_SCORED: {PHASE_SPENT, PHASE_FAILED},
    PHASE_SPENT: set(),
    PHASE_FAILED: set(),
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _atomic_write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_bytes(raw)
    os.replace(tmp, path)


class PersistentCustody:
    def __init__(self, store_dir: Path) -> None:
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)

    def claim_path(self, claim_id: str) -> Path:
        return self.store_dir / f"{claim_id}.json"

    def lock_path(self, claim_id: str) -> Path:
        return self.store_dir / f"{claim_id}.lock"

    def forecasts_path(self, claim_id: str) -> Path:
        return self.store_dir / f"{claim_id}.forecasts.json"

    def seal_path(self, claim_id: str) -> Path:
        return self.store_dir / f"{claim_id}.forecasts.sha256"

    def scores_path(self, claim_id: str) -> Path:
        return self.store_dir / f"{claim_id}.scores.json"

    def _exclusive_lock(self, claim_id: str) -> None:
        if claim_id == ARCHIVED_R5_CLAIM:
            raise RetroRefuse("archived R5 consumed claim cannot be issued or reused")
        lock = self.lock_path(claim_id)
        try:
            fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise RetroRefuse(f"exclusive claim refused (restart/replay/second writer): {claim_id}") from exc
        with os.fdopen(fd, "w") as fh:
            fh.write(f"{os.getpid()}\n{_utc()}\n")

    def load(self, claim_id: str) -> dict[str, Any] | None:
        path = self.claim_path(claim_id)
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def issue(self, claim_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        if self.claim_path(claim_id).is_file() or self.lock_path(claim_id).is_file():
            raise RetroRefuse(f"exclusive claim refused (restart/replay/second writer): {claim_id}")
        self._exclusive_lock(claim_id)
        row = {
            **dict(payload),
            "claim_id": claim_id,
            "phase": PHASE_CLAIMED,
            "status": PHASE_CLAIMED,
            "cert": CERT,
            "issued_utc": _utc(),
        }
        _atomic_write(self.claim_path(claim_id), row)
        return dict(row)

    def advance(self, claim_id: str, phase: str, extra: Mapping[str, Any] | None = None) -> dict[str, Any]:
        row = self.load(claim_id)
        if row is None:
            raise RetroRefuse(f"claim missing {claim_id}")
        current = str(row.get("phase") or row.get("status"))
        if current in TERMINAL:
            raise RetroRefuse(f"terminal claim cannot advance {claim_id} {current}→{phase}")
        if phase not in LEGAL.get(current, set()):
            raise RetroRefuse(f"illegal phase {current}→{phase} for {claim_id}")
        row["phase"] = phase
        row["status"] = phase
        row[f"{phase.lower()}_utc"] = _utc()
        if extra:
            row.update(dict(extra))
        _atomic_write(self.claim_path(claim_id), row)
        return dict(row)

    def refuse_if_terminal_or_foreign(self, claim_id: str) -> dict[str, Any]:
        row = self.load(claim_id)
        if row is None:
            raise RetroRefuse(f"claim not in custody {claim_id}")
        phase = str(row.get("phase") or row.get("status"))
        if phase == PHASE_SPENT:
            raise RetroRefuse(f"spent claim cannot retry {claim_id}")
        if phase == PHASE_FAILED:
            raise RetroRefuse(f"failed claim cannot reset {claim_id}")
        return dict(row)

    def write_forecasts_and_seal(self, claim_id: str, forecasts: list[Mapping[str, Any]], digest: str) -> None:
        row = self.refuse_if_terminal_or_foreign(claim_id)
        if row["phase"] != PHASE_CLAIMED:
            raise RetroRefuse(f"forecasts only from CLAIMED, not {row['phase']}")
        if self.forecasts_path(claim_id).is_file() or self.seal_path(claim_id).is_file():
            raise RetroRefuse(f"forecasts already sealed {claim_id}")
        _atomic_write(self.forecasts_path(claim_id), {"forecasts": list(forecasts), "n": len(forecasts)})
        self.seal_path(claim_id).write_text(digest + "\n", encoding="utf-8")
        self.advance(claim_id, PHASE_FORECASTS_SEALED, extra={"forecast_digest": digest, "n_forecasts": len(forecasts)})

    def write_scores(self, claim_id: str, scores: Mapping[str, Any]) -> None:
        row = self.refuse_if_terminal_or_foreign(claim_id)
        if row["phase"] != PHASE_FORECASTS_SEALED:
            raise RetroRefuse(f"labels unread until FORECASTS_SEALED, phase={row['phase']}")
        if self.scores_path(claim_id).is_file():
            raise RetroRefuse(f"scores already written {claim_id}")
        _atomic_write(self.scores_path(claim_id), scores)
        self.advance(claim_id, PHASE_SCORED)

    def spend(self, claim_id: str) -> dict[str, Any]:
        return self.advance(claim_id, PHASE_SPENT)

    def fail(self, claim_id: str, *, reason: str) -> dict[str, Any]:
        row = self.load(claim_id)
        if row is None:
            raise RetroRefuse("cannot fail unknown claim")
        if row.get("phase") in TERMINAL:
            raise RetroRefuse(f"terminal claim cannot be rebound {claim_id}")
        return self.advance(claim_id, PHASE_FAILED, extra={"fail_reason": reason})
