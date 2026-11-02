"""Atomic per-game paired-arm seal. Duplicate / race / partial-write refuse.

Offline only. No network, DB, or outcome reader.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from src.services.nfl_r6_caller.contract import (
    OUTPUT_KIND,
    PACKAGE_ID,
    PAIRED_ARMS,
    SCHEMA_VERSION,
    R6Refuse,
    R6RefuseCode,
    pin_block,
)

REQUIRED_SEAL_KEYS = (
    "package_id",
    "schema_version",
    "game_id",
    "output_kind",
    "arms",
    "input_hash",
    "state_hash",
    "config_hash",
    "seal_id",
    "cutoff",
    "refusals",
    "manifest_id",
    "synthetic",
)


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _is_complete_seal(record: Mapping[str, Any]) -> bool:
    if any(key not in record for key in REQUIRED_SEAL_KEYS):
        return False
    if record.get("output_kind") != OUTPUT_KIND:
        return False
    arms = record.get("arms")
    if not isinstance(arms, dict):
        return False
    if set(arms) != PAIRED_ARMS:
        return False
    for name in PAIRED_ARMS:
        arm = arms.get(name)
        if not isinstance(arm, dict) or "status" not in arm:
            return False
    return True


class PairedArmLedger:
    """One JSON file per game_id. Write is tmp+fsync+replace under flock."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock_path = self.root / ".ledger.lock"

    def path_for(self, game_id: str) -> Path:
        safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in game_id)
        return self.root / f"{safe}.json"

    def _lock(self, *, blocking: bool = False) -> int:
        fd = os.open(self.lock_path, os.O_CREAT | os.O_RDWR, 0o644)
        flags = fcntl.LOCK_EX if blocking else fcntl.LOCK_EX | fcntl.LOCK_NB
        try:
            fcntl.flock(fd, flags)
        except BlockingIOError as exc:
            os.close(fd)
            raise R6Refuse(R6RefuseCode.REFUSE_RACE, "ledger lock held (race)") from exc
        return fd

    def _unlock(self, fd: int) -> None:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)

    def read(self, game_id: str) -> Optional[Dict[str, Any]]:
        path = self.path_for(game_id)
        if not path.exists():
            return None
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or not _is_complete_seal(raw):
            raise R6Refuse(
                R6RefuseCode.REFUSE_PARTIAL,
                f"existing seal for {game_id} is incomplete",
            )
        return raw

    def seal(self, record: Mapping[str, Any]) -> Dict[str, Any]:
        if not isinstance(record, dict) or not _is_complete_seal(record):
            raise R6Refuse(R6RefuseCode.REFUSE_PARTIAL, "paired-arm seal incomplete")
        if record.get("package_id") != PACKAGE_ID or record.get("schema_version") != SCHEMA_VERSION:
            raise R6Refuse(R6RefuseCode.REFUSE_VERSION, "seal package/schema mismatch")
        game_id = str(record["game_id"])
        dest = self.path_for(game_id)
        fd = self._lock(blocking=False)
        tmp: Optional[Path] = None
        try:
            if dest.exists():
                existing = json.loads(dest.read_text(encoding="utf-8"))
                if not isinstance(existing, dict) or not _is_complete_seal(existing):
                    raise R6Refuse(
                        R6RefuseCode.REFUSE_PARTIAL,
                        f"refusing to overwrite incomplete seal {dest.name}",
                    )
                raise R6Refuse(
                    R6RefuseCode.REFUSE_DUPLICATE,
                    f"game {game_id} already sealed",
                )
            leftovers = list(self.root.glob(f".{dest.name}.*.tmp"))
            if leftovers:
                raise R6Refuse(
                    R6RefuseCode.REFUSE_PARTIAL,
                    f"partial tmp present for {game_id}",
                )
            payload = dict(record)
            payload["pins"] = pin_block()
            blob = canonical_json(payload) + "\n"
            tmp = dest.with_name(f".{dest.name}.{os.getpid()}.tmp")
            with open(tmp, "w", encoding="utf-8") as handle:
                handle.write(blob)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, dest)
            tmp = None
            dir_fd = os.open(self.root, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
            return json.loads(dest.read_text(encoding="utf-8"))
        finally:
            if tmp is not None and tmp.exists():
                tmp.unlink()
            self._unlock(fd)


def make_seal_record(
    *,
    game_id: str,
    input_hash: str,
    state_hash: str,
    config_hash: str,
    cutoff: Mapping[str, Any],
    arms: Mapping[str, Any],
    refusals: list[str],
    manifest_id: str,
    synthetic: bool,
) -> Dict[str, Any]:
    body = {
        "package_id": PACKAGE_ID,
        "schema_version": SCHEMA_VERSION,
        "game_id": game_id,
        "output_kind": OUTPUT_KIND,
        "arms": dict(arms),
        "input_hash": input_hash,
        "state_hash": state_hash,
        "config_hash": config_hash,
        "cutoff": dict(cutoff),
        "refusals": list(refusals),
        "manifest_id": manifest_id,
        "synthetic": bool(synthetic),
    }
    body["seal_id"] = sha256_hex(canonical_json(body))
    return body
