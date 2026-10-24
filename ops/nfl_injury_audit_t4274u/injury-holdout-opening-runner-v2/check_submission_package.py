#!/usr/bin/env python3
"""Opening-runner v2 package checker. No 2024/25 open. No real lock."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import List

REQUIRED_D2_RULING = "b7364186cc2aa900fd39e2dd22e78e2e69b63d2cac11fd6fa6b234997494b6b8"
REQUIRED_DECISION = "fabf87320453c274b2b8ec8e443b8af4709d8d24ff8fb6baa449fe3d739d4bd0"
REQUIRED_OPENING_RETURN = "a8958e850cd75cce5a24feda95a865e86ca39a2afaff5144748f70cfe4dcbeaa"
REQUIRED_SCORER = "ca98ae0e70fcdee77d46aed3c4f9be5644079da6adf08411891e1d5b7970e6c6"
REQUIRED_WRITER = "9947b880bc789192a26b850ee53dc89d4c43a4c107bdf3fc549c65730739d58f"
REQUIRED_FIT = "6a5490dbc09b160f4509ea65b3b2257f9703f9d43635092d0da94c1577abb657"
REQUIRED_FROZEN_EXPORT = "d87e6129c451bbdc51d49eb7745a31ebb64ab6108ac58d8f8c4948dcc13e18e8"
REQUIRED_FROZEN_SCRIPT = "8d188da27d3c9f802acdca76763e1ca05e714040cc5ea3722e4922853f28167c"
REQUIRED_NULL_CONTRACT = "ff8e6527f63b0afd727eed30444436ceae320cc336d9113a2634fd66d4aebad2"
REQUIRED_EXPECTED = "cda0da90a18db4872a784f3ae245d5047e05eb03af0579749e5a1bcef248e441"
REQUIRED_EXPECTED_COMMIT = "73b537b2e394def333e2ad5ce22a24ecc42d9ff2"
REQUIRED_EXPORT = "a38a55bb765e977ed88f8808d76715faddf50098b2354b122a5499f0ec706ac8"
REQUIRED_RECORD_BASELINE = "502110cfc9293d96fd5635fbfdd3fad2c19367fa043ce3770cfbae05f2cdbe12"
REAL_LOCK = Path("/workspace/ops/nfl_injury_audit_t4274u/holdout-once.lock")
SKIP_DIRS = {".git", "__pycache__"}
SKIP_NAMES = {"MANIFEST", "SHA256SUMS", "MANIFEST.sha256", "checker.log", "checker.stdout.txt"}
SEEDED = (
    ("ruling", "seeded/IMV_RULING_NFL_INJURY_HOLDOUT_RUNNER_D2_v1.txt", REQUIRED_D2_RULING),
    ("return", "seeded/IMV_RULING_NFL_INJURY_HOLDOUT_OPENING_RUNNER_v1.txt", REQUIRED_OPENING_RETURN),
    ("decision", "seeded/DECISION_RYAN_t4335s14919_HOLDOUT_CLEAR_v3_1_v1.txt", REQUIRED_DECISION),
    ("scorer", "seeded/ca98ae0e/run_injury_residual_evaluator.py", REQUIRED_SCORER),
    ("writer", "seeded/write_sealed_injury_export_ts_v1.py", REQUIRED_WRITER),
    ("fit", "seeded/fit_object.json", REQUIRED_FIT),
    ("frozen_export", "seeded/sealed_injury_export_d87e6129.json", REQUIRED_FROZEN_EXPORT),
    ("frozen_script", "seeded/run_injury_residual_fit.py", REQUIRED_FROZEN_SCRIPT),
    ("null", "seeded/nfl_injury_null_contract_8e2a15ac.py", REQUIRED_NULL_CONTRACT),
    ("expected", "t_expected/HOLDOUT_EXPECTED.json", REQUIRED_EXPECTED),
    ("export", "seeded/sealed_injury_export_ts_v1.json", REQUIRED_EXPORT),
    ("baseline_csv", "inputs/record_baseline_le2023.csv", REQUIRED_RECORD_BASELINE),
)


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


def main() -> int:
    root = Path(__file__).resolve().parent
    errors: List[str] = []
    if REAL_LOCK.exists():
        errors.append("real lock exists")
    listings = root / "seeded/listings-le2023"
    if list(listings.glob("listings_2024.csv")) or list(listings.glob("listings_2025.csv")):
        errors.append("holdout listings present")
    if list((root / "seeded").rglob("__pycache__")) or list((root / "seeded").rglob("*.pyc")):
        errors.append("seeded/ contains __pycache__ or pyc")
    for label, rel, exp in SEEDED:
        got = sha256_file(root / rel)
        if got != exp:
            errors.append(f"SEEDED {label} {got} != {exp}")
    commit = (root / "inputs/expected_answers_commit.txt").read_text(encoding="utf-8").strip()
    if commit != REQUIRED_EXPECTED_COMMIT:
        errors.append("expected-answers commit drifted")
    expected = json.loads((root / "t_expected/HOLDOUT_EXPECTED.json").read_text(encoding="utf-8"))
    if expected.get("holdout_values") is not None:
        errors.append("expected answers must have no holdout values")
    if expected.get("opening_permitted") is not False:
        errors.append("opening_permitted must be false")
    if "baseline_method" not in expected or "lock_fields" not in expected or "receipt_schema" not in expected:
        errors.append("expected answers missing baseline_method/lock_fields/receipt_schema")
    src = (root / "run_injury_holdout_opening.py").read_text(encoding="utf-8")
    if "main([\"--mode\", \"holdout\"" not in src and "main(['--mode', 'holdout'" not in src:
        errors.append("O-4: main(['--mode','holdout']) fixture missing")
    if "no tuning or refit" not in src:
        errors.append("O-1 refit refuse missing")
    if "baseline_margin = -3.0" in src or "baseline_total = 45.0" in src:
        errors.append("R-3 hardcoded -3.0/45.0 still present")
    if "import_writer" not in src or "timestamps_for_game" not in src:
        errors.append("R-1 writer invoke missing")
    if "holdout-once.lock.consumed" not in src:
        errors.append("R-5 consumed sidecar missing")
    if "REAL_LOCK" not in src or "verified_opening_pass_sha" not in src:
        errors.append("R-4 production lock path missing")
    if "copy_fixture_to_temp" not in src:
        errors.append("R-9 temp-dir copy missing")
    if "write_receipt" not in src:
        errors.append("R-7 receipt writer missing")
    proc = subprocess.run(
        [sys.executable, str(root / "run_injury_holdout_opening.py"), "--mode", "all"],
        cwd=str(root),
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        errors.append("runner --mode all failed")
        errors.append((proc.stderr or "")[-3000:])
    holdout = subprocess.run(
        [sys.executable, str(root / "run_injury_holdout_opening.py"), "--mode", "holdout"],
        cwd=str(root),
        capture_output=True,
        text=True,
    )
    if holdout.returncode == 0 or "O-1 opening blocked" not in (holdout.stderr or ""):
        errors.append("CLI --mode holdout default must STOP blocked")
    if REAL_LOCK.exists():
        errors.append("real lock written during check")
    log_path = root / "out/runner.log"
    if not log_path.is_file() or "STOP:" not in log_path.read_text(encoding="utf-8"):
        errors.append("O-6 runner.log missing STOP lines")
    receipt = root / "out/synthetic/receipt.json"
    if receipt.is_file():
        doc = json.loads(receipt.read_text(encoding="utf-8"))
        if doc.get("kind") != "opening_receipt":
            errors.append("receipt kind")
        if not doc.get("writer_invoked"):
            errors.append("receipt writer_invoked")
        if doc.get("holdout_years_opened") or doc.get("opening_permitted"):
            errors.append("receipt opened holdout")
        for field in ("lock", "export_on_disk_sha", "tz", "incomplete", "n_missing_close", "folds", "consumed"):
            if field not in doc:
                errors.append(f"receipt missing {field}")
    else:
        errors.append("missing F-E2E receipt")
    le = root / "out/le2023/d2_results.json"
    if le.is_file():
        doc = json.loads(le.read_text(encoding="utf-8"))
        if doc.get("holdout_years_opened") or doc.get("opening_permitted"):
            errors.append("le2023 opened holdout")
        if doc.get("incomplete", {}).get("n_incomplete") != 11:
            errors.append("le2023 n_incomplete")
    else:
        errors.append("missing le2023 results")
    write_manifest(root)
    payload = {"ok": not errors, "n_errors": len(errors), "errors": errors, "package": "."}
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
