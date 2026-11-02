#!/usr/bin/env python3
"""t5165u reporting addendum (CERT=0). No one-exec / --score / --cos-bind."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.nfl_t5107u.r5_reporting_addendum import (  # noqa: E402
    build_reporting_addendum,
)


def main() -> int:
    report = build_reporting_addendum(root=ROOT, write=True)
    print(
        json.dumps(
            {
                "ok": True,
                "verified": False,
                "new_scientific_look": False,
                "kind": report["kind"],
                "joined_n": report["joined_n"],
                "joined_sha256": report["joined_sha256"],
                "code_sha256": report["hashes"]["code_sha256"],
                "input_sha256": report["hashes"]["input_sha256"],
                "output_sha256": report["hashes"]["output_sha256"],
                "exec_receipt_sha256": report["exec_receipt_sha256"],
                "exec_bind_id": report["exec_bind_id"],
                "cert_candidate": 0,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
