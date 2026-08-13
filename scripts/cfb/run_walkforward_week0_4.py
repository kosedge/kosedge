#!/usr/bin/env python3
"""Walk-forward CFB research fair vs lake closes (Week 0–4 emphasis).

Usage:
  python scripts/cfb/run_walkforward_week0_4.py
  python scripts/cfb/run_walkforward_week0_4.py --seasons 2024,2025
  python scripts/cfb/run_walkforward_week0_4.py --limit 20
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.cfb_warehouse.paths import clean_dir  # noqa: E402
from src.services.cfb_warehouse.walkforward import (  # noqa: E402
    build_program_priors,
    example_row,
    index_week_efficiency,
    summarize,
    walkforward_games,
)


def _read(path: Path):
    import pandas as pd

    return pd.read_parquet(path).to_dict(orient="records")


def _parse_seasons(raw: str) -> list[int]:
    raw = raw.strip()
    if not raw:
        return []
    if "-" in raw and "," not in raw:
        a, b = raw.split("-", 1)
        return list(range(int(a), int(b) + 1))
    return [int(s.strip()) for s in raw.split(",") if s.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seasons", default="2020-2025")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--repo-fallback", action="store_true")
    parser.add_argument("--example-id", default="401628323")
    args = parser.parse_args(argv)
    prefer_hd = not args.repo_fallback
    clean = clean_dir(prefer_hd=prefer_hd)
    games_path = clean / "games.parquet"
    closes_path = clean / "closing_lines.parquet"
    week_path = clean / "efficiency" / "team_week_efficiency.parquet"
    season_path = clean / "efficiency" / "team_season_efficiency.parquet"
    missing = [p for p in (games_path, closes_path, week_path, season_path) if not p.is_file()]
    if missing:
        print(f"Missing {missing}", file=sys.stderr)
        return 1

    seasons = _parse_seasons(args.seasons) or list(range(2020, 2026))
    games = [g for g in _read(games_path) if int(g.get("season") or 0) in set(seasons)]
    closes = _read(closes_path)
    by_id = {str(c.get("game_id")): c for c in closes}
    joined = []
    unmatched = 0
    for g in games:
        c = by_id.get(str(g.get("game_id")))
        row = dict(g)
        if not c:
            unmatched += 1
            row.setdefault("close_spread_home", None)
            joined.append(row)
            continue
        for k in (
            "close_spread_home",
            "open_spread_home",
            "close_total",
            "open_total",
            "book",
            "source",
            "line_fidelity",
            "close_captured_at",
            "available_at",
            "n_lake_snaps",
        ):
            if c.get(k) is not None:
                row[k] = c.get(k)
        joined.append(row)
    if args.limit and args.limit > 0:
        joined = joined[: args.limit]

    finals = _read(season_path)
    priors = build_program_priors(finals, seasons)
    eff_idx = index_week_efficiency(_read(week_path))
    graded = walkforward_games(joined, priors=priors, eff_idx=eff_idx)
    summary = summarize(graded)
    summary["unmatched_close_games"] = unmatched
    summary["n_joined"] = len(joined)
    summary["example"] = example_row(graded, args.example_id)
    out_dir = clean / "walkforward"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "week0_4_summary.json").write_text(
        json.dumps(summary, indent=2, default=str) + "\n"
    )
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
