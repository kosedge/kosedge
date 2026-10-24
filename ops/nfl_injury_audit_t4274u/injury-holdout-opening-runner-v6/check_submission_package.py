#!/usr/bin/env python3
"""Opening-runner v6 package checker. No 2024/25 open. No real lock."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import List

REQUIRED_D2_RULING = "b7364186cc2aa900fd39e2dd22e78e2e69b63d2cac11fd6fa6b234997494b6b8"
REQUIRED_DECISION = "fabf87320453c274b2b8ec8e443b8af4709d8d24ff8fb6baa449fe3d739d4bd0"
REQUIRED_OPENING_RETURN_V4 = "0505e49295df6c0d3b3ddd2256607325da67baf561cc5d3b8a5a477fb669d508"
REQUIRED_OPENING_RETURN_V5 = "2c71e4d0baa0da16ef48f5f4560f1b151c742bb176226335b922d649aebf7a66"
REQUIRED_SCORER_CA98 = "ca98ae0e70fcdee77d46aed3c4f9be5644079da6adf08411891e1d5b7970e6c6"
ACTIVE_SCORER_SHA = "8b482cb9ddf46ea3bfb80cbfc429978467cbccc126fb0d9d7ca8013ef2f34b37"
REQUIRED_SCORER_V62_BASELINE = "755d30a8ce0dde7cd31b2e5ded9d4e06240e73f963b68a6ae4bd9af30d90ea5f"
REQUIRED_V62_DIFF = "280d9785ffc1a313e9415e0b3cf8f75f7d0156908aba29a9902e4bb8a8788c55"
REQUIRED_RYAN_SCORER_DECISION = "592e0bb9e57ef4c7d997d48b336cb37594f7353a891b8ab56d6a70b55492e021"
REQUIRED_WRITER = "9947b880bc789192a26b850ee53dc89d4c43a4c107bdf3fc549c65730739d58f"
REQUIRED_FIT = "6a5490dbc09b160f4509ea65b3b2257f9703f9d43635092d0da94c1577abb657"
REQUIRED_FROZEN_EXPORT = "d87e6129c451bbdc51d49eb7745a31ebb64ab6108ac58d8f8c4948dcc13e18e8"
REQUIRED_FROZEN_SCRIPT = "8d188da27d3c9f802acdca76763e1ca05e714040cc5ea3722e4922853f28167c"
REQUIRED_NULL_CONTRACT = "ff8e6527f63b0afd727eed30444436ceae320cc336d9113a2634fd66d4aebad2"
REQUIRED_INJURY_PATHS = "ebd3dac083562afb4928e2ed756f617248894e636356f7426f0bc6ae58344e8b"
REQUIRED_BUILDER = "247744d23fef6f289e11da78523bdb007ada136f070916cf66a2bfee161e9cad"
REQUIRED_EXPECTED = "0c31243dc3016610ece4cca53ee1fd3cfe0cdcded7e5c16d3ac966260367cd10"
REQUIRED_EXPECTED_COMMIT = "daf94a7d7383400cac78c5b8adf6ee4096ea83dd"
REQUIRED_EXPORT = "a38a55bb765e977ed88f8808d76715faddf50098b2354b122a5499f0ec706ac8"
REQUIRED_LE2023_DELTAS = "8af44a7eaa96ff695e10a61c827f942020c534f578ee36893701409857429394"
REQUIRED_LE2023_COMPARE = "bc89721f170be3c5b4435c70597565e515d52fd662eb522516c35e1087be7501"
REQUIRED_RECORD_BASELINE = "502110cfc9293d96fd5635fbfdd3fad2c19367fa043ce3770cfbae05f2cdbe12"
REQUIRED_METHOD = "76aac887eddc67f19aaa3236d89fbcd51d2f1675e1416761dd70756df5d1a311"
REQUIRED_PRODUCER = "ae8f9585cca6400fe1f9c73b71c480bea1fb77ff75467b9d5536f614ac8dd630"
REAL_LOCK = Path("/workspace/ops/nfl_injury_audit_t4274u/holdout-once.lock")
RYAN_SCORER_DECISION = Path("/workspace/ops/nfl_injury_audit_t4274u/DECISION_RYAN_SCORER_V6_2.txt")
SKIP_DIRS = {".git", "__pycache__"}
SKIP_NAMES = {"MANIFEST", "SHA256SUMS", "MANIFEST.sha256", "checker.log", "checker.stdout.txt", "checker.stderr.txt"}
SEEDED = (
    ("ruling_v4", "seeded/IMV_RULING_NFL_INJURY_HOLDOUT_OPENING_RUNNER_v4.txt", REQUIRED_OPENING_RETURN_V4),
    ("ruling_v5", "seeded/IMV_RULING_NFL_INJURY_HOLDOUT_OPENING_RUNNER_v5.txt", REQUIRED_OPENING_RETURN_V5),
    ("d2", "seeded/IMV_RULING_NFL_INJURY_HOLDOUT_RUNNER_D2_v1.txt", REQUIRED_D2_RULING),
    ("decision", "seeded/DECISION_RYAN_t4335s14919_HOLDOUT_CLEAR_v3_1_v1.txt", REQUIRED_DECISION),
    ("scorer_decision", "seeded/DECISION_RYAN_SCORER_V6_2.txt", REQUIRED_RYAN_SCORER_DECISION),
    ("scorer_ca98", "seeded/ca98ae0e/run_injury_residual_evaluator.py", REQUIRED_SCORER_CA98),
    ("scorer_v62", "seeded/v6.2/run_injury_residual_evaluator.py", ACTIVE_SCORER_SHA),
    ("scorer_v62_baseline", "seeded/v6.2-755d30a8/run_injury_residual_evaluator.py", REQUIRED_SCORER_V62_BASELINE),
    ("scorer_v62_diff", "seeded/v6.2/DIFF_vs_755d30a8.txt", REQUIRED_V62_DIFF),
    ("le2023_deltas", "out/le2023/rebuilt_le2023_deltas.json", REQUIRED_LE2023_DELTAS),
    ("le2023_compare", "out/le2023/rebuilt_le2023_compare.json", REQUIRED_LE2023_COMPARE),
    ("writer", "seeded/write_sealed_injury_export_ts_v1.py", REQUIRED_WRITER),
    ("fit", "seeded/fit_object.json", REQUIRED_FIT),
    ("frozen_export", "seeded/sealed_injury_export_d87e6129.json", REQUIRED_FROZEN_EXPORT),
    ("frozen_script", "seeded/run_injury_residual_fit.py", REQUIRED_FROZEN_SCRIPT),
    ("null", "seeded/nfl_injury_null_contract_8e2a15ac.py", REQUIRED_NULL_CONTRACT),
    ("injury_paths", "seeded/injury_paths_8e2a15ac.py", REQUIRED_INJURY_PATHS),
    ("builder", "holdout_frozen_row_builder.py", REQUIRED_BUILDER),
    ("expected", "t_expected/HOLDOUT_EXPECTED.json", REQUIRED_EXPECTED),
    ("export", "seeded/sealed_injury_export_ts_v1.json", REQUIRED_EXPORT),
    ("baseline_csv", "inputs/record_baseline_le2023.csv", REQUIRED_RECORD_BASELINE),
    ("method", "record_hfa_baseline_method.py", REQUIRED_METHOD),
    ("producer", "holdout_delta_producer.py", REQUIRED_PRODUCER),
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
    man_sha = sha256_file(root / "MANIFEST")
    (root / "SHA256SUMS").write_text("\n".join(lines + [f"{man_sha}  MANIFEST"]) + "\n", encoding="utf-8")
    (root / "MANIFEST.sha256").write_text(f"{man_sha}  MANIFEST\n", encoding="utf-8")
    log(f"wrote MANIFEST n={len(lines)} SUMS_extra=MANIFEST")


def main() -> int:
    sys.dont_write_bytecode = True
    root = Path(__file__).resolve().parent
    errors: List[str] = []
    if REAL_LOCK.exists():
        errors.append("real lock exists")
    listings = root / "seeded/listings-le2023"
    if list(listings.glob("listings_2024.csv")) or list(listings.glob("listings_2025.csv")):
        errors.append("holdout listings present")
    if list((root / "fixtures").glob("**/listings_2024.csv")) or list((root / "fixtures").glob("**/listings_2025.csv")):
        errors.append("fixture holdout listings present")
    if list((root / "seeded").rglob("__pycache__")) or list((root / "seeded").rglob("*.pyc")):
        errors.append("seeded/ contains __pycache__ or pyc")
    for label, rel, exp in SEEDED:
        got = sha256_file(root / rel)
        if got != exp:
            errors.append(f"SEEDED {label} {got} != {exp}")
    if sha256_file(RYAN_SCORER_DECISION) != REQUIRED_RYAN_SCORER_DECISION:
        errors.append("audit-dir Ryan scorer decision drifted")
    commit = (root / "inputs/expected_answers_commit.txt").read_text(encoding="utf-8").strip()
    if commit != REQUIRED_EXPECTED_COMMIT:
        errors.append("expected-answers commit drifted")
    expected = json.loads((root / "t_expected/HOLDOUT_EXPECTED.json").read_text(encoding="utf-8"))
    if expected.get("holdout_values") is not None:
        errors.append("expected answers must have no holdout values")
    if expected.get("opening_permitted") is not False:
        errors.append("opening_permitted must be false")
    if expected.get("scorer_pin_active") != ACTIVE_SCORER_SHA:
        errors.append("active scorer pin must be the single v6.2 sha")
    if expected.get("scorer_v6_2_status") != "AUTHORIZED":
        errors.append("v6.2 must be AUTHORIZED")
    if expected.get("scorer_v6_2_imv_diff") != "DOCSTRING_ONLY_RECHECK":
        errors.append("v6.2 IMV diff must be DOCSTRING_ONLY_RECHECK")
    if expected.get("opening_runner_return_v5_sha") != REQUIRED_OPENING_RETURN_V5:
        errors.append("v5 RETURN sha missing from expected")
    if expected.get("v62_sha_755d30a8") != REQUIRED_SCORER_V62_BASELINE:
        errors.append("755d30a8 baseline missing from expected")
    if expected.get("scorer_v6_2_diff_vs_755d30a8_sha") != REQUIRED_V62_DIFF:
        errors.append("L-1 DIFF sha missing from expected")
    years = expected.get("allowed_roster_years") or {}
    if years.get("le2023") != list(range(2012, 2024)):
        errors.append("B-4b(n) le2023 roster years undeclared")
    if years.get("production") != [2023, 2024, 2025]:
        errors.append("B-4b(n) production roster years undeclared")
    if years.get("synthetic") != [2098, 2099]:
        errors.append("B-4b(n) synthetic roster years undeclared")
    if (root / "seeded" / "v6.2-draft").exists():
        errors.append("seeded/v6.2-draft still present")
    scorer_doc = (root / "seeded/v6.2/run_injury_residual_evaluator.py").read_text(encoding="utf-8")
    header = scorer_doc.split('"""', 2)[1] if scorer_doc.count('"""') >= 2 else scorer_doc[:800]
    if "DRAFT" in header or "PENDING_RYAN" in header:
        errors.append("active scorer docstring still DRAFT/PENDING_RYAN")
    if expected.get("scorer_v6_2_sha") != ACTIVE_SCORER_SHA:
        errors.append("v6.2 sha drifted")
    if expected.get("runtime_scorer_switch") is not False:
        errors.append("runtime scorer switch must be false")
    if (expected.get("ryan_scorer_decision") or {}).get("sha") != REQUIRED_RYAN_SCORER_DECISION:
        errors.append("Ryan scorer decision sha missing from expected")
    if expected.get("qb1_index_units") != 0.12:
        errors.append("QB1_INDEX_UNITS must be 0.12")
    if expected.get("naive_timestamp") != "STOP":
        errors.append("naive timestamp must STOP")
    if expected.get("i3_field_name") != "i3_holm_scorer":
        errors.append("i3 field must be i3_holm_scorer")
    if expected.get("fold_years", {}).get("F1") != 2024 or expected.get("fold_years", {}).get("F2") != 2025:
        errors.append("expected fold years must be 2024/2025")
    if expected.get("synthetic_holdout_years", {}).get("F1") != 2098:
        errors.append("synthetic holdout years missing")
    src = (root / "run_injury_holdout_opening.py").read_text(encoding="utf-8")
    if "REQUIRED_OPENING_PASS" in src and "No REQUIRED_OPENING_PASS" not in src:
        errors.append("B-8 REQUIRED_OPENING_PASS constant present")
    if "except BaseException" not in src:
        errors.append("B-1 missing BaseException handler")
    if "opening_pass_text_ok" not in src or "VERDICT_ANCHORED" not in src:
        errors.append("B-8a anchored PASS missing")
    if "assert_workspace_inputs_pre_lock" not in src:
        errors.append("B-13 pre-lock input check missing")
    if "hash_raw_inputs_before_parse" not in src:
        errors.append("B-4b(P) hash_raw_inputs_before_parse missing")
    if "raw_input_shas" not in src:
        errors.append("B-4b(P) raw_input_shas missing from runner")
    if "reproduce_le2023_a38a55bb" not in src:
        errors.append("B-4b(R) reproduce_le2023_a38a55bb not called")
    if "float(raw_p) * (9" in src or "min(1.0, float(raw_p)" in src:
        errors.append("B-6 runner Holm formula still present")
    if re.search(r"^def ryan_scorer_v62_authorized\(", src, re.M):
        errors.append("B-14 runtime scorer switch still present")
    if "ACTIVE_SCORER_SHA" not in src or ACTIVE_SCORER_SHA not in src:
        errors.append("B-14 single scorer constant missing")
    if "/workspace/ops/nfl_injury_audit_t4274u/DECISION_RYAN_SCORER_V6_2.txt" not in src:
        errors.append("Ryan v6.2 decision path missing")
    proc = subprocess.run(
        [sys.executable, str(root / "run_injury_holdout_opening.py"), "--mode", "all"],
        cwd=str(root),
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        errors.append("runner --mode all failed")
        errors.append((proc.stderr or "")[-4000:])
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
        if not doc.get("writer_invoked") or not doc.get("producer_invoked"):
            errors.append("receipt writer/producer")
        if doc.get("holdout_years_opened") or doc.get("opening_permitted"):
            errors.append("receipt opened holdout")
        if doc.get("scorer_sha") != ACTIVE_SCORER_SHA:
            errors.append("receipt scorer is not the single v6.2 sha")
        raw = doc.get("raw_input_shas") or {}
        for key in ("listings_2098.csv", "listings_2099.csv", "schedule.csv", "roster_2098.csv", "roster_2099.csv", "close.csv", "games.json"):
            if key not in raw:
                errors.append(f"receipt raw_input_shas missing {key}")
        for field in ("lock", "export_on_disk_sha", "tz", "incomplete", "n_missing_close", "folds", "consumed", "runner_sha", "scorer_sha"):
            if field not in doc:
                errors.append(f"receipt missing {field}")
        pooled = (doc.get("folds") or {}).get("pooled") or {}
        if "i1" not in pooled or "i3_holm_scorer" not in pooled or "k2" not in pooled:
            errors.append("receipt folds missing I-1/Holm/K-2")
        if "i3_holm_adjusted_p" in pooled:
            errors.append("receipt still uses i3_holm_adjusted_p")
        if pooled.get("i3_holm_source") != "scorer holm list only":
            errors.append("receipt holm source")
        for item in pooled.get("i3_holm") or []:
            if "p_holm_adj" in item:
                errors.append("runner Holm-adjusted p present")
    else:
        errors.append("missing F-E2E receipt")
    le = root / "out/le2023/d2_results.json"
    if le.is_file():
        doc = json.loads(le.read_text(encoding="utf-8"))
        if doc.get("holdout_years_opened") or doc.get("opening_permitted"):
            errors.append("le2023 opened holdout")
        if doc.get("incomplete", {}).get("n_incomplete") != 11:
            errors.append("le2023 n_incomplete")
        rebuild = doc.get("le2023_rebuild") or {}
        if rebuild.get("verdict") != "0_DIFF" or rebuild.get("n_rows") != 2863:
            errors.append("le2023 rebuild not deposited 0_DIFF/2863")
        if rebuild.get("deposited_deltas_sha") != REQUIRED_LE2023_DELTAS:
            errors.append("le2023 rebuild deltas sha drifted")
        if rebuild.get("deposited_compare_sha") != REQUIRED_LE2023_COMPARE:
            errors.append("le2023 rebuild compare sha drifted")
    else:
        errors.append("missing le2023 results")
    write_manifest(root)
    payload = {"ok": not errors, "n_errors": len(errors), "errors": errors, "package": "."}
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
