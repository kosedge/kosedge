#!/usr/bin/env python3
"""P2 walk-forward compare vs the published W0–1 baseline (47.7% / 8.36).

Historical seasons must NOT use the 2026 roster/QB pack (future overlay).
This script re-runs the existing program-prior harness when HD is mounted.
If HD is missing, it records the baseline and the leakage diagnosis.

Usage:
  python scripts/cfb/run_p2_walkforward_compare.py
  python scripts/cfb/run_p2_walkforward_compare.py --limit 40
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASELINE = {
    "slice": "w0_1",
    "ats": 0.477,
    "mae": 8.36,
    "n": 439,
    "source": "data/ops/cfb-p0-audit-20260813.md",
    "used_in_spread": False,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--repo-fallback", action="store_true")
    args = parser.parse_args(argv)
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "cfb" / "run_walkforward_week0_4.py"),
        "--seasons",
        "2020-2025",
    ]
    if args.limit:
        cmd.extend(["--limit", str(args.limit)])
    if args.repo_fallback:
        cmd.append("--repo-fallback")
    ran = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    after = None
    diagnosis = (
        "2026 roster/QB/coaching DNA is not applied to 2020–25 walk-forward "
        "(that would leak a future overlay). Valid W0–1 test remains the "
        "program-prior (opponent-adj EPA, seasons < Y). P2 does not retune "
        "era weights in-sample. used_in_spread stays false."
    )
    if ran.returncode != 0:
        report = {
            "ok": False,
            "baseline": BASELINE,
            "after": None,
            "hd_ran": False,
            "stderr": (ran.stderr or "")[-800:],
            "diagnosis": diagnosis + " HD/repo parquet missing — baseline stands.",
            "used_in_spread": False,
            "kei": False,
        }
    else:
        try:
            after = json.loads(ran.stdout)
        except json.JSONDecodeError:
            after = {"raw": ran.stdout[-1200:]}
        w01 = (after or {}).get("by_week_band", {}).get("w0_1") or {}
        overall = (after or {}).get("overall") or {}
        report = {
            "ok": True,
            "baseline": BASELINE,
            "after_w0_1": {
                "ats": w01.get("ats_rate"),
                "mae": w01.get("mae"),
                "ats_n": w01.get("ats_n"),
                "n_close": w01.get("n_close"),
                "ats_ci95": w01.get("ats_ci95"),
            },
            "after_overall": {
                "ats": overall.get("ats_rate"),
                "mae": overall.get("mae"),
                "ats_n": overall.get("ats_n"),
                "n_close": overall.get("n_close"),
            },
            "hd_ran": True,
            "delta_w0_1": {
                "ats": round(float(w01.get("ats_rate") or 0) - BASELINE["ats"], 4),
                "mae": round(float(w01.get("mae") or 0) - BASELINE["mae"], 4),
                "read": "flat unless ATS/MAE move outside noise; no in-sample retune",
            },
            "diagnosis": diagnosis,
            "used_in_spread": False,
            "kei": False,
        }
    out = ROOT / "data" / "ops" / "cfb-p2-walkforward-20260813.json"
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
