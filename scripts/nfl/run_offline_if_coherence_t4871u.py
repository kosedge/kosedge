#!/usr/bin/env python3
"""EVAL_ONLY t4871u — IF-only coherence packet. No math change. No merge."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MS = ROOT / "services" / "model-service"
if str(MS) not in sys.path:
    sys.path.insert(0, str(MS))

from src.services.nfl_if_coherence import run_coherence_slate  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="IF-only coherence t4871u")
    parser.add_argument("--write-packet", action="store_true")
    args = parser.parse_args(argv)
    artifacts = run_coherence_slate(write=bool(args.write_packet))
    mapped = artifacts["verdict"]
    print(
        json.dumps(
            {
                "verdict": mapped["verdict"],
                "label": mapped["label"],
                "execution_tip": artifacts["manifest"]["execution_tip"],
                "run_id": artifacts["manifest"]["run_id"],
                "a_fail": mapped["a_fail"],
                "b_fail": mapped["b_fail"],
                "b_cond": mapped["b_cond"],
                "j14": artifacts["j14"]["band"],
                "public_delivery": False,
                "e1_admissible": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if mapped["verdict"] != "BLOCKED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
