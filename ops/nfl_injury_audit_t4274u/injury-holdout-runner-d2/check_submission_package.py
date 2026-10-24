#!/usr/bin/env python3
"""D-2 package checker — fixtures + le2023. No 2024/25 open."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

REQUIRED_DECISION = "fabf87320453c274b2b8ec8e443b8af4709d8d24ff8fb6baa449fe3d739d4bd0"
REQUIRED_READINESS_V6 = "8ca00bc49b412c1524b4a0d5a1ebacdd7bc4fe26f3e6354d52cb549812dbb012"
REQUIRED_ERRATUM_V6 = "14ac18190c89d3620a6f27d0a0be64fc8147c321063ca4aeaa459faa31fcde41"
REQUIRED_REQUEST_V31 = "35cbb56e10cfe0ec3730441a453f171bda917e7c58ad3e5eb2fe2c573de5ef7b"
REQUIRED_SPEC = "a156459b545e3b7d6a483f1db34cda7a4d32fc3afc70ed499b3adc726b1b6881"
REQUIRED_ACCEPT = "54bc78ecc70e6a440481253b9c7eeef0e749690e893f501862f5dd5c54444574"
REQUIRED_EXPORT = "a38a55bb765e977ed88f8808d76715faddf50098b2354b122a5499f0ec706ac8"
REQUIRED_EXPORT_BLOB_NOT_A_PIN = "46d2a5657d1b5a5eb1af03f4d643afbfaa4762f31260daff439b5df1ac1456eb"
REQUIRED_EXPECTED = "e46b4fec5bdf892291c1f1617f59a5b1bd0d6f90d1e288fd005a149542260043"
REQUIRED_EXPECTED_COMMIT = "ff3b3b0bfe91a42d4165a2cd81d5a811277b38c7"
SKIP_DIRS = {".git", "__pycache__"}
SKIP_NAMES = {"MANIFEST", "SHA256SUMS", "MANIFEST.sha256", "checker.log", "checker.stdout.txt"}
SEEDED = (
    ("decision", "seeded/DECISION_RYAN_t4335s14919_HOLDOUT_CLEAR_v3_1_v1.txt", REQUIRED_DECISION),
    ("v6", "seeded/IMV_RULING_NFL_INJURY_EVALUATOR_READINESS_v6.txt", REQUIRED_READINESS_V6),
    ("erratum", "seeded/IMV_RULING_NFL_INJURY_EVALUATOR_READINESS_v6_ERRATUM_v1.txt", REQUIRED_ERRATUM_V6),
    ("request", "seeded/nfl-injury-holdout-request-2024-2025-v3.1.md", REQUIRED_REQUEST_V31),
    ("spec", "seeded/IMV_SPEC_NFL_INJURY_ADJUSTMENT_TESTS_v1.txt", REQUIRED_SPEC),
    ("accept", "seeded/IMV_SPEC_NFL_INJURY_PRE_HOLDOUT_ACCEPTANCE_v1.txt", REQUIRED_ACCEPT),
    ("export", "seeded/sealed_injury_export_ts_v1.json", REQUIRED_EXPORT),
    ("expected", "t_expected/D2_EXPECTED.json", REQUIRED_EXPECTED),
)
COMPARE_OUT = ("d2_results.json", "provenance.md")


def log(msg: str) -> None:
    sys.stderr.write(msg + "\n")
    sys.stderr.flush()


def sha256_file(path: Path) -> str:
    if not path.is_file():
        return ""
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_runner(root: Path):
    spec = importlib.util.spec_from_file_location("injury_d2", root / "run_injury_holdout_d2.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load D-2 runner")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def write_manifest(root: Path) -> None:
    files = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(p in SKIP_DIRS for p in path.parts) or path.name in SKIP_NAMES or path.suffix == ".pyc":
            continue
        files.append(path)
    lines = [f"{sha256_file(p)}  {p.relative_to(root).as_posix()}" for p in files]
    (root / "MANIFEST").write_text("\n".join(lines) + "\n", encoding="utf-8")
    log(f"wrote MANIFEST n={len(lines)}")


def behavioral(mod, root: Path, errors: List[str]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    expected = json.loads((root / "t_expected/D2_EXPECTED.json").read_text(encoding="utf-8"))
    fixtures = mod.run_fixtures(expected, root / "out" / "fixtures-checker")
    for key in (
        "F-NAIVE",
        "F-INC-TS",
        "F-INC-DELTA",
        "F-COMP-NULL",
        "F-V2-MISSING",
        "F-V2-BLOB",
        "F-V2-MISMATCH",
        "F-JOIN-FIRST",
        "F-NAME",
        "F-HOLDOUT",
    ):
        text = fixtures[key]
        needle = expected[key]["must_contain"]
        if needle not in text:
            errors.append(f"{key} missing {needle}")
        out[key] = "stop"
    if fixtures["F-OK"]["n_incomplete"] != 1:
        errors.append("F-OK n_incomplete")
    out["F-OK"] = "ok"
    # holdout mode must die without resolving listings
    holdout_died = False
    try:
        mod.mode_holdout()
    except SystemExit:
        holdout_died = True
    if not holdout_died:
        errors.append("holdout mode must STOP")
    # name trap must not require a 2024 file
    if (root / "fixtures/name-trap/listings_2024.csv").exists():
        errors.append("name-trap must not ship listings_2024.csv")
    if (root / "seeded/listings-le2023/listings_2024.csv").exists() or (root / "seeded/listings-le2023/listings_2025.csv").exists():
        errors.append("le2023 listings include holdout year")
    blob = (root / "seeded/sealed_injury_export_ts_v1.json.sha256").read_text(encoding="utf-8").split()[0]
    if blob != REQUIRED_EXPORT_BLOB_NOT_A_PIN:
        errors.append("blob sidecar is not 46d2a565")
    v2 = (root / "seeded/sealed_injury_export_ts_v1.json.sha256.v2").read_text(encoding="utf-8").split()[0]
    if v2 != REQUIRED_EXPORT:
        errors.append("v2 sidecar is not a38a55bb")
    if sha256_file(root / "seeded/sealed_injury_export_ts_v1.json") == REQUIRED_EXPORT_BLOB_NOT_A_PIN:
        errors.append("on-disk export equals blob hash")
    commit = (root / "inputs/expected_answers_commit.txt").read_text(encoding="utf-8").strip()
    if commit != REQUIRED_EXPECTED_COMMIT:
        errors.append("expected-answers commit drifted")
    out["holdout_mode"] = "stop"
    return out


def main() -> int:
    root = Path(__file__).resolve().parent
    errors: List[str] = []
    for label, rel, exp in SEEDED:
        path = root / rel
        got = sha256_file(path)
        if got != exp:
            errors.append(f"SEEDED {label} {got} != {exp}")
    if (root / "seeded/listings-le2023").glob("listings_2024.csv") or list((root / "seeded/listings-le2023").glob("listings_2025.csv")):
        errors.append("holdout listings present")
    if errors:
        print(json.dumps({"ok": False, "n_errors": len(errors), "errors": errors}, indent=2))
        return 2
    mod = load_runner(root)
    behavior = behavioral(mod, root, errors)
    proc = subprocess.run(
        [sys.executable, str(root / "run_injury_holdout_d2.py"), "--mode", "all"],
        cwd=str(root),
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        errors.append("runner --mode all failed")
        errors.append(proc.stderr[-2000:])
    holdout = subprocess.run(
        [sys.executable, str(root / "run_injury_holdout_d2.py"), "--mode", "holdout"],
        cwd=str(root),
        capture_output=True,
        text=True,
    )
    if holdout.returncode == 0 or "D-2 opening blocked" not in (holdout.stderr or ""):
        errors.append("CLI --mode holdout must STOP")
    le = root / "out/le2023/d2_results.json"
    if le.is_file():
        doc = json.loads(le.read_text(encoding="utf-8"))
        if doc.get("holdout_years_opened") or doc.get("joined") or doc.get("opening_permitted"):
            errors.append("le2023 results opened or joined holdout")
        if doc.get("incomplete", {}).get("n_incomplete") != 11:
            errors.append("le2023 n_incomplete")
        if "excluded_game_ids" not in (root / "out/le2023/provenance.md").read_text(encoding="utf-8"):
            errors.append("le2023 provenance missing excluded_game_ids")
    else:
        errors.append("missing out/le2023/d2_results.json")
    write_manifest(root)
    payload = {
        "ok": not errors,
        "n_errors": len(errors),
        "errors": errors,
        "behavior": behavior,
        "package": ".",
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
