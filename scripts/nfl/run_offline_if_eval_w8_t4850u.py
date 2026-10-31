#!/usr/bin/env python3
"""EVAL_ONLY t4850u — diagnostic W8 IF slate (through-W7 / rating_week=7).

Not E1. Not FREE_PUBLIC. Not betting. Does not merge. Does not touch W9 emit.
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

from src.services.nfl_offline_if_eval_w8 import run_eval_slate  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="EVAL_ONLY W8 diagnostic IF (t4850u)")
    parser.add_argument("--write-packet", action="store_true")
    args = parser.parse_args(argv)
    artifacts = run_eval_slate(write=bool(args.write_packet))
    packet = artifacts["packet"]
    print(
        json.dumps(
            {
                "status": packet["status"],
                "eval_class": packet["eval_class"],
                "e1_admissible": False,
                "public_delivery": False,
                "n_supported": packet["n_supported"],
                "n_invoked": packet["n_invoked"],
                "n_fail_closed": packet["n_fail_closed"],
                "tnf_excluded": packet["tnf_excluded"],
                "unresolved": artifacts["unresolved"],
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
