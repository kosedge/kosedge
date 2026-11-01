#!/usr/bin/env python3
"""t5119u R2-B — materialize one DEV_RESEARCH record. Not EVAL. No claim."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.nfl_t5107u.dev_research import (  # noqa: E402
    DEFAULT_RECORD,
    materialize_pinned_dev_research,
)
from src.services.nfl_t5107u.outcome_gate import refuse_preserved_t5116u_path  # noqa: E402


def main() -> int:
    dest = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_RECORD
    refuse_preserved_t5116u_path(dest)
    record = materialize_pinned_dev_research(dest=dest, quotes=None)
    print(
        json.dumps(
            {
                "status": "DEV_RESEARCH",
                "game_id": record["game_id"],
                "market": record["market"]["status"],
                "one_run_claim": record["one_run_claim"],
                "eval": record["eval"],
                "record_sha256": record["record_sha256"],
                "path": str(dest),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
