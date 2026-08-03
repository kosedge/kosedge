#!/usr/bin/env python3
"""Stress / sanity validation for the hierarchical NFL season engine.

Writes artifacts under ``data/ops/nfl-season-engine-harden-YYYYMMDD/``.

Examples
--------
python scripts/nfl/harden_validate_season_engine.py --demo --n-sims 40
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Harden/validate NFL season engine")
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--n-sims", type=int, default=40)
    parser.add_argument("--game-reps", type=int, default=200)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--demo", action="store_true", default=True)
    parser.add_argument(
        "--out-dir",
        default="",
        help="Output directory (default data/ops/nfl-season-engine-harden-YYYYMMDD)",
    )
    args = parser.parse_args()

    from src.services.nfl_season_engine import (
        DEFAULT_SEASON_ENGINE_VERSION,
        InjuryPath,
        build_demo_universe,
        evaluate_survivor,
        parse_injury_paths,
        project_game_player_boxes,
        simulate_full_season,
    )
    from src.services.nfl_season_engine.calibration import GAME_SANITY, calibration_notes
    from src.services.nfl_season_engine.injury_paths import apply_injury_paths_for_week

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    out_dir = Path(args.out_dir) if args.out_dir else ROOT / "data" / "ops" / f"nfl-season-engine-harden-{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    universe = build_demo_universe(season=args.season)
    checklist: Dict[str, Any] = {}

    # --- Season win distributions ---
    season = simulate_full_season(
        universe, n_sims=args.n_sims, seed=args.seed, include_diagnostics=True
    )
    means = [v["mean"] for v in season.team_wins.values()]
    checklist["win_distributions"] = {
        "ok": (
            all(math.isfinite(m) for m in means)
            and abs(season.diagnostics["mean_wins_sum"] - 272.0) < 0.05
            and season.diagnostics["win_mean_spread"] >= 2.0
            and GAME_SANITY["team_win_mean"][0]
            <= season.diagnostics["win_mean_min"]
            <= season.diagnostics["win_mean_max"]
            <= GAME_SANITY["team_win_mean"][1]
        ),
        "min": season.diagnostics["win_mean_min"],
        "max": season.diagnostics["win_mean_max"],
        "spread": season.diagnostics["win_mean_spread"],
        "stdev": season.diagnostics["win_mean_stdev"],
        "sum": season.diagnostics["mean_wins_sum"],
    }
    _write(
        out_dir / "season_win_summary.json",
        {
            "engine_version": season.engine_version,
            "n_sims": season.n_sims,
            "diagnostics": season.diagnostics,
            "top_teams": sorted(
                [{"team": t, **s} for t, s in season.team_wins.items()],
                key=lambda r: -r["mean"],
            )[:10],
        },
    )

    # --- BUF@KC box realism ---
    boxes = project_game_player_boxes(
        universe,
        home_team="KC",
        away_team="BUF",
        week=1,
        n_replicates=args.game_reps,
        seed=args.seed,
        include_diagnostics=True,
    )

    def _pe(name: str, team: str | None = None) -> Dict[str, Any]:
        for p in boxes.players:
            if name in p["player_name"] and (team is None or p["team"] == team):
                return p
        raise KeyError(name)

    cook = _pe("Cook", "BUF")
    rice = _pe("Rice", "KC")
    mahomes = _pe("Mahomes")
    checklist["box_scores_buf_kc"] = {
        "ok": (
            cook["point_estimate"]["rush_yards"] <= 110
            and rice["point_estimate"]["rec_yards"] <= 120
            and GAME_SANITY["qb_pass_yards"][0]
            <= mahomes["point_estimate"]["pass_yards"]
            <= GAME_SANITY["qb_pass_yards"][1]
            and boxes.diagnostics.get("share_integrity_home", {}).get("ok")
        ),
        "cook_rush": cook["point_estimate"]["rush_yards"],
        "rice_rec": rice["point_estimate"]["rec_yards"],
        "mahomes_pass": mahomes["point_estimate"]["pass_yards"],
        "script": boxes.game_script_summary,
    }
    _write(
        out_dir / "buf_at_kc_boxes.json",
        {
            "engine_version": boxes.engine_version,
            "game_script_summary": boxes.game_script_summary,
            "players": [
                {
                    "player_name": p["player_name"],
                    "team": p["team"],
                    "position": p["position"],
                    "usage_role": p.get("usage_role"),
                    "point_estimate": p["point_estimate"],
                }
                for p in boxes.players[:16]
            ],
            "diagnostics_keys": sorted(boxes.diagnostics.keys()),
            "share_integrity_home": boxes.diagnostics.get("share_integrity_home"),
        },
    )

    # --- CMC out reallocation ---
    paths = parse_injury_paths(
        [
            {
                "player_name": "Christian McCaffrey",
                "team": "SF",
                "status": "out",
                "week_start": 1,
                "week_end": 3,
            }
        ]
    )
    adj_in, _, adj_rows = apply_injury_paths_for_week(
        universe.rosters, universe.strengths, paths, week=2
    )
    adj_out, _, adj_out_rows = apply_injury_paths_for_week(
        universe.rosters, universe.strengths, paths, week=10
    )
    cmc_h = next(r for r in universe.rosters["SF"] if "McCaffrey" in r.player_name)
    mason_h = next(r for r in universe.rosters["SF"] if "Mason" in r.player_name)
    cmc_in = next(r for r in adj_in["SF"] if r.player_key == cmc_h.player_key)
    mason_in = next(r for r in adj_in["SF"] if r.player_key == mason_h.player_key)
    cmc_out = next(r for r in adj_out["SF"] if r.player_key == cmc_h.player_key)
    checklist["injury_multi_week"] = {
        "ok": (
            bool(adj_rows)
            and adj_rows[0].realloc_notes != "player_not_found_on_roster"
            and cmc_in.rush_share == 0.0
            and mason_in.rush_share > mason_h.rush_share
            and not adj_out_rows
            and cmc_out.rush_share == cmc_h.rush_share
        ),
        "matched_as": adj_rows[0].player_name if adj_rows else None,
        "mason_rush_delta": round(mason_in.rush_share - mason_h.rush_share, 4),
        "outside_week_active": len(adj_out_rows),
    }
    _write(
        out_dir / "cmc_injury_path.json",
        {
            "path": [
                {
                    "player_name": "Christian McCaffrey",
                    "team": "SF",
                    "status": "out",
                    "week_start": 1,
                    "week_end": 3,
                }
            ],
            "week_2_adjustments": [
                {
                    "player_name": r.player_name,
                    "availability": r.availability,
                    "offense_delta": r.offense_delta,
                    "freed_rush_share": r.freed_rush_share,
                    "realloc_notes": r.realloc_notes,
                }
                for r in adj_rows
            ],
            "mason_rush_before": mason_h.rush_share,
            "mason_rush_after": mason_in.rush_share,
        },
    )

    # --- Survivor exclusion ---
    survivor = evaluate_survivor(
        universe,
        week=5,
        n_sims=max(25, args.n_sims // 2),
        seed=args.seed,
        already_used=["KC", "BUF"],
        top_n=16,
        include_diagnostics=True,
    )
    ranked = {r["team"] for r in survivor.ranked_picks}
    checklist["survivor"] = {
        "ok": "KC" not in ranked and "BUF" not in ranked and len(survivor.ranked_picks) >= 1,
        "already_used": survivor.already_used,
        "top3": [
            {"team": r["team"], "win_rate": r["win_rate"], "pick_now_score": r["pick_now_score"]}
            for r in survivor.ranked_picks[:3]
        ],
        "bye_count": survivor.diagnostics.get("bye_count"),
    }
    _write(
        out_dir / "survivor_week5.json",
        {
            "engine_version": survivor.engine_version,
            "already_used": survivor.already_used,
            "ranked_picks": survivor.ranked_picks[:10],
            "formula": survivor.formula,
            "diagnostics": survivor.diagnostics,
        },
    )

    # --- CMC-out game boxes vs healthy ---
    healthy_sf = project_game_player_boxes(
        universe,
        home_team="SF",
        away_team="SEA",
        week=2,
        n_replicates=args.game_reps,
        seed=args.seed,
    )
    injured_sf = project_game_player_boxes(
        universe,
        home_team="SF",
        away_team="SEA",
        week=2,
        n_replicates=args.game_reps,
        seed=args.seed,
        injury_paths=[
            InjuryPath(
                player_name="C.McCaffrey",
                team="SF",
                status="out",
                week_start=1,
                week_end=3,
            )
        ],
        include_diagnostics=True,
    )

    def _rush(players: List[Dict[str, Any]], name: str) -> float:
        for p in players:
            if name in p["player_name"]:
                return float(p["point_estimate"].get("rush_yards") or 0.0)
        return 0.0

    mason_delta = _rush(injured_sf.players, "Mason") - _rush(healthy_sf.players, "Mason")
    cmc_injured = _rush(injured_sf.players, "McCaffrey")
    checklist["cmc_out_boxes"] = {
        "ok": cmc_injured < 5.0 and mason_delta > 10.0,
        "cmc_rush_out": cmc_injured,
        "mason_rush_delta": round(mason_delta, 3),
    }
    _write(
        out_dir / "with_without_cmc_boxes.json",
        {
            "engine_version": injured_sf.engine_version,
            "healthy_mason_rush": _rush(healthy_sf.players, "Mason"),
            "injured_mason_rush": _rush(injured_sf.players, "Mason"),
            "injured_cmc_rush": cmc_injured,
            "injury_adjustments": injured_sf.diagnostics.get("injury_adjustments"),
        },
    )

    summary = {
        "engine_version": DEFAULT_SEASON_ENGINE_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_sims": args.n_sims,
        "game_reps": args.game_reps,
        "seed": args.seed,
        "mode": "demo",
        "calibration": calibration_notes(),
        "checklist": checklist,
        "all_ok": all(bool(v.get("ok")) for v in checklist.values()),
    }
    _write(out_dir / "run_summary.json", summary)
    print(json.dumps(summary, indent=2))
    print(f"\nWrote artifacts → {out_dir}")
    if not summary["all_ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
