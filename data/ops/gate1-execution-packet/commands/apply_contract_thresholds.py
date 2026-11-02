#!/usr/bin/env python3
"""Apply CONTRACT abs_delta_max (NOT +/-0.05) to hard-gate table. Do not clear Gate 1 on FG FAIL."""
from __future__ import annotations

import json
import pathlib
import sys


def main() -> int:
    thresh_path = pathlib.Path(sys.argv[1])
    pre_path = pathlib.Path(sys.argv[2])
    out_dir = pathlib.Path(sys.argv[3])
    thresh = json.loads(thresh_path.read_text())
    pre = json.loads(pre_path.read_text())

    rows = []
    all_pass = True
    for row in pre["hard_gate_metrics"]:
        m = row["metric"]
        gate = thresh["hard_gates"][m]
        d = abs(row["sim"] - row["train"])
        mx = gate["abs_delta_max"]
        ok = d <= mx
        if not ok:
            all_pass = False
        rows.append(
            {
                "metric": m,
                "train": row["train"],
                "sim": row["sim"],
                "abs_delta": d,
                "abs_delta_max": mx,
                "expected_verdict": row["expected_verdict"],
                "observed_verdict": "PASS" if ok else "FAIL",
                "hard_gate": True,
                "source_receipt": row["source_receipt"],
                "note": "CONTRACT thresholds applied; +/-0.05 forbidden",
            }
        )

    structural = pre["structural_expected_after_wrapper"]
    gate1_cleared = all_pass and all(
        r["expected_verdict"] == "PASS" for r in structural
    )
    receipt = {
        "status": "GATE_1_CLEARED" if gate1_cleared else "GATE_1_NOT_CLEARED",
        "clears_gate_1": gate1_cleared,
        "policy": "Alex contract abs_delta_max; NOT +/-0.05; thresholds not fitted to SHA",
        "hard_gate_rows": rows,
        "structural_expected": structural,
        "honest_blocker_if_not_cleared": (
            None
            if gate1_cleared
            else (
                "field_goal_makes_per_game mechanism fail "
                "(delta~0.7595 >> abs_delta_max 0.119987); "
                "wrapper does not fix FG volume; Gate 1 remains NOT CLEARED"
            )
        ),
        "forbidden": "Do not declare Gate 1 cleared while any hard gate FAILs",
        "reuse_note": (
            "train/sim from prior parent receipt (reuse-until-rebind). "
            "If certify/freeze re-measure and differ, rebind and re-evaluate; "
            "do not fit thresholds."
        ),
    }
    path = out_dir / "gate1-contract-eval.json"
    path.write_text(json.dumps(receipt, indent=2) + "\n")
    print(
        json.dumps(
            {
                "wrote": str(path),
                "status": receipt["status"],
                "clears_gate_1": gate1_cleared,
            },
            indent=2,
        )
    )
    if not gate1_cleared:
        print("GATE_1_NOT_CLEARED — Cursor must not clear Gate 1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
