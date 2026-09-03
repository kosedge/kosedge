#!/usr/bin/env python3
"""Closed-door CFB totals-guard real-roster holdout runner.

Refuses to invent numbers when 2023–24 live-style roster/SP+ packs are
missing. Fit+eval must share the same roster path — never apply proxy-fit
λ from the league-avg harness onto a real-roster eval.

Does NOT edit apply_cfb_kei / pack / live tagger / PLAY flags.

Usage:
  PYTHONPATH=services/model-service \\
    python3 scripts/cfb/run_totals_guard_real_roster_holdout.py

Exit codes:
  0 — reconstructable (would run twin holdout; not implemented until packs land)
  2 — STOP blocker (expected today)
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.cfb_season_engine.totals_guard_real_roster import (  # noqa: E402
    PROXY_ROSTER_PATH,
    REAL_ROSTER_PATH,
    assert_same_roster_path,
    blocker_payload,
    real_roster_path_reconstructable,
)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Real-roster totals-guard holdout (STOP if packs missing)."
    )
    ap.add_argument(
        "--stamp",
        default=date.today().strftime("%Y%m%d"),
        help="Ops stamp for artifact folder name",
    )
    ap.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Optional directory for summary.json (default: data/ops/...)",
    )
    ap.add_argument(
        "--allow-proxy-mix",
        action="store_true",
        help="Forbidden flag — present only so we can hard-refuse it.",
    )
    args = ap.parse_args(argv)

    if args.allow_proxy_mix:
        print(
            "REFUSED: --allow-proxy-mix is forbidden "
            f"(would mix {PROXY_ROSTER_PATH} λ onto {REAL_ROSTER_PATH}).",
            file=sys.stderr,
        )
        return 2

    # Same-path self-check (identity of the intended path).
    assert_same_roster_path(REAL_ROSTER_PATH, REAL_ROSTER_PATH)

    gate = real_roster_path_reconstructable()
    payload = blocker_payload()
    payload["stamp"] = args.stamp
    payload["script"] = "scripts/cfb/run_totals_guard_real_roster_holdout.py"
    payload["ops_note"] = (
        "data/ops/cfb-totals-guard-real-roster-holdout-blocker-20260903.md"
    )

    out_dir = args.out_dir or (
        ROOT
        / "data"
        / "ops"
        / f"cfb-totals-guard-real-roster-holdout-blocker-{args.stamp}"
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    # Do not clobber the curated ops summary.json — write runner output beside it.
    out_path = out_dir / "runner_blocker.json"
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(payload, indent=2))
    print(f"\nwrote {out_path}", file=sys.stderr)

    if gate["stop"]:
        print(
            "\nSTOP — real-roster path not reconstructable. "
            "No eval table. Flag OFF. No apply_cfb_kei.",
            file=sys.stderr,
        )
        return 2

    print(
        "\nGO — packs present; twin holdout implementation still required "
        "(not auto-run here).",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
