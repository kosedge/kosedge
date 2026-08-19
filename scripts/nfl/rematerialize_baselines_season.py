#!/usr/bin/env python3
"""Rematerialize 2025 weekly baselines after Phase 2 structural knob changes.

Runs ``materialize_nfl_player_baseline_projections`` for each week so the
local holdout diagnosis reads the new shared means. Does not flip
NFL_WEEKLY_PROPS_LIVE.
"""

from __future__ import annotations

import argparse
import os
import sys
import time

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, os.path.join(ROOT, "services", "model-service"))
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge")

from src.tasks import materialize_nfl_player_baseline_projections  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, default=2025)
    parser.add_argument("--week-start", type=int, default=1)
    parser.add_argument("--week-end", type=int, default=18)
    parser.add_argument("--model-version", default="nfl-player-v1")
    args = parser.parse_args()

    results = []
    t0 = time.time()
    for week in range(int(args.week_start), int(args.week_end) + 1):
        w0 = time.time()
        out = materialize_nfl_player_baseline_projections(
            season=int(args.season),
            week=int(week),
            model_version=str(args.model_version),
        )
        elapsed = time.time() - w0
        n = out.get("baselines_upserted") or out.get("upserted") or out
        print(f"week={week} ok elapsed={elapsed:.1f}s result={n}")
        results.append({"week": week, "result": out, "elapsed_s": round(elapsed, 2)})
    print(
        {
            "season": args.season,
            "weeks": f"{args.week_start}-{args.week_end}",
            "total_elapsed_s": round(time.time() - t0, 1),
            "n_weeks": len(results),
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
