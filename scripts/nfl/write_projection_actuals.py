#!/usr/bin/env python3
"""Weekly writer for Projections Hub Actual columns.

Production entrypoint. Preseason / pre-kickoff writes an empty scaffold.
After REG weeks settle, `--from-db` fills team W/L + player season-to-date
yards / receptions / TDs from owned nflverse tables.

Usage:
  .venv/bin/python scripts/nfl/write_projection_actuals.py --season 2026
  .venv/bin/python scripts/nfl/write_projection_actuals.py --season 2026 --from-db
  .venv/bin/python scripts/nfl/write_projection_actuals.py --season 2025 --from-db  # smoke

Ops cadence: see data/ops/nfl-weekly-ops-cadence.md
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from data_platform_nfl.projection_actuals import (  # noqa: E402
    empty_bundle,
    load_from_db,
    validate_bundle,
)


def _connect():
    import psycopg

    url = os.environ.get("DATABASE_URL", "postgresql://ryankos:postgres@127.0.0.1:5432/kosedge")
    url = url.replace("postgresql+psycopg://", "postgresql://").replace("postgres://", "postgresql://")
    if "@postgres:" in url:
        url = url.replace("@postgres:", "@127.0.0.1:")
    return psycopg.connect(url)


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
            with _connect() as conn:
                bundle = load_from_db(conn, args.season)
        except Exception as exc:  # noqa: BLE001
            print(f"DB load failed ({exc}); writing empty scaffold", file=sys.stderr)
            bundle = empty_bundle(args.season)
    else:
        bundle = empty_bundle(args.season)

    ok, errors = validate_bundle(bundle)
    if not ok:
        print(f"Invalid bundle: {errors}", file=sys.stderr)
        sys.exit(2)

    # Hub ignores meta; keep file lean for Vercel packing.
    payload = {
        "season": bundle["season"],
        "asOfUtc": bundle.get("asOfUtc"),
        "source": bundle.get("source"),
        "teams": bundle.get("teams") or {},
        "players": bundle.get("players") or {},
        "notes": bundle.get("notes"),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    unique_players = len({json.dumps(v, sort_keys=True) for v in payload["players"].values()})
    print(
        json.dumps(
            {
                "wrote": str(out),
                "teams": len(payload["teams"]),
                "playerKeys": len(payload["players"]),
                "uniquePlayers": unique_players,
                "source": payload["source"],
                "asOfUtc": payload["asOfUtc"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
