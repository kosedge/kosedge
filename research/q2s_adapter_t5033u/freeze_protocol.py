#!/usr/bin/env python3
"""Freeze protocol/code/config/manifest BEFORE any outcome comparison."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "artifacts" / "PROTOCOL_FREEZE.json"
LOOK = ROOT / "artifacts" / "LOOK_CONSUMED.json"

FREEZE_PATHS = [
    "emit_q2s_adapter.py",
    "compare_appendix_o.py",
    "freeze_protocol.py",
    "q2s/blend.py",
    "q2s/bootstrap.py",
    "q2s/coverage.py",
    "q2s/__init__.py",
    "q2pb/strength.py",
    "q2pb/metrics.py",
    "q2pb/data.py",
    "q2pb/constants.py",
    "frozen/FROZEN_CONFIG_Q2PB_t5009u.json",
    "frozen/FROZEN_CONFIG_Q2PB_t5009u.md",
    "pins/t4910u/SCORE_RESULTS.json",
    "pins/t4910u/SAMPLE_MANIFEST_70.json",
    "data/games_4fe1cdd7.csv",
    "data/outcomes_2013_2022_score_only.csv",
    "authority/AMEND_681_ISOLATION_H6.md",
    "tests/test_q2s_adapter.py",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    if LOOK.exists():
        raise SystemExit("REFUSE: look already consumed; freeze is closed")
    files = {}
    for rel in FREEZE_PATHS:
        path = ROOT / rel
        if not path.exists():
            raise SystemExit(f"REFUSE: missing freeze path {rel}")
        files[rel] = sha256_file(path)
    payload = {
        "label": "RETRO_FIT / DEV_RESEARCH",
        "cert": 0,
        "nfl": "NO-GO",
        "ticket": "t5033u",
        "amend": "fdf91ff5",
        "delegation": "d7e0a6bc",
        "work_package": "2db90f76",
        "guardrails": "52c79ee6",
        "score_results_control": "2b9f302e",
        "q2_eval_closed": "03a4dd90",
        "annotate_684_accept": "9982d42f",
        "frozen_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "files": files,
        "note": (
            "Protocol/code/config/manifest frozen before Appendix O. "
            "One look only. Failed or inconclusive result does NOT authorize "
            "another weight or look."
        ),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if OUT.exists():
        prev = json.loads(OUT.read_text())
        if prev.get("files") != files:
            raise SystemExit("REFUSE: PROTOCOL_FREEZE already exists with different file shas")
        print(f"PROTOCOL_FREEZE already sealed ({OUT})")
        return 0
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"froze {len(files)} paths -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
