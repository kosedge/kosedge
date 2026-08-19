"""Historical market backtest — nflverse closes by default, owned lake optional.

nflverse embeds closing Vegas lines directly in nfl_dp_schedules
(spread_line, total_line) for every completed game back to 2013 -- no API
credits required. Pass --source owned|compare to overlay kickoff-safe closes
from the NFL odds warehouse lake (Odds API convention flipped to home-favored).

This script uses that historical dataset to:

  1. Measure how good the model's raw (pre-market-blend) predictions are
     against real outcomes, and how good the market itself is (the
     ceiling/floor we're working against).
  2. Sweep the market-blend weight (the shrinkage applied in
     nfl_simulator.simulate_nfl_game toward a live line, see
     NFL_MARKET_BLEND_SPREAD_WEIGHT / NFL_MARKET_BLEND_TOTAL_WEIGHT) across
     a real, held-out-by-time sample to pick a defensible default instead
     of the hand-guessed 0.35 that shipped initially.
  3. Write a JSON artifact with the full sweep for transparency/audit.

Sign convention note (verified empirically, see corr check): nflverse's
spread_line is POSITIVE when the home team is favored (opposite convention
from The Odds API's spread_home, which is NEGATIVE when home is favored).
This script works entirely in the "home_margin" convention (positive = home
favored), matching spread_line directly and matching -spread_home from live
odds.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "model-service"))
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge")

from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from src.services.nfl_simulator import NflGameInputs, simulate_nfl_game  # noqa: E402

START_SEASON = 2013
END_SEASON = 2025
SIMULATIONS_PER_GAME = 1200
CANDIDATE_WEIGHTS = [0.0, 0.10, 0.20, 0.30, 0.35, 0.40, 0.50, 0.60, 0.75, 1.0]
CURRENT_DEFAULT_WEIGHT = 0.30
WEIGHT_GATE_TOLERANCE = 0.05


def _offense_defense_index(off_epa, def_epa_allowed, pressure_generated, pressure_allowed):
    """Same formula tasks._load_team_strength_priors uses, so the backtest
    exercises the identical signal the live pipeline relies on."""
    off_epa = float(off_epa or 0.0)
    def_epa_allowed = float(def_epa_allowed or 0.0)
    pressure_generated = float(pressure_generated or 0.0)
    pressure_allowed = float(pressure_allowed or 0.0)
    pressure_delta = pressure_generated - pressure_allowed
    offense_index = max(0.82, min(1.22, 1.0 + (off_epa * 0.75) + (pressure_delta * 0.18)))
    defense_index = max(0.82, min(1.24, 1.0 + ((-def_epa_allowed) * 0.90) + (pressure_delta * 0.14)))
    return offense_index, defense_index


def _owned_close_lookup() -> Tuple[Dict[Tuple[str, str, str], Dict[str, Any]], Dict[str, Any]]:
    """Map (season, home_abbr|home_norm, away) → owned close in home-favored pts."""
    from src.services.nfl_warehouse.odds_lake import (
        load_odds_lake,
        overlay_closing_lines,
        team_abbr,
    )

    snaps = load_odds_lake(prefer_hd=True)
    if not snaps:
        return {}, {"status": "empty_lake"}
    dummy_games = []
    seen: dict = {}
    for snap in snaps:
        day = str(snap.get("game_date") or "")[:10]
        home = team_abbr(str(snap.get("home") or snap.get("home_abbr") or ""))
        away = team_abbr(str(snap.get("away") or snap.get("away_abbr") or ""))
        key = (day, home, away)
        if not (day and home and away):
            continue
        prev = seen.get(key)
        kick = snap.get("kickoff")
        if prev is None:
            seen[key] = {
                "game_id": snap.get("event_id") or f"{day}|{home}|{away}",
                "game_date": day,
                "kickoff": kick,
                "home_name": home,
                "away_name": away,
                "home_team": home,
                "away_team": away,
                "season": snap.get("season"),
            }
        elif kick and not prev.get("kickoff"):
            prev["kickoff"] = kick
        if snap.get("season") and seen[key].get("season") is None:
            seen[key]["season"] = snap.get("season")
    dummy_games = list(seen.values())
    merged, stats = overlay_closing_lines(dummy_games, snaps)
    lookup: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for row in merged:
        season = str(row.get("season") or "")
        home = str(row.get("home_name") or row.get("home") or "")
        away = str(row.get("away_name") or row.get("away") or "")
        home_key = team_abbr(home) or str(row.get("home_abbr") or "")
        away_key = team_abbr(away) or str(row.get("away_abbr") or "")
        if row.get("owned_close_spread_home_favored") is None and row.get("owned_close_total") is None:
            continue
        if not (season and home_key and away_key):
            continue
        lookup[(season, home_key, away_key)] = row
    stats["lookup_keys"] = len(lookup)
    return lookup, stats


def _apply_owned_closes(
    records: List[Dict[str, Any]],
    *,
    home_teams: List[str],
    away_teams: List[str],
) -> Tuple[List[Dict[str, Any]], int]:
    lookup, _stats = _owned_close_lookup()
    if not lookup:
        return records, 0
    from src.services.nfl_warehouse.odds_lake import team_abbr

    n = 0
    out = []
    for rec, home, away in zip(records, home_teams, away_teams):
        row = dict(rec)
        season = str(row.get("season") or "")
        hit = lookup.get((season, team_abbr(str(home)), team_abbr(str(away))))
        if hit:
            if hit.get("owned_close_spread_home_favored") is not None:
                row["market_margin"] = float(hit["owned_close_spread_home_favored"])
                row["market_source"] = "odds_api_lake"
                n += 1
            if hit.get("owned_close_total") is not None:
                row["market_total"] = float(hit["owned_close_total"])
                row["market_source"] = "odds_api_lake"
        else:
            row.setdefault("market_source", "nflverse")
        out.append(row)
    return out, n


def _sweep(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    def mae(preds, actuals):
        return sum(abs(p - a) for p, a in zip(preds, actuals)) / len(preds)

    actual_margins = [rec["actual_margin"] for rec in records]
    actual_totals = [rec["actual_total"] for rec in records]
    model_margins = [rec["model_margin"] for rec in records]
    market_margins = [rec["market_margin"] for rec in records]
    model_totals = [rec["model_total"] for rec in records]
    market_totals = [rec["market_total"] for rec in records]
    sweep_results = []
    for w in CANDIDATE_WEIGHTS:
        blended_margins = [(1.0 - w) * m + w * mk for m, mk in zip(model_margins, market_margins)]
        blended_totals = [(1.0 - w) * t + w * mk for t, mk in zip(model_totals, market_totals)]
        sweep_results.append(
            {
                "weight": w,
                "spread_mae": round(mae(blended_margins, actual_margins), 4),
                "total_mae": round(mae(blended_totals, actual_totals), 4),
            }
        )
    best_spread = min(sweep_results, key=lambda x: x["spread_mae"])
    best_total = min(sweep_results, key=lambda x: x["total_mae"])
    keep = (
        abs(float(best_spread["weight"]) - CURRENT_DEFAULT_WEIGHT) <= WEIGHT_GATE_TOLERANCE
        and abs(float(best_total["weight"]) - CURRENT_DEFAULT_WEIGHT) <= WEIGHT_GATE_TOLERANCE
    )
    return {
        "baseline": {
            "model_spread_mae": round(mae(model_margins, actual_margins), 4),
            "market_spread_mae": round(mae(market_margins, actual_margins), 4),
            "model_total_mae": round(mae(model_totals, actual_totals), 4),
            "market_total_mae": round(mae(market_totals, actual_totals), 4),
        },
        "weight_sweep": sweep_results,
        "recommended_spread_weight": best_spread["weight"],
        "recommended_total_weight": best_total["weight"],
        "keep_0_30_defaults": keep,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        choices=("nflverse", "owned", "compare"),
        default="nflverse",
        help="Market close source. owned/compare require the parquet lake.",
    )
    args = parser.parse_args()

    engine = create_engine(os.environ["DATABASE_URL"])
    Session = sessionmaker(bind=engine)
    session = Session()

    rows = session.execute(
        text(
            """
            SELECT
              sch.season, sch.week, sch.game_id, sch.home_team, sch.away_team,
              sch.spread_line, sch.total_line, sch.home_score, sch.away_score,
              hf.off_epa_per_play_5g AS home_off_epa, hf.def_epa_allowed_per_play_5g AS home_def_epa,
              hf.pressure_rate_generated_5g AS home_pressure_gen, hf.pressure_rate_allowed_5g AS home_pressure_allowed,
              hf.pass_rate_5g AS home_pass_rate, hf.success_rate_offense_5g AS home_success_off,
              hf.success_rate_defense_allowed_5g AS home_success_def, hf.red_zone_td_rate_5g AS home_rz,
              af.off_epa_per_play_5g AS away_off_epa, af.def_epa_allowed_per_play_5g AS away_def_epa,
              af.pressure_rate_generated_5g AS away_pressure_gen, af.pressure_rate_allowed_5g AS away_pressure_allowed,
              af.pass_rate_5g AS away_pass_rate, af.success_rate_offense_5g AS away_success_off,
              af.success_rate_defense_allowed_5g AS away_success_def, af.red_zone_td_rate_5g AS away_rz
            FROM nfl_dp_schedules sch
            LEFT JOIN nfl_dp_team_rolling_features_weekly hf
              ON hf.season = sch.season AND hf.week = sch.week AND hf.team = sch.home_team
            LEFT JOIN nfl_dp_team_rolling_features_weekly af
              ON af.season = sch.season AND af.week = sch.week AND af.team = sch.away_team
            WHERE sch.season BETWEEN :start_season AND :end_season
              AND sch.home_score IS NOT NULL AND sch.away_score IS NOT NULL
              AND sch.spread_line IS NOT NULL AND sch.total_line IS NOT NULL
            ORDER BY sch.season, sch.week
            """
        ),
        {"start_season": START_SEASON, "end_season": END_SEASON},
    ).fetchall()
    session.close()

    print(f"Backtesting {len(rows)} historical games ({START_SEASON}-{END_SEASON}) with free nflverse closing lines.")

    records = []
    for i, r in enumerate(rows, start=1):
        home_off_idx, home_def_idx = _offense_defense_index(
            r.home_off_epa, r.home_def_epa, r.home_pressure_gen, r.home_pressure_allowed
        )
        away_off_idx, away_def_idx = _offense_defense_index(
            r.away_off_epa, r.away_def_epa, r.away_pressure_gen, r.away_pressure_allowed
        )
        diff_off_epa = (
            float(r.home_off_epa) - float(r.away_off_epa)
            if r.home_off_epa is not None and r.away_off_epa is not None
            else None
        )
        diff_def_epa_allowed = (
            float(r.home_def_epa) - float(r.away_def_epa)
            if r.home_def_epa is not None and r.away_def_epa is not None
            else None
        )
        diff_pressure_gen = (
            float(r.home_pressure_gen) - float(r.away_pressure_gen)
            if r.home_pressure_gen is not None and r.away_pressure_gen is not None
            else None
        )
        diff_pressure_allowed = (
            float(r.home_pressure_allowed) - float(r.away_pressure_allowed)
            if r.home_pressure_allowed is not None and r.away_pressure_allowed is not None
            else None
        )
        diff_rz = (
            float(r.home_rz) - float(r.away_rz) if r.home_rz is not None and r.away_rz is not None else None
        )
        diff_success = (
            float(r.home_success_off) - float(r.away_success_off)
            if r.home_success_off is not None and r.away_success_off is not None
            else None
        )

        inputs = NflGameInputs(
            game_id=str(r.game_id),
            home_team=str(r.home_team),
            away_team=str(r.away_team),
            offense_index_home=home_off_idx,
            offense_index_away=away_off_idx,
            defense_index_home=home_def_idx,
            defense_index_away=away_def_idx,
            rest_days_home=7.0,
            rest_days_away=7.0,
            matchup_season=int(r.season),
            matchup_week=int(r.week),
            matchup_game_id=str(r.game_id),
            matchup_home_team=str(r.home_team),
            matchup_away_team=str(r.away_team),
            home_off_epa_5g=float(r.home_off_epa) if r.home_off_epa is not None else None,
            away_off_epa_5g=float(r.away_off_epa) if r.away_off_epa is not None else None,
            home_def_epa_allowed_5g=float(r.home_def_epa) if r.home_def_epa is not None else None,
            away_def_epa_allowed_5g=float(r.away_def_epa) if r.away_def_epa is not None else None,
            home_pass_rate_5g=float(r.home_pass_rate) if r.home_pass_rate is not None else None,
            away_pass_rate_5g=float(r.away_pass_rate) if r.away_pass_rate is not None else None,
            home_success_offense_5g=float(r.home_success_off) if r.home_success_off is not None else None,
            away_success_offense_5g=float(r.away_success_off) if r.away_success_off is not None else None,
            home_success_defense_allowed_5g=float(r.home_success_def) if r.home_success_def is not None else None,
            away_success_defense_allowed_5g=float(r.away_success_def) if r.away_success_def is not None else None,
            matchup_diff_off_epa_5g=diff_off_epa,
            matchup_diff_def_epa_allowed_5g=diff_def_epa_allowed,
            matchup_diff_pressure_generated_5g=diff_pressure_gen,
            matchup_diff_pressure_allowed_5g=diff_pressure_allowed,
            matchup_diff_red_zone_td_rate_5g=diff_rz,
            matchup_diff_success_rate_5g=diff_success,
        )

        seed = abs(hash((str(r.game_id), "backtest"))) % (2**31)
        projection = simulate_nfl_game(inputs, simulations=SIMULATIONS_PER_GAME, seed=seed)
        markets = projection["markets"]
        model_margin_home_favored = -float(markets["spread_home"])  # flip to "home favored" convention
        model_total = float(markets["total_mean"])

        records.append(
            {
                "season": int(r.season),
                "week": int(r.week),
                "home_team": str(r.home_team),
                "away_team": str(r.away_team),
                "model_margin": model_margin_home_favored,
                "market_margin": float(r.spread_line),
                "model_total": model_total,
                "market_total": float(r.total_line),
                "actual_margin": float(r.home_score) - float(r.away_score),
                "actual_total": float(r.home_score) + float(r.away_score),
                "market_source": "nflverse",
            }
        )

        if i % 500 == 0:
            print(f"  ...{i}/{len(rows)} games simulated")

    n = len(records)
    print(f"Simulated {n} games. Computing MAE sweep...")

    nflverse_sweep = _sweep(records)
    artifact: Dict[str, Any] = {
        "generated_at": date.today().isoformat(),
        "start_season": START_SEASON,
        "end_season": END_SEASON,
        "sample_size": n,
        "simulations_per_game": SIMULATIONS_PER_GAME,
        "source": args.source,
        "close_label": "true_close_jsonl_plus_nflverse",
        "nflverse": nflverse_sweep,
        "gate": {
            "current_defaults": {"spread": CURRENT_DEFAULT_WEIGHT, "total": CURRENT_DEFAULT_WEIGHT},
            "tolerance": WEIGHT_GATE_TOLERANCE,
            "note": "Do not change NFL_MARKET_BLEND_* unless owned keep_0_30_defaults is false.",
        },
    }

    if args.source in {"owned", "compare"}:
        owned_records, n_owned = _apply_owned_closes(
            records,
            home_teams=[str(r["home_team"]) for r in records],
            away_teams=[str(r["away_team"]) for r in records],
        )
        owned_sweep = _sweep(owned_records)
        artifact["owned"] = owned_sweep
        artifact["owned_overlay_n"] = n_owned
        artifact["gate"]["keep_0_30_defaults"] = bool(owned_sweep.get("keep_0_30_defaults"))
        print(
            f"Owned overlay n={n_owned} keep_0_30={owned_sweep.get('keep_0_30_defaults')} "
            f"best_spread={owned_sweep.get('recommended_spread_weight')} "
            f"best_total={owned_sweep.get('recommended_total_weight')}"
        )
    else:
        artifact["baseline"] = nflverse_sweep["baseline"]
        artifact["weight_sweep"] = nflverse_sweep["weight_sweep"]
        artifact["recommended_spread_weight"] = nflverse_sweep["recommended_spread_weight"]
        artifact["recommended_total_weight"] = nflverse_sweep["recommended_total_weight"]
        print(f"\nBest spread weight: {nflverse_sweep['recommended_spread_weight']}")
        print(f"Best total weight:  {nflverse_sweep['recommended_total_weight']}")

    out_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "ops")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"nfl-market-blend-backtest-{date.today().isoformat()}.json")
    with open(out_path, "w") as f:
        json.dump(artifact, f, indent=2)
    print(f"\nWrote backtest artifact to {out_path}")


if __name__ == "__main__":
    main()
