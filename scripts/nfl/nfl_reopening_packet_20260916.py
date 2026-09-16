#!/usr/bin/env python3
"""Build the 2026-09-16 NFL production reopening packet (research only).

Does not write Railway, flip Coming soon, retune coefficients, or continue KE R&D.

  PYTHONPATH=services/model-service python3 scripts/nfl/nfl_reopening_packet_20260916.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MS_SRC = ROOT / "services" / "model-service"
if str(MS_SRC) not in sys.path:
    sys.path.insert(0, str(MS_SRC))

from src.services.nfl_reopening_packet import assemble_packet  # noqa: E402

OUT_DIR = ROOT / "data" / "ops" / "nfl-reopening-packet-20260916"


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    bundle = assemble_packet()
    written = {
        "summary.json": bundle["packet"],
        "gate1_integrity.json": bundle["gate1"],
        "shadow_slate.json": bundle["shadow"],
        "numerical_audit.json": bundle["audit"],
        "frozen_eval.json": bundle["gate3"],
    }
    for name, payload in written.items():
        (OUT_DIR / name).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    packet = bundle["packet"]
    print("NFL production reopening packet (research only)")
    print(f"packet_id={packet['packet_id']} run_id={packet['run_id']}")
    print(
        f"gate1 candidate={packet['gate1']['candidate_path']} "
        f"live_isolation={packet['gate1']['live_production_isolation']} "
        f"reopen={packet['gate1']['reopen_gate']}"
    )
    print(
        f"gate2 sanity={packet['gate2']['sanity']} "
        f"w2={packet['gate2']['w2_game_count']} "
        f"flagged={len(packet['gate2']['flagged_games'])}"
    )
    print(f"gate3 {packet['gate3']['verdict']} n_w1={packet['gate3']['n_w1']}")
    print(f"recommendation={packet['recommendation']} production_promote=false")
    if packet.get("alex_live"):
        print(
            f"alex fold live_sha={packet['alex_live'].get('live_git_sha')} "
            f"integrity={packet['gate1'].get('integrity')} "
            f"w2_live={packet['gate2'].get('alex_live_game_count')} "
            f"gate4={packet.get('gate4', {}).get('release_spread')}"
        )
    print(f"wrote {OUT_DIR}")
    if packet["recommendation"] == "NO-GO":
        return 1
    if packet["gate1"]["candidate_path"] != "PASS":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
