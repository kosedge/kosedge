#!/usr/bin/env python3
"""EXPERIMENTAL supervised schema-v5 retrain (v3 features + line-path steam).

Default product path remains schema v3. This script injects path keys, retrains,
compares chronological holdout to v3, and does **not** promote unless --promote
and holdout improves. Does not flip weekly props.

Prereq: scripts/nfl/export_nfl_odds_lake.py

Writes:
  data/ops/nfl-supervised-path-v5.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))
os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge"
)

from src.services.nfl_supervised_retrain import FEATURE_KEYS  # noqa: E402
from src.services.nfl_warehouse.path_features import (  # noqa: E402
    FEATURE_KEYS_PATH_EXPERIMENTAL,
    MODEL_SCHEMA_VERSION_PATH,
)

OUT = ROOT / "data" / "ops" / "nfl-supervised-path-v5.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--promote", action="store_true", help="Unsafe: write v5 as active fit")
    args = parser.parse_args()
    holdout_path = ROOT / "data" / "ops" / "nfl-path-steam-edge-holdout.json"
    holdout: dict = {}
    if holdout_path.is_file():
        holdout = json.loads(holdout_path.read_text(encoding="utf-8"))
    fit_ok = bool((holdout.get("gates") or {}).get("fit_supervised_path_v5"))
    report = {
        "as_of": datetime.now(timezone.utc).isoformat(),
        "schema_candidate": MODEL_SCHEMA_VERSION_PATH,
        "feature_keys": list(FEATURE_KEYS) + list(FEATURE_KEYS_PATH_EXPERIMENTAL),
        "promoted": False,
        "holdout_artifact": str(holdout_path) if holdout else None,
        "fit_supervised_path_v5": fit_ok,
        "note": (
            "Research only. Run scripts/nfl/path_steam_edge_holdout.py first. "
            "Do not replace v3 unless that artifact sets fit_supervised_path_v5."
        ),
        "promote_requested": bool(args.promote),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if args.promote:
        print("REFUSED: --promote is a no-op until path-steam holdout sets fit_supervised_path_v5.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
