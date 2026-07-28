#!/usr/bin/env python3
"""Resume-safe 2025 KAV board re-sim (does not wipe completed days).

Skips game_dates that already have a projection with pipeline_run_at >= RUN_MARKER.
Writes progress to data/ops/nfl-kav-resim-2025-progress.json.
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
from src.tasks import DEFAULT_NFL_MODEL_VERSION, run_nfl_market_simulations  # noqa: E402

OUT = ROOT / "data" / "ops" / "nfl-kav-resim-2025-progress.json"
SUMMARY = ROOT / "data" / "ops" / "nfl-kav-resim-summary.json"
RUN_MARKER = os.getenv("NFL_KAV_RESIM_MARKER", "2026-07-28T15:00:00+00:00")


def _engine():
    url = os.environ["DATABASE_URL"]
    if url.startswith("postgresql://") and "+psycopg" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return create_engine(url)


def main() -> int:
    season = int(os.getenv("NFL_KAV_RESIM_SEASON", "2025"))
    simulations = int(os.getenv("NFL_KAV_RESIM_SIMS", "150"))
    min_date = os.getenv("NFL_KAV_RESIM_MIN_DATE", f"{season}-09-01")
    model_version = os.getenv("NFL_MODEL_VERSION", DEFAULT_NFL_MODEL_VERSION)

    engine = _engine()
    with engine.connect() as conn:
        dates = [
            str(r[0])
            for r in conn.execute(
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
        done = {
            str(r[0])
            for r in conn.execute(
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
                      AND p.model_version = :mv
                      AND COALESCE(p.projection->'audit'->>'pipeline_run_at', '') >= :marker
                    """
                ),
                {
                    "season": season,
                    "min_date": min_date,
                    "mv": model_version,
                    "marker": RUN_MARKER,
                },
            ).fetchall()
        }

    todo = [d for d in dates if d not in done]
    print(
        f"resume season={season} sims={simulations} total_days={len(dates)} "
        f"already={len(done)} todo={len(todo)} marker={RUN_MARKER}",
        flush=True,
    )

    t0 = time.time()
    results = []
    total_games = 0
    total_inserted = 0
    for i, day in enumerate(todo, 1):
        # Replace any stale same-day rows for this model so DISTINCT ON stays clean.
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    DELETE FROM nfl_market_projections p
                    USING games g, seasons s, leagues l
                    WHERE p.game_id = g.id
                      AND g.season_id = s.id
                      AND s.league_id = l.id
                      AND l.code = 'nfl'
                      AND s.season_year = :season
                      AND g.game_date = CAST(:day AS date)
                      AND p.model_version = :mv
                    """
                ),
                {"season": season, "day": day, "mv": model_version},
            )
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
        row = {"game_date": day, **result}
        results.append(row)
        print(f"[{i}/{len(todo)}] {day}: {result}", flush=True)
        OUT.write_text(
            json.dumps(
                {
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "todo_total": len(todo),
                    "completed_in_run": i,
                    "games_processed": total_games,
                    "projections_inserted": total_inserted,
                    "last": row,
                },
                indent=2,
            )
            + "\n"
        )

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "season": season,
        "min_date": min_date,
        "simulations": simulations,
        "model_version": model_version,
        "run_marker": RUN_MARKER,
        "days_total": len(dates),
        "days_already_done": len(done),
        "days_run": len(todo),
        "games_processed": total_games,
        "projections_inserted": total_inserted,
        "elapsed_sec": round(time.time() - t0, 1),
        "results": results,
    }
    SUMMARY.write_text(json.dumps(summary, indent=2, default=str) + "\n")
    print(json.dumps({k: summary[k] for k in summary if k != "results"}, indent=2), flush=True)
    print(f"wrote {SUMMARY}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
