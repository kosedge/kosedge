#!/usr/bin/env python3
"""Weekly writer for Projections Hub Actual columns.

Scaffold / ops entrypoint. Until REG weeks settle, writes an empty template.
Later: fill teams/players from DB box scores / nfl_dp_schedules scores.

Usage:
  .venv/bin/python scripts/nfl/write_projection_actuals.py --season 2026
  .venv/bin/python scripts/nfl/write_projection_actuals.py --season 2026 --from-db
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def empty_bundle(season: int) -> dict:
    return {
        "season": season,
        "asOfUtc": None,
        "source": "empty_preseason_scaffold",
        "teams": {},
        "players": {},
        "notes": (
            "Actual cells stay null / UI '—' until REG weeks settle. "
            "Re-run with --from-db after kickoffs to populate."
        ),
    }


def load_from_db(season: int) -> dict:
    """Best-effort actuals from nfl_dp_schedules + player box if present."""
    import psycopg

    url = os.environ.get("DATABASE_URL", "postgresql://ryankos:postgres@127.0.0.1:5432/kosedge")
    url = url.replace("postgresql+psycopg://", "postgresql://").replace("postgres://", "postgresql://")
    if "@postgres:" in url:
        url = url.replace("@postgres:", "@127.0.0.1:")
    conn = psycopg.connect(url)
    cur = conn.cursor()
    teams: dict = {}
    cur.execute(
        """
        SELECT home_team, away_team, home_score, away_score
        FROM nfl_dp_schedules
        WHERE season = %s AND home_score IS NOT NULL AND away_score IS NOT NULL
        """,
        (season,),
    )
    for home, away, hs, aws in cur.fetchall():
        for team, scored, allowed in ((home, hs, aws), (away, aws, hs)):
            entry = teams.setdefault(team, {"wins": 0, "losses": 0})
            if scored > allowed:
                entry["wins"] += 1
            elif scored < allowed:
                entry["losses"] += 1
    conn.close()
    return {
        "season": season,
        "asOfUtc": datetime.now(timezone.utc).isoformat(),
        "source": "nfl_dp_schedules_final_scores",
        "teams": teams,
        "players": {},
        "notes": "Player actuals not yet wired — team wins/losses only when scores exist.",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", type=int, default=2026)
    ap.add_argument("--from-db", action="store_true")
    ap.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Defaults to data/ops/nfl-projection-actuals-{season}.json",
    )
    args = ap.parse_args()
    out = args.out or (ROOT / "data" / "ops" / f"nfl-projection-actuals-{args.season}.json")
    if args.from_db:
        try:
            bundle = load_from_db(args.season)
            if not bundle["teams"]:
                bundle = empty_bundle(args.season)
                bundle["notes"] = "No final scores yet — wrote empty scaffold."
        except Exception as exc:  # noqa: BLE001
            print(f"DB load failed ({exc}); writing empty scaffold", file=sys.stderr)
            bundle = empty_bundle(args.season)
    else:
        bundle = empty_bundle(args.season)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(out), "teams": len(bundle["teams"]), "source": bundle["source"]}, indent=2))


if __name__ == "__main__":
    main()
