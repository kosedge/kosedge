#!/usr/bin/env python3
"""t4608u: re-audit W8 completeness after Railway token injection. CERT=0."""

from __future__ import annotations

import json
import os
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "nfl"))
from audit_w8_input_completeness_t4605u import audit_week_inputs

PACK = ROOT / "data/ops/nfl-t4605u-w8-pipeline-restore/current_inputs"
SLATE = [
    "2026-W08-CAR@GB",
    "2026-W08-ARI@DAL",
    "2026-W08-ATL@TB",
    "2026-W08-BAL@BUF",
    "2026-W08-CLE@PIT",
    "2026-W08-IND@JAX",
    "2026-W08-LV@NYJ",
    "2026-W08-MIN@DET",
    "2026-W08-TEN@CIN",
    "2026-W08-LAC@LAR",
    "2026-W08-KC@DEN",
    "2026-W08-NE@MIA",
    "2026-W08-PHI@WAS",
    "2026-W08-CHI@SEA",
]


def _write_0444(path: Path, blob: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.chmod(stat.S_IWUSR | stat.S_IRUSR)
    path.write_bytes(blob)
    path.chmod(0o444)


def main() -> int:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    report = audit_week_inputs(
        season=2026,
        week=8,
        depth_path=PACK / "nfl_depth_chart_2026_w8.json",
        injury_paths=[PACK / "nfl_injuries_2026_w7_designated.json"],
        efficiency_path=PACK / "nfl_team_efficiency_backbone_2026_inseason_w7.json",
        slate_game_ids=SLATE,
        now_utc=now,
    )
    report["ticket"] = "t4608u"
    report["authority"] = {
        "decision_sha256": "5357266707b5555e96b746dce91435f862884db92b2124215f0d65d9ac435904",
        "cos_order_sha256": "889fd7643226953bb6bd7d0eb867a157abe840c45966b4df5537249f8c1f16ad",
        "parent_decision_sha256": "e65b9c7781a2f120dc6b6c0c1d171cce3b5daae31577edfcbc4a99eccff3d69a",
        "prior_access_blocker_sha256": "125b264a2456d2701924f01e44c8ea18c892775bd2e10eeadd93bbca979a6065",
        "prior_completeness_sha256": "fd2fa3d91dba09057be7a949e0a665e496cbda1e1a045b4e8e9517de7a3c1bf7",
    }
    dests = [
        ROOT / "data/ops/nfl-t4608u-w8-depth-db-token-unblock",
        ROOT
        / "data/ops/nfl-model-forecast-emit-t4559u/research_runs"
        / f"nfl-w8-2026-t4608u-token-{now.strftime('%Y%m%dT%H%M%SZ')}",
    ]
    blob = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode()
    for dest in dests:
        _write_0444(dest / "completeness.json", blob)
        print(
            json.dumps(
                {
                    "path": str(dest.relative_to(ROOT) if dest.is_relative_to(ROOT) else dest),
                    "completeness_sha256": report["input_completeness_sha256"],
                    "completeness_sha8": report["input_completeness_sha256"][:8],
                    "ok": report["ok"],
                    "passed": report["passed"],
                    "failing": report["failing_components"],
                    "RAILWAY_TOKEN": "SET" if os.environ.get("RAILWAY_TOKEN") else "UNSET",
                    "RAILWAY_TOKEN_length": len(os.environ.get("RAILWAY_TOKEN") or ""),
                },
                indent=2,
            )
        )
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
