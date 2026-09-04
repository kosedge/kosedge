#!/usr/bin/env python3
"""Truth-chain audit harness — step 1 inventory + provenance gate.

Fixture-based. No live prod secrets. No KEI mint. No rematerialize.
No PLAY eligibility flips.

Usage:
  python3 scripts/ops/truth_chain_audit.py \\
    --fixture data/ops/truth-chain-fixtures/step1_inventory.json

Exit 0 = PASS, 1 = FAIL.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REQUIRED_SURFACE_KEYS = ("id", "route", "fields", "sot")


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)


def check_number(surface_id: str, num: dict[str, Any], errors: list[str]) -> None:
    name = num.get("name") or "<unnamed>"
    label = f"{surface_id}/{name}"

    if "value" not in num:
        errors.append(f"{label}: missing value")

    requires_run_id = bool(num.get("requires_run_id"))
    requires_as_of = bool(num.get("requires_as_of"))

    if requires_run_id:
        run_id = num.get("run_id") or (num.get("provenance") or {}).get("run_id")
        snap = (num.get("provenance") or {}).get("snapshot_id")
        if not run_id and not snap:
            errors.append(
                f"{label}: requires_run_id but missing run_id/snapshot_id provenance"
            )

    if requires_as_of:
        as_of = num.get("as_of") or (num.get("provenance") or {}).get("as_of")
        if not as_of:
            errors.append(f"{label}: requires_as_of but missing as_of")

    tag = num.get("tag")
    if tag == "PLAY":
        # Step-1 guard: fixtures must not assert CFB PLAY while sit is product law.
        # NFL PLAY is out of scope for this stub (documented separately).
        sit = str((num.get("provenance") or {}).get("sit_flags") or "")
        if "CFB_" in sit and "false" in sit:
            errors.append(
                f"{label}: fixture asserts PLAY while CFB sit flags are false"
            )


def audit(fixture: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if int(fixture.get("schema_version") or 0) < 1:
        errors.append("schema_version must be >= 1")

    surfaces = fixture.get("surfaces")
    if not isinstance(surfaces, list) or not surfaces:
        errors.append("surfaces must be a non-empty list")
        return errors

    seen: set[str] = set()
    for surface in surfaces:
        if not isinstance(surface, dict):
            errors.append("surface entry must be an object")
            continue
        sid = str(surface.get("id") or "")
        if not sid:
            errors.append("surface missing id")
            continue
        if sid in seen:
            errors.append(f"duplicate surface id: {sid}")
        seen.add(sid)

        for key in REQUIRED_SURFACE_KEYS:
            if key not in surface:
                errors.append(f"{sid}: missing surface key '{key}'")

        fields = surface.get("fields")
        if not isinstance(fields, list) or not fields:
            errors.append(f"{sid}: fields must be a non-empty list")

        numbers = surface.get("numbers") or []
        if not isinstance(numbers, list):
            errors.append(f"{sid}: numbers must be a list")
            continue
        for num in numbers:
            if not isinstance(num, dict):
                errors.append(f"{sid}: number entry must be an object")
                continue
            check_number(sid, num, errors)

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixture",
        required=True,
        help="Path to step1 inventory JSON fixture",
    )
    args = parser.parse_args(argv)

    path = Path(args.fixture)
    if not path.is_file():
        fail(f"fixture not found: {path}")
        return 1

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON: {exc}")
        return 1

    errors = audit(data)
    if errors:
        for err in errors:
            fail(err)
        print(f"truth-chain audit: {len(errors)} error(s)", file=sys.stderr)
        return 1

    n_surfaces = len(data.get("surfaces") or [])
    n_numbers = sum(len(s.get("numbers") or []) for s in data.get("surfaces") or [])
    print(
        f"PASS: truth-chain step1 inventory ok "
        f"({n_surfaces} surfaces, {n_numbers} gated numbers)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
