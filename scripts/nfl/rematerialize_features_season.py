#!/usr/bin/env python3
"""Rematerialize nfl_player_projection_features_weekly for a season.

Requires existing nfl_dp_player_usage_weekly rows. Does not re-ingest nflverse.
"""

from __future__ import annotations

import argparse
import os
import sys
import time

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, os.path.join(ROOT, "services", "model-service"))
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge")

from data_platform_nfl.ingest import materialize_player_projection_features  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--week", type=int, default=None)
    parser.add_argument("--replace", action="store_true", default=True)
    args = parser.parse_args()
    t0 = time.time()
    out = materialize_player_projection_features(
        seasons=[int(args.season)],
        week=int(args.week) if args.week is not None else None,
        replace_existing=bool(args.replace),
    )
    print({"elapsed_s": round(time.time() - t0, 1), "result": out})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
