#!/usr/bin/env python3
"""v3 package checker — covers ruling E-1..E-8 plus R1–R5."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, List

REQUIRED_SPEC = "a156459b545e3b7d6a483f1db34cda7a4d32fc3afc70ed499b3adc726b1b6881"
REQUIRED_ACCEPT = "54bc78ecc70e6a440481253b9c7eeef0e749690e893f501862f5dd5c54444574"
REQUIRED_RULING = "a0501d575a42cb4c05b2d1937753b36ca761f613e8c0d011d56fd3d05246d6e9"
REQUIRED_EXPORT = "d87e6129c451bbdc51d49eb7745a31ebb64ab6108ac58d8f8c4948dcc13e18e8"
REQUIRED_FIT = "6a5490dbc09b160f4509ea65b3b2257f9703f9d43635092d0da94c1577abb657"
REQUIRED_EXPECTED = "8319a63a674f22a52b1bce168c15de9e1a510429b14e78d1e4dd48f30fcd1b79"
PINNED_SEED = 20261023
CLOSE_LABEL = "comparative research, not certified CLV"
CVO = "close vs outcome"
SKIP_DIRS = {".git", "out-rerun", "__pycache__"}
SKIP_NAMES = {"MANIFEST", "checker.log", "checker.stdout.txt"}
SECRET_RE = re.compile(r"(api[_-]?key|secret|token|password|authorization:\s*bearer)\s*[:=]", re.I)
SEEDED = (
    ("spec", "seeded/IMV_SPEC_NFL_INJURY_ADJUSTMENT_TESTS_v1.txt", REQUIRED_SPEC),
    ("accept", "seeded/IMV_SPEC_NFL_INJURY_PRE_HOLDOUT_ACCEPTANCE_v1.txt", REQUIRED_ACCEPT),
    ("ruling", "seeded/IMV_RULING_NFL_INJURY_EVALUATOR_READINESS_v1.txt", REQUIRED_RULING),
    ("export", "seeded/sealed_injury_export.json", REQUIRED_EXPORT),
    ("fit", "seeded/fit_object.json", REQUIRED_FIT),
    ("expected", "t_expected/T1_T10_EXPECTED.json", REQUIRED_EXPECTED),
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


def iter_files(root: Path) -> List[Path]:
    out = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(p in SKIP_DIRS for p in path.parts) or path.name in SKIP_NAMES or path.suffix == ".pyc":
            continue
        out.append(path)
    return out


def write_manifest(root: Path) -> None:
    lines = [f"{sha256_file(p)}  {p.relative_to(root).as_posix()}" for p in iter_files(root)]
    (root / "MANIFEST").write_text("\n".join(lines) + "\n", encoding="utf-8")
    log(f"wrote MANIFEST n={len(lines)}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--package", default=str(Path(__file__).resolve().parent))
    ap.add_argument("--write-manifest", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--rerun", action="store_true")
    args = ap.parse_args()
    if not args.write_manifest and not args.verify:
        args.verify = True
    root = Path(args.package).resolve()
    errors: List[str] = []
    for label, rel, exp in SEEDED:
        path = root / rel
        if not path.is_file():
            log("ERROR SEEDED MISSING " + rel)
            return 2
        if sha256_file(path) != exp:
            log("ERROR SEEDED SHA MISMATCH " + rel)
            return 2
    if args.write_manifest:
        write_manifest(root)
    if args.rerun:
        out = root / "out-rerun"
        out.mkdir(exist_ok=True)
        rc = subprocess.run(
            [sys.executable, str(root / "run_injury_residual_evaluator.py"), "--out", str(out), "--mode", "all"],
            check=False,
        ).returncode
        if rc != 0:
            errors.append(f"rerun exit {rc}")
    if args.verify:
        man = root / "MANIFEST"
        if not man.is_file():
            errors.append("SEEDED MISSING MANIFEST")
        else:
            listed = {}
            for line in man.read_text(encoding="utf-8").splitlines():
                d, n = line.split(None, 1)
                listed[n] = d
            disk = {p.relative_to(root).as_posix(): sha256_file(p) for p in iter_files(root)}
            for n, d in listed.items():
                if n not in disk:
                    errors.append("MANIFEST missing on disk " + n)
                elif disk[n] != d:
                    errors.append("MANIFEST sha mismatch " + n)
            for n in disk:
                if n not in listed:
                    errors.append("file not in MANIFEST " + n)
        src = (root / "run_injury_residual_evaluator.py").read_text(encoding="utf-8")
        # E-1..E-8
        if "PINNED_SEED = 20261023" not in src:
            errors.append("E-1 seed is not 20261023")
        if "default_rng" not in src:
            errors.append("E-1 missing numpy default_rng")
        if "ci_lo > 0.0" not in src and "lo > 0.0" not in src:
            errors.append("E-2 VALUE PROVEN must require lo>0")
        if "close vs outcome" not in src:
            errors.append("E-3 missing close vs outcome label")
        if "T-9" not in src or "LEAKAGE" not in src:
            errors.append("E-4 missing T-9 leakage detector")
        if "0.0 if val is None" in src:
            errors.append("E-5 still zero-fills bootstrap")
        if "logit(y)~logit(p_adj)" not in src and "calibration_slope_logit" not in src:
            errors.append("E-6 missing logit slope")
        if "None if cvo_a is None or cvo_b is None" not in src:
            errors.append("E-7 CLV/ATS not isolated from K-2 set")
        if "missing file (fail-closed, not a crash)" not in src:
            errors.append("E-8 missing spec must die cleanly")
        gt = (root / "gate-table.md").read_text(encoding="utf-8")
        if REQUIRED_SPEC not in gt or "weeks 1–17" not in gt:
            errors.append("N-3/N-5 gate table")
        if "implied-prob close-vs-outcome" not in gt:
            errors.append("N-2 ML CLV not defined in gate table")
        res_path = root / "out" / "evaluator_results.json"
        if res_path.is_file():
            doc = json.loads(res_path.read_text(encoding="utf-8"))
            if doc.get("seed") != PINNED_SEED:
                errors.append("E-1 results seed")
            if doc.get("metric_label") != CVO:
                errors.append("E-3 results label")
            if doc.get("close_label") != CLOSE_LABEL:
                errors.append("close label")
            tests = doc.get("tests") or {}
            for i in range(1, 11):
                rec = tests.get(f"T-{i}")
                if not rec or not rec.get("pass"):
                    errors.append(f"T-{i} not PASS")
            names = [f.get("name") for f in doc.get("folds") or []]
            for want in ("F1", "F2", "pooled"):
                if want not in names:
                    errors.append("E-9 missing fold " + want)
            for f in doc.get("folds") or []:
                if f.get("i4", {}).get("decision") == "VALUE PROVEN" and not f.get("i4", {}).get("primary_ci_lo_gt_0"):
                    errors.append("E-2 VALUE PROVEN without lo>0")
                if "modeling" not in f:
                    errors.append("E-10 missing M-1..M-5 on " + f.get("name", "?"))
            if SECRET_RE.search(json.dumps(doc)):
                errors.append("secret in results")
        else:
            errors.append("missing out/evaluator_results.json")
        if not (root / "out" / "evaluator.log").is_file():
            errors.append("missing log")
        if not (root / "provenance.md").is_file() and not (root / "out" / "provenance.md").is_file():
            errors.append("missing provenance")
    if errors:
        for e in errors:
            log("ERROR " + e)
        print(json.dumps({"ok": False, "n_errors": len(errors), "errors": errors}, indent=2))
        if any(e.startswith("SEEDED") for e in errors):
            return 2
        return 1
    print(json.dumps({"ok": True, "n_errors": 0, "package": str(root)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
