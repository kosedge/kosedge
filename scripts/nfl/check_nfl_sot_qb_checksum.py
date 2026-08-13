#!/usr/bin/env python3
"""Fail publish if the research board still has the dual-map QB world.

Required:
  ATL QB1 = Tua (open_competition OK as a label)
  MIA QB1 = Willis
  MIN QB1 = Kyler
  ARI QB1 ≠ Kyler

Checks both the packaged depth SoT and the published player CSV volume leader.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service" / "src"))
sys.path.insert(0, str(ROOT / "scripts" / "nfl"))

from services.nfl_canonical_teams import canonicalize_team  # noqa: E402


def _canon(team: Any) -> str:
    return canonicalize_team(str(team or "")) or str(team or "").strip().upper()


def _contains(name: str, needle: str) -> bool:
    return needle.lower() in (name or "").lower()


def _depth_qb1(season: int = 2026) -> Dict[str, str]:
    path = (
        ROOT
        / "services/model-service/src/services/nfl_season_engine/data"
        / f"nfl_depth_chart_{season}_w1.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    out: Dict[str, str] = {}
    for row in payload.get("rows") or []:
        if str(row.get("position") or "").upper() != "QB":
            continue
        try:
            depth = int(row.get("depth_order") or 99)
        except (TypeError, ValueError):
            continue
        if depth != 1:
            continue
        team = _canon(row.get("team"))
        name = str(row.get("player_name") or "").strip()
        if team and name:
            out[team] = name
    return out


def _volume_qb1(bundle: Path) -> Dict[str, str]:
    csv_path = bundle / "player_regular_season_totals.csv"
    if not csv_path.is_file():
        return {}
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    best: Dict[str, Tuple[float, str]] = {}
    for r in rows:
        if str(r.get("position") or "").upper() != "QB":
            continue
        team = _canon(r.get("team"))
        name = str(r.get("player_name") or "").strip()
        try:
            yds = float(r.get("pass_yards_total") or 0)
        except (TypeError, ValueError):
            yds = 0.0
        prev = best.get(team)
        if prev is None or yds > prev[0]:
            best[team] = (yds, name)
    return {t: n for t, (_, n) in best.items()}


CHECKS = (
    ("ATL", "Tua", True),
    ("MIA", "Willis", True),
    ("MIN", "Kyler", True),
    ("ARI", "Kyler", False),
)


def checksum(bundle: Path, *, season: int = 2026) -> Dict[str, Any]:
    depth = _depth_qb1(season)
    volume = _volume_qb1(bundle)
    rows: List[Dict[str, Any]] = []
    failed: List[str] = []
    for team, needle, must in CHECKS:
        d_name = depth.get(team) or ""
        v_name = volume.get(team) or ""
        d_ok = _contains(d_name, needle) if must else (not _contains(d_name, needle) and bool(d_name))
        v_ok = _contains(v_name, needle) if must else (not _contains(v_name, needle) and bool(v_name))
        ok = d_ok and v_ok
        if not ok:
            want = f"contains {needle}" if must else f"≠ {needle}"
            failed.append(f"{team}: want {want}; depth={d_name or 'MISSING'} volume={v_name or 'MISSING'}")
        rows.append(
            {
                "team": team,
                "needle": needle,
                "must_match": must,
                "depth_qb1": d_name,
                "volume_qb1": v_name,
                "ok": ok,
            }
        )
    return {
        "ok": not failed,
        "failed": failed,
        "rows": rows,
        "bundle": str(bundle),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bundle", type=Path, required=True)
    args = ap.parse_args()
    result = checksum(args.bundle.resolve())
    print(json.dumps(result, indent=2))
    if not result["ok"]:
        print("FAILED:", "; ".join(result["failed"]), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
