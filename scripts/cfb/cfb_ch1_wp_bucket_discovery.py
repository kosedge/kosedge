#!/usr/bin/env python3
"""Chapter 1 Phase 0 — read-only warehouse close-spread bucket counts.

Does NOT fit WP/margin curves. Does NOT call project_game or apply_cfb_kei.

Usage (HD or repo warehouse required):
  python3 scripts/cfb/cfb_ch1_wp_bucket_discovery.py
  python3 scripts/cfb/cfb_ch1_wp_bucket_discovery.py --repo-fallback
  python3 scripts/cfb/cfb_ch1_wp_bucket_discovery.py --json > data/ops/cfb-ch1-wp-bucket-corpus.json

If parquet is missing, exits 2 and prints inventory citation only.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.cfb_season_engine.conferences import conference_for  # noqa: E402
from src.services.cfb_warehouse.paths import HD_CLEAN, clean_dir  # noqa: E402

# Chapter 0 edges (absolute close spread)
BUCKETS: Tuple[Tuple[str, float, float], ...] = (
    ("pick", 0.0, 3.0),
    ("short", 3.0, 7.0),
    ("mid", 7.0, 14.0),
    ("long", 14.0, 21.0),
    ("cupcake", 21.0, 999.0),
)

P4 = frozenset({"SEC", "Big Ten", "Big 12", "ACC", "Pac-12"})
INVENTORY = ROOT / "data/ops/cfb-historical-warehouse-v1-20260812-inventory.json"
# Prefer monorepo warehouse path; paths.clean_dir can resolve to service-root
# when model-service has a nested data/ + services/ tree.
MONOREPO_CLEAN = ROOT / "data" / "cfb" / "warehouse" / "clean"


def bucket_abs(abs_spread: float) -> str:
    for name, lo, hi in BUCKETS:
        if lo <= abs_spread < hi:
            return name
    return "cupcake"


def tier_for(home: str, away: str, fcs: bool) -> str:
    if fcs:
        return "FCS"
    hc = conference_for(str(home or ""))
    ac = conference_for(str(away or ""))
    if hc in P4 and ac in P4:
        return "P4_vs_P4"
    if hc in P4 or ac in P4:
        return "P4_vs_G5"
    return "G5_vs_G5"


def _read_parquet(path: Path) -> List[Dict[str, Any]]:
    import pandas as pd

    return pd.read_parquet(path).to_dict(orient="records")


def _resolve_clean(prefer_hd: bool) -> Path:
    candidates = []
    if prefer_hd:
        candidates.append(HD_CLEAN)
    candidates.append(MONOREPO_CLEAN)
    candidates.append(clean_dir(prefer_hd=prefer_hd))
    for path in candidates:
        if (path / "games.parquet").is_file() and (path / "closing_lines.parquet").is_file():
            return path
    return candidates[0]


def discover(prefer_hd: bool) -> Dict[str, Any]:
    clean = _resolve_clean(prefer_hd=prefer_hd)
    games_path = clean / "games.parquet"
    closes_path = clean / "closing_lines.parquet"
    if not games_path.is_file() or not closes_path.is_file():
        inv = None
        if INVENTORY.is_file():
            inv = json.loads(INVENTORY.read_text())
        return {
            "ok": False,
            "error": "warehouse_parquet_missing",
            "clean_dir": str(clean),
            "candidates_checked": [str(HD_CLEAN), str(MONOREPO_CLEAN), str(clean_dir(prefer_hd=prefer_hd))],
            "hint": "Mount KosEdgeData or run ingest_historical_warehouse.py --repo-fallback",
            "inventory_citation": {
                "path": str(INVENTORY.relative_to(ROOT)),
                "season_range": (inv or {}).get("season_range"),
                "games": (inv or {}).get("games"),
                "closing_lines": (inv or {}).get("closing_lines"),
                "by_season_with_close": {
                    s: (v or {}).get("with_close_spread")
                    for s, v in ((inv or {}).get("by_season") or {}).items()
                },
                "note": "Games+closes are 2020–2025 in v1 inventory; 2019 is PBP-only.",
            },
        }

    games = {str(g.get("game_id")): g for g in _read_parquet(games_path)}
    closes = _read_parquet(closes_path)

    by_season: Dict[str, Counter] = defaultdict(Counter)
    by_bucket: Counter = Counter()
    by_bucket_tier: Dict[str, Counter] = defaultdict(Counter)
    n_close = 0
    n_missing_close = 0
    seasons_seen: Counter = Counter()

    for row in closes:
        gid = str(row.get("game_id") or "")
        game = games.get(gid) or {}
        season = int(row.get("season") or game.get("season") or 0)
        seasons_seen[season] += 1
        close = row.get("close_spread_home")
        if close is None:
            close = game.get("close_spread_home")
        if close is None:
            n_missing_close += 1
            continue
        n_close += 1
        abs_s = abs(float(close))
        b = bucket_abs(abs_s)
        fcs = bool(
            game.get("fcs_home")
            or game.get("fcs_away")
            or game.get("fcs_opponent")
            or row.get("fcs_opponent")
        )
        home = game.get("home_team_id") or row.get("home_team_id") or ""
        away = game.get("away_team_id") or row.get("away_team_id") or ""
        tier = tier_for(str(home), str(away), fcs)
        by_season[str(season)][b] += 1
        by_bucket[b] += 1
        by_bucket_tier[b][tier] += 1

    return {
        "ok": True,
        "clean_dir": str(clean),
        "n_games": len(games),
        "n_close_rows": len(closes),
        "n_with_close_spread": n_close,
        "n_missing_close_spread": n_missing_close,
        "seasons_close_rows": dict(sorted(seasons_seen.items())),
        "by_bucket": {name: by_bucket.get(name, 0) for name, _, _ in BUCKETS},
        "by_season_bucket": {
            s: {name: by_season[s].get(name, 0) for name, _, _ in BUCKETS}
            for s in sorted(by_season.keys())
        },
        "by_bucket_tier": {
            name: dict(by_bucket_tier.get(name, {})) for name, _, _ in BUCKETS
        },
        "bucket_edges": {name: [lo, hi] for name, lo, hi in BUCKETS},
        "fit": False,
        "note": "Counts only — no model residual, no WP refit.",
    }


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo-fallback", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    out = discover(prefer_hd=not args.repo_fallback)
    if args.json:
        print(json.dumps(out, indent=2, default=str))
    else:
        if not out.get("ok"):
            print("WAREHOUSE MISSING:", out.get("clean_dir"), file=sys.stderr)
            print(json.dumps(out.get("inventory_citation"), indent=2), file=sys.stderr)
            return 2
        print(f"clean_dir={out['clean_dir']}")
        print(f"n_with_close_spread={out['n_with_close_spread']}")
        print("by_bucket:", out["by_bucket"])
        print("by_bucket_tier:", out["by_bucket_tier"])
    return 0 if out.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
