#!/usr/bin/env python3
"""EVAL_ONLY t4850u v3 — re-execute W8 IF slate at declared execution tip.

Not E1. Not FREE_PUBLIC. Does not rewrite eval_w8_t4850u/ or eval_w8_t4850u_v2/.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MS = ROOT / "services" / "model-service"
if str(MS) not in sys.path:
    sys.path.insert(0, str(MS))

from src.services.nfl_offline_if_eval_w8_v3 import run_eval_slate_v3  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="EVAL_ONLY W8 diagnostic IF v3 (t4864u)")
    parser.add_argument("--write-packet", action="store_true")
    args = parser.parse_args(argv)
    artifacts = run_eval_slate_v3(write=bool(args.write_packet))
    packet = artifacts["packet"]
    print(
        json.dumps(
            {
                "status": packet["status"],
                "packet_version": packet.get("packet_version"),
                "run_id": packet.get("run_id"),
                "execution_tip": artifacts["manifest"]["execution_tip"],
                "invoke_head_matches_execution_tip": artifacts["manifest"][
                    "invoke_head_matches_execution_tip"
                ],
                "e1_admissible": False,
                "scoring_admissible_now": False,
                "public_delivery": False,
                "n_invoked": packet["n_invoked"],
                "tnf_excluded": packet["tnf_excluded"],
                "before_after": packet["before_after"],
                "call_audit_passed": artifacts["call_audit"]["passed"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    ok = (
        packet["n_invoked"] == 13
        and packet["public_delivery"] is False
        and artifacts["manifest"]["invoke_head_matches_execution_tip"] is True
    )
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
