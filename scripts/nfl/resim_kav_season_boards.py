#!/usr/bin/env python3
"""Re-sim NFL boards with KAV-wired market path for a season window.

Deletes prior projections for the same model_version/window so grading's
DISTINCT ON (game_id ORDER BY created_at DESC) cannot pick stale rows when
kickoff-minus-buffer timestamps collide.

Usage:
  NFL_KAV_RESIM_SEASON=2025 NFL_KAV_RESIM_SIMS=1000 \\
    DATABASE_URL=postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge \\
    .venv/bin/python scripts/nfl/resim_kav_season_boards.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))
os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge"
)

from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from src.tasks import DEFAULT_NFL_MODEL_VERSION, run_nfl_market_simulations  # noqa: E402

OUT = ROOT / "data" / "ops" / "nfl-kav-resim-summary.json"


def main() -> int:
    season = int(os.getenv("NFL_KAV_RESIM_SEASON", "2025"))
    simulations = int(os.getenv("NFL_KAV_RESIM_SIMS", "1000"))
    min_date = os.getenv("NFL_KAV_RESIM_MIN_DATE", f"{season}-09-01")
    model_version = os.getenv("NFL_MODEL_VERSION", DEFAULT_NFL_MODEL_VERSION)
    # NFL_KAV_RESIM_RESUME=1 skips dates that already have >=simulations rows
    # written with pipeline_run_at in the last NFL_KAV_RESIM_RESUME_HOURS hours.
    resume = os.getenv("NFL_KAV_RESIM_RESUME", "0") == "1"
    resume_hours = int(os.getenv("NFL_KAV_RESIM_RESUME_HOURS", "12"))
    delete_prior = os.getenv("NFL_KAV_RESIM_DELETE_PRIOR", "0" if resume else "1") == "1"

    url = os.environ["DATABASE_URL"]
    if url.startswith("postgresql://") and "+psycopg" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    engine = create_engine(url)
    Session = sessionmaker(bind=engine)
    session = Session()

    deleted = 0
    if delete_prior:
        deleted = session.execute(
            text(
                """
                DELETE FROM nfl_market_projections p
                USING games g, seasons s, leagues l
                WHERE p.game_id = g.id
                  AND g.season_id = s.id
                  AND s.league_id = l.id
                  AND l.code = 'nfl'
                  AND s.season_year = :season
                  AND g.game_date >= CAST(:min_date AS date)
                  AND p.model_version = :model_version
                """
            ),
            {"season": season, "min_date": min_date, "model_version": model_version},
        ).rowcount
        session.commit()

    dates = [
        str(r[0])
        for r in session.execute(
            text(
                """
                SELECT DISTINCT g.game_date::text
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
    skipped = []
    if resume:
        done = {
            str(r[0])
            for r in session.execute(
                text(
                    """
                    SELECT DISTINCT g.game_date::text
                    FROM nfl_market_projections p
                    JOIN games g ON g.id = p.game_id
                    JOIN seasons s ON s.id = g.season_id
                    JOIN leagues l ON l.id = s.league_id
                    WHERE l.code = 'nfl'
                      AND s.season_year = :season
                      AND g.game_date >= CAST(:min_date AS date)
                      AND p.model_version = :model_version
                      AND p.simulation_count >= :simulations
                      AND COALESCE(
                        (p.projection->'audit'->>'pipeline_run_at')::timestamptz,
                        p.created_at
                      ) > NOW() - make_interval(hours => :hours)
                    """
                ),
                {
                    "season": season,
                    "min_date": min_date,
                    "model_version": model_version,
                    "simulations": simulations,
                    "hours": resume_hours,
                },
            ).fetchall()
        }
        skipped = [d for d in dates if d in done]
        dates = [d for d in dates if d not in done]
    session.close()

    print(
        f"resim season={season} min_date={min_date} days={len(dates)} "
        f"skipped_resume={len(skipped)} sims={simulations} deleted={deleted} "
        f"resume={resume}",
        flush=True,
    )
    t0 = time.time()
    total_games = 0
    total_inserted = 0
    results = []
    for i, day in enumerate(dates, 1):
        result = run_nfl_market_simulations(
            game_date=day,
            simulations=simulations,
            model_version=model_version,
            include_completed_games=True,
            projection_created_at_mode="kickoff_minus_buffer",
            kickoff_buffer_minutes=30,
        )
        total_games += int(result.get("games_processed") or 0)
        total_inserted += int(result.get("projections_inserted") or 0)
        results.append({"game_date": day, **result})
        print(f"[{i}/{len(dates)}] {day}: {result}", flush=True)

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "season": season,
        "min_date": min_date,
        "simulations": simulations,
        "model_version": model_version,
        "deleted_prior_projections": int(deleted or 0),
        "days": len(dates),
        "games_processed": total_games,
        "projections_inserted": total_inserted,
        "elapsed_sec": round(time.time() - t0, 1),
        "results": results,
    }
    OUT.write_text(json.dumps(summary, indent=2, default=str) + "\n")
    print(json.dumps({k: summary[k] for k in summary if k != "results"}, indent=2), flush=True)
    print(f"wrote {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
