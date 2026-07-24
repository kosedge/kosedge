#!/usr/bin/env python3
"""Backfill MLB outcomes + historical re-sim for holdout densify (target n≥120).

Requires:
  DATABASE_URL
  MLB_ALLOW_HISTORICAL_SIM=true

Usage:
  MLB_ALLOW_HISTORICAL_SIM=true PYTHONPATH=services/model-service \
    python scripts/mlb/backfill_outcomes_and_resim.py \
      --start-date 2026-05-20 --end-date 2026-07-17 --max-games 400 --force-resim
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("MLB_ALLOW_HISTORICAL_SIM", "true")

from src.tasks import backfill_mlb_historical_resim  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="MLB outcomes + historical re-sim holdout densify")
    ap.add_argument("--start-date", default=None)
    ap.add_argument("--end-date", default=None)
    ap.add_argument("--max-games", type=int, default=200)
    ap.add_argument("--simulations", type=int, default=2000)
    ap.add_argument("--model-version", default="mlb-v1-pa-sim")
    ap.add_argument(
        "--force-resim",
        action="store_true",
        help="Delete existing projections in-window and re-sim with current PA-sim features",
    )
    ap.add_argument(
        "--skip-outcomes-pull",
        action="store_true",
        help="Skip MLB Stats API outcomes pull (use existing mlb_market_outcomes)",
    )
    args = ap.parse_args()

    result = backfill_mlb_historical_resim(
        start_date=args.start_date,
        end_date=args.end_date,
        max_games=args.max_games,
        simulations=args.simulations,
        model_version=args.model_version,
        force_resim=bool(args.force_resim),
        skip_outcomes_pull=bool(args.skip_outcomes_pull or args.force_resim),
    )
    print(json.dumps(result, indent=2, default=str))
    holdout_n = int((result.get("holdout") or {}).get("sample_size") or 0)
    print(f"holdout_n={holdout_n} target=120 ok={holdout_n >= 120}")
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
