#!/usr/bin/env python3
"""Re-run NFL market simulations for a season after totals-level fixes."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

# Prefer apps/web env if present.
env_local = ROOT / "apps" / "web" / ".env.local"
if env_local.exists():
    for line in env_local.read_text().splitlines():
        if line.startswith("DATABASE_URL=") and "DATABASE_URL" not in os.environ:
            os.environ["DATABASE_URL"] = line.split("=", 1)[1].strip().strip('"').strip("'")
        if line.startswith("ODDS_API_KEY=") and "ODDS_API_KEY" not in os.environ:
            os.environ["ODDS_API_KEY"] = line.split("=", 1)[1].strip().strip('"').strip("'")

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge")

from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from src.tasks import run_nfl_market_simulations  # noqa: E402


def main() -> int:
    season = int(os.getenv("NFL_RESIM_SEASON", "2026"))
    simulations = int(os.getenv("NFL_RESIM_SIMS", "4000"))
    min_date = os.getenv("NFL_RESIM_MIN_DATE", f"{season}-09-01")

    db_url = os.environ["DATABASE_URL"]
    if db_url.startswith("postgresql://") and "+psycopg" not in db_url:
        db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    dates = [
        str(r[0])
        for r in session.execute(
            text(
                """
                SELECT DISTINCT g.game_date
                FROM games g
                JOIN seasons s ON s.id = g.season_id
                JOIN leagues l ON l.id = s.league_id
                WHERE l.code = 'nfl'
                  AND s.season_year = :season
                  AND g.game_date >= CAST(:min_date AS date)
                ORDER BY 1
                """
            ),
            {"season": season, "min_date": min_date},
        ).fetchall()
    ]
    session.close()

    summary = {"season": season, "simulations": simulations, "days": len(dates), "results": []}
    total_games = 0
    total_inserted = 0
    for i, day in enumerate(dates, 1):
        result = run_nfl_market_simulations(
            game_date=day,
            simulations=simulations,
            include_completed_games=True,
            projection_created_at_mode="kickoff_minus_buffer",
            kickoff_buffer_minutes=30,
        )
        total_games += int(result.get("games_processed") or 0)
        total_inserted += int(result.get("projections_inserted") or 0)
        summary["results"].append({"game_date": day, **result})
        print(f"[{i}/{len(dates)}] {day}: {result}", flush=True)

    summary["games_processed"] = total_games
    summary["projections_inserted"] = total_inserted

    # Post-resim board level check
    session = Session()
    level = dict(
        session.execute(
            text(
                """
                SELECT
                  COUNT(*) AS n,
                  ROUND(AVG(p.total_mean)::numeric, 2) AS avg_total,
                  ROUND(MIN(p.total_mean)::numeric, 2) AS min_total,
                  ROUND(MAX(p.total_mean)::numeric, 2) AS max_total
                FROM nfl_market_projections p
                JOIN games g ON g.id = p.game_id
                JOIN seasons s ON s.id = g.season_id
                WHERE s.season_year = :season
                  AND g.game_date >= CAST(:min_date AS date)
                  AND p.created_at > NOW() - INTERVAL '6 hours'
                """
            ),
            {"season": season, "min_date": min_date},
        )
        .mappings()
        .one()
    )
    session.close()
    summary["fresh_projection_level"] = level

    out = ROOT / "data" / "ops" / f"nfl-totals-resim-{season}.json"
    out.write_text(json.dumps(summary, indent=2, default=str) + "\n")
    print(
        json.dumps(
            {"games_processed": total_games, "inserted": total_inserted, "level": level},
            indent=2,
            default=str,
        )
    )
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
