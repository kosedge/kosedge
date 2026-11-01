"""Persistent atomic one-run bind (t5108u / t5110u). Real EVAL stays gated."""

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
STATUS_BOUND = "BOUND"
STATUS_CLAIMED = "CLAIMED"
STATUS_IN_PROGRESS = "IN_PROGRESS"
STATUS_FAILED = "FAILED"
STATUS_CONSUMED = "CONSUMED"
TERMINAL_STATUSES = frozenset(
    {STATUS_CLAIMED, STATUS_IN_PROGRESS, STATUS_FAILED, STATUS_CONSUMED}
)


class OneRunRefuse(ValueError):
    """Fail-closed one-run bind."""


def _canonical(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _r2_hash_set(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "bind_id": str(payload["bind_id"]),
        "forecast_file_sha256": str(payload["forecast_file_sha256"]),
        "quote_manifest_sha256": str(payload["quote_manifest_sha256"]),
        "quote_extract_sha256s": [str(x) for x in payload["quote_extract_sha256s"]],
    }


def bind_id_for(payload: Mapping[str, Any]) -> str:
    body = {k: payload[k] for k in HASH_FIELDS}
    r2 = payload.get("r2_runtime_bytes")
    if r2:
        body["r2_runtime_bytes"] = _r2_hash_set(r2)
    return hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_one_run(path: Path | None = None) -> dict[str, Any] | None:
    dest = Path(path) if path else DEFAULT_PATH
    if not dest.is_file():
        return None
    return json.loads(dest.read_text(encoding="utf-8"))


def _write_exclusive(dest: Path, text: str) -> None:
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    try:
        fd = os.open(str(dest), flags, 0o644)
    except FileExistsError as exc:
        raise OneRunRefuse("one-run exclusive create refused — file exists") from exc
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
    except Exception:
        try:
            dest.unlink()
        except OSError:
            pass
        raise


def _replace_atomic(dest: Path, text: str) -> None:
    tmp = dest.with_name(dest.name + f".{os.getpid()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, dest)


def bind_one_run(
    *,
    effective_spec_sha256: str,
    code_sha256: str,
    input_sha256: str,
    forecast_sha256: str,
    cohort_sha256: str,
    alex_go_id: str,
    path: Path | None = None,
    r2_runtime_bytes: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Atomically persist the one-run record via exclusive create. Refuse duplicate/mismatch."""
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
        "status": STATUS_BOUND,
        "bound_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "exec_scoring": "BOUND_NOT_AUTHORIZED_UNTIL_COS_GO",
        "label": "RESEARCH_CONSUMED_RETRO",
        "cert_candidate": 0,
    }
    if r2_runtime_bytes is not None:
        try:
            record["r2_runtime_bytes"] = _r2_hash_set(r2_runtime_bytes)
        except KeyError as exc:
            raise OneRunRefuse(
                "r2_runtime_bytes requires bind_id + freeze/manifest/extract hash sets"
            ) from exc
    record["bind_id"] = bind_id_for(record)

    dest = Path(path) if path else DEFAULT_PATH
    dest.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(record, indent=2) + "\n"
    try:
        _write_exclusive(dest, text)
    except OneRunRefuse:
        existing = load_one_run(dest)
        if existing and existing.get("bind_id") == record["bind_id"]:
            raise OneRunRefuse("duplicate one-run bind — refuse second execution")
        mismatched = [
            name
            for name in HASH_FIELDS
            if existing and str(existing.get(name) or "") != str(record.get(name) or "")
        ]
        if existing and existing.get("r2_runtime_bytes") != record.get("r2_runtime_bytes"):
            mismatched.append("r2_runtime_bytes")
        raise OneRunRefuse(
            "one-run mismatch vs existing record: " + ", ".join(mismatched or ["bind_id"])
        )
    record["_path"] = str(dest)
    return record


def claim_path_for(dest: Path, bind_id: str) -> Path:
    return dest.with_name(f"{dest.name}.claim.{bind_id}")


def result_path_for(dest: Path, bind_id: str) -> Path:
    return dest.with_name(f"{dest.name}.result.{bind_id}.json")


def claim_one_run(path: Path | None, bind_id: str) -> dict[str, Any]:
    """Exclusive persistent claim keyed by bind ID. Must run before outcome join."""
    dest = Path(path) if path else DEFAULT_PATH
    record = load_one_run(dest)
    if not record:
        raise OneRunRefuse("no persistent one-run record")
    if record.get("bind_id") != bind_id:
        raise OneRunRefuse("claim bind_id mismatch")
    if record.get("status") in TERMINAL_STATUSES:
        raise OneRunRefuse(
            f"one-run already {record.get('status')} — refuse concurrent/second execution"
        )
    claim = claim_path_for(dest, bind_id)
    payload = {
        "bind_id": bind_id,
        "status": STATUS_IN_PROGRESS,
        "pid": os.getpid(),
        "claimed_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    try:
        _write_exclusive(claim, json.dumps(payload, indent=2) + "\n")
    except OneRunRefuse as exc:
        raise OneRunRefuse(
            "one-run exclusive claim refused — already claimed / concurrent caller"
        ) from exc
    # Re-read after exclusive create so a raced verifier cannot both proceed.
    record = load_one_run(dest) or {}
    if record.get("bind_id") != bind_id:
        raise OneRunRefuse("claim bind_id mismatch after exclusive create")
    if record.get("status") in TERMINAL_STATUSES:
        raise OneRunRefuse(
            f"one-run already {record.get('status')} — refuse concurrent/second execution"
        )
    record["status"] = STATUS_IN_PROGRESS
    record["claimed_at_utc"] = payload["claimed_at_utc"]
    record["claim_path"] = str(claim)
    _replace_atomic(dest, json.dumps(record, indent=2) + "\n")
    record["_path"] = str(dest)
    record["_claim_path"] = str(claim)
    return record


def complete_one_run(
    path: Path | None,
    bind_id: str,
    result: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Separate completion receipt. Does not reopen the exclusive claim."""
    dest = Path(path) if path else DEFAULT_PATH
    record = load_one_run(dest)
    if not record:
        raise OneRunRefuse("no persistent one-run record")
    if record.get("bind_id") != bind_id:
        raise OneRunRefuse("complete bind_id mismatch")
    if record.get("status") not in {STATUS_CLAIMED, STATUS_IN_PROGRESS}:
        raise OneRunRefuse(
            f"one-run complete refused from status {record.get('status')}"
        )
    receipt = {
        "schema_version": "nfl-t5113u-one-run-result-v1",
        "bind_id": bind_id,
        "status": "COMPLETED",
        "completed_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "result": dict(result or {}),
        "label": "RESEARCH_CONSUMED_RETRO",
        "cert_candidate": 0,
    }
    receipt_path = result_path_for(dest, bind_id)
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    record["status"] = STATUS_CONSUMED
    record["consumed_at_utc"] = receipt["completed_at_utc"]
    record["result_receipt_path"] = str(receipt_path)
    _replace_atomic(dest, json.dumps(record, indent=2) + "\n")
    record["_path"] = str(dest)
    record["_result_path"] = str(receipt_path)
    return record


def fail_one_run(path: Path | None, bind_id: str, error: str) -> dict[str, Any]:
    """Crash after claim: stay consumed/in-progress. No automatic rerun."""
    dest = Path(path) if path else DEFAULT_PATH
    record = load_one_run(dest) or {}
    if record.get("bind_id") != bind_id:
        raise OneRunRefuse("fail bind_id mismatch")
    record["status"] = STATUS_FAILED
    record["failed_at_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    record["failure"] = str(error)
    _replace_atomic(dest, json.dumps(record, indent=2) + "\n")
    record["_path"] = str(dest)
    return record


def consume_one_run(path: Path | None, bind_id: str) -> dict[str, Any]:
    """Back-compat alias: exclusive claim must already exist."""
    dest = Path(path) if path else DEFAULT_PATH
    record = load_one_run(dest)
    if not record:
        raise OneRunRefuse("no persistent one-run record")
    if record.get("status") == STATUS_CONSUMED:
        raise OneRunRefuse("one-run already CONSUMED — refuse second execution")
    if record.get("bind_id") != bind_id:
        raise OneRunRefuse("consume bind_id mismatch")
    if record.get("status") not in {STATUS_CLAIMED, STATUS_IN_PROGRESS}:
        raise OneRunRefuse(
            "consume requires a prior exclusive claim — refuse read-then-replace score"
        )
    return complete_one_run(dest, bind_id)


def verify_one_run(
    record: Mapping[str, Any] | None,
    *,
    forecast_sha256: str,
    cohort_sha256: str,
    exec_bind: str | None,
    alex_go_id: str | None = None,
    live_effective_spec_sha256: str | None = None,
    live_code_sha256: str | None = None,
    live_input_sha256: str | None = None,
    code_root: Path | None = None,
    spec_path: Path | None = None,
    input_path: Path | None = None,
    path: Path | None = None,
    r2_runtime_bytes: Mapping[str, Any] | None = None,
    require_r2_runtime_bytes: bool = False,
) -> dict[str, Any]:
    if not record:
        raise OneRunRefuse("no persistent one-run record")
    if record.get("status") in TERMINAL_STATUSES:
        raise OneRunRefuse(
            f"one-run already {record.get('status')} — refuse second execution"
        )
    dest = Path(path) if path is not None else None
    bind_id = str(record.get("bind_id") or "")
    claim = Path(str(record["claim_path"])) if record.get("claim_path") else None
    if claim is None and dest is not None and bind_id:
        candidate = claim_path_for(dest, bind_id)
        if candidate.is_file():
            claim = candidate
    if claim is not None and claim.is_file() and record.get("status") == STATUS_BOUND:
        raise OneRunRefuse("one-run exclusive claim exists — refuse automatic rerun")
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

    live_code = hash_code_tree(Path(code_root)) if code_root is not None else live_code_sha256
    live_spec = sha256_file(Path(spec_path)) if spec_path is not None else live_effective_spec_sha256
    live_input = sha256_file(Path(input_path)) if input_path is not None else live_input_sha256
    if not live_code or not live_spec or not live_input:
        raise OneRunRefuse("runtime rehash of code/spec/input required")
    if live_code != record.get("code_sha256"):
        raise OneRunRefuse("code hash mismatch at run time")
    if live_spec != record.get("effective_spec_sha256"):
        raise OneRunRefuse("effective-spec hash mismatch at run time")
    if live_input != record.get("input_sha256"):
        raise OneRunRefuse("input hash mismatch at run time")
    bound_r2 = record.get("r2_runtime_bytes")
    if require_r2_runtime_bytes and not bound_r2:
        raise OneRunRefuse(
            "ONE_RUN missing r2_runtime_bytes — side bind alone insufficient"
        )
    if bound_r2 is not None or require_r2_runtime_bytes:
        if r2_runtime_bytes is None:
            raise OneRunRefuse("live R2 file-byte hashes required for verify_one_run")
        try:
            live_r2 = _r2_hash_set(r2_runtime_bytes)
            expected_r2 = _r2_hash_set(bound_r2 or {})
        except KeyError as exc:
            raise OneRunRefuse(
                "r2_runtime_bytes requires bind_id + freeze/manifest/extract hash sets"
            ) from exc
        if live_r2 != expected_r2:
            raise OneRunRefuse(
                "ONE_RUN r2_runtime_bytes mismatch — refuse before claim"
            )
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
