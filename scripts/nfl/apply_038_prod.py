#!/usr/bin/env python3
"""Apply infra/db/038_nfl_snap_usage_bridge.sql using DATABASE_URL from the env."""

from __future__ import annotations

import os
import sys

from sqlalchemy import create_engine, text


def main() -> int:
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL missing", file=sys.stderr)
        return 2
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    engine = create_engine(url)
    stmts = [
        "ALTER TABLE nfl_dp_snap_counts_weekly ADD COLUMN IF NOT EXISTS gsis_player_id text",
        """
        CREATE INDEX IF NOT EXISTS idx_nfl_dp_snap_counts_weekly_gsis
          ON nfl_dp_snap_counts_weekly (season, week, team, gsis_player_id)
          WHERE gsis_player_id IS NOT NULL
        """,
        "ALTER TABLE nfl_player_projection_features_weekly ADD COLUMN IF NOT EXISTS offense_snaps numeric",
        "ALTER TABLE nfl_player_projection_features_weekly ADD COLUMN IF NOT EXISTS offense_snap_pct numeric",
        "ALTER TABLE nfl_player_projection_features_weekly ADD COLUMN IF NOT EXISTS snap_source text",
    ]
    with engine.begin() as conn:
        for stmt in stmts:
            conn.execute(text(stmt))
            print("applied:", " ".join(stmt.split()[:6]))
        present = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'nfl_dp_snap_counts_weekly'
                  AND column_name = 'gsis_player_id'
                """
            )
        ).scalar()
        print("gsis_player_id_present", int(present or 0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
