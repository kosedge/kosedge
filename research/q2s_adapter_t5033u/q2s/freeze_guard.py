"""t5035u freeze re-hash guards (Alex RETURN 404a4ab2 M1).

Re-hash every PROTOCOL_FREEZE entry and the FREEZE_ADDENDUM rows pin.
Refuse on mismatch. Do not rewrite PROTOCOL_FREEZE or Appendix O artifacts.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

SEALED_ROWS_SHA = (
    "0d6a5e144ef13c3ebe65d601404445909fb3f504ec3e9e34b101db643b8423ae"
)
SEALED_ROWS_PREFIX = "0d6a5e14"
ADDENDUM_REL = "artifacts/FREEZE_ADDENDUM.json"
ROWS_REL = "artifacts/q2s_rows_t5033u.json"
FREEZE_REL = "artifacts/PROTOCOL_FREEZE.json"


class FreezeGuardRefuse(RuntimeError):
    """Fail-closed freeze / rows pin mismatch."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise FreezeGuardRefuse(f"{path.name} is not a JSON object")
    return payload


def verify_protocol_freeze(
    root: Path,
    freeze_path: Path,
    addendum: Mapping[str, Any] | None = None,
) -> None:
    """Re-hash every PROTOCOL_FREEZE entry. Refuse on mismatch.

    A post-look guard amend listed in FREEZE_ADDENDUM may replace the live
    bytes of that path only when the current sha matches the addendum's
    guard_sha256. The executed PROTOCOL_FREEZE object is not rewritten.
    """
    if not freeze_path.exists():
        raise FreezeGuardRefuse("PROTOCOL_FREEZE missing — freeze before the look")
    freeze = load_json_object(freeze_path)
    files = freeze.get("files")
    if not isinstance(files, dict) or not files:
        raise FreezeGuardRefuse("PROTOCOL_FREEZE has no files map")

    allowed: dict[str, str] = {}
    if addendum:
        raw = addendum.get("post_look_guard_amends") or {}
        if not isinstance(raw, dict):
            raise FreezeGuardRefuse("FREEZE_ADDENDUM post_look_guard_amends is not a map")
        for rel, meta in raw.items():
            if not isinstance(meta, dict):
                raise FreezeGuardRefuse(f"addendum amend {rel} is not a map")
            guard_sha = str(meta.get("guard_sha256") or "")
            if not guard_sha:
                raise FreezeGuardRefuse(f"addendum amend {rel} missing guard_sha256")
            allowed[str(rel)] = guard_sha

    missing: list[str] = []
    mismatches: list[dict[str, str]] = []
    for rel, expected in files.items():
        path = root / str(rel)
        if not path.exists():
            missing.append(str(rel))
            continue
        actual = sha256_file(path)
        expected_s = str(expected)
        if actual == expected_s:
            continue
        if allowed.get(str(rel)) == actual:
            continue
        mismatches.append(
            {"path": str(rel), "expected": expected_s, "actual": actual}
        )
    if missing or mismatches:
        raise FreezeGuardRefuse(
            "PROTOCOL_FREEZE re-hash mismatch: "
            f"missing={missing} mismatches={mismatches}"
        )


def verify_rows_addendum(
    root: Path,
    addendum_path: Path,
    rows_path: Path,
) -> Mapping[str, Any]:
    """Re-hash emitted q2s rows against FREEZE_ADDENDUM. Refuse on mismatch."""
    if not addendum_path.exists():
        raise FreezeGuardRefuse("FREEZE_ADDENDUM missing")
    if not rows_path.exists():
        raise FreezeGuardRefuse("q2s_rows_t5033u.json missing")
    addendum = load_json_object(addendum_path)
    emitted = addendum.get("emitted_rows") or {}
    if not isinstance(emitted, dict):
        raise FreezeGuardRefuse("FREEZE_ADDENDUM emitted_rows is not a map")
    expected = str(emitted.get("sha256") or "")
    if not expected.startswith(SEALED_ROWS_PREFIX):
        raise FreezeGuardRefuse(
            f"FREEZE_ADDENDUM rows sha {expected[:8]} != sealed {SEALED_ROWS_PREFIX}"
        )
    if expected != SEALED_ROWS_SHA:
        raise FreezeGuardRefuse(
            f"FREEZE_ADDENDUM rows sha {expected} != sealed {SEALED_ROWS_SHA}"
        )
    actual = sha256_file(rows_path)
    if actual != expected:
        raise FreezeGuardRefuse(
            f"q2s rows sha {actual} != FREEZE_ADDENDUM {expected}"
        )
    rel = str(emitted.get("path") or ROWS_REL)
    if (root / rel).resolve() != rows_path.resolve() and rel != rows_path.name:
        # Allow either the package-relative path or a test temp file named the same.
        if rows_path.name != "q2s_rows_t5033u.json":
            raise FreezeGuardRefuse(f"rows path {rows_path.name} != q2s_rows_t5033u.json")
    return addendum


def assert_freeze_and_rows(root: Path) -> dict[str, Any]:
    freeze_path = root / FREEZE_REL
    addendum_path = root / ADDENDUM_REL
    rows_path = root / ROWS_REL
    addendum = verify_rows_addendum(root, addendum_path, rows_path)
    verify_protocol_freeze(root, freeze_path, addendum)
    return dict(addendum)
