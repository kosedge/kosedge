#!/usr/bin/env python3
"""Rematerialize player box-score sims + prop edges for a season week range."""

from __future__ import annotations

import argparse
import os
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "services", "model-service"))
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--week-start", type=int, default=2)
    parser.add_argument("--week-end", type=int, default=18)
    parser.add_argument("--model-version", default="nfl-player-v1")
    args = parser.parse_args()

    from src.tasks import materialize_nfl_player_box_score_sims, materialize_nfl_player_props_edges

    t0 = time.time()
    for week in range(int(args.week_start), int(args.week_end) + 1):
        w0 = time.time()
        box = materialize_nfl_player_box_score_sims(season=int(args.season), week=week)
        print(
            f"box  w{week:02d} teams={box.get('teams_simulated')} "
            f"rows={box.get('player_rows_upserted')} in {time.time() - w0:.1f}s",
            flush=True,
        )
        p0 = time.time()
        props = materialize_nfl_player_props_edges(
            season=int(args.season),
            week=week,
            model_version=str(args.model_version),
        )
        print(
            f"props w{week:02d} edges={props.get('prop_edges_upserted')} "
            f"play={props.get('play_tagged')} watch={props.get('watch_tagged')} "
            f"in {time.time() - p0:.1f}s",
            flush=True,
        )
    print(f"DONE box+props {args.week_start}-{args.week_end} in {time.time() - t0:.1f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
