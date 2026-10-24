#!/usr/bin/env python3
"""Submission-readiness package checker (Ryan t4317u 5c4e6578 + t4320u).

Reusable safeguard. Verifies:
  (a) MANIFEST sha256 of every listed file
  (b) successful run on le2023 + synthetic (re-runs fixtures)
  (c) every required metric computed; no stub; no unexplained NaN
  (d) gate table quotes a156459b verbatim with line citations
  (e) provenance: inputs, commit, command, no secrets

Exits 2 when a seeded file is missing or has the wrong sha.
Exits 1 on any other readiness failure.
Exits 0 only when the package is IMV-ready.

Does not create CLEAR / IMV tokens. Does not open 2024–25.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

REQUIRED_SPEC = "a156459b545e3b7d6a483f1db34cda7a4d32fc3afc70ed499b3adc726b1b6881"
REQUIRED_EXPORT = "d87e6129c451bbdc51d49eb7745a31ebb64ab6108ac58d8f8c4948dcc13e18e8"
REQUIRED_FIT_OBJECT = "6a5490dbc09b160f4509ea65b3b2257f9703f9d43635092d0da94c1577abb657"
REQUIRED_HEAD = "8e2a15ac581277ecda71ea745c3b3477185d733b"
PINNED_SEED = 2708041115
CLOSE_LABEL = "comparative research, not certified CLV"

SPEC_STORE = Path("/cursor/stores/self/imv-inputs/IMV_SPEC_NFL_INJURY_ADJUSTMENT_TESTS_v1.txt")
EXPORT = Path("/opt/cursor/artifacts/injury-fit-le2023/sealed_injury_export.json")
FIT_OBJECT = Path("/opt/cursor/artifacts/injury-fit-le2023/fit_object.json")

SEEDED_INPUTS = (
    ("spec", SPEC_STORE, REQUIRED_SPEC),
    ("export", EXPORT, REQUIRED_EXPORT),
    ("fit_object", FIT_OBJECT, REQUIRED_FIT_OBJECT),
)

REQUIRED_METRICS = (
    "spread_clv_delta",
    "spread_ats_delta",
    "spread_logloss_delta",
    "total_clv_delta",
    "total_ats_delta",
    "total_logloss_delta",
    "ml_clv_implied_prob_delta",
    "ml_ats_delta",
    "ml_logloss_delta",
    "mean_logloss_base",
    "mean_logloss_adj",
    "mean_brier_base",
    "mean_brier_adj",
    "logloss_delta_adj_minus_base",
    "brier_delta_adj_minus_base",
    "slope_adj",
)
HOLM_NINE = REQUIRED_METRICS[:9]
KNOWN_ANSWERS = {
    "synthetic_inconclusive": "INCONCLUSIVE",
    "synthetic_fail": "NO CLAIM",
    "synthetic_pass": "VALUE PROVEN",
}
VERBATIM = {
    "I-1": "Paired comparison, adjusted vs base, same games, priced at the same as_of_ts, against the CLOSING line: CLV (points and implied-prob), ATS win rate, log-loss delta.",
    "I-2": "Minimum sample: >= 500 games with a non-zero adjustment in the sealed holdout and >= 2 full seasons; below that the result is INCONCLUSIVE (no claim).",
    "I-3": "Multiple comparisons: 3 markets x 3 metrics = 9 tests; Holm-Bonferroni at family alpha 0.05. Primary endpoint = mean CLV delta (spread) - stated now, not chosen later.",
    "I-4": "Decision rule: VALUE PROVEN only if primary endpoint significant after Holm, its 95% block-bootstrap CI excludes 0, and K-4 passes. Anything else = NO CLAIM.",
    "I-5": 'Soft, borderline or insignificant results cannot become a product claim, marketing copy, or a "improves accuracy" statement. Report them as null results.',
    "K-2": "Metrics, base vs adjusted on the same games: Brier and log loss (win prob); cover reliability for spread and total (predicted cover prob vs actual); reliability diagram in 10 bins with counts.",
    "K-3": "CIs: block bootstrap by NFL week, 10,000 resamples, 95% percentile CI, paired.",
    "K-4": "Gate: adjusted must not be worse than base: upper 95% CI of (adj - base) log loss <= 0.002 and Brier <= 0.0005. Calibration slope of adjusted within [0.9, 1.1]. Failing = layer stays off.",
}
TOKEN_NAMES = ("RYAN_CLEAR_ON_FROZEN_RECORD", "IMV_PASS", "CLEAR", "RYAN_CLEAR")
SECRET_RE = re.compile(r"(api[_-]?key|secret|token|password|authorization:\s*bearer)\s*[:=]", re.I)

MANIFEST_SKIP_NAMES = {"MANIFEST", "checker.log", "checker.stdout.txt"}
MANIFEST_SKIP_DIR_PARTS = {".git", "out-rerun", "__pycache__"}


def log(msg: str) -> None:
    sys.stderr.write(msg + "\n")
    sys.stderr.flush()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def relpath(root: Path, path: Path) -> str:
    return str(path.resolve().relative_to(root.resolve())).replace("\\", "/")


def iter_package_files(root: Path) -> List[Path]:
    out = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in MANIFEST_SKIP_DIR_PARTS for part in path.parts):
            continue
        if path.name in MANIFEST_SKIP_NAMES or path.suffix == ".pyc":
            continue
        out.append(path)
    return out


def write_manifest(root: Path) -> Path:
    dest = root / "MANIFEST"
    lines = []
    for path in iter_package_files(root):
        lines.append(f"{sha256_file(path)}  {relpath(root, path)}")
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log(f"wrote {dest} ({len(lines)} files)")
    return dest


def parse_manifest(path: Path) -> List[tuple]:
    rows = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        digest, name = line.split(None, 1)
        if len(digest) != 64:
            raise ValueError(f"bad digest in MANIFEST: {line!r}")
        rows.append((digest, name))
    return rows


def check_seeded_inputs() -> List[str]:
    errors = []
    for label, path, expected in SEEDED_INPUTS:
        if not path.is_file():
            errors.append(f"SEEDED MISSING {label}: {path}")
            continue
        got = sha256_file(path)
        if got != expected:
            errors.append(f"SEEDED SHA MISMATCH {label}: {path} got {got} expected {expected}")
    return errors


def check_manifest(root: Path) -> List[str]:
    errors = []
    man = root / "MANIFEST"
    if not man.is_file():
        return ["SEEDED MISSING MANIFEST"]
    listed = parse_manifest(man)
    listed_names = {name for _, name in listed}
    on_disk = {relpath(root, p) for p in iter_package_files(root)}
    for digest, name in listed:
        path = root / name
        if not path.is_file():
            errors.append(f"MANIFEST file missing: {name}")
            continue
        got = sha256_file(path)
        if got != digest:
            errors.append(f"MANIFEST sha mismatch: {name} got {got} listed {digest}")
    extra = sorted(on_disk - listed_names)
    missing_from_disk_set = sorted(listed_names - on_disk)
    for name in extra:
        errors.append(f"file on disk not in MANIFEST: {name}")
    for name in missing_from_disk_set:
        errors.append(f"MANIFEST name not on disk: {name}")
    return errors


def is_number(val: Any) -> bool:
    return isinstance(val, (int, float)) and not isinstance(val, bool)


def metric_ok(name: str, val: Any, reason: Any) -> List[str]:
    errors = []
    if val is None:
        if not reason:
            errors.append(f"metric {name} is null without nan_reason")
        return errors
    if isinstance(val, float) and val != val:  # NaN
        if not reason:
            errors.append(f"metric {name} is NaN without nan_reason")
        return errors
    if not is_number(val):
        errors.append(f"metric {name} is not numeric: {val!r}")
    return errors


def check_cohort(cohort: Dict[str, Any]) -> List[str]:
    errors = []
    name = cohort.get("name", "?")
    metrics = cohort.get("metrics") or {}
    undefined = cohort.get("metric_undefined") or {}
    for key in REQUIRED_METRICS:
        if key not in metrics:
            errors.append(f"{name}: missing metric {key}")
            continue
        errors.extend(f"{name}: {e}" for e in metric_ok(key, metrics[key], undefined.get(key)))
    holm = cohort.get("holm") or []
    if len(holm) != 9:
        errors.append(f"{name}: Holm family is {len(holm)} tests, need 9")
    got_ids = {h.get("test_id") for h in holm}
    if holm and got_ids != set(HOLM_NINE):
        errors.append(f"{name}: Holm ids {sorted(got_ids)} != 3x3 family")
    rel = cohort.get("reliability") or {}
    for market in ("spread", "total", "ml"):
        bins = rel.get(market) or []
        if len(bins) != 10:
            errors.append(f"{name}: reliability[{market}] has {len(bins)} bins, need 10")
            continue
        for b in bins:
            if b.get("n", 0) == 0 and not b.get("nan_reason"):
                errors.append(f"{name}: empty {market} bin {b.get('bin')} has no nan_reason")
            if b.get("n", 0) > 0:
                if b.get("mean_p") is None or b.get("mean_y") is None:
                    errors.append(f"{name}: occupied {market} bin {b.get('bin')} missing mean")
    missing = cohort.get("missing") or {}
    for key in (
        "n_universe",
        "n_incomplete_residual",
        "n_missing_close",
        "n_missing_actual",
        "n_missing_baseline",
        "n_missing_close_by_season",
        "n_missing_actual_by_season",
        "n_missing_baseline_by_season",
        "n_incomplete_by_season",
        "n_universe_by_season",
        "n_identical_cohort",
        "n_paired_both_clv",
    ):
        if key not in missing:
            errors.append(f"{name}: missing accounting field {key}")
    boot = cohort.get("bootstrap") or {}
    primary = boot.get("spread_clv_delta") or {}
    if primary.get("n_boot") != 10000:
        errors.append(f"{name}: K-3 n_boot={primary.get('n_boot')} != 10000")
    if primary.get("seed") != PINNED_SEED:
        errors.append(f"{name}: K-3 seed={primary.get('seed')} != {PINNED_SEED}")
    k4 = cohort.get("k4") or {}
    for key in ("logloss_delta_ci_hi", "brier_delta_ci_hi", "slope_adj", "pass"):
        if key not in k4:
            errors.append(f"{name}: K-4 missing {key}")
    if k4.get("slope_adj") is None and not (k4.get("notes") or []):
        errors.append(f"{name}: K-4 slope null without notes")
    i4 = cohort.get("i4") or {}
    if i4.get("decision") not in {"INCONCLUSIVE", "VALUE PROVEN", "NO CLAIM"}:
        errors.append(f"{name}: illegal I-4 decision {i4.get('decision')!r}")
    if i4.get("product_claim") is not False:
        errors.append(f"{name}: product_claim must be false (I-5)")
    expect = KNOWN_ANSWERS.get(name)
    if expect and i4.get("decision") != expect:
        errors.append(f"{name}: known-answer {i4.get('decision')!r} != {expect!r}")
    if cohort.get("close_label") != CLOSE_LABEL:
        errors.append(f"{name}: close_label {cohort.get('close_label')!r} != {CLOSE_LABEL!r}")
    return errors


def check_results(path: Path, required_cohorts: List[str]) -> List[str]:
    errors = []
    if not path.is_file():
        return [f"missing results {path}"]
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("spec_sha") != REQUIRED_SPEC:
        errors.append(f"results spec_sha {doc.get('spec_sha')} != {REQUIRED_SPEC}")
    if doc.get("export_sha") != REQUIRED_EXPORT:
        errors.append("results export_sha mismatch")
    if doc.get("fit_object_sha") != REQUIRED_FIT_OBJECT:
        errors.append("results fit_object_sha mismatch")
    if doc.get("seed") != PINNED_SEED:
        errors.append("results seed mismatch")
    if doc.get("close_label") != CLOSE_LABEL:
        errors.append("results close_label mismatch")
    if doc.get("holdout") != "STOPPED":
        errors.append("results holdout is not STOPPED")
    if SECRET_RE.search(json.dumps(doc)):
        errors.append("results appear to contain a secret")
    names = [c.get("name") for c in doc.get("cohorts") or []]
    for want in required_cohorts:
        if want not in names:
            errors.append(f"results missing cohort {want}")
    for cohort in doc.get("cohorts") or []:
        errors.extend(check_cohort(cohort))
    return errors


def check_gate_table(path: Path) -> List[str]:
    errors = []
    if not path.is_file():
        return ["SEEDED MISSING gate-table.md"]
    text = path.read_text(encoding="utf-8")
    squashed = " ".join(text.split())
    if REQUIRED_SPEC not in text:
        errors.append("gate-table.md missing verified spec sha")
    for key, quote in VERBATIM.items():
        if " ".join(quote.split()) not in squashed:
            errors.append(f"gate-table.md missing verbatim {key}")
    for cite in ("L125–127", "L128", "L129–131", "L136–137", "L138–139", "L140–141", "L142–143", "L144–145"):
        if cite not in text:
            errors.append(f"gate-table.md missing citation {cite}")
    return errors


def check_provenance(path: Path) -> List[str]:
    errors = []
    if not path.is_file():
        return ["missing provenance.md"]
    text = path.read_text(encoding="utf-8")
    for needle in (
        REQUIRED_HEAD,
        REQUIRED_SPEC,
        REQUIRED_EXPORT,
        REQUIRED_FIT_OBJECT,
        str(PINNED_SEED),
        "run_injury_residual_evaluator.py",
        "No secrets",
        CLOSE_LABEL,
    ):
        if needle not in text:
            errors.append(f"provenance.md missing {needle}")
    if SECRET_RE.search(text):
        errors.append("provenance.md appears to contain a secret")
    return errors


def check_no_tokens(root: Path) -> List[str]:
    errors = []
    for path in root.rglob("*"):
        if path.is_file() and path.name in TOKEN_NAMES:
            errors.append(f"token file present: {path}")
    return errors


def run_evaluator(root: Path, out: Path, cohorts: str) -> int:
    script = root / "run_injury_residual_evaluator.py"
    cmd = [sys.executable, str(script), "--out", str(out), "--cohorts", cohorts]
    log("re-run: " + " ".join(cmd))
    log_path = out / "evaluator.log"
    stdout_path = out / "evaluator.stdout.txt"
    out.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as err, stdout_path.open("w", encoding="utf-8") as out_f:
        proc = subprocess.run(cmd, stdout=out_f, stderr=err, check=False)
    return proc.returncode


def compare_rerun(submitted: Path, rerun: Path, required_cohorts: List[str]) -> List[str]:
    """Compare decisions and required metrics; ignore run HEAD (ops commit may differ)."""
    errors = []
    if not rerun.is_file():
        return [f"rerun results missing {rerun}"]
    a = json.loads(submitted.read_text(encoding="utf-8"))
    b = json.loads(rerun.read_text(encoding="utf-8"))
    for key in ("spec_sha", "export_sha", "fit_object_sha", "seed", "close_label", "holdout"):
        if a.get(key) != b.get(key):
            errors.append(f"rerun {key} {b.get(key)!r} != submitted {a.get(key)!r}")
    by_a = {c["name"]: c for c in a.get("cohorts") or []}
    by_b = {c["name"]: c for c in b.get("cohorts") or []}
    for name in required_cohorts:
        ca, cb = by_a.get(name), by_b.get(name)
        if not ca or not cb:
            errors.append(f"rerun missing cohort compare {name}")
            continue
        if ca.get("i4", {}).get("decision") != cb.get("i4", {}).get("decision"):
            errors.append(
                f"rerun {name} decision {cb['i4']['decision']!r} != submitted {ca['i4']['decision']!r}"
            )
        for key in REQUIRED_METRICS:
            va, vb = (ca.get("metrics") or {}).get(key), (cb.get("metrics") or {}).get(key)
            if va is None and vb is None:
                continue
            if va is None or vb is None or abs(float(va) - float(vb)) > 1e-12:
                errors.append(f"rerun {name} metric {key} {vb!r} != submitted {va!r}")
        if ca.get("k4", {}).get("pass") != cb.get("k4", {}).get("pass"):
            errors.append(f"rerun {name} k4.pass mismatch")
    return errors


def main() -> int:
    p = argparse.ArgumentParser(description="IMV submission-readiness package checker")
    p.add_argument("--package", default=str(Path(__file__).resolve().parent))
    p.add_argument("--write-manifest", action="store_true")
    p.add_argument("--verify", action="store_true")
    p.add_argument("--rerun", action="store_true")
    p.add_argument("--cohorts", default="synthetic_inconclusive,synthetic_fail,synthetic_pass,le2023")
    args = p.parse_args()
    if not args.write_manifest and not args.verify:
        args.verify = True

    root = Path(args.package).resolve()
    errors: List[str] = []
    seeded_errors = check_seeded_inputs()
    if seeded_errors:
        for e in seeded_errors:
            log("ERROR " + e)
        return 2

    if args.write_manifest:
        write_manifest(root)

    required_cohorts = [c.strip() for c in args.cohorts.split(",") if c.strip()]
    if args.rerun:
        rerun_out = root / "out-rerun"
        rc = run_evaluator(root, rerun_out, args.cohorts)
        if rc != 0:
            log(f"ERROR evaluator re-run exited {rc}")
            errors.append(f"evaluator re-run exited {rc}")
        else:
            errors.extend(
                compare_rerun(
                    root / "out" / "evaluator_results.json",
                    rerun_out / "evaluator_results.json",
                    required_cohorts,
                )
            )

    if args.verify:
        errors.extend(check_manifest(root))
        errors.extend(check_gate_table(root / "gate-table.md"))
        prov = root / "provenance.md"
        if not prov.is_file():
            prov = root / "out" / "provenance.md"
        errors.extend(check_provenance(prov))
        errors.extend(check_results(root / "out" / "evaluator_results.json", required_cohorts))
        errors.extend(check_no_tokens(root))
        seeded_copy = root / "seeded" / "IMV_SPEC_NFL_INJURY_ADJUSTMENT_TESTS_v1.txt"
        if not seeded_copy.is_file():
            errors.append("SEEDED MISSING seeded/IMV_SPEC_NFL_INJURY_ADJUSTMENT_TESTS_v1.txt")
        elif sha256_file(seeded_copy) != REQUIRED_SPEC:
            errors.append("SEEDED SHA MISMATCH package spec copy")
        log_path = root / "out" / "evaluator.log"
        if not log_path.is_file() or log_path.stat().st_size == 0:
            errors.append("missing or empty out/evaluator.log")
        stdout_path = root / "out" / "evaluator.stdout.txt"
        if not stdout_path.is_file() or stdout_path.stat().st_size == 0:
            errors.append("missing or empty out/evaluator.stdout.txt")

    if errors:
        for e in errors:
            log("ERROR " + e)
        print(json.dumps({"ok": False, "n_errors": len(errors), "errors": errors}, indent=2))
        if any(e.startswith("SEEDED MISSING") or e.startswith("SEEDED SHA") for e in errors):
            return 2
        return 1
    print(json.dumps({"ok": True, "n_errors": 0, "package": str(root)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
