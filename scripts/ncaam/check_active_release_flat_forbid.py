#!/usr/bin/env python3
"""CI forbid: governed readers must not use legacy flat constants as SoT (CR7).

Scans known governed consumer entrypoints for direct authoritative reads through
``C.FEATURE_DIR`` / ``C.LABEL_DIR`` / ``C.SEAL_DIR`` / ``C.CANONICAL_PACK_PATH`` /
``C.REJECTED_DIR`` or hard-coded flat seal/feature paths under the holdout root.

Allowed: active_release imports, promote/recovery internals, forensic scripts,
constants definitions, and explicit staging writers.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

# Governed reader entrypoints that MUST resolve via active_release / CURRENT.
GOVERNED_READER_FILES = (
    "scripts/ncaam/verify_2425_sealed_artifacts.py",
    "scripts/ncaam/run_2425_coverage_26b.py",
    "scripts/ncaam/run_2425_phase26c.py",
    "scripts/ncaam/build_2425_sealed_holdout.py",
)

# Patterns that indicate a direct flat-constant authoritative read.
FORBIDDEN_PATTERNS = (
    re.compile(r"\bC\.FEATURE_DIR\b"),
    re.compile(r"\bC\.LABEL_DIR\b"),
    re.compile(r"\bC\.SEAL_DIR\b"),
    re.compile(r"\bC\.REJECTED_DIR\b"),
    re.compile(r"\bC\.CANONICAL_PACK_PATH\b"),
    re.compile(r"\bCANONICAL_PACK_PATH\b"),
    re.compile(r'OUT_ROOT\s*/\s*["\']feature_package["\']'),
    re.compile(r'OUT_ROOT\s*/\s*["\']seal["\']'),
    re.compile(r'HOLDOUT\s*/\s*["\']seal["\']'),
    re.compile(
        r'ncaam_schedule["\']?\s*/\s*["\']?data["\']?\s*/\s*["\']?'
        r"ncaam_official_schedule_2024_25"
    ),
)

# Lines that mention the constant only in error messages / refuse docs are OK
# when they also reference active_release or CURRENT dual-reality language.
ALLOW_LINE_HINTS = (
    "non-authoritative",
    "active_release",
    "CURRENT",
    "ActiveReleaseError",
    "load_canonical_pack",
    "canonical_pack_path_for_active",
    "active_artifacts",
    "load_feature_content",
    "load_seal_receipt",
)


def _violations_in(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    found: list[str] = []
    # Builder may still mkdir flat dirs when CURRENT is absent; pack/feature/seal
    # *reads* must go through active_release.
    is_builder = path.name == "build_2425_sealed_holdout.py"
    for i, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if any(h in line for h in ALLOW_LINE_HINTS):
            continue
        if is_builder and re.search(r"\bC\.(SEAL_DIR|REJECTED_DIR|QUARANTINE_DIR)\b", line):
            # Flat write destinations for pre-CURRENT builds only (refused when CURRENT set).
            continue
        for pat in FORBIDDEN_PATTERNS:
            if pat.search(line):
                found.append(f"{path.relative_to(REPO)}:{i}: {stripped[:120]}")
                break
    return found


def main() -> int:
    violations: list[str] = []
    for rel in GOVERNED_READER_FILES:
        path = REPO / rel
        if not path.exists():
            violations.append(f"missing governed reader: {rel}")
            continue
        # Must import active_release API.
        text = path.read_text(encoding="utf-8")
        if "active_release" not in text:
            violations.append(f"{rel}: missing active_release import/usage")
        violations.extend(_violations_in(path))

    # Model-service schedule loader must not claim static DATA_DIR is recovered pack.
    sched = (
        REPO
        / "services"
        / "model-service"
        / "src"
        / "services"
        / "ncaam_schedule"
        / "official_schedule.py"
    )
    sched_text = sched.read_text(encoding="utf-8")
    if "resolve_holdout_pack_via_current" not in sched_text:
        violations.append(
            "official_schedule.py: missing CURRENT holdout pack resolution (CR7)"
        )
    if "holdout_CURRENT_release" not in sched_text:
        violations.append(
            "official_schedule.py: missing authority stamp for holdout season"
        )

    if violations:
        print("CR7 flat-constant authoritative-read forbid FAILED:", file=sys.stderr)
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        return 2
    print(
        "CR7 flat-constant forbid OK: "
        f"{len(GOVERNED_READER_FILES)} governed readers + schedule loader."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
