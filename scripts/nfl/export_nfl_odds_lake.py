#!/usr/bin/env python3
"""Export NFL mainlines from HD SQLite → parquet lake (no Odds API, no rewrite).

Usage:
  PYTHONPATH=services/model-service \\
    python scripts/nfl/export_nfl_odds_lake.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.nfl_warehouse.odds_lake import (  # noqa: E402
    export_odds_lake,
    export_odds_lake_from_csv,
)
from src.services.nfl_warehouse.paths import HD_ROOT  # noqa: E402


def main() -> int:
    os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
    csv_path = HD_ROOT / "clean" / "odds" / "americanfootball_nfl" / "open_close" / "lines.csv"
    if csv_path.is_file():
        print(f"exporting from csv {csv_path}", flush=True)
        inv = export_odds_lake_from_csv(csv_path, prefer_hd=True)
    else:
        print("csv missing; falling back to sqlite", flush=True)
        inv = export_odds_lake(prefer_hd=True)
    print(json.dumps(inv, indent=2), flush=True)
    return 0 if inv.get("rows", 0) or inv.get("status") == "empty" else 1


if __name__ == "__main__":
    raise SystemExit(main())
