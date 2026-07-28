#!/usr/bin/env python3
"""Apply infra/db/039 + 040 MLB enterprise migrations using DATABASE_URL."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = [
    ROOT / "infra/db/039_mlb_enterprise_runline_quality.sql",
    ROOT / "infra/db/040_mlb_enterprise_clv_board_health.sql",
]


def main() -> int:
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL missing", file=sys.stderr)
        return 2
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    engine = create_engine(url)
    with engine.begin() as conn:
        raw = conn.connection.driver_connection
        for path in MIGRATIONS:
            sql = path.read_text()
            # Multi-statement migration files need the DBAPI cursor.
            with raw.cursor() as cur:
                cur.execute(sql)
            print("applied:", path.name)
        checks = conn.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name IN (
                    'mlb_model_quality_snapshots',
                    'mlb_odds_densify_runs',
                    'mlb_clv_attribution',
                    'mlb_board_health_snapshots',
                    'mlb_prop_stake_policy'
                  )
                ORDER BY table_name
                """
            )
        ).fetchall()
        print("tables:", [r[0] for r in checks])
        stake = conn.execute(
            text("SELECT play_stake_eligible FROM mlb_prop_stake_policy WHERE market_family = 'player_props'")
        ).scalar()
        print("props_play_stake_eligible", stake)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
