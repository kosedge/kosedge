#!/usr/bin/env python3
"""Relink orphan Odds-API game odds_snapshots onto nflverse schedule games.

Persist can create duplicate `games` rows keyed by Odds API event ids while
schedule rows use nflverse ids (`2024_10_NYJ_ARI`). Grading joins via
`nfl_dp_schedules.game_id = games.external_id`, so orphans look like missing OC
even when snapshots exist.

DB-only: no Odds API calls. Safe to re-run (idempotent when already linked).
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "ops" / "nfl-oc-orphan-rematch.json"
DB = os.environ.get(
    "DATABASE_URL_PSYCOPG",
    "postgresql://ryankos:postgres@127.0.0.1:5432/kosedge",
).replace("postgresql+psycopg://", "postgresql://")

PAIRS_SQL = """
WITH orphan AS (
  SELECT g.id AS orphan_id, g.external_id AS orphan_eid, g.game_date::date AS gd,
         s.season_year, ht.abbr AS home, at.abbr AS away,
         (SELECT count(*) FROM odds_snapshots o WHERE o.game_id = g.id) AS snaps
  FROM games g
  JOIN seasons s ON s.id = g.season_id
  JOIN leagues l ON l.id = s.league_id
  JOIN teams ht ON ht.id = g.home_team_id
  JOIN teams at ON at.id = g.away_team_id
  WHERE l.code = 'nfl'
    AND s.season_year BETWEEN 2020 AND 2025
    AND NOT EXISTS (SELECT 1 FROM nfl_dp_schedules sch WHERE sch.game_id = g.external_id)
    AND EXISTS (SELECT 1 FROM odds_snapshots o WHERE o.game_id = g.id)
),
targets AS (
  SELECT sch.game_id AS dp_id, sch.season, sch.home_team, sch.away_team, sch.game_date,
         g.id AS target_id,
         (SELECT count(*) FROM odds_snapshots o WHERE o.game_id = g.id) AS target_snaps
  FROM nfl_dp_schedules sch
  JOIN games g ON g.external_id = sch.game_id
  WHERE sch.season BETWEEN 2020 AND 2025
    AND sch.home_score IS NOT NULL
),
matched AS (
  SELECT o.orphan_id, o.orphan_eid, o.gd, o.season_year, o.home, o.away, o.snaps,
         t.target_id, t.dp_id, t.game_date AS target_date, t.target_snaps,
         abs(o.gd - t.game_date) AS date_delta,
         ROW_NUMBER() OVER (
           PARTITION BY o.orphan_id
           ORDER BY abs(o.gd - t.game_date), t.target_snaps ASC
         ) AS rn_orphan,
         COUNT(*) OVER (PARTITION BY o.orphan_id) AS n_targets_for_orphan
  FROM orphan o
  JOIN targets t
    ON t.season = o.season_year
   AND t.home_team = o.home
   AND t.away_team = o.away
   AND t.game_date BETWEEN o.gd - 1 AND o.gd + 1
)
SELECT *
FROM matched
WHERE rn_orphan = 1
  AND n_targets_for_orphan = 1
  AND date_delta <= 1
ORDER BY season_year, gd, home
"""


def main() -> int:
    with psycopg.connect(DB, autocommit=False) as conn:
        cur = conn.execute(PAIRS_SQL)
        cols = [d.name for d in cur.description]
        pairs = [dict(zip(cols, r)) for r in cur.fetchall()]

        by_target: dict[str, dict] = {}
        conflicts = 0
        unique_pairs: list[dict] = []
        for p in pairs:
            tid = str(p["target_id"])
            if tid in by_target:
                conflicts += 1
                continue
            by_target[tid] = p
            unique_pairs.append(p)

        moved = 0
        for p in unique_pairs:
            if int(p["target_snaps"] or 0) > int(p["snaps"] or 0):
                continue
            res = conn.execute(
                "UPDATE odds_snapshots SET game_id = %s WHERE game_id = %s",
                (p["target_id"], p["orphan_id"]),
            )
            moved += res.rowcount
        conn.commit()

        inv = conn.execute(
            """
            WITH sched AS (
              SELECT sch.season, g.id AS game_uuid
              FROM nfl_dp_schedules sch
              JOIN games g ON g.external_id = sch.game_id
              WHERE sch.home_score IS NOT NULL AND sch.season BETWEEN 2020 AND 2025
            ),
            oc AS (
              SELECT game_id, count(DISTINCT captured_at) AS ts_n
              FROM odds_snapshots GROUP BY 1
            )
            SELECT s.season,
                   count(*) FILTER (WHERE COALESCE(oc.ts_n,0) >= 2) AS owned_2plus,
                   count(*) FILTER (WHERE COALESCE(oc.ts_n,0) = 0) AS still_zero,
                   count(*) AS n
            FROM sched s
            LEFT JOIN oc ON oc.game_id = s.game_uuid
            GROUP BY 1 ORDER BY 1
            """
        ).fetchall()

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "candidate_pairs": len(pairs),
        "unique_pairs_used": len(unique_pairs),
        "target_conflicts_skipped": conflicts,
        "snapshots_relinked": moved,
        "coverage_after": [
            {"season": r[0], "owned_2plus": r[1], "still_zero": r[2], "n": r[3]} for r in inv
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(json.dumps(report, indent=2, default=str))
    print(f"Wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
