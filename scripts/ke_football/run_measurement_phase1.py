#!/usr/bin/env python3
"""KE Football v1 Phase 1 measurement runner (research only).

Downloads owned nflverse / SportsDataverse PBP into gitignored research
cache, computes team-week snapshots, writes compact ops artifacts.

Does not write production tables, KEI, boards, or Team Strength.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
MS = ROOT / "services" / "model-service"
if str(MS) not in sys.path:
    sys.path.insert(0, str(MS))

from src.services.ke_football.adapters import adapt_rows
from src.services.ke_football.aggregate import build_team_games, filter_week_lt
from src.services.ke_football.opp_adj import future_week_changes_snapshot
from src.services.ke_football.pipeline import run_measurement

NFL_PBP = "https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{season}.parquet"
CFB_PBP = (
    "https://github.com/sportsdataverse/sportsdataverse-data/releases/download/"
    "espn_cfb_pbp/play_by_play_{season}.parquet"
)
UA = "kosedge-ke-football-measurement-phase1/1.0"


def _download(url: str, dest: Path, *, timeout: int = 300) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    tmp = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp, tmp.open("wb") as out:
        while True:
            chunk = resp.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)
    tmp.replace(dest)
    return dest


def _load_parquet(path: Path):
    import pandas as pd

    return pd.read_parquet(path)


def _rows(df, *, limit: int | None = None) -> List[Dict[str, Any]]:
    if limit is not None:
        df = df.head(limit)
    return df.to_dict(orient="records")


def _write(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str) + "\n", encoding="utf-8")


def run_nfl(season: int, as_of_week: int, cache: Path) -> Dict[str, Any]:
    path = _download(NFL_PBP.format(season=season), cache / f"nfl_pbp_{season}.parquet")
    df = _load_parquet(path)
    if "season_type" in df.columns:
        df = df[df["season_type"].astype(str).str.upper().eq("REG")]
    elif "game_type" in df.columns:
        df = df[df["game_type"].astype(str).str.upper().eq("REG")]
    plays = adapt_rows("nfl", _rows(df))
    examples = ["KC", "BUF", "PHI", "BAL", "SF", "DET", "NYJ", "CAR", "NE", "CLE"]
    out = run_measurement(
        plays, sport="nfl", season=season, as_of_week=as_of_week, example_teams=examples
    )
    out["source"] = {
        "url": NFL_PBP.format(season=season),
        "path": str(path),
        "bytes": path.stat().st_size,
        "n_plays_adapted": len(plays),
    }
    # Real-data leakage probe: inject a future-week game with huge EPA.
    window = filter_week_lt(plays, season=season, as_of_week=as_of_week)
    games = build_team_games(window)
    if games:
        from copy import deepcopy

        leak = deepcopy(games[0])
        leak.week = as_of_week
        leak.game_id = "LEAK_FUTURE"
        leak.off_epa_sum = 50.0
        leak.off_epa_n = 80
        out["leakage_live"] = {
            "future_week_changes_snapshot": future_week_changes_snapshot(
                games, team=leak.team, as_of_week=as_of_week, future_game=leak
            ),
            "expected": False,
        }
    # Drop full snapshot dump from the returned blob — keep examples + validation.
    compact = {k: v for k, v in out.items() if k != "snapshots"}
    compact["snapshot_count"] = len(out["snapshots"])
    compact["ranking"] = out["validation"]["ranking_sanity"]
    return compact


def run_cfb(season: int, as_of_week: int, cache: Path) -> Dict[str, Any]:
    dest = cache / f"cfb_pbp_{season}.parquet"
    # Never write 2026 into the historical lake path. Research cache only.
    path = _download(CFB_PBP.format(season=season), dest)
    df = _load_parquet(path)
    plays = adapt_rows("cfb", _rows(df))
    # Prefer well-known names if present; else pipeline ranking.
    names = {p.offense for p in plays}
    wanted = [
        n
        for n in (
            "Georgia Bulldogs",
            "Ohio State Buckeyes",
            "Alabama Crimson Tide",
            "Oregon Ducks",
            "Michigan Wolverines",
            "Texas Longhorns",
            "Kent State Golden Flashes",
            "Massachusetts Minutemen",
        )
        if n in names
    ]
    out = run_measurement(
        plays, sport="cfb", season=season, as_of_week=as_of_week, example_teams=wanted or None
    )
    out["source"] = {
        "url": CFB_PBP.format(season=season),
        "path": str(path),
        "bytes": path.stat().st_size,
        "n_plays_adapted": len(plays),
        "historical_lake_write": False,
    }
    compact = {k: v for k, v in out.items() if k != "snapshots"}
    compact["snapshot_count"] = len(out["snapshots"])
    compact["ranking"] = out["validation"]["ranking_sanity"]
    compact["leakage_live"] = _leakage_probe(plays, season=season, as_of_week=as_of_week)
    return compact


def _leakage_probe(plays, *, season: int, as_of_week: int) -> Dict[str, Any]:
    window = filter_week_lt(plays, season=season, as_of_week=as_of_week)
    games = build_team_games(window)
    if not games:
        return {"future_week_changes_snapshot": None, "expected": False}
    from copy import deepcopy

    leak = deepcopy(games[0])
    leak.week = as_of_week
    leak.game_id = "LEAK_FUTURE"
    leak.off_epa_sum = 50.0
    leak.off_epa_n = 80
    return {
        "future_week_changes_snapshot": future_week_changes_snapshot(
            games, team=leak.team, as_of_week=as_of_week, future_game=leak
        ),
        "expected": False,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--nfl-season", type=int, default=2025)
    p.add_argument("--nfl-as-of-week", type=int, default=18)
    p.add_argument("--cfb-season", type=int, default=2025)
    p.add_argument("--cfb-as-of-week", type=int, default=13)
    p.add_argument(
        "--cache",
        type=Path,
        default=ROOT / "data" / "cfb" / "research" / "ke_football_pbp",
    )
    p.add_argument(
        "--ops",
        type=Path,
        default=ROOT / "data" / "ops" / "ke-football-v1-measurement-20260915",
    )
    args = p.parse_args()

    nfl = run_nfl(args.nfl_season, args.nfl_as_of_week, args.cache)
    cfb = run_cfb(args.cfb_season, args.cfb_as_of_week, args.cache)

    ops = args.ops
    _write(ops / "nfl_measurement.json", nfl)
    _write(ops / "cfb_measurement.json", cfb)
    _write(
        ops / "disruption_inventory.json",
        {"nfl": nfl.get("disruption_inventory"), "cfb": cfb.get("disruption_inventory")},
    )
    _write(
        ops / "validation.json",
        {
            "forbidden_objectives": ["ats", "close", "roi", "kei", "issue_562_totals"],
            "nfl": nfl.get("validation"),
            "cfb": cfb.get("validation"),
            "nfl_leakage_live": nfl.get("leakage_live"),
            "cfb_leakage_live": cfb.get("leakage_live"),
        },
    )
    _write(
        ops / "provenance.json",
        {
            "taxonomy": ["RAW", "DERIVED", "ADJUSTED", "MODELED"],
            "amend": "docs/ratings/KE_FOOTBALL_V1_PROVENANCE_AMEND_2026-09-15.md",
            "nfl": nfl.get("validation", {}).get("provenance"),
            "cfb": cfb.get("validation", {}).get("provenance"),
            "production_promote": False,
        },
    )
    print(json.dumps({"nfl_examples": len(nfl.get("examples") or []), "cfb_examples": len(cfb.get("examples") or []), "ops": str(ops)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
