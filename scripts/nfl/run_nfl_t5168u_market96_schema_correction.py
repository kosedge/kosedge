#!/usr/bin/env python3
"""t5168u market96 MARKET schema correction (CERT=0). No one-exec / --score."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.nfl_t5107u.r5_market96_schema_correction import (  # noqa: E402
    build_market96_schema_correction,
)


def main() -> int:
    report = build_market96_schema_correction(root=ROOT, write=True)
    market = report["market96"]
    print(
        json.dumps(
            {
                "ok": True,
                "verified": False,
                "new_scientific_look": False,
                "kind": report["kind"],
                "n": market["n"],
                "mae_market": market["mae_market"],
                "rmse_market": market["rmse_market"],
                "bias_market": market["bias_market"],
                "code_sha256": report["hashes"]["code_sha256"],
                "input_sha256": report["hashes"]["input_sha256"],
                "output_sha256": report["hashes"]["output_sha256"],
                "joined_sha256": report["joined_sha256"],
                "cert_candidate": 0,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
