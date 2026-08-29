#!/usr/bin/env python3
"""Local smoke: log CFB PLAY + LEAN, grade, print summary (JSONL backend)."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

# Allow running from repo root
ROOT = Path(__file__).resolve().parents[2]
MS = ROOT / "services" / "model-service"
sys.path.insert(0, str(MS))

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ["MODEL_TRACKER_BACKEND"] = "jsonl"


def main() -> int:
    from src.services.model_tracker.core import (
        close_pick,
        grade_pick,
        log_pick,
        status_payload,
        summary,
    )

    lake = Path(tempfile.mkdtemp(prefix="model_tracker_smoke_"))
    print("lake:", lake)

    play = log_pick(
        {
            "sport": "cfb",
            "season": 2026,
            "week": 0,
            "home_team": "TCU",
            "away_team": "UNC",
            "game_id": "401856766",
            "market_type": "spread",
            "side": "home",
            "line_at_publish": -3.5,
            "tag": "PLAY",
            "engine_version": "cfb-season-engine-v0.9-inseason",
            "kei_version": "cfb-kei-v1.0-2026w0",
            "edge_pts": 4.2,
            "created_by": "desk",
            "source": "manual",
        },
        lake_dir=lake,
    )
    lean = log_pick(
        {
            "sport": "cfb",
            "season": 2026,
            "week": 0,
            "home_team": "USC",
            "away_team": "SJSU",
            "market_type": "spread",
            "side": "home",
            "line_at_publish": -24.5,
            "tag": "LEAN",
            "engine_version": "cfb-season-engine-v0.9-inseason",
            "created_by": "desk",
            "source": "manual",
        },
        lake_dir=lake,
    )
    close_pick(play["id"], line_at_close=-6.5, lake_dir=lake)
    grade_pick(play["id"], home_score=31, away_score=24, lake_dir=lake)
    grade_pick(lean["id"], home_score=42, away_score=14, lake_dir=lake)

    s = summary(sport="cfb", season=2026, lake_dir=lake)
    st = status_payload(lake_dir=lake)
    print(json.dumps({"status": st, "summary_units": s["units"], "plays": s["plays"], "leans": s["leans"]}, indent=2))
    assert s["plays"]["wins"] == 1
    assert s["leans"]["wins"] == 1
    assert s["units"]["units_net"] > 0
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
