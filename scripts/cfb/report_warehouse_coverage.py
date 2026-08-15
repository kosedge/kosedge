#!/usr/bin/env python3
"""CFB warehouse coverage: years × games / odds / PBP.

Reads committed inventory JSONs so this works without HD. When
``/Volumes/KosEdgeData`` is mounted, overlays parquet row counts.

Usage:
  python scripts/cfb/report_warehouse_coverage.py
  python scripts/cfb/report_warehouse_coverage.py --dry-run
  python scripts/cfb/report_warehouse_coverage.py --out /tmp/cfb-coverage.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / "data" / "ops" / "cfb-p1-coverage-20260813.json"
GAMES_INV = ROOT / "data" / "ops" / "cfb-historical-warehouse-v1-20260812-inventory.json"
PBP_INV = ROOT / "data" / "ops" / "cfb-historical-warehouse-v1-20260812-pbp-inventory.json"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _int(raw: Any, default: int = 0) -> int:
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def committed_coverage() -> dict[str, Any]:
    games = _load_json(GAMES_INV)
    pbp = _load_json(PBP_INV)
    by_season: dict[str, dict[str, Any]] = {}
    game_seasons = games.get("by_season") or {}
    pbp_seasons = (pbp.get("by_season") or games.get("pbp", {}).get("by_season") or {})
    lake = games.get("owned_odds_api_cfb_inventory") or {}
    lake_export = lake.get("export") or {}
    lake_by_season = lake_export.get("by_season") or {}

    years = sorted(
        {
            int(y)
            for y in list(game_seasons) + list(pbp_seasons) + list(lake_by_season)
            if str(y).isdigit()
        }
    )
    for year in years:
        key = str(year)
        g = game_seasons.get(key) or {}
        p = pbp_seasons.get(key) or {}
        by_season[key] = {
            "games": _int(g.get("games")),
            "close_spread": _int(g.get("with_close_spread")),
            "open_spread": _int(g.get("with_open_spread")),
            "lake_primary": _int(g.get("lake_primary")),
            "fcs_flagged": _int(g.get("fcs_flagged")),
            "odds_lake_snaps": _int(lake_by_season.get(key)),
            "pbp_plays": _int(p.get("plays")),
            "pbp_games": _int(p.get("games")),
        }
    join = lake.get("join") or {}
    return {
        "as_of": "2026-08-13",
        "source": "committed_inventory",
        "inventories": {
            "games": str(GAMES_INV.relative_to(ROOT)),
            "pbp": str(PBP_INV.relative_to(ROOT)),
        },
        "totals": {
            "games_2020_2025": _int(games.get("games")),
            "close_spread": sum(_int(v.get("with_close_spread")) for v in game_seasons.values()),
            "open_spread": sum(_int(v.get("with_open_spread")) for v in game_seasons.values()),
            "odds_lake_snaps": _int(lake_export.get("rows")),
            "odds_lake_games": _int(lake_export.get("games")),
            "lake_matched": _int(join.get("matched")),
            "lake_unmatched": _int(join.get("unmatched")),
            "pbp_plays": _int(pbp.get("plays") or games.get("pbp", {}).get("plays")),
            "pbp_games": _int(pbp.get("games") or games.get("pbp", {}).get("games")),
            "fcs_flagged": sum(_int(v.get("fcs_flagged")) for v in game_seasons.values()),
        },
        "by_season": by_season,
        "leakage_rule": games.get("leakage_rule") or "strictly_before_kickoff",
        "hd_overlay": None,
    }


def _parquet_count(path: Path) -> Optional[int]:
    if not path.is_file():
        return None
    try:
        import pandas as pd

        return int(len(pd.read_parquet(path, columns=[])))
    except Exception:
        try:
            import pyarrow.parquet as pq

            return int(pq.ParquetFile(path).metadata.num_rows)
        except Exception:
            return None


def overlay_hd(report: dict[str, Any]) -> dict[str, Any]:
    sys.path.insert(0, str(ROOT / "services" / "model-service"))
    from src.services.cfb_warehouse.paths import clean_dir, hd_mounted, odds_lake_dir

    if not hd_mounted():
        report["hd_overlay"] = {"mounted": False}
        return report
    clean = clean_dir(prefer_hd=True)
    odds = odds_lake_dir(prefer_hd=True)
    games_n = _parquet_count(clean / "games.parquet")
    closes_n = _parquet_count(clean / "closing_lines.parquet")
    lake_snaps = 0
    lake_files = 0
    for snap in sorted(odds.glob("snapshots-*.parquet")):
        n = _parquet_count(snap)
        if n is not None:
            lake_snaps += n
            lake_files += 1
    pbp_plays = 0
    pbp_files = 0
    pbp_dir = clean / "pbp"
    for core in sorted(pbp_dir.glob("pbp_*_core.parquet")):
        n = _parquet_count(core)
        if n is not None:
            pbp_plays += n
            pbp_files += 1
    report["hd_overlay"] = {
        "mounted": True,
        "clean_dir": str(clean),
        "games_parquet": games_n,
        "closing_lines_parquet": closes_n,
        "odds_lake_snaps": lake_snaps if lake_files else None,
        "odds_lake_files": lake_files,
        "pbp_core_plays": pbp_plays if pbp_files else None,
        "pbp_core_files": pbp_files,
    }
    return report


def build_report(*, overlay: bool = True) -> dict[str, Any]:
    report = committed_coverage()
    if overlay:
        try:
            overlay_hd(report)
        except Exception as exc:
            report["hd_overlay"] = {"mounted": None, "error": str(exc)}
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print JSON only; do not write --out",
    )
    parser.add_argument(
        "--no-hd",
        action="store_true",
        help="Skip HD parquet overlay (committed inventories only)",
    )
    args = parser.parse_args(argv)
    report = build_report(overlay=not args.no_hd)
    text = json.dumps(report, indent=2, default=str) + "\n"
    print(text, end="")
    if args.dry_run:
        return 0
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text)
    print(f"wrote {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
