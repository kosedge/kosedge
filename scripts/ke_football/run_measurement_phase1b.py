#!/usr/bin/env python3
"""KE Football v1 Phase 1B — measurement validation and repair (research only).

Repairs NFL finishing drive boundaries, validates each KE component,
runs a PIT opponent-adjustment bakeoff, writes a Ryan-readable scorecard.

Does not weight Team Strength. Does not touch production scoring/boards/UI.
ATS / close / ROI / CLV are forbidden objectives.
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

from src.services.ke_football import PIPELINE_VERSION, PRODUCTION_PROMOTE, TAXONOMY
from src.services.ke_football.adapters import adapt_rows
from src.services.ke_football.aggregate import build_team_games, filter_week_lt
from src.services.ke_football.bakeoff import future_week_changes_any_method, run_bakeoff
from src.services.ke_football.component_validate import validate_all_components
from src.services.ke_football.disruption import inventory_report
from src.services.ke_football.finishing import finishing_diagnosis
from src.services.ke_football.opp_adj import future_week_changes_snapshot
from src.services.ke_football.pipeline import run_measurement
from src.services.ke_football.sanity import build_sanity
from src.services.ke_football.scorecard import build_scorecard

NFL_PBP = "https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{season}.parquet"
CFB_PBP = (
    "https://github.com/sportsdataverse/sportsdataverse-data/releases/download/"
    "espn_cfb_pbp/play_by_play_{season}.parquet"
)
UA = "kosedge-ke-football-measurement-phase1b/1.0"


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


def _rows(df, *, limit: int | None = None) -> List[Dict[str, Any]]:
    if limit is not None:
        df = df.head(limit)
    return df.to_dict(orient="records")


def _write(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str) + "\n", encoding="utf-8")


def _leak_game(games):
    from copy import deepcopy

    leak = deepcopy(games[0])
    leak.week = max(g.week for g in games) + 1
    leak.game_id = "LEAK_FUTURE"
    leak.off_epa_sum = 50.0
    leak.off_epa_n = 80
    return leak


def run_sport(
    *,
    sport: str,
    season: int,
    as_of_week: int,
    cache: Path,
    example_teams: List[str],
    early_through: int,
    late_from: int,
    selection_weeks: tuple[int, int],
    confirmation_weeks: tuple[int, int],
    full_weeks: tuple[int, int],
) -> Dict[str, Any]:
    if sport == "nfl":
        path = _download(NFL_PBP.format(season=season), cache / f"nfl_pbp_{season}.parquet")
        df = _load_parquet(path)
        if "season_type" in df.columns:
            df = df[df["season_type"].astype(str).str.upper().eq("REG")]
        elif "game_type" in df.columns:
            df = df[df["game_type"].astype(str).str.upper().eq("REG")]
        url = NFL_PBP.format(season=season)
    else:
        path = _download(CFB_PBP.format(season=season), cache / f"cfb_pbp_{season}.parquet")
        df = _load_parquet(path)
        url = CFB_PBP.format(season=season)

    plays = adapt_rows(sport, _rows(df))
    window = filter_week_lt(plays, season=season, as_of_week=as_of_week)
    games = build_team_games(window)
    finish = finishing_diagnosis(window) if sport == "nfl" else {"sport": "cfb", "note": "CFB type.text heuristic unchanged"}
    inventory = inventory_report(sport=sport, plays=window)
    validation = validate_all_components(
        games,
        sport=sport,
        season=season,
        early_through=early_through,
        late_from=late_from,
    )
    bakeoff = run_bakeoff(
        games,
        selection_weeks=selection_weeks,
        confirmation_weeks=confirmation_weeks,
        full_weeks=full_weeks,
    )
    names = {p.offense for p in window} | {g.team for g in games}
    examples = [t for t in example_teams if t in names]
    if not examples:
        examples = sorted({g.team for g in games})[:8]
    sanity = build_sanity(games, sport=sport, example_teams=examples, min_games=4)
    scorecard = build_scorecard(
        sport=sport,
        validation=validation,
        inventory=inventory,
        bakeoff=bakeoff,
        finishing=finish,
    )
    measurement = run_measurement(
        plays, sport=sport, season=season, as_of_week=as_of_week, example_teams=examples
    )
    leak = _leak_game(games) if games else None
    leakage = {
        "future_week_changes_snapshot": (
            future_week_changes_snapshot(games, team=leak.team, as_of_week=as_of_week, future_game=leak)
            if leak
            else None
        ),
        "future_week_changes_any_bakeoff_method": (
            future_week_changes_any_method(games, team=leak.team, as_of_week=as_of_week, future_game=leak)
            if leak
            else None
        ),
        "expected": False,
    }
    compact = {k: v for k, v in measurement.items() if k != "snapshots"}
    compact["snapshot_count"] = len(measurement.get("snapshots") or [])
    compact["ranking"] = measurement.get("validation", {}).get("ranking_sanity")
    compact["finishing_diagnosis"] = finish
    compact["leakage_live"] = leakage
    compact["source"] = {
        "url": url,
        "path": str(path),
        "bytes": path.stat().st_size,
        "n_plays_adapted": len(plays),
        "historical_lake_write": False,
    }
    return {
        "pipeline_version": PIPELINE_VERSION,
        "production_promote": PRODUCTION_PROMOTE,
        "taxonomy": list(TAXONOMY),
        "sport": sport,
        "season": season,
        "as_of_week": as_of_week,
        "measurement": compact,
        "component_validation": validation,
        "bakeoff": bakeoff,
        "sanity": sanity,
        "scorecard": scorecard,
        "disruption_inventory": inventory,
        "finishing_diagnosis": finish,
        "leakage_live": leakage,
        "hard_stops": {
            "team_strength": False,
            "scoring": False,
            "matchup": False,
            "market": False,
            "ui": False,
            "named_havoc_weights": False,
            "issue_562_tuning": False,
        },
    }


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


def write_scorecard_md(path: Path, nfl: Dict[str, Any], cfb: Dict[str, Any]) -> None:
    def section(blob: Dict[str, Any]) -> str:
        sc = blob["scorecard"]
        lines = [
            f"### {blob['sport'].upper()} {blob['season']} as_of {blob['as_of_week']}",
            "",
            f"Team-games: {blob['component_validation']['n_team_games']}. "
            f"Bakeoff winner: `{blob['bakeoff']['winner']}`.",
            "",
            _md_table(
                [
                    {
                        "id": g["id"],
                        "grade": g["grade"],
                        "p2": "yes" if g.get("phase2_eligible") else "no",
                        "rec": g.get("recommendation"),
                    }
                    for g in sc["grades"]
                ],
                [("ID", "id"), ("Grade", "grade"), ("Phase 2", "p2"), ("Recommendation", "rec")],
            ),
            "",
            f"Counts: {json.dumps(sc['counts'])}",
            "",
        ]
        finish = blob.get("finishing_diagnosis") or {}
        if blob["sport"] == "nfl":
            lines += [
                "Finishing repair (owned nflverse):",
                "",
                f"- kickoff yl≤40 rate: {finish.get('kickoff_false_opp_rate')}",
                f"- opportunity rate: {finish.get('opportunity_rate')}",
                f"- PPO repaired: {finish.get('ppo_repaired')}",
                f"- finish repaired: {finish.get('finish_repaired')}",
                f"- calibrated: {finish.get('calibrated')}",
                "",
            ]
        return "\n".join(lines)

    text = "\n".join(
        [
            "# KE Football v1 — Phase 1B component scorecard",
            "",
            "**Status:** `MEASUREMENT_PHASE1B` · `production_promote=false`",
            "**GO:** Ryan review of #570 Phase 1 → measurement validation and repair only.",
            "**STOP:** Team Strength / composite weights, scoring, matchup, market, UI, boards, named KE Disruption.",
            "",
            "Architecture preserved: RAW → DERIVED → ADJUSTED → MODELED. Week W never consumes post-W info.",
            "Objectives are football-only (EPA, success, explosiveness, finishing, pace). Not ATS/ROI/CLV.",
            "",
            section(nfl),
            section(cfb),
            "## Phase 2 eligibility (measurement only)",
            "",
            "Eligible IDs may enter a later Team Strength GO as independent measurements. "
            "This PR does not assign weights.",
            "",
            f"- NFL eligible: {', '.join(nfl['scorecard']['phase2_eligible_ids'])}",
            f"- NFL hold: {', '.join(nfl['scorecard']['phase2_hold_ids'])}",
            f"- CFB eligible: {', '.join(cfb['scorecard']['phase2_eligible_ids'])}",
            f"- CFB hold: {', '.join(cfb['scorecard']['phase2_hold_ids'])}",
            "",
            "Narrative: `docs/ratings/KE_FOOTBALL_V1_MEASUREMENT_PHASE1B_2026-09-15.md`.",
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
        default=ROOT / "data" / "ops" / "ke-football-v1-phase1b-20260915",
    )
    args = p.parse_args()

    nfl = run_sport(
        sport="nfl",
        season=args.nfl_season,
        as_of_week=args.nfl_as_of_week,
        cache=args.cache,
        example_teams=["KC", "BUF", "PHI", "BAL", "SF", "DET", "NE", "CLE", "HOU", "LV"],
        early_through=6,
        late_from=10,
        selection_weeks=(5, 10),
        confirmation_weeks=(11, 18),
        full_weeks=(3, 18),
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
            "Michigan Wolverines",
            "Texas Longhorns",
            "Vanderbilt Commodores",
            "Kent State Golden Flashes",
        ],
        early_through=5,
        late_from=9,
        selection_weeks=(4, 8),
        confirmation_weeks=(9, 13),
        full_weeks=(3, 13),
    )

    ops = args.ops
    _write(ops / "nfl_phase1b.json", {k: v for k, v in nfl.items() if k != "component_validation"})
    _write(ops / "cfb_phase1b.json", {k: v for k, v in cfb.items() if k != "component_validation"})
    _write(ops / "nfl_component_validation.json", nfl["component_validation"])
    _write(ops / "cfb_component_validation.json", cfb["component_validation"])
    _write(ops / "bakeoff.json", {"nfl": nfl["bakeoff"], "cfb": cfb["bakeoff"]})
    _write(ops / "sanity.json", {"nfl": nfl["sanity"], "cfb": cfb["sanity"]})
    _write(ops / "scorecard.json", {"nfl": nfl["scorecard"], "cfb": cfb["scorecard"]})
    _write(
        ops / "finishing_diagnosis.json",
        {"nfl": nfl["finishing_diagnosis"], "cfb": cfb["finishing_diagnosis"]},
    )
    _write(
        ops / "disruption_inventory.json",
        {"nfl": nfl["disruption_inventory"], "cfb": cfb["disruption_inventory"]},
    )
    write_scorecard_md(ops / "SCORECARD.md", nfl, cfb)
    print(
        json.dumps(
            {
                "ops": str(ops),
                "nfl_winner": nfl["bakeoff"]["winner"],
                "cfb_winner": cfb["bakeoff"]["winner"],
                "nfl_ppo": (nfl["finishing_diagnosis"] or {}).get("ppo_repaired"),
                "nfl_finish": (nfl["finishing_diagnosis"] or {}).get("finish_repaired"),
                "production_promote": False,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
