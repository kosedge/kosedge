#!/usr/bin/env python3
"""Orchestrate Phase 4: IF score → Q2s emit → freeze (row identity). No look."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PHASE4 = Path(__file__).resolve().parent
if str(PHASE4) not in sys.path:
    sys.path.insert(0, str(PHASE4))

from emit_q2s_w7w17 import emit_adapter  # noqa: E402
from freeze_protocol import write_freeze  # noqa: E402
from score_if_w7w17 import ScoreRefuse, assemble_sample, import_if, score_game, write_if_mus  # noqa: E402
from score_if_w7w17 import assert_no_forbidden_open  # noqa: E402


def main() -> int:
    assumptions = PHASE4 / "ASSUMPTIONS.md"
    if not assumptions.is_file():
        raise SystemExit("ASSUMPTIONS.md must exist before first score write")
    look = PHASE4 / "artifacts" / "LOOK_CONSUMED.json"
    if look.exists():
        raise SystemExit("LOOK_CONSUMED exists — Phase 4 stops pre-look")
    assert_no_forbidden_open()
    games, sealed = assemble_sample()
    sim = import_if()
    rows = [score_game(sim, g) for g in games]
    if_payload = write_if_mus(rows, sealed)
    emit_payload = emit_adapter()
    freeze = write_freeze()
    print(
        json.dumps(
            {
                "ok": True,
                "n_scored": if_payload["n_scored"],
                "n_emitted": emit_payload["n_emitted"],
                "if_mus_sha256": if_payload["sha256"],
                "q2s_sha256": emit_payload["sha256"],
                "freeze_rows": {k: v["sha8"] for k, v in freeze["rows"].items()},
                "look_run": False,
                "cert": 0,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ScoreRefuse as exc:
        print(f"PHASE4_REFUSE: {exc}", file=sys.stderr)
        raise SystemExit(2)
