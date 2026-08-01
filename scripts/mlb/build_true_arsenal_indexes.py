#!/usr/bin/env python3
"""Build true pitch-type arsenal + team batter-family as-of indexes from Statcast CSVs."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SVC = REPO / "services" / "model-service"
# Prefer repo-root CSVs for rebuild; indexes also mirrored into service data/.
os.environ.setdefault(
    "MLB_STATCAST_CACHE_DIR",
    str(REPO / "data" / "mlb" / "statcast_cache"),
)
sys.path.insert(0, str(SVC))

from src.services.mlb_pitch_matchup import (  # noqa: E402
    build_true_arsenal_indexes_from_cache,
)
from src.services.mlb_statcast_stuff import CACHE_DIR  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", type=int, default=2026)
    ap.add_argument("--through", type=str, default="2026-07-16")
    args = ap.parse_args()
    through = date.fromisoformat(args.through)
    print(f"CACHE_DIR={CACHE_DIR}")
    paths = build_true_arsenal_indexes_from_cache(season=int(args.season), through=through)
    for k, p in paths.items():
        size = p.stat().st_size if p.exists() else 0
        print(f"{k}: {p} ({size} bytes)")
    svc_dir = SVC / "data" / "mlb" / "statcast_cache" / str(args.season)
    for name in (
        "pitcher_arsenal_asof_index.json",
        "team_batter_family_asof_index.json",
    ):
        target = svc_dir / name
        print(f"service_mirror {name}: exists={target.exists()} size={target.stat().st_size if target.exists() else 0}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
