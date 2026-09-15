#!/usr/bin/env python3
"""Replay NFL projected-point components for the 2026-09-15 regression track.

Read-only. Does not rematerialize, write Railway, or flip Coming soon.

  PYTHONPATH=services/model-service python3 scripts/nfl/nfl_projected_points_decompose.py
  PYTHONPATH=services/model-service python3 scripts/nfl/nfl_projected_points_decompose.py --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MS_SRC = ROOT / "services" / "model-service"
if str(MS_SRC) not in sys.path:
    sys.path.insert(0, str(MS_SRC))

from src.services.nfl_regression_diagnose import (  # noqa: E402
    LOCKED_SCORING,
    locked_scoring_snapshot,
    replay_focus_matchups,
)


def _print_human(rows: list) -> None:
    scoring = locked_scoring_snapshot()
    print("NFL projected-points decompose (investigation only)")
    print(f"framework {scoring['framework_version']} prior_total={scoring['base_total_points']} HFA={scoring['home_field_points']}")
    print("production_promote=false  Coming soon stays")
    print()
    for row in rows:
        print(f"=== {row['key']}  W{row['week']} ===")
        live = row["live"]
        print(
            f"  live July-31  model_spread={live['model_spread_home']:+.2f}  "
            f"kei_spread={live['kei_spread_home']:+.2f}  "
            f"model_total={live['model_total']:.2f}  kei_total={live['kei_total']:.2f}"
        )
        if row.get("actual"):
            act = row["actual"]
            print(f"  actual        {act['away']}-{act['home']}  total={act['total']}")
        for label in ("epa", "record"):
            block = row[label]
            print(
                f"  {label:6s}       spread_home={block['spread_home']:+.2f}  "
                f"total={block['predicted_total']:.2f}  "
                f"H {block['expected_home_points']:.1f} / A {block['expected_away_points']:.1f}  "
                f"src={block['strength_source']}"
            )
            comps = block["components"]
            for name in (
                "base_efficiency",
                "home_field_advantage",
                "injuries_depth",
                "personnel_efficiency",
                "rest_travel",
            ):
                item = comps.get(name) or {}
                print(
                    f"           {name:24s}  margin={item.get('margin_points', 0):+.3f}  "
                    f"total={item.get('total_points', 0):+.3f}"
                )
        d = row["deltas"]
        print(
            f"  Δ epa−live_spread={d['epa_spread_minus_live_model']}  "
            f"record−live_spread={d['record_spread_minus_live_model']}  "
            f"record−epa_spread={d['record_spread_minus_epa_spread']}"
        )
        print()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args()
    rows = replay_focus_matchups()
    payload = {
        "production_promote": False,
        "locked_scoring": LOCKED_SCORING,
        "live_scoring": locked_scoring_snapshot(),
        "matchups": rows,
    }
    if args.json:
        json.dump(payload, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    else:
        _print_human(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
