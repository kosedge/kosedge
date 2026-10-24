#!/usr/bin/env python3
"""v4 behavioral package checker — ruling 1a090e3b B-2.

Reruns the evaluator from the package root, compares output hashes to the
deposited fixture and T-1..T-10 results, and exits nonzero on any failure.
E-2/E-3/E-5/E-7/B-1/B-3 are asserted by calling scorer functions, not by
source-string presence.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

REQUIRED_SPEC = "a156459b545e3b7d6a483f1db34cda7a4d32fc3afc70ed499b3adc726b1b6881"
REQUIRED_ACCEPT = "54bc78ecc70e6a440481253b9c7eeef0e749690e893f501862f5dd5c54444574"
REQUIRED_RULING = "1a090e3b58e440c79888662813f1a3d64c1761d4ae32d400170ee19a144eb20c"
REQUIRED_EXPORT = "d87e6129c451bbdc51d49eb7745a31ebb64ab6108ac58d8f8c4948dcc13e18e8"
REQUIRED_FIT = "6a5490dbc09b160f4509ea65b3b2257f9703f9d43635092d0da94c1577abb657"
REQUIRED_EXPECTED = "2ccdd7530c7a954f5ede635832a079548cfb92be6a98a0f4966b1c5932b6a1c1"
PINNED_SEED = 20261023
CLOSE_LABEL = "comparative research, not certified CLV"
CVO = "close vs outcome"
SKIP_DIRS = {".git", "out-rerun", "__pycache__"}
SKIP_NAMES = {"MANIFEST", "SHA256SUMS", "MANIFEST.sha256", "checker.log", "checker.stdout.txt"}
SEEDED = (
    ("spec", "seeded/IMV_SPEC_NFL_INJURY_ADJUSTMENT_TESTS_v1.txt", REQUIRED_SPEC),
    ("accept", "seeded/IMV_SPEC_NFL_INJURY_PRE_HOLDOUT_ACCEPTANCE_v1.txt", REQUIRED_ACCEPT),
    ("ruling", "seeded/IMV_RULING_NFL_INJURY_EVALUATOR_READINESS_v2.txt", REQUIRED_RULING),
    ("export", "seeded/sealed_injury_export.json", REQUIRED_EXPORT),
    ("fit", "seeded/fit_object.json", REQUIRED_FIT),
    ("expected", "t_expected/T1_T10_EXPECTED.json", REQUIRED_EXPECTED),
)
COMPARE_OUT = (
    "evaluator_results.json",
    "dry-run-report.md",
    "provenance.md",
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


def load_scorer(root: Path):
    spec = importlib.util.spec_from_file_location("injury_eval_v4", root / "run_injury_residual_evaluator.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load scorer")
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
    # E-2: VALUE PROVEN requires lo>0
    if mod.i4_decision("MET", True, 0.0, True) != "NO CLAIM":
        errors.append("E-2 i4_decision lo==0 must be NO CLAIM")
    if mod.i4_decision("MET", True, 0.01, True) != "VALUE PROVEN":
        errors.append("E-2 i4_decision lo>0 must be VALUE PROVEN")
    if mod.i4_decision("MET", True, -0.01, True) != "NO CLAIM":
        errors.append("E-2 i4_decision lo<0 must be NO CLAIM")
    out["E-2"] = "ok" if not any(e.startswith("E-2") for e in errors) else "fail"
    # E-3: T-1 sign
    cvo = mod.cvo_points(-3.0, -4.5, -4.5)
    if abs((cvo or 0) - 1.5) > 1e-12:
        errors.append(f"E-3 adj cvo {cvo} != 1.5")
    if mod.cvo_points(-3.0, -4.5, -3.0) != 0.0:
        errors.append("E-3 no-pick cvo_pts must be 0")
    out["E-3"] = "ok" if not any(e.startswith("E-3") for e in errors) else "fail"
    # B-1 / E-7: no-pick ATS is None, not a loss
    if mod.ats_from_line(-3.0, -3.0, 1.0) is not None:
        errors.append("B-1 spread no-pick ATS must be None")
    if mod.ats_from_line(-4.5, -3.0, 1.0) != 1.0:
        errors.append("B-1 covering home pick ATS must be 1")
    if mod.ats_from_prob(0.5, 1.0) is not None:
        errors.append("B-1 p==0.5 ATS must be None")
    if mod.ats_from_prob(0.6, 1.0) != 1.0:
        errors.append("B-1 p>0.5 home win ATS must be 1")
    out["B-1"] = "ok" if not any(e.startswith("B-1") for e in errors) else "fail"
    # E-5: undefined bootstrap is not filled with 0.0
    rows = [{"season": 2018, "week": 1, "spread_clv_delta": 0.1}]
    boot = mod.week_block_bootstrap(rows, lambda _rs: None)
    if boot.get("ci_lo") is not None or boot.get("ci_hi") is not None or boot.get("p") != 1.0:
        errors.append(f"E-5 undefined bootstrap filled {boot}")
    out["E-5"] = "ok" if not any(e.startswith("E-5") for e in errors) else "fail"
    # B-3: real export missing timestamps; planted rows carry
    ts = mod.export_timestamp_status(root / "seeded" / "sealed_injury_export.json")
    if not ts.get("missing"):
        errors.append("B-3 export should report missing source_ts/as_of_ts")
    planted = [
        {
            "season": 2018,
            "week": 1,
            "home": "AAA",
            "away": "BBB",
            "game_id": "2018_1_BBB_AAA",
            "complete": True,
            "delta_margin": 1.0,
            "delta_total": 0.2,
            "source_ts": "2022-09-11T16:00:00Z",
            "as_of_ts": "2022-09-11T17:00:00Z",
        }
    ]
    joined = mod.join_fold(
        planted,
        {(2018, 1, "AAA", "BBB"): {"close_spread_home": -3.0, "close_total": 45.0, "actual_margin": 4.5, "actual_total": 47.0}},
        (2018,),
    )
    if not joined or joined[0].get("source_ts") != "2022-09-11T16:00:00Z" or joined[0].get("as_of_ts") != "2022-09-11T17:00:00Z":
        errors.append("B-3 join_fold did not carry timestamps")
    died = False
    try:
        mod.join_fold([{**planted[0], "source_ts": None, "as_of_ts": None}], {}, (2018,))
    except SystemExit:
        died = True
    if not died:
        errors.append("B-3 missing timestamps must stop")
    out["B-3"] = "ok" if not any(e.startswith("B-3") for e in errors) else "fail"
    # B-4: no store fallbacks in scorer source
    src = (root / "run_injury_residual_evaluator.py").read_text(encoding="utf-8")
    if "/cursor/stores/self" in src or "/opt/cursor" in src:
        errors.append("B-4 scorer still has store fallbacks")
    out["B-4"] = "ok" if not any(e.startswith("B-4") for e in errors) else "fail"
    if mod.PINNED_SEED != PINNED_SEED:
        errors.append("E-1 seed")
    return out


def main() -> int:
    root = Path(__file__).resolve().parent
    errors: List[str] = []
    for label, rel, exp in SEEDED:
        path = root / rel
        if not path.is_file():
            log("ERROR SEEDED MISSING " + rel)
            print(json.dumps({"ok": False, "n_errors": 1, "errors": ["SEEDED MISSING " + rel]}, indent=2))
            return 2
        if sha256_file(path) != exp:
            log("ERROR SEEDED SHA MISMATCH " + rel)
            print(json.dumps({"ok": False, "n_errors": 1, "errors": ["SEEDED SHA MISMATCH " + rel]}, indent=2))
            return 2
    try:
        mod = load_scorer(root)
    except Exception as exc:
        errors.append(f"load scorer: {exc}")
        print(json.dumps({"ok": False, "n_errors": 1, "errors": errors}, indent=2))
        return 1
    behavior = behavioral(mod, root, errors)
    rerun = root / "out-rerun"
    if rerun.exists():
        for p in rerun.rglob("*"):
            if p.is_file():
                p.unlink()
    rerun.mkdir(exist_ok=True)
    proc = subprocess.run(
        [sys.executable, "run_injury_residual_evaluator.py", "--out", "out-rerun", "--mode", "all"],
        cwd=str(root),
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    (rerun / "evaluator.stdout.txt").write_text(proc.stdout)
    (rerun / "evaluator.log").write_text(proc.stderr)
    if proc.returncode != 0:
        errors.append(f"rerun exit {proc.returncode}")
    out_hashes = {}
    rerun_hashes = {}
    for name in COMPARE_OUT:
        a = root / "out" / name
        b = rerun / name
        out_hashes[name] = sha256_file(a)
        rerun_hashes[name] = sha256_file(b)
        if not a.is_file():
            errors.append("missing fixture out/" + name)
        if not b.is_file():
            errors.append("missing out-rerun/" + name)
        elif a.is_file() and out_hashes[name] != rerun_hashes[name]:
            errors.append(f"hash mismatch {name}")
    fixture = root / "out" / "evaluator_results.json"
    rerun_res = rerun / "evaluator_results.json"
    tests_ok = {}
    if fixture.is_file() and rerun_res.is_file():
        doc = json.loads(fixture.read_text(encoding="utf-8"))
        rer = json.loads(rerun_res.read_text(encoding="utf-8"))
        if doc.get("seed") != PINNED_SEED or rer.get("seed") != PINNED_SEED:
            errors.append("E-1 results seed")
        if doc.get("metric_label") != CVO or rer.get("metric_label") != CVO:
            errors.append("E-3 results label")
        if doc.get("close_label") != CLOSE_LABEL:
            errors.append("close label")
        if doc.get("ruling_sha") != REQUIRED_RULING:
            errors.append("results ruling sha")
        tests = doc.get("tests") or {}
        tests_r = rer.get("tests") or {}
        for i in range(1, 11):
            key = f"T-{i}"
            rec = tests.get(key) or {}
            rec_r = tests_r.get(key) or {}
            tests_ok[key] = bool(rec.get("pass") and rec_r.get("pass"))
            if not rec.get("pass"):
                errors.append(f"{key} fixture not PASS")
            if rec != rec_r:
                errors.append(f"{key} rerun result mismatch")
        if tests.get("T-10", {}).get("c_k4_computed") is not False:
            errors.append("T-10c not wired to computed k4")
        if (tests.get("T-10", {}).get("b_n_unique_deltas") or 0) < 2:
            errors.append("T-10b missing real variance")
        bci = tests.get("T-10", {}).get("b_ci") or [0, 0]
        if len(bci) == 2 and bci[0] == 0 and bci[1] == 0:
            errors.append("T-10b CI still degenerate [0,0]")
        if not (doc.get("b3") or {}).get("missing"):
            errors.append("B-3 stop not recorded in fixture results")
        if (doc.get("b3") or {}) != (rer.get("b3") or {}):
            errors.append("B-3 rerun mismatch")
        if doc.get("folds") or rer.get("folds"):
            errors.append("folds must not be scored when export timestamps are missing")
    else:
        errors.append("missing evaluator_results.json for fixture or rerun")
    payload = {
        "ok": not errors,
        "n_errors": len(errors),
        "errors": errors,
        "package": ".",
        "behavior": behavior,
        "tests": tests_ok,
        "out_hashes": out_hashes,
        "out_rerun_hashes": rerun_hashes,
        "bit_identical_out": out_hashes == rerun_hashes and all(out_hashes.values()),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    if errors:
        for e in errors:
            log("ERROR " + e)
        return 2 if any(e.startswith("SEEDED") for e in errors) else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
