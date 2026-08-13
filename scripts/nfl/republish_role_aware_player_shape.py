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
    align_skill_identities_to_depth_sot,
    apply_role_aware_player_shape,
)

SOURCE_DEFAULT = ROOT / "data/ops/nfl-preseason-sim-2026-20260813T151800Z"
DEPTH_PACK = (
    ROOT
    / "services/model-service/src/services/nfl_season_engine/data"
    / "nfl_depth_chart_2026_w1.json"
)


def sot_skill_names() -> List[str]:
    """Only move identities listed in SOT_SKILL_OVERRIDES (no silent FA swaps)."""
    import importlib.util

    path = ROOT / "scripts/nfl/package_season_engine_depth_2026.py"
    spec = importlib.util.spec_from_file_location("package_depth_2026", path)
    if spec is None or spec.loader is None:
        return []
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    names: List[str] = []
    for by_pos in getattr(mod, "SOT_SKILL_OVERRIDES", {}).values():
        for slots in by_pos.values():
            for _depth, name, _pid in slots:
                names.append(str(name))
    return names

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "data-platform-nfl" / "src"))

from data_platform_nfl.role_aware_production import (  # noqa: E402
    align_skill_identities_to_depth_sot,
    apply_role_aware_player_shape,
)

SOURCE_DEFAULT = ROOT / "data/ops/nfl-preseason-sim-2026-20260813T151800Z"
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

    players = _load_csv(dest / "player_regular_season_totals.csv")
    identity_audit: dict = {}
    if args.align_depth_sot:
        pack = json.loads(DEPTH_PACK.read_text(encoding="utf-8"))
        players, identity_audit = align_skill_identities_to_depth_sot(
            players,
            pack.get("rows") or [],
            only_names=list(sot_skill_names()),
        )
    shaped, audit = apply_role_aware_player_shape(players, teams=("SEA", "KC"))
    fields = list(players[0].keys()) if players else []
    for extra in ("rush_yards_total", "rush_tds_total", "receiving_yards_total", "receptions_total", "rec_tds_total", "carry_share"):
        if extra not in fields:
            fields.append(extra)
    _write_csv(dest / "player_regular_season_totals.csv", shaped, fields)

    (dest / "role_aware_shape_audit.json").write_text(
        json.dumps(
            {"identity": identity_audit, "shape": audit},
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
