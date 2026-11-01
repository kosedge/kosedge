"""R2 runtime byte rehash — file bytes, not in-memory re-serialize.

t5129u: ``FrozenCohort.forecast_sha256`` is an in-memory serialize. That is
insufficient. The R2 EVAL path must hash:

- frozen forecast **file** bytes
- quote **manifest** file bytes
- **each** admitted quote extract file bytes

Bind all into a new exclusive run record. The quote-manifest pin string
alone is insufficient. Mutation of any bound file refuses **before**
claim and **before** ``outcome_loader``.

CERT=0. No EVAL EXEC. DRAFT≠merge. Does not write R2-A coverage files.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA = "nfl-t5129u-r2-runtime-bytes-v1"
CERT_CANDIDATE = 0
LABEL = "RESEARCH_CONSUMED_RETRO"

_PKG_ROOT = Path(__file__).resolve().parents[5]
_OPS = _PKG_ROOT / "data/ops/nfl-forecast-builder-t5107u"

FORBIDDEN_BIND_NAMES = frozenset(
    {
        "ONE_RUN.json",
        "ONE_EXEC_RESULT_t5116u.json",
        "CURSOR_ONE_EXEC_RESULT_t5116u.md",
        "DEV_RESEARCH_t5119u_R2B.json",
        "DEV_RESEARCH_t5125u_R2B2_437.json",
        "OWNED_COVERAGE_t5119u.json",
        "R2A_COVERAGE_MANIFEST.json",
    }
)
FORBIDDEN_BIND_DESTS = frozenset(
    {
        _OPS / "ONE_RUN.json",
        _OPS / "ONE_EXEC_RESULT_t5116u.json",
        _PKG_ROOT / "ops/CURSOR_ONE_EXEC_RESULT_t5116u.md",
        _OPS / "DEV_RESEARCH_t5119u_R2B.json",
        _OPS / "DEV_RESEARCH_t5125u_R2B2_437.json",
        _OPS / "OWNED_COVERAGE_t5119u.json",
        _OPS / "R2A_COVERAGE_MANIFEST.json",
    }
)


class R2ByteRefuse(ValueError):
    """Fail-closed runtime file-byte rehash. Not a claim. Not EVAL EXEC."""


def sha256_file_bytes(path: Path | str) -> str:
    """SHA-256 of on-disk file bytes. Does not re-serialize JSON."""
    dest = Path(path)
    if not dest.is_file():
        raise R2ByteRefuse(f"runtime byte hash missing file: {dest}")
    digest = hashlib.sha256()
    with dest.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def bind_id_for(payload: Mapping[str, Any]) -> str:
    body = {
        "forecast_file_sha256": payload["forecast_file_sha256"],
        "quote_manifest_sha256": payload["quote_manifest_sha256"],
        "quote_extract_sha256s": list(payload["quote_extract_sha256s"]),
    }
    return hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()


def _refuse_preserved_bind_dest(path: Path) -> None:
    name = path.name
    if name in FORBIDDEN_BIND_NAMES:
        raise R2ByteRefuse(
            f"refusing R2 byte-bind dest {name} — preserved t5116u / first-case / DEV437 / R2-A"
        )
    resolved = path.resolve()
    for forbidden in FORBIDDEN_BIND_DESTS:
        if resolved == forbidden.resolve():
            raise R2ByteRefuse(
                f"refusing R2 byte-bind dest {resolved} — preserved / R2-A coverage"
            )


def _write_exclusive(dest: Path, text: str) -> None:
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    try:
        fd = os.open(str(dest), flags, 0o644)
    except FileExistsError as exc:
        raise R2ByteRefuse("R2 runtime-byte bind exclusive create refused — file exists") from exc
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
    except Exception:
        try:
            dest.unlink()
        except OSError:
            pass
        raise


def _require_files(
    *,
    forecast_file: Any,
    quote_manifest_file: Any,
    quote_extract_files: Sequence[Any] | None,
) -> tuple[Path, Path, list[Path]]:
    if forecast_file in (None, ""):
        raise R2ByteRefuse(
            "frozen forecast file required — in-memory serialize insufficient"
        )
    if quote_manifest_file in (None, ""):
        raise R2ByteRefuse(
            "quote manifest file required — pin string insufficient"
        )
    if not quote_extract_files:
        raise R2ByteRefuse(
            "admitted quote extract files required — manifest pin alone insufficient"
        )
    extracts = [Path(p) for p in quote_extract_files]
    if not extracts:
        raise R2ByteRefuse(
            "admitted quote extract files required — manifest pin alone insufficient"
        )
    return Path(forecast_file), Path(quote_manifest_file), extracts


def _extract_entries(extracts: Sequence[Path]) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for path in extracts:
        entries.append(
            {
                "path": str(path),
                "resolved": str(path.resolve()),
                "sha256": sha256_file_bytes(path),
            }
        )
    entries.sort(key=lambda row: row["resolved"])
    return entries


def bind_r2_runtime_bytes(
    *,
    forecast_file: Path | str,
    quote_manifest_file: Path | str,
    quote_extract_files: Sequence[Path | str],
    path: Path | str | None = None,
) -> dict[str, Any]:
    """Exclusive bind of freeze / manifest / extract **file** byte hashes."""
    if path in (None, ""):
        raise R2ByteRefuse(
            "R2 runtime-byte bind requires an explicit dest "
            "(not ONE_RUN / first-case / DEV437 / R2-A)"
        )
    dest = Path(path)
    _refuse_preserved_bind_dest(dest)
    freeze, manifest, extracts = _require_files(
        forecast_file=forecast_file,
        quote_manifest_file=quote_manifest_file,
        quote_extract_files=quote_extract_files,
    )
    extract_rows = _extract_entries(extracts)
    record = {
        "schema_version": SCHEMA,
        "forecast_file": str(freeze),
        "forecast_file_sha256": sha256_file_bytes(freeze),
        "quote_manifest_file": str(manifest),
        "quote_manifest_sha256": sha256_file_bytes(manifest),
        "quote_extracts": extract_rows,
        "quote_extract_sha256s": [row["sha256"] for row in extract_rows],
        "label": LABEL,
        "cert_candidate": CERT_CANDIDATE,
        "eval": None,
        "one_run_claim": False,
        "bound_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "note": "file-byte hashes; in-memory FrozenCohort serialize + manifest pin insufficient",
    }
    record["bind_id"] = bind_id_for(record)
    dest.parent.mkdir(parents=True, exist_ok=True)
    _write_exclusive(dest, json.dumps(record, indent=2) + "\n")
    record["_path"] = str(dest)
    return record


def load_r2_byte_bind(path: Path | str | Mapping[str, Any] | None) -> dict[str, Any]:
    if path is None:
        raise R2ByteRefuse(
            "R2 runtime-byte bind required — manifest pin alone insufficient"
        )
    if isinstance(path, Mapping):
        return dict(path)
    dest = Path(path)
    if not dest.is_file():
        raise R2ByteRefuse(f"R2 runtime-byte bind missing: {dest}")
    return json.loads(dest.read_text(encoding="utf-8"))


def verify_r2_runtime_bytes(
    *,
    forecast_file: Any,
    quote_manifest_file: Any,
    quote_extract_files: Sequence[Any] | None,
    r2_byte_bind: Path | str | Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Rehash freeze / manifest / each extract file. Refuse on any mutation."""
    freeze, manifest, extracts = _require_files(
        forecast_file=forecast_file,
        quote_manifest_file=quote_manifest_file,
        quote_extract_files=quote_extract_files,
    )
    record = load_r2_byte_bind(r2_byte_bind)
    if record.get("schema_version") != SCHEMA:
        raise R2ByteRefuse("R2 runtime-byte bind schema mismatch")
    if record.get("bind_id") != bind_id_for(record):
        raise R2ByteRefuse("R2 runtime-byte bind_id does not match bound file hashes")

    live_forecast = sha256_file_bytes(freeze)
    if live_forecast != record.get("forecast_file_sha256"):
        raise R2ByteRefuse("frozen forecast file bytes mutated — refuse before claim")
    live_manifest = sha256_file_bytes(manifest)
    if live_manifest != record.get("quote_manifest_sha256"):
        raise R2ByteRefuse("quote manifest file bytes mutated — refuse before claim")

    live_extracts = _extract_entries(extracts)
    bound_shas = list(record.get("quote_extract_sha256s") or [])
    live_shas = [row["sha256"] for row in live_extracts]
    if not live_shas:
        raise R2ByteRefuse(
            "admitted quote extract files required — manifest pin alone insufficient"
        )
    if live_shas != bound_shas:
        raise R2ByteRefuse(
            "admitted quote extract file bytes mutated — refuse before claim"
        )
    bound_rows = list(record.get("quote_extracts") or [])
    if len(bound_rows) != len(live_extracts):
        raise R2ByteRefuse(
            "admitted quote extract set mismatch — manifest pin alone insufficient"
        )
    bound_by_resolved = {str(row.get("resolved") or ""): row for row in bound_rows}
    for row in live_extracts:
        bound = bound_by_resolved.get(row["resolved"])
        if bound is None or bound.get("sha256") != row["sha256"]:
            raise R2ByteRefuse(
                "admitted quote extract file bytes mutated — refuse before claim"
            )

    return {
        "schema_version": SCHEMA,
        "bind_id": record["bind_id"],
        "forecast_file_sha256": live_forecast,
        "quote_manifest_sha256": live_manifest,
        "quote_extract_sha256s": live_shas,
        "quote_extract_n": len(live_shas),
        "in_memory_serialize_only": False,
        "manifest_pin_alone": False,
        "verified_before_claim": True,
        "verified_before_outcome_loader": True,
    }
