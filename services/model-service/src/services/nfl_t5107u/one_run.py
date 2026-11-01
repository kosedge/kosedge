"""Persistent atomic one-run bind (t5108u). Real EVAL stays gated on this + Alex GO."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

DEFAULT_PATH = Path("data/ops/nfl-forecast-builder-t5107u/ONE_RUN.json")
SCHEMA = "nfl-t5108u-one-run-v1"
HASH_FIELDS = (
    "effective_spec_sha256",
    "code_sha256",
    "input_sha256",
    "forecast_sha256",
    "cohort_sha256",
    "alex_go_id",
)


class OneRunRefuse(ValueError):
    """Fail-closed one-run bind."""


def _canonical(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def bind_id_for(payload: Mapping[str, Any]) -> str:
    body = {k: payload[k] for k in HASH_FIELDS}
    return hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()


def load_one_run(path: Path | None = None) -> dict[str, Any] | None:
    dest = Path(path) if path else DEFAULT_PATH
    if not dest.is_file():
        return None
    return json.loads(dest.read_text(encoding="utf-8"))


def bind_one_run(
    *,
    effective_spec_sha256: str,
    code_sha256: str,
    input_sha256: str,
    forecast_sha256: str,
    cohort_sha256: str,
    alex_go_id: str,
    path: Path | None = None,
) -> dict[str, Any]:
    """Atomically persist the one-run record. Refuse duplicate or mismatch."""
    if not str(alex_go_id or "").strip():
        raise OneRunRefuse("Alex GO id required for one-run bind")
    for name, value in (
        ("effective_spec_sha256", effective_spec_sha256),
        ("code_sha256", code_sha256),
        ("input_sha256", input_sha256),
        ("forecast_sha256", forecast_sha256),
        ("cohort_sha256", cohort_sha256),
    ):
        if not str(value or "").strip() or str(value) in {"", "0" * 64}:
            raise OneRunRefuse(f"{name} missing or placeholder")

    record = {
        "schema_version": SCHEMA,
        "effective_spec_sha256": str(effective_spec_sha256),
        "code_sha256": str(code_sha256),
        "input_sha256": str(input_sha256),
        "forecast_sha256": str(forecast_sha256),
        "cohort_sha256": str(cohort_sha256),
        "alex_go_id": str(alex_go_id).strip(),
        "bound_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "exec_scoring": "BOUND_NOT_AUTHORIZED_UNTIL_COS_GO",
        "label": "RESEARCH_CONSUMED_RETRO",
        "cert_candidate": 0,
    }
    record["bind_id"] = bind_id_for(record)

    dest = Path(path) if path else DEFAULT_PATH
    dest.parent.mkdir(parents=True, exist_ok=True)
    existing = load_one_run(dest)
    if existing:
        if existing.get("bind_id") == record["bind_id"]:
            raise OneRunRefuse("duplicate one-run bind — refuse second execution")
        mismatched = [
            name
            for name in HASH_FIELDS
            if str(existing.get(name) or "") != str(record.get(name) or "")
        ]
        raise OneRunRefuse(
            "one-run mismatch vs existing record: " + ", ".join(mismatched or ["bind_id"])
        )

    tmp = dest.with_name(dest.name + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, dest)
    record["_path"] = str(dest)
    return record


def verify_one_run(
    record: Mapping[str, Any] | None,
    *,
    forecast_sha256: str,
    cohort_sha256: str,
    exec_bind: str | None,
    alex_go_id: str | None = None,
) -> dict[str, Any]:
    if not record:
        raise OneRunRefuse("no persistent one-run record")
    if record.get("bind_id") != bind_id_for(record):
        raise OneRunRefuse("one-run bind_id does not match bound hashes")
    if exec_bind != record.get("bind_id"):
        raise OneRunRefuse("exec_bind does not match persistent one-run bind_id")
    if record.get("forecast_sha256") != forecast_sha256:
        raise OneRunRefuse("one-run forecast hash mismatch")
    if record.get("cohort_sha256") != cohort_sha256:
        raise OneRunRefuse("one-run cohort hash mismatch")
    if alex_go_id and alex_go_id != record.get("alex_go_id"):
        raise OneRunRefuse("Alex GO id mismatch vs one-run record")
    if not record.get("alex_go_id"):
        raise OneRunRefuse("one-run record missing Alex GO id")
    return dict(record)


def hash_code_tree(root: Path) -> str:
    digest = hashlib.sha256()
    files = sorted(p for p in root.rglob("*.py") if p.is_file() and "__pycache__" not in p.parts)
    if not files:
        raise OneRunRefuse(f"no python files under {root}")
    for path in files:
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()
