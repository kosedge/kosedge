#!/usr/bin/env python3
"""Package nflverse depth snapshots for Phase 3 historical replay (no look-ahead).

Writes:
  services/model-service/src/services/nfl_season_engine/data/historical/
    nfl_depth_chart_<season>_w1.json

Cutoff rules are enforced in
``src.services.nfl_season_engine.historical_replay.package_historical_depth_rows``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MS = ROOT / "services" / "model-service"
sys.path.insert(0, str(MS))

from src.services.nfl_season_engine.historical_replay import (  # noqa: E402
    DEFAULT_HIST_DEPTH_DIR,
    write_historical_depth_pack,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--seasons",
        default="2019-2025",
        help="Comma list or start-end range (default 2019-2025)",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=ROOT / "data" / "ops" / "nfl-phase3-depth-cache",
    )
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_HIST_DEPTH_DIR)
    args = parser.parse_args(argv)

    seasons: list[int] = []
    for part in str(args.seasons).split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part and part.count("-") == 1:
            a, b = part.split("-")
            seasons.extend(range(int(a), int(b) + 1))
        else:
            seasons.append(int(part))

    written = []
    for season in seasons:
        path = write_historical_depth_pack(
            season, cache_dir=args.cache_dir, out_dir=args.out_dir
        )
        payload = json.loads(path.read_text(encoding="utf-8"))
        written.append(
            {
                "season": season,
                "path": str(path),
                "snapshot_id": payload.get("snapshot_id"),
                "rows": payload.get("row_count"),
                "full_skill_starter_teams": payload.get("full_skill_starter_teams"),
                "cutoff_rule": payload.get("cutoff_rule"),
            }
        )
        print(json.dumps(written[-1]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
