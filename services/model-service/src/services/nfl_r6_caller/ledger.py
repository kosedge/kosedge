"""Atomic per-game paired-arm seal. Duplicate / race / partial-write refuse.

Verify digest, identities, hashes, KO−60 cutoff and finite arms on BOTH
seal and read. Tampered files refuse without overwrite.
Offline only. No network, DB, or outcome reader.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from src.services.nfl_r6_caller.contract import (
    OUTPUT_KIND,
    PACKAGE_ID,
    PAIRED_ARMS,
    SCHEMA_VERSION,
    SYNTHETIC_CHANNEL,
    R6Refuse,
    R6RefuseCode,
    pin_block,
    require_canonical_hash,
    require_full_pins,
    require_parsed_cutoff,
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
    "pins",
)


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def seal_digest(record: Mapping[str, Any]) -> str:
    body = {key: record[key] for key in record if key != "seal_id"}
    return sha256_hex(canonical_json(body))


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


def _finite_arm_mean(arm: Mapping[str, Any], *, name: str) -> None:
    status = str(arm.get("status") or "")
    if status != "SEALED":
        return
    value = arm.get("mean")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise R6Refuse(R6RefuseCode.REFUSE_OUTPUT, f"{name} mean is not a number")
    if not math.isfinite(float(value)):
        raise R6Refuse(R6RefuseCode.REFUSE_OUTPUT, f"{name} mean is not finite")


def verify_seal_record(record: Mapping[str, Any]) -> Dict[str, Any]:
    """Fail-closed verify. Used on both seal and read. Does not write."""
    if not isinstance(record, dict) or not _is_complete_seal(record):
        raise R6Refuse(R6RefuseCode.REFUSE_PARTIAL, "paired-arm seal incomplete")
    if record.get("package_id") != PACKAGE_ID or record.get("schema_version") != SCHEMA_VERSION:
        raise R6Refuse(R6RefuseCode.REFUSE_VERSION, "seal package/schema mismatch")
    if record.get("output_kind") != OUTPUT_KIND:
        raise R6Refuse(R6RefuseCode.REFUSE_OUTPUT, "output_kind must be POINT_MARGIN")
    if record.get("synthetic") is not True:
        raise R6Refuse(R6RefuseCode.REFUSE_SYNTHETIC, "seal.synthetic must be true")
    game_id = str(record.get("game_id") or "").strip()
    if not game_id:
        raise R6Refuse(R6RefuseCode.REFUSE_IDENTITY, "game_id missing")
    schema_hash = record.get("schema_hash")
    forbidden = frozenset([str(schema_hash)]) if schema_hash else frozenset()
    require_canonical_hash(record.get("input_hash"), label="input_hash", forbidden=forbidden)
    require_canonical_hash(record.get("state_hash"), label="state_hash", forbidden=forbidden)
    require_canonical_hash(record.get("config_hash"), label="config_hash", forbidden=forbidden)
    require_parsed_cutoff(record.get("cutoff"))
    pins = record.get("pins")
    if not isinstance(pins, Mapping):
        raise R6Refuse(R6RefuseCode.REFUSE_PIN, "pins missing on seal")
    require_full_pins(pins)
    arms = record["arms"]
    for name in PAIRED_ARMS:
        _finite_arm_mean(arms[name], name=name)
    digest = seal_digest(record)
    seal_id = str(record.get("seal_id") or "")
    if seal_id != digest:
        raise R6Refuse(
            R6RefuseCode.REFUSE_TAMPER,
            f"seal_id {seal_id!r} != digest {digest}",
        )
    return dict(record)


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

    def _load_raw(self, path: Path) -> Any:
        return json.loads(path.read_text(encoding="utf-8"))

    def read(self, game_id: str) -> Optional[Dict[str, Any]]:
        path = self.path_for(game_id)
        if not path.exists():
            return None
        raw = self._load_raw(path)
        return verify_seal_record(raw)

    def seal(self, record: Mapping[str, Any]) -> Dict[str, Any]:
        verified = verify_seal_record(record)
        game_id = str(verified["game_id"])
        dest = self.path_for(game_id)
        fd = self._lock(blocking=False)
        tmp: Optional[Path] = None
        try:
            if dest.exists():
                existing = self._load_raw(dest)
                try:
                    verify_seal_record(existing)
                except R6Refuse as exc:
                    raise R6Refuse(
                        R6RefuseCode.REFUSE_TAMPER,
                        f"existing seal for {game_id} failed verify; will not overwrite",
                    ) from exc
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
            blob = canonical_json(verified) + "\n"
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
            return verify_seal_record(self._load_raw(dest))
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
    schema_hash: str | None = None,
) -> Dict[str, Any]:
    parsed_cutoff = require_parsed_cutoff(cutoff)
    body: Dict[str, Any] = {
        "package_id": PACKAGE_ID,
        "schema_version": SCHEMA_VERSION,
        "game_id": game_id,
        "output_kind": OUTPUT_KIND,
        "arms": dict(arms),
        "input_hash": input_hash,
        "state_hash": state_hash,
        "config_hash": config_hash,
        "cutoff": parsed_cutoff,
        "refusals": list(refusals),
        "manifest_id": manifest_id,
        "synthetic": bool(synthetic),
        "channel": SYNTHETIC_CHANNEL,
        "pins": pin_block(),
    }
    if schema_hash:
        body["schema_hash"] = str(schema_hash)
    body["seal_id"] = seal_digest(body)
    return body
