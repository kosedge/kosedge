#!/usr/bin/env python3
"""Verify t5055u final pre-look freeze + preserved history.

Parent PROTOCOL_FREEZE.json sha == 90774bd4 (prediction files unchanged).
History FINAL_PRELOOK_FREEZE.json object sha == a4652323 (do not re-hash
its old evaluator file map against live code).
Live complete set is FINAL_PRELOOK_FREEZE_t5055u.json.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

PACKET = Path(__file__).resolve().parents[1]
EVAL = Path(__file__).resolve().parent
PARENT_FREEZE_PATH = PACKET / "phase4" / "artifacts" / "PROTOCOL_FREEZE.json"
HISTORY_FREEZE_PATH = EVAL / "FINAL_PRELOOK_FREEZE.json"
FINAL_FREEZE_PATH = HISTORY_FREEZE_PATH  # t5053u history writer still binds this
T5055U_FREEZE_PATH = EVAL / "FINAL_PRELOOK_FREEZE_t5055u.json"
ALEX_RECEIPT_PATH = EVAL / "ALEX_RECEIPT_T5055U.json"
COS_EXECUTE_PATH = EVAL / "COS_EXECUTE_LOOK_T5055U.json"

PARENT_FREEZE_SHA = (
    "90774bd40c03c1b1de6f16967f29ba3ff2017b25d93620c6d5e351f56460df98"
)
HISTORY_FREEZE_SHA = (
    "a46523231f55fc3b147a8e3864f74faf3de08d8f6c76d4cc92eebdeee7c174d4"
)
IF_MUS_SHA = "32e9743483259f2a9c13efe9826e550f610a6068995fad3bc9fdb6b1698d5d43"
Q2S_SHA = "55d8c8bc2155705c04e9ef88ba5637ea491bf5c245e4f7bb8fcfb3523f9ec925"
MATRIX_SHA = "b56be1462e591ac5e04cfaf860938118e013664a2c661e156afdf5c5f41bc216"

# t5053u history writer list — do not expand (freeze_final_prelook.py).
EVALUATOR_PATHS = [
    "evaluator/AUTHORITY_T5053U.md",
    "evaluator/METRIC_PROTOCOL.md",
    "evaluator/bootstrap.py",
    "evaluator/compare.py",
    "evaluator/verify_final_prelook.py",
    "evaluator/freeze_final_prelook.py",
    "evaluator/fixtures/synthetic_w7w17.json",
    "tests/test_t5053u_evaluator_synthetic.py",
]

T5055U_EVALUATOR_PATHS = [
    "evaluator/AUTHORITY_T5053U.md",
    "evaluator/AUTHORITY_T5055U.md",
    "evaluator/METRIC_PROTOCOL.md",
    "evaluator/bootstrap.py",
    "evaluator/compare.py",
    "evaluator/verify_final_prelook.py",
    "evaluator/freeze_final_prelook.py",
    "evaluator/freeze_t5055u.py",
    "evaluator/fixtures/synthetic_w7w17.json",
    "evaluator/fixtures/synthetic_unequal_clusters.json",
    "evaluator/FINAL_PRELOOK_FREEZE.json",
    "tests/test_t5053u_evaluator_synthetic.py",
    "tests/test_t5055u_week_cluster_and_look.py",
]


class LookGateRefuse(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_parent_history() -> dict[str, Any]:
    if not PARENT_FREEZE_PATH.exists():
        raise LookGateRefuse("parent PROTOCOL_FREEZE.json missing")
    live = sha256_file(PARENT_FREEZE_PATH)
    if live != PARENT_FREEZE_SHA:
        raise LookGateRefuse(
            f"parent freeze sha {live} != history {PARENT_FREEZE_SHA} — do not look"
        )
    parent = json.loads(PARENT_FREEZE_PATH.read_text())
    files = parent.get("files") or {}
    mismatches = []
    for rel, expected in files.items():
        path = PACKET / rel
        if not path.exists():
            raise LookGateRefuse(f"parent freeze path missing: {rel}")
        actual = sha256_file(path)
        if actual != expected:
            mismatches.append({"path": rel, "expected": expected, "actual": actual})
    if mismatches:
        raise LookGateRefuse(f"parent 90774bd4 files drifted: {mismatches[:4]}")
    rows = parent.get("rows") or {}
    if rows.get("if_mus", {}).get("sha256") != IF_MUS_SHA:
        raise LookGateRefuse("IF mus row hash drifted from 32e97434")
    if rows.get("q2s_rows", {}).get("sha256") != Q2S_SHA:
        raise LookGateRefuse("q2s row hash drifted from 55d8c8bc")
    if files.get("gate2/RECON_MATRIX_W7W17.csv") != MATRIX_SHA:
        raise LookGateRefuse("matrix hash drifted from b56be146")
    if sha256_file(PACKET / "phase4/artifacts/IF_MUS_W7W17.json") != IF_MUS_SHA:
        raise LookGateRefuse("live IF mus != 32e97434")
    if sha256_file(PACKET / "phase4/artifacts/q2s_rows_w7w17.json") != Q2S_SHA:
        raise LookGateRefuse("live q2s rows != 55d8c8bc")
    return parent


def verify_history_freeze_a4652323() -> dict[str, Any]:
    """Object-sha only. Do not re-hash a4652323's old evaluator file map."""
    if not HISTORY_FREEZE_PATH.exists():
        raise LookGateRefuse("history FINAL_PRELOOK_FREEZE.json missing")
    live = sha256_file(HISTORY_FREEZE_PATH)
    if live != HISTORY_FREEZE_SHA:
        raise LookGateRefuse(
            f"history freeze sha {live} != a4652323 — do not rewrite history"
        )
    hist = json.loads(HISTORY_FREEZE_PATH.read_text())
    if hist.get("parent_rewritten") is True:
        raise LookGateRefuse("history freeze claims parent rewrite — refuse")
    parent_bind = hist.get("parent_freeze") or {}
    if str(parent_bind.get("sha256") or "") != PARENT_FREEZE_SHA:
        raise LookGateRefuse("history freeze does not bind parent 90774bd4")
    rows = hist.get("rows") or {}
    if rows.get("if_mus", {}).get("sha256") != IF_MUS_SHA:
        raise LookGateRefuse("history freeze IF mus != 32e97434")
    if rows.get("q2s_rows", {}).get("sha256") != Q2S_SHA:
        raise LookGateRefuse("history freeze q2s != 55d8c8bc")
    return hist


def _verify_freeze_files(final: dict[str, Any], parent: dict[str, Any]) -> None:
    files = final.get("files")
    if not isinstance(files, dict) or not files:
        raise LookGateRefuse("final freeze has no complete files map")
    parent_rels = set(parent["files"])
    eval_rels = set(T5055U_EVALUATOR_PATHS)
    expected = parent_rels | eval_rels | {"phase4/artifacts/PROTOCOL_FREEZE.json"}
    if not expected <= set(files):
        missing = sorted(expected - set(files))
        raise LookGateRefuse(f"t5055u freeze incomplete set, missing {missing}")
    mismatches = []
    for rel, expected_sha in files.items():
        path = PACKET / rel
        if not path.exists():
            raise LookGateRefuse(f"t5055u freeze path missing: {rel}")
        actual = sha256_file(path)
        if actual != expected_sha:
            mismatches.append({"path": rel, "expected": expected_sha, "actual": actual})
    if mismatches:
        raise LookGateRefuse(f"t5055u freeze re-hash mismatch: {mismatches[:6]}")


def verify_complete_set() -> dict[str, Any]:
    parent = verify_parent_history()
    verify_history_freeze_a4652323()
    if not T5055U_FREEZE_PATH.exists():
        raise LookGateRefuse(
            "FINAL_PRELOOK_FREEZE_t5055u.json missing — evaluator not frozen"
        )
    final = json.loads(T5055U_FREEZE_PATH.read_text())
    if final.get("parent_rewritten") is True:
        raise LookGateRefuse("t5055u freeze claims parent rewrite — refuse")
    parent_bind = final.get("parent_freeze") or {}
    if str(parent_bind.get("sha256") or "") != PARENT_FREEZE_SHA:
        raise LookGateRefuse("t5055u freeze does not bind parent 90774bd4")
    hist_bind = final.get("history_freeze") or {}
    if str(hist_bind.get("sha256") or "") != HISTORY_FREEZE_SHA:
        raise LookGateRefuse("t5055u freeze does not bind history a4652323")
    _verify_freeze_files(final, parent)
    rows = final.get("rows") or {}
    if rows.get("if_mus", {}).get("sha256") != IF_MUS_SHA:
        raise LookGateRefuse("t5055u freeze IF mus != 32e97434")
    if rows.get("q2s_rows", {}).get("sha256") != Q2S_SHA:
        raise LookGateRefuse("t5055u freeze q2s != 55d8c8bc")
    if final.get("look_run") or final.get("look_authorized"):
        raise LookGateRefuse("t5055u freeze must stay look_authorized=false / look_run=false")
    return final


def require_alex_receipt_for_look(final: dict[str, Any]) -> None:
    if not ALEX_RECEIPT_PATH.exists():
        raise LookGateRefuse(
            "independent Alex receipt absent — a4652323/8b80ad7b are not "
            "receipts for this t5055u freeze"
        )
    receipt = json.loads(ALEX_RECEIPT_PATH.read_text())
    live = sha256_file(T5055U_FREEZE_PATH)
    if str(receipt.get("binds_final_freeze_sha256") or "") != live:
        raise LookGateRefuse("Alex receipt sha != live FINAL_PRELOOK_FREEZE_t5055u")
    if receipt.get("authorizes_look") is not True:
        raise LookGateRefuse("Alex receipt does not authorize a look")


def main() -> int:
    try:
        final = verify_complete_set()
    except LookGateRefuse as exc:
        print(f"VERIFY_REFUSE: {exc}")
        return 2
    print(
        json.dumps(
            {
                "ok": True,
                "parent_sha8": "90774bd4",
                "history_sha8": "a4652323",
                "final_path": "evaluator/FINAL_PRELOOK_FREEZE_t5055u.json",
                "n_files": len(final["files"]),
                "look_authorized": False,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
