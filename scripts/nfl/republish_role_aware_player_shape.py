#!/usr/bin/env python3
"""Copy a published web bundle and re-shape player totals (no 100k re-run).

Applies ``apply_role_aware_player_shape`` on ``player_regular_season_totals.csv``.
Team W/L, PF/PA, and defense CSVs are copied unchanged.

Does NOT flip ``nfl-web-launch-bundle.json`` — run
``scripts/nfl/check_nfl_fantasy_shape_gates.py`` first.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "data-platform-nfl" / "src"))

from data_platform_nfl.role_aware_production import (  # noqa: E402
    apply_role_aware_player_shape,
)

SOURCE_DEFAULT = ROOT / "data/ops/nfl-preseason-sim-2026-20260813T132801Z"


def _load_csv(path: Path) -> List[Dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _write_csv(path: Path, rows: List[Dict[str, Any]], fields: List[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-bundle", type=Path, default=SOURCE_DEFAULT)
    ap.add_argument("--stamp", default=None)
    args = ap.parse_args()
    source = args.source_bundle.resolve()
    if not (source / "player_regular_season_totals.csv").is_file():
        print(f"missing player CSV in {source}", file=sys.stderr)
        return 2
    stamp = args.stamp or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = ROOT / f"data/ops/nfl-preseason-sim-2026-{stamp}"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(source, dest)

    players = _load_csv(dest / "player_regular_season_totals.csv")
    shaped, audit = apply_role_aware_player_shape(players)
    fields = list(players[0].keys()) if players else []
    for extra in ("rush_yards_total", "rush_tds_total", "receiving_yards_total", "receptions_total", "rec_tds_total", "carry_share"):
        if extra not in fields:
            fields.append(extra)
    _write_csv(dest / "player_regular_season_totals.csv", shaped, fields)

    (dest / "role_aware_shape_audit.json").write_text(
        json.dumps(audit, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "bundle": dest.name,
                "source": source.name,
                "stamp": stamp,
                "n_notes": audit.get("n_notes"),
                "rush_pool": audit.get("rush_pool"),
                "pointer_flipped": False,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
