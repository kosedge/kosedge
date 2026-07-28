#!/usr/bin/env python3
"""Faster 2025 KAV re-sim: reverse date order + short calibration lookback.

Safe to run alongside scripts/nfl/resim_kav_2025_resume.py — each skips dates
already stamped with pipeline_run_at >= MARKER, so they meet in the middle.
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

# Speed knobs before importing tasks
os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge"
)
os.environ.setdefault("NFL_TOTALS_CALIBRATION_LOOKBACK_DAYS", "120")
os.environ.setdefault("NFL_TOTALS_CALIBRATION_MIN_SLATE", "16")
os.environ.setdefault("LOKY_MAX_CPU_COUNT", "2")

from sqlalchemy import create_engine, text  # noqa: E402
from src.tasks import DEFAULT_NFL_MODEL_VERSION, run_nfl_market_simulations  # noqa: E402

OUT = ROOT / "data" / "ops" / "nfl-kav-resim-2025-fast-progress.json"
MARKER = os.getenv("NFL_KAV_RESIM_MARKER", "2026-07-28T15:00:00+00:00")


def main() -> int:
    season = 2025
    simulations = int(os.getenv("NFL_KAV_RESIM_SIMS", "100"))
    min_date = os.getenv("NFL_KAV_RESIM_MIN_DATE", "2025-09-01")
    model_version = DEFAULT_NFL_MODEL_VERSION
    engine = create_engine(os.environ["DATABASE_URL"])

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
                      AND g.game_date <= DATE '2026-02-15'
                    ORDER BY 1 DESC
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
                      AND p.model_version = :mv
                      AND COALESCE(p.projection->'audit'->>'pipeline_run_at','') >= :marker
                    """
                ),
                {"season": season, "mv": model_version, "marker": MARKER},
            ).fetchall()
        }

    todo = [d for d in dates if d not in done]
    print(
        f"fast_batch reverse sims={simulations} todo={len(todo)} done={len(done)}",
        flush=True,
    )
    t0 = time.time()
    games = inserted = 0
    for i, day in enumerate(todo, 1):
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    DELETE FROM nfl_market_projections p
                    USING games g, seasons s, leagues l
                    WHERE p.game_id = g.id AND g.season_id = s.id AND s.league_id = l.id
                      AND l.code = 'nfl' AND s.season_year = :season
                      AND g.game_date = CAST(:day AS date) AND p.model_version = :mv
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
        games += int(result.get("games_processed") or 0)
        inserted += int(result.get("projections_inserted") or 0)
        print(f"[fast {i}/{len(todo)}] {day}: {result}", flush=True)
        OUT.write_text(
            json.dumps(
                {
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "i": i,
                    "todo": len(todo),
                    "games": games,
                    "inserted": inserted,
                    "elapsed_sec": round(time.time() - t0, 1),
                    "last": {"day": day, **result},
                },
                indent=2,
            )
            + "\n"
        )
    print(f"done games={games} inserted={inserted} elapsed={time.time()-t0:.1f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
