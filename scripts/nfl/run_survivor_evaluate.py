#!/usr/bin/env python3
"""CLI: survivor-pool week evaluation on the hierarchical season engine.

Examples
--------
# Offline demo — Week 5 picks with KC/BUF already used
python scripts/nfl/run_survivor_evaluate.py --demo --week 5 \\
  --already-used KC,BUF --n-sims 300 --seed 42

# With optional injury paths
python scripts/nfl/run_survivor_evaluate.py --demo --week 6 \\
  --already-used KC,BUF,DET \\
  --injury-paths '[{"player_name":"C.McCaffrey","team":"SF","status":"out","week_start":4,"week_end":8}]'
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))


def _sqlalchemy_database_url(raw: str) -> str:
    url = (raw or "").strip().strip('"').strip("'")
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    return url


def _load_injury_paths(raw: str) -> List[Any]:
    from src.services.nfl_season_engine import parse_injury_paths

    text = (raw or "").strip()
    if not text:
        return []
    path = Path(text)
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
    else:
        payload = json.loads(text)
    if isinstance(payload, dict) and "injury_paths" in payload:
        payload = payload["injury_paths"]
    if not isinstance(payload, list):
        raise SystemExit("--injury-paths must be a JSON array or {injury_paths: [...]}")
    return parse_injury_paths(payload)


def _parse_used(raw: str) -> List[str]:
    return [p.strip().upper() for p in (raw or "").split(",") if p.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="NFL survivor-pool season-engine evaluate")
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--week", type=int, required=True, help="Target evaluation week")
    parser.add_argument("--n-sims", type=int, default=300)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--demo", action="store_true", help="Force offline demo universe")
    parser.add_argument(
        "--already-used",
        default="",
        help="Comma-separated team codes already picked (e.g. KC,BUF)",
    )
    parser.add_argument("--injury-paths", default="", help="JSON array/file of injury paths")
    parser.add_argument("--top-n", type=int, default=12)
    parser.add_argument(
        "--out-dir",
        default="",
        help="Output directory (default data/ops/nfl-survivor-<ts>)",
    )
    args = parser.parse_args()

    from src.services.nfl_season_engine import (  # noqa: E402
        build_demo_universe,
        evaluate_survivor,
        load_universe_from_db,
    )

    injury_paths = _load_injury_paths(args.injury_paths)
    already_used = _parse_used(args.already_used)

    universe = None
    mode = "demo"
    if not args.demo and os.getenv("DATABASE_URL"):
        try:
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker

            os.environ["DATABASE_URL"] = _sqlalchemy_database_url(os.environ["DATABASE_URL"])
            engine = create_engine(os.environ["DATABASE_URL"])
            Session = sessionmaker(bind=engine)
            session = Session()
            try:
                universe = load_universe_from_db(
                    session, season=args.season, as_of_week=args.week
                )
                mode = "db"
            finally:
                session.close()
        except Exception as exc:  # pragma: no cover
            print(f"DB load failed ({exc}); falling back to demo universe")

    if universe is None:
        universe = build_demo_universe(season=args.season)
        mode = "demo"

    print(
        f"Survivor eval mode={mode} season={universe.season} week={args.week} "
        f"n_sims={args.n_sims} already_used={already_used or '(none)'}"
    )
    result = evaluate_survivor(
        universe,
        week=args.week,
        n_sims=args.n_sims,
        seed=args.seed,
        already_used=already_used,
        injury_paths=injury_paths,
        top_n=args.top_n,
    )

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = (
        Path(args.out_dir)
        if args.out_dir
        else ROOT / "data" / "ops" / f"nfl-survivor-{ts}"
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = result.to_dict()
    payload["mode"] = mode
    payload["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
    out_path = out_dir / "survivor_evaluate.json"
    out_path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")

    print(f"engine_version={result.engine_version}")
    print("Top ranked remaining picks (pick_now_score):")
    for i, row in enumerate(result.ranked_picks[: args.top_n], 1):
        ha = row.get("home_away") or "?"
        opp = row.get("opponent") or "?"
        print(
            f"  {i:2}. {row['team']:3} vs {opp:3} ({ha})  "
            f"wp={row['win_rate']:.3f}  save={row['save_score']:.3f}  "
            f"pick_now={row['pick_now_score']:.3f}"
        )
    print(f"Wrote → {out_path}")


if __name__ == "__main__":
    main()
