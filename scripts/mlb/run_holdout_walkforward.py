#!/usr/bin/env python3
"""Run MLB walkforward holdout and print n / Brier / MAE.

Usage:
  PYTHONPATH=services/model-service \
    python scripts/mlb/run_holdout_walkforward.py --lookback-days 180
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

from src.tasks import run_mlb_quality_grading, run_mlb_walkforward_backtest  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="MLB holdout walkforward report")
    ap.add_argument("--lookback-days", type=int, default=180)
    # 28 matches backfill_mlb_historical_resim; 45 needs ~45+ calendar days of joinable data.
    ap.add_argument("--training-days", type=int, default=28)
    ap.add_argument("--step-days", type=int, default=7)
    ap.add_argument("--model-version", default="mlb-v1-pa-sim")
    ap.add_argument("--with-quality", action="store_true")
    args = ap.parse_args()

    holdout = run_mlb_walkforward_backtest(
        model_version=args.model_version,
        lookback_days=args.lookback_days,
        training_days=args.training_days,
        step_days=args.step_days,
        apply_calibration=True,
    )
    payload = {"holdout": holdout, "holdout_target_n": 120, "holdout_n_ok": int(holdout.get("sample_size") or 0) >= 120}
    if args.with_quality:
        payload["quality"] = run_mlb_quality_grading(
            model_version=args.model_version,
            lookback_days=args.lookback_days,
        )
    print(json.dumps(payload, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
