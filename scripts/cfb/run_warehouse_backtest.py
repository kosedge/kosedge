#!/usr/bin/env python3
"""Skeleton CFB warehouse backtest — join games → close → result; optional fairs.

Usage:
  python scripts/cfb/run_warehouse_backtest.py
  python scripts/cfb/run_warehouse_backtest.py --limit 5
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.cfb_warehouse.backtest import join_game_close_result, run_harness  # noqa: E402
from src.services.cfb_warehouse.paths import clean_dir  # noqa: E402


def _read_parquet(path: Path):
    import pandas as pd

    return pd.read_parquet(path).to_dict(orient="records")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--repo-fallback", action="store_true")
    args = parser.parse_args(argv)
    clean = clean_dir(prefer_hd=not args.repo_fallback)
    games_path = clean / "games.parquet"
    closes_path = clean / "closing_lines.parquet"
    if not games_path.is_file() or not closes_path.is_file():
        print(f"Missing warehouse parquet under {clean}", file=sys.stderr)
        print("Run: python scripts/cfb/ingest_historical_warehouse.py", file=sys.stderr)
        return 1
    games = _read_parquet(games_path)
    closes = _read_parquet(closes_path)
    joined = join_game_close_result(games, closes)
    if args.limit and args.limit > 0:
        joined = joined[: args.limit]
    graded = run_harness(joined, fairs={})  # placeholder — no model fair
    sample = next((g for g in graded if g.get("close_spread_home") is not None), graded[0] if graded else {})
    print(
        json.dumps(
            {
                "n_joined": len(joined),
                "n_graded": len(graded),
                "with_close": sum(1 for g in graded if g.get("close_spread_home") is not None),
                "model_fair_present": sum(1 for g in graded if g.get("model_fair_present")),
                "sample": sample,
                "clean_dir": str(clean),
            },
            indent=2,
            default=str,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
