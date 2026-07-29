#!/usr/bin/env python3
"""Evaluate NFL enterprise ATS/CLV/MAE/holdout gates → GREEN/YELLOW/RED.

Reads existing ops artifacts (DB-first grading + supervised retrain). Writes:
  data/ops/nfl-enterprise-gates-latest.json
  data/ops/nfl-enterprise-gates-latest.md
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.nfl_enterprise_gates import evaluate_enterprise_gates  # noqa: E402
from src.services.nfl_prop_edge_policy import PLAY_STAKE_ELIGIBLE  # noqa: E402
from src.services.nfl_side_total_publish_policy import (  # noqa: E402
    DEFAULT_SEGMENT_EVIDENCE,
    publish_tag,
)

OUT_JSON = ROOT / "data" / "ops" / "nfl-enterprise-gates-latest.json"
OUT_MD = ROOT / "data" / "ops" / "nfl-enterprise-gates-latest.md"

GRADING_CANDIDATES = [
    ROOT / "data" / "ops" / "nfl-kav-grading-after.json",
    ROOT / "data" / "ops" / "nfl-odds-open-close-grading.json",
    ROOT / "data" / "ops" / "nfl-kav-grading-before.json",
]
SUPERVISED_CANDIDATES = [
    ROOT / "data" / "ops" / "nfl-kav-supervised-retrain-v3.json",
]
PLAY_HOLDOUT_CANDIDATES = [
    ROOT / "data" / "ops" / "nfl-play-only-holdout.json",
]


def _load_first(paths: list[Path]) -> tuple[dict, str | None]:
    for p in paths:
        if p.exists():
            return json.loads(p.read_text()), str(p.relative_to(ROOT))
    return {}, None


def main() -> int:
    grading, grading_path = _load_first(GRADING_CANDIDATES)
    supervised, supervised_path = _load_first(SUPERVISED_CANDIDATES)
    play_holdout, play_path = _load_first(PLAY_HOLDOUT_CANDIDATES)
    report = evaluate_enterprise_gates(
        grading=grading,
        supervised=supervised,
        play_holdout=play_holdout,
        props_stake_eligible=bool(PLAY_STAKE_ELIGIBLE),
    )

    # Example selective publish decisions for desk sanity
    examples = [
        publish_tag(
            market="spread",
            abs_edge=3.2,
            product_gate_status=report.overall,
        ),
        publish_tag(
            market="spread",
            abs_edge=1.5,
            product_gate_status=report.overall,
        ),
        publish_tag(
            market="total",
            abs_edge=2.7,
            product_gate_status=report.overall,
        ),
        publish_tag(
            market="total",
            abs_edge=3.5,
            product_gate_status=report.overall,
        ),
    ]

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "grading_artifact": grading_path,
        "supervised_artifact": supervised_path,
        "play_holdout_artifact": play_path,
        "database_url_host": os.environ.get("DATABASE_URL", "").split("@")[-1] or None,
        "report": report.to_dict(),
        "publish_policy_examples": examples,
        "segment_evidence_keys": list(DEFAULT_SEGMENT_EVIDENCE.keys()),
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n")

    lines = [
        "# NFL Enterprise Gates",
        "",
        f"Generated: {payload['generated_at']}",
        f"Overall: **{report.overall}**",
        f"Betting-product ready: **{report.betting_product_ready}**",
        f"Selective PLAY ready: **{report.selective_play_ready}**",
        f"Grading: `{grading_path}`",
        f"Supervised: `{supervised_path}`",
        f"PLAY holdout: `{play_path}`",
        "",
        "| Check | Status | Detail |",
        "| --- | --- | --- |",
    ]
    for c in report.checks:
        lines.append(f"| `{c.name}` | {c.status} | {c.detail} |")
    lines.append("")
    if report.notes:
        lines.append("## Notes")
        lines.append("")
        for n in report.notes:
            lines.append(f"- {n}")
        lines.append("")
    lines.append("## Selective publish examples")
    lines.append("")
    for ex in examples:
        lines.append(
            f"- candidate={ex.get('candidate_tag')} → tag={ex.get('tag')} "
            f"stake={ex.get('stake_eligible')} ({ex.get('reason')})"
        )
    lines.append("")
    OUT_MD.write_text("\n".join(lines) + "\n")

    print(
        json.dumps(
            {
                "overall": report.overall,
                "betting_product_ready": report.betting_product_ready,
                "selective_play_ready": report.selective_play_ready,
            },
            indent=2,
        )
    )
    print(f"wrote {OUT_JSON}")
    print(f"wrote {OUT_MD}")
    # Non-zero exit on RED overall so CI/ops can gate deploys.
    return 2 if report.overall == "RED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
