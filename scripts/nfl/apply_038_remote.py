"""Apply infra/db/038_nfl_snap_usage_bridge.sql using DATABASE_URL in-env."""
from __future__ import annotations

import os
from sqlalchemy import create_engine, text

SQL = """
ALTER TABLE nfl_dp_snap_counts_weekly
  ADD COLUMN IF NOT EXISTS gsis_player_id text;

CREATE INDEX IF NOT EXISTS idx_nfl_dp_snap_counts_weekly_gsis
  ON nfl_dp_snap_counts_weekly (season, week, team, gsis_player_id)
  WHERE gsis_player_id IS NOT NULL;

ALTER TABLE nfl_player_projection_features_weekly
  ADD COLUMN IF NOT EXISTS offense_snaps numeric;

ALTER TABLE nfl_player_projection_features_weekly
  ADD COLUMN IF NOT EXISTS offense_snap_pct numeric;

ALTER TABLE nfl_player_projection_features_weekly
  ADD COLUMN IF NOT EXISTS snap_source text;
"""


def main() -> None:
    url = os.environ["DATABASE_URL"]
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://") :]
    elif url.startswith("postgresql://") and "+psycopg" not in url:
        url = "postgresql+psycopg://" + url[len("postgresql://") :]

    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(text(SQL))
        cols = conn.execute(
            text(
                """
                SELECT table_name, column_name
                FROM information_schema.columns
                WHERE (table_name = 'nfl_dp_snap_counts_weekly' AND column_name = 'gsis_player_id')
                   OR (table_name = 'nfl_player_projection_features_weekly'
                       AND column_name IN ('offense_snaps','offense_snap_pct','snap_source'))
                ORDER BY 1,2
                """
            )
        ).fetchall()
    print("038_applied_ok")
    print("verified_columns", [(r[0], r[1]) for r in cols])


if __name__ == "__main__":
    main()
