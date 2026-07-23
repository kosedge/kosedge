#!/usr/bin/env python3
"""Fit + evaluate market-residual prop correctors on graded records.

Does NOT flip PLAY_STAKE_ELIGIBLE. Writes a JSON report under data/ops/.

Usage:
  PYTHONPATH=services/model-service:.venv ... \
    python scripts/nfl/prop_market_residual_holdout.py \
      --records data/ops/nfl-player-prop-vegas-benchmark/raw_prop_records.json
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from src.services.nfl_prop_market_residual import (
    fit_residual_corrector,
    residual_holdout_metrics,
)


def _load_points(path: Path, market_key: str) -> List[Dict[str, Any]]:
    raw = json.loads(path.read_text())
    rows = raw if isinstance(raw, list) else raw.get("records") or raw.get("rows") or []
    out: List[Dict[str, Any]] = []
    for row in rows:
        if str(row.get("market_key") or row.get("market") or "") != market_key:
            continue
        try:
            out.append(
                {
                    "model_mean": float(row.get("model_mean") or row.get("pred") or row.get("blended_mean")),
                    "market_line": float(row.get("market_line") or row.get("line") or row.get("close")),
                    "actual": float(row.get("actual") or row.get("truth") or row.get("result")),
                }
            )
        except (TypeError, ValueError):
            continue
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", required=True)
    parser.add_argument(
        "--markets",
        default="pass_yds,rush_yds,rec_yds,receptions",
        help="Comma-separated market keys",
    )
    parser.add_argument("--fit-frac", type=float, default=0.70)
    parser.add_argument("--out-dir", default="data/ops/nfl-player-prop-vegas-benchmark")
    args = parser.parse_args()

    records_path = Path(args.records)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report: Dict[str, Any] = {
        "as_of": datetime.now(timezone.utc).isoformat(),
        "records": str(records_path),
        "markets": {},
        "note": "Research only — does not enable PLAY stake tags.",
    }

    for market in [m.strip() for m in str(args.markets).split(",") if m.strip()]:
        points = _load_points(records_path, market)
        if len(points) < 40:
            report["markets"][market] = {"status": "insufficient_n", "n": len(points)}
            continue
        cut = max(20, int(len(points) * float(args.fit_frac)))
        fit_pts = points[:cut]
        hold_pts = points[cut:]
        corrector = fit_residual_corrector(fit_pts, market_key=market, min_sample_size=40)
        metrics = residual_holdout_metrics(hold_pts, corrector=corrector)
        report["markets"][market] = {
            "fit_n": len(fit_pts),
            "hold_n": len(hold_pts),
            "beta": corrector.beta,
            "source": corrector.source,
            "holdout": metrics,
        }

    out_path = out_dir / "market_residual_holdout.json"
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True))
    print(json.dumps({"wrote": str(out_path), "markets": list(report["markets"].keys())}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
