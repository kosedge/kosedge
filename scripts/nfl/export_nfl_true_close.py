#!/usr/bin/env python3
"""Export kickoff-safe labeled open/close into the NFL parquet lake.

Sources: Aug-6 enterprise jsonl (DK/FD timestamps) + nflverse close as fill.
No Odds API. Does not overwrite path parquets.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge")

from sqlalchemy import create_engine, text  # noqa: E402

from src.services.nfl_warehouse.odds_lake import team_abbr  # noqa: E402
from src.services.nfl_warehouse.paths import ensure_lake_dir  # noqa: E402
from src.services.nfl_warehouse.true_close import export_true_close_lake  # noqa: E402


def _kickoffs_from_path_lake() -> dict:
    import pandas as pd

    kick: dict = {}
    lake = ensure_lake_dir(prefer_hd=True)
    for path in sorted(lake.glob("snapshots-*.parquet")):
        if "trueclose" in path.name:
            continue
        df = pd.read_parquet(path)
        wanted = [
            c
            for c in ("game_date", "home", "away", "home_abbr", "away_abbr", "kickoff", "commence_time")
            if c in df.columns
        ]
        if not wanted:
            continue
        for rec in df.loc[:, wanted].itertuples(index=False):
            row = rec._asdict()
            day = str(row.get("game_date") or "")[:10]
            home = team_abbr(str(row.get("home") or row.get("home_abbr") or ""))
            away = team_abbr(str(row.get("away") or row.get("away_abbr") or ""))
            kickoff = row.get("kickoff") or row.get("commence_time")
            if day and home and away and kickoff:
                kick[(day, home, away)] = kickoff
    return kick


def _games() -> list:
    engine = create_engine(os.environ["DATABASE_URL"])
    print("loading path-lake kickoffs...", flush=True)
    kick = _kickoffs_from_path_lake()
    print(f"kickoff_keys={len(kick)}", flush=True)
    with engine.connect() as conn:
        rows = list(
            conn.execute(
                text(
                    """
                    SELECT season, week, game_date, home_team, away_team,
                           spread_line, total_line, home_score, away_score
                    FROM nfl_dp_schedules
                    WHERE season BETWEEN 2013 AND 2026
                    """
                )
            )
        )
    games = []
    for r in rows:
        day = str(r.game_date or "")[:10]
        home = team_abbr(str(r.home_team))
        away = team_abbr(str(r.away_team))
        games.append(
            {
                "season": int(r.season) if r.season is not None else None,
                "week": r.week,
                "game_date": day,
                "home_team": home,
                "away_team": away,
                "spread_line": r.spread_line,
                "total_line": r.total_line,
                "kickoff": kick.get((day, home, away)),
            }
        )
    return games


def main() -> int:
    games = _games()
    print(f"schedule_games={len(games)}", flush=True)
    inv = export_true_close_lake(games=games, prefer_hd=True)
    print(json.dumps(inv, indent=2), flush=True)
    return 0 if inv.get("rows") else 1


if __name__ == "__main__":
    raise SystemExit(main())
