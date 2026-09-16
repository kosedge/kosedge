#!/usr/bin/env python3
"""KE Football v1 Phase 2A — Off/Def Efficiency unit ratings (research only).

Does not build Team Strength. Does not reopen opponent adjustment.
Does not fit ATS / close / ROI / CLV. Production boards/UI untouched.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
MS = ROOT / "services" / "model-service"
if str(MS) not in sys.path:
    sys.path.insert(0, str(MS))

from src.services.ke_football import PIPELINE_VERSION, PRODUCTION_PROMOTE
from src.services.ke_football.adapters import adapt_rows
from src.services.ke_football.aggregate import build_team_games, filter_week_lt
from src.services.ke_football.unit_ratings import clear_z_cache
from src.services.ke_football.unit_validate import run_phase2a

NFL_PBP = "https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{season}.parquet"
CFB_PBP = (
    "https://github.com/sportsdataverse/sportsdataverse-data/releases/download/"
    "espn_cfb_pbp/play_by_play_{season}.parquet"
)
UA = "kosedge-ke-football-unit-ratings-phase2a/1.0"


def _download(url: str, dest: Path, *, timeout: int = 300) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    import urllib.request

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


def _write(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str) + "\n", encoding="utf-8")


def _md_table(rows: List[Dict[str, Any]], cols: List[tuple[str, str]]) -> str:
    head = "| " + " | ".join(c[0] for c in cols) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    body = []
    for row in rows:
        cells = []
        for _title, key in cols:
            val = row.get(key)
            if isinstance(val, float):
                cells.append(f"{val:.3f}")
            elif val is None:
                cells.append("—")
            else:
                cells.append(str(val))
        body.append("| " + " | ".join(cells) + " |")
    return "\n".join([head, sep, *body])


def load_plays(sport: str, season: int, cache: Path):
    if sport == "nfl":
        path = _download(NFL_PBP.format(season=season), cache / f"nfl_pbp_{season}.parquet")
        df = _load_parquet(path)
        if "season_type" in df.columns:
            df = df[df["season_type"].astype(str).str.upper().eq("REG")]
        elif "game_type" in df.columns:
            df = df[df["game_type"].astype(str).str.upper().eq("REG")]
    else:
        path = _download(CFB_PBP.format(season=season), cache / f"cfb_pbp_{season}.parquet")
        df = _load_parquet(path)
    plays = adapt_rows(sport, df.to_dict(orient="records"))
    return plays, path


def run_sport(
    *,
    sport: str,
    season: int,
    as_of_week: int,
    cache: Path,
    example_teams: List[str],
    selection_weeks: tuple[int, int],
    confirmation_weeks: tuple[int, int],
    full_weeks: tuple[int, int],
    early_through: int,
    late_from: int,
) -> Dict[str, Any]:
    plays, path = load_plays(sport, season, cache)
    window = filter_week_lt(plays, season=season, as_of_week=as_of_week)
    games = build_team_games(window)
    clear_z_cache()
    out = run_phase2a(
        games,
        sport=sport,
        season=season,
        as_of_week=as_of_week,
        example_teams=example_teams,
        selection_weeks=selection_weeks,
        confirmation_weeks=confirmation_weeks,
        full_weeks=full_weeks,
        early_through=early_through,
        late_from=late_from,
    )
    out["source"] = {
        "path": str(path),
        "bytes": path.stat().st_size,
        "n_plays_window": len(window),
        "n_team_games": len(games),
        "historical_lake_write": False,
    }
    out["pipeline_version"] = PIPELINE_VERSION
    return out


def write_scorecard_md(path: Path, nfl: Dict[str, Any], cfb: Dict[str, Any]) -> None:
    def section(blob: Dict[str, Any]) -> str:
        lines = [
            f"### {blob['sport'].upper()} {blob['season']} as_of {blob['as_of_week']}",
            "",
            f"Off winner: `{blob['methods']['off']}` · Def winner: `{blob['methods']['def']}`",
            "",
        ]
        for side in ("off", "def"):
            ev = blob["bakeoff"][side]
            g = blob["grades"][side]
            lines += [
                f"**{side} unit** — {g['grade']} · {g['recommendation']}",
                "",
                _md_table(
                    [
                        {
                            "method": name,
                            "mae": row["confirmation"]["mae"],
                            "r": row["confirmation"]["pearson"],
                            "n": row["confirmation"]["n"],
                            "beat": row.get("beats_strongest_constituent"),
                        }
                        for name, row in ev["candidates"].items()
                    ],
                    [
                        ("Method", "method"),
                        ("Conf MAE", "mae"),
                        ("Conf r", "r"),
                        ("n", "n"),
                        ("Beats EPA?", "beat"),
                    ],
                ),
                "",
                f"Earned PARTIAL features: {ev.get('earned_partial_features')}",
                f"Finishing earned: {ev.get('finishing_earned')}",
                f"shrink k: {ev.get('shrink_k')}",
                "",
            ]
        return "\n".join(lines)

    text = "\n".join(
        [
            "# KE Football v1 — Phase 2A unit rating scorecard",
            "",
            "**Status:** `UNIT_RATINGS_PHASE2A` · `production_promote=false`",
            "**STOP:** Team Strength, overall weights, matchup, scoring, market, ATS, UI, boards.",
            "",
            "`NO_ADJUSTMENT_WINNER` accepted. Opponent adjustment was not reopened.",
            "Complexity must beat trailing EPA. If it does not, the unit rating is shrunken/raw EPA.",
            "",
            section(nfl),
            section(cfb),
            "Narrative: `docs/ratings/KE_FOOTBALL_V1_UNIT_RATINGS_PHASE2A_2026-09-16.md`.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


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
        default=ROOT / "data" / "ops" / "ke-football-v1-phase2a-20260916",
    )
    args = p.parse_args()

    nfl = run_sport(
        sport="nfl",
        season=args.nfl_season,
        as_of_week=args.nfl_as_of_week,
        cache=args.cache,
        example_teams=["KC", "BUF", "PHI", "NE", "SF", "HOU", "CLE", "LV"],
        selection_weeks=(5, 10),
        confirmation_weeks=(11, 18),
        full_weeks=(3, 18),
        early_through=6,
        late_from=10,
    )
    cfb = run_sport(
        sport="cfb",
        season=args.cfb_season,
        as_of_week=args.cfb_as_of_week,
        cache=args.cache,
        example_teams=[
            "Georgia Bulldogs",
            "Ohio State Buckeyes",
            "Alabama Crimson Tide",
            "Oregon Ducks",
            "Vanderbilt Commodores",
            "Texas Longhorns",
        ],
        selection_weeks=(4, 8),
        confirmation_weeks=(9, 13),
        full_weeks=(3, 13),
        early_through=5,
        late_from=9,
    )

    ops = args.ops
    compact_keys = (
        "pipeline",
        "pipeline_version",
        "production_promote",
        "sport",
        "season",
        "as_of_week",
        "feature_policy",
        "methods",
        "fits",
        "bakeoff",
        "grades",
        "ranking_sanity",
        "examples",
        "leakage_live",
        "hard_stops",
        "source",
        "incremental_over_epa",
        "persistence",
        "stability",
        "outlier_sensitivity",
        "stop",
        "opp_adj_reopened",
        "opp_adj_result",
        "n_snapshots",
    )
    _write(ops / "nfl_phase2a.json", {k: nfl[k] for k in compact_keys if k in nfl})
    _write(ops / "cfb_phase2a.json", {k: cfb[k] for k in compact_keys if k in cfb})
    _write(ops / "scorecard.json", {"nfl": nfl["grades"], "cfb": cfb["grades"]})
    write_scorecard_md(ops / "SCORECARD.md", nfl, cfb)
    print(
        json.dumps(
            {
                "ops": str(ops),
                "nfl_off": nfl["methods"]["off"],
                "nfl_def": nfl["methods"]["def"],
                "cfb_off": cfb["methods"]["off"],
                "cfb_def": cfb["methods"]["def"],
                "nfl_off_grade": nfl["grades"]["off"]["grade"],
                "nfl_def_grade": nfl["grades"]["def"]["grade"],
                "cfb_off_grade": cfb["grades"]["off"]["grade"],
                "cfb_def_grade": cfb["grades"]["def"]["grade"],
                "production_promote": PRODUCTION_PROMOTE,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
