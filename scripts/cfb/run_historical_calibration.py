#!/usr/bin/env python3
"""Run CFB hierarchical engine historical calibration vs closing lines.

Data (free, no Odds API credits):
  SportsDataverse espn_cfb_betting + team_box + linescores
  Prior-year cfb_ratings adj EPA → efficiency proxy

Writes:
  data/ops/cfb-historical-calibration-YYYYMMDD/
    before_metrics.json / after_metrics.json / summary.json
    games_sample.json (first 50 graded rows)
  data/ops/cfb-historical-calibration-YYYYMMDD.md

Usage:
  PYTHONPATH=services/model-service \\
    python scripts/cfb/run_historical_calibration.py --phase before
  # (apply knob changes)
  PYTHONPATH=services/model-service \\
    python scripts/cfb/run_historical_calibration.py --phase after
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.cfb_season_engine.historical_calibration import (  # noqa: E402
    run_historical_backtest,
)
from src.services.cfb_season_engine import priors as P  # noqa: E402


def _round_metrics(obj: Any) -> Any:
    if isinstance(obj, float):
        return round(obj, 4)
    if isinstance(obj, dict):
        return {k: _round_metrics(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_round_metrics(v) for v in obj]
    return obj


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, default=str)
        fh.write("\n")


def main() -> int:
    ap = argparse.ArgumentParser(description="CFB historical closing-line calibration")
    ap.add_argument(
        "--phase",
        choices=("before", "after", "both"),
        default="after",
        help="Label for this run's metrics artifact",
    )
    ap.add_argument(
        "--seasons",
        default="2022,2023,2024,2025",
        help="Comma-separated seasons to grade",
    )
    ap.add_argument(
        "--stamp",
        default=date.today().strftime("%Y%m%d"),
        help="Artifact folder stamp YYYYMMDD",
    )
    args = ap.parse_args()
    seasons = [int(x.strip()) for x in args.seasons.split(",") if x.strip()]
    out_dir = ROOT / "data" / "ops" / f"cfb-historical-calibration-{args.stamp}"
    cache_dir = out_dir / "cache"
    out_dir.mkdir(parents=True, exist_ok=True)

    phases = ["before", "after"] if args.phase == "both" else [args.phase]
    results: Dict[str, Any] = {}
    for phase in phases:
        print(f"== running {phase} backtest seasons={seasons} ==")
        payload = run_historical_backtest(seasons=seasons, cache_dir=cache_dir)
        rows = payload.pop("rows")
        slim = {
            "phase": phase,
            "engine_version": P.ENGINE_VERSION,
            "calibration_tag": P.CALIBRATION_TAG,
            "load": payload["load"],
            "efficiency": payload["efficiency"],
            "priors_snapshot": payload["priors_snapshot"],
            "metrics": _round_metrics(payload["metrics"]),
        }
        _write_json(out_dir / f"{phase}_metrics.json", slim)
        _write_json(out_dir / f"{phase}_games_sample.json", rows[:50])
        results[phase] = slim
        overall = slim["metrics"]["overall"]
        print(
            f"  n={overall.get('n')} "
            f"spread_close_mae={overall.get('spread_vs_close_mae')} "
            f"total_close_mae={overall.get('total_vs_close_mae')} "
            f"ats={overall.get('ats_hit_rate')} "
            f"ou={overall.get('ou_hit_rate')} "
            f"brier={overall.get('brier_home_wp')}"
        )

    summary = {
        "stamp": args.stamp,
        "engine_version": P.ENGINE_VERSION,
        "calibration_tag": P.CALIBRATION_TAG,
        "phases": {k: v["metrics"]["overall"] for k, v in results.items()},
        "slices_after": (results.get("after") or results.get("before") or {})
        .get("metrics", {})
        .get("slices"),
        "artifact_dir": str(out_dir.relative_to(ROOT)),
    }
    _write_json(out_dir / "summary.json", _round_metrics(summary))
    print(json.dumps(_round_metrics(summary), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
