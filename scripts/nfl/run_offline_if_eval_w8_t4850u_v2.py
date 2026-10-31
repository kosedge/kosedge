#!/usr/bin/env python3
"""EVAL_ONLY t4850u v2 — diagnostic W8 IF slate + Alex RO HARD-gap evidence.

Not E1. Not FREE_PUBLIC. Not betting. Does not merge. Does not touch W9 emit.
Does not rewrite eval_w8_t4850u/.
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

from src.services.nfl_offline_if_eval_w8_v2 import (  # noqa: E402
    run_eval_slate_v2,
    stamp_tip,
    test_6_1_missing_field,
    test_6_3_pin_mismatch,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="EVAL_ONLY W8 diagnostic IF v2 (t4850u/t4851u)")
    parser.add_argument("--write-packet", action="store_true")
    parser.add_argument("--test-6-1-missing-field", action="store_true")
    parser.add_argument("--test-6-3-pin-mismatch", action="store_true")
    parser.add_argument("--stamp-tip", metavar="SHA")
    args = parser.parse_args(argv)

    if args.test_6_1_missing_field:
        result = test_6_1_missing_field()
        print(json.dumps(result, indent=2, sort_keys=True))
        return int(result["exit_code"])

    if args.test_6_3_pin_mismatch:
        result = test_6_3_pin_mismatch()
        print(json.dumps(result, indent=2, sort_keys=True))
        return int(result["exit_code"])

    if args.stamp_tip:
        stamp_tip(args.stamp_tip)
        print(json.dumps({"stamped": args.stamp_tip, "parent_v1_tip": "426bd1d9"}, indent=2))
        return 0

    artifacts = run_eval_slate_v2(write=bool(args.write_packet))
    packet = artifacts["packet"]
    print(
        json.dumps(
            {
                "status": packet["status"],
                "eval_class": packet["eval_class"],
                "packet_version": packet.get("packet_version"),
                "run_id": packet.get("run_id"),
                "e1_admissible": False,
                "scoring_admissible_now": False,
                "public_delivery": False,
                "n_supported": packet["n_supported"],
                "n_invoked": packet["n_invoked"],
                "n_fail_closed": packet["n_fail_closed"],
                "tnf_excluded": packet["tnf_excluded"],
                "parent_v1_tip": "426bd1d9",
                "cmd": artifacts["manifest"]["cmd"],
                "call_audit_passed": artifacts["call_audit"]["passed"],
                "publication": {
                    "free_public": packet["publication_controls"]["free_public"],
                    "coming_soon": "ON",
                    "enabled": False,
                },
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if packet["n_invoked"] == 13 and packet["public_delivery"] is False else 2


if __name__ == "__main__":
    raise SystemExit(main())
