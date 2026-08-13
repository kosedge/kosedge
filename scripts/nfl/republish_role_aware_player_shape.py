#!/usr/bin/env python3
"""Copy a published web bundle and re-shape player totals (no 100k re-run).

Aligns skill identities to the depth pack (pack team wins), then applies
``apply_role_aware_player_shape`` on touched teams only.

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
from typing import Any, Dict, List, Set

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "data-platform-nfl" / "src"))

from data_platform_nfl.role_aware_production import (  # noqa: E402
    align_skill_identities_to_depth_sot,
    apply_role_aware_player_shape,
)

SOURCE_DEFAULT = ROOT / "data/ops/nfl-preseason-sim-2026-20260813T161500Z"
DEPTH_PACK = (
    ROOT
    / "services/model-service/src/services/nfl_season_engine/data"
    / "nfl_depth_chart_2026_w1.json"
)


def _load_csv(path: Path) -> List[Dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _write_csv(path: Path, rows: List[Dict[str, Any]], fields: List[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _teams_from_moves(moves: List[str]) -> Set[str]:
    teams: Set[str] = set()
    for move in moves:
        if ":" not in move or "→" not in move:
            continue
        _name, rest = move.split(":", 1)
        left, right = rest.split("→", 1)
        for token in (left.split("-")[0], right.split("-")[0]):
            team = token.strip().upper()
            if team == "LA":
                team = "LAR"
            if team:
                teams.add(team)
    return teams


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-bundle", type=Path, default=SOURCE_DEFAULT)
    ap.add_argument("--stamp", default=None)
    ap.add_argument(
        "--align-depth-sot",
        action="store_true",
        default=True,
        help="Relabel skill identities to the depth pack before reshaping (default on).",
    )
    ap.add_argument(
        "--no-align-depth-sot",
        action="store_false",
        dest="align_depth_sot",
        help="Skip identity alignment (shape only).",
    )
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

    pack = json.loads(DEPTH_PACK.read_text(encoding="utf-8"))
    pack_rows = pack.get("rows") or []

    players = _load_csv(dest / "player_regular_season_totals.csv")
    identity_audit: dict = {}
    if args.align_depth_sot:
        players, identity_audit = align_skill_identities_to_depth_sot(
            players, pack_rows
        )
    touched = sorted(_teams_from_moves(list(identity_audit.get("moves") or [])))
    if touched:
        shaped, audit = apply_role_aware_player_shape(players, teams=touched)
    else:
        shaped, audit = players, {"applied": False, "n_notes": 0, "reason": "no_identity_moves"}
    fields = list(players[0].keys()) if players else []
    for extra in (
        "rush_yards_total",
        "rush_tds_total",
        "receiving_yards_total",
        "receptions_total",
        "rec_tds_total",
        "carry_share",
    ):
        if extra not in fields:
            fields.append(extra)
    _write_csv(dest / "player_regular_season_totals.csv", shaped, fields)

    playoff_path = dest / "player_playoff_totals.csv"
    playoff_audit: dict = {}
    if playoff_path.is_file() and args.align_depth_sot:
        playoff = _load_csv(playoff_path)
        playoff, playoff_audit = align_skill_identities_to_depth_sot(
            playoff, pack_rows, restore_budgets=False
        )
        pfields = list(playoff[0].keys()) if playoff else []
        _write_csv(playoff_path, playoff, pfields)

    (dest / "role_aware_shape_audit.json").write_text(
        json.dumps(
            {
                "identity": identity_audit,
                "playoff_identity": playoff_audit,
                "touched_teams": touched,
                "shape": audit,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "bundle": dest.name,
                "source": source.name,
                "stamp": stamp,
                "n_identity_moves": identity_audit.get("n_moves"),
                "identity_moves": identity_audit.get("moves"),
                "touched_teams": touched,
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
