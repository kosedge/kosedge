#!/usr/bin/env python3
"""DB-first NFL mainline open/close densify for 2020–2023 only.

Skips dates already owned (enterprise_training_pull.mainline_date_owned).
Does not pull props. Clears failed cache rows for NFL historical mainlines.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "odds"))

import enterprise_training_pull as m  # noqa: E402
import psycopg  # noqa: E402

m.PLANS["nfl"].nfl_seasons = [2020, 2021, 2022, 2023]
m.PLANS["nfl"].include_props = False
m.PLANS["nfl"].props_open_close = False


def main() -> int:
    conn = psycopg.connect(m.DATABASE_URL_PSYCOPG, autocommit=True)
    deleted = conn.execute(
        """
        DELETE FROM odds_api_request_cache
        WHERE endpoint = 'historical/sports/americanfootball_nfl/odds'
          AND status <> 'success'
        """
    ).rowcount
    conn.close()
    print(f"cleared_failed_cache_rows={deleted}", flush=True)
    sys.argv = [
        "enterprise_training_pull.py",
        "--sports",
        "nfl",
        "--skip-props",
        "--max-spend",
        "150000",
    ]
    return int(m.main())


if __name__ == "__main__":
    raise SystemExit(main())
