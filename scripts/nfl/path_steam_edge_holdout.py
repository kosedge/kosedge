#!/usr/bin/env python3
"""Chronological steam-filter holdout — research only, no live promote.

Uses kickoff-safe lake path (open / 7d / 3d / 1d / close) plus the same raw
simulator the blend backtest uses. Asks two questions:

  1. Filter: does agreeing with 7d→close steam improve PLAY-band ATS/ROI
     on 2024–2025 vs the unfiltered PLAY band?
  2. Residual: does steam explain leftover model error enough to justify
     fitting supervised schema v5? (do not fit here)

Writes data/ops/nfl-path-steam-edge-holdout.json
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date
from typing import Any, Dict, List, Optional, Sequence, Tuple

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, os.path.join(ROOT, "services", "model-service"))
sys.path.insert(0, ROOT)
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge")

from sqlalchemy import create_engine, text  # noqa: E402

from scripts.nfl.historical_market_backtest import (  # noqa: E402
    SIMULATIONS_PER_GAME,
    _offense_defense_index,
    _owned_close_lookup,
)
from src.services.nfl_simulator import NflGameInputs, simulate_nfl_game  # noqa: E402
from src.services.nfl_warehouse.odds_lake import team_abbr  # noqa: E402
from src.services.nfl_warehouse.path_features import (  # noqa: E402
    in_play_band,
    sides_agree,
    steam_home_favored,
)

HOLDOUT_SEASONS = {2024, 2025}
CONFIRM_SEASONS = {2020, 2021, 2022, 2023}
WIN_PROFIT = 100.0 / 110.0
ATS_LIFT_MIN = 0.02
RESIDUAL_CORR_MIN = 0.08
OUT = os.path.join(ROOT, "data", "ops", "nfl-path-steam-edge-holdout.json")


def _unit_pnl(won: Optional[bool]) -> float:
    if won is None:
        return 0.0
    return WIN_PROFIT if won else -1.0


def _ats(actual_margin: float, market_margin: float, bet_home: bool) -> Optional[bool]:
    if abs(actual_margin - market_margin) < 1e-9:
        return None
    home_covers = actual_margin > market_margin
    return home_covers if bet_home else (not home_covers)


def _corr(xs: Sequence[float], ys: Sequence[float]) -> Optional[float]:
    n = len(xs)
    if n < 20:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = sum((x - mx) ** 2 for x in xs) ** 0.5
    dy = sum((y - my) ** 2 for y in ys) ** 0.5
    if dx == 0 or dy == 0:
        return None
    return num / (dx * dy)


def _slice_stats(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    decided = [r for r in rows if r.get("won") is not None]
    n = len(decided)
    if n == 0:
        return {"n": 0, "ats": None, "roi": None, "units": 0.0, "mean_abs_edge": None}
    hits = sum(1 for r in decided if r["won"])
    units = sum(_unit_pnl(r["won"]) for r in decided)
    return {
        "n": n,
        "ats": round(hits / n, 4),
        "roi": round(units / n, 4),
        "units": round(units, 3),
        "mean_abs_edge": round(sum(r["abs_edge"] for r in decided) / n, 3),
    }


def _load_schedule() -> List[Any]:
    engine = create_engine(os.environ["DATABASE_URL"])
    with engine.connect() as conn:
        return list(
            conn.execute(
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
                    WHERE sch.season BETWEEN 2020 AND 2025
                      AND sch.home_score IS NOT NULL AND sch.away_score IS NOT NULL
                      AND sch.spread_line IS NOT NULL
                    ORDER BY sch.season, sch.week
                    """
                )
            )
        )


def main() -> int:
    lookup, lake_stats = _owned_close_lookup()
    rows = _load_schedule()
    print(f"schedule={len(rows)} lake_keys={lake_stats.get('lookup_keys')}", flush=True)

    records: List[Dict[str, Any]] = []
    for i, r in enumerate(rows, start=1):
        home_off_idx, home_def_idx = _offense_defense_index(
            r.home_off_epa, r.home_def_epa, r.home_pressure_gen, r.home_pressure_allowed
        )
        away_off_idx, away_def_idx = _offense_defense_index(
            r.away_off_epa, r.away_def_epa, r.away_pressure_gen, r.away_pressure_allowed
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
        )
        seed = abs(hash((str(r.game_id), "path-steam"))) % (2**31)
        markets = simulate_nfl_game(inputs, simulations=SIMULATIONS_PER_GAME, seed=seed)["markets"]
        model_margin = -float(markets["spread_home"])
        owned = lookup.get((str(int(r.season)), team_abbr(str(r.home_team)), team_abbr(str(r.away_team))))
        market_margin = (
            float(owned["owned_close_spread_home_favored"])
            if owned and owned.get("owned_close_spread_home_favored") is not None
            else float(r.spread_line)
        )
        actual_margin = float(r.home_score) - float(r.away_score)
        edge = model_margin - market_margin
        open_hf = None
        if owned and owned.get("open_spread_home") is not None:
            open_hf = -float(owned["open_spread_home"])
        steam_hf = steam_home_favored((owned or {}).get("steam_spread_pre7d"))
        steam_source = "pre7d" if steam_hf is not None else None
        if steam_hf is None and open_hf is not None:
            steam_hf = float(market_margin) - float(open_hf)
            steam_source = "open_to_close"
        steam_1d = steam_home_favored((owned or {}).get("steam_spread_pre1d"))
        if steam_1d is None:
            steam_1d = steam_home_favored((owned or {}).get("steam_spread_pre3d"))
        bet_home = edge > 0
        won = _ats(actual_margin, market_margin, bet_home)
        clv = None
        if open_hf is not None:
            clv = (market_margin - open_hf) if bet_home else (open_hf - market_margin)
        rec = {
            "season": int(r.season),
            "week": int(r.week),
            "abs_edge": abs(edge),
            "edge": edge,
            "steam_hf": steam_hf,
            "steam_1d": steam_1d,
            "steam_source": steam_source,
            "play": in_play_band(abs(edge)),
            "agree_7d": sides_agree(edge, steam_hf),
            "disagree_7d": sides_agree(-edge, steam_hf),
            "agree_1d": sides_agree(edge, steam_1d),
            "won": won,
            "clv": clv,
            "residual": actual_margin - model_margin,
            "owned": bool(owned),
            "source": "odds_api_lake" if owned else "nflverse",
        }
        records.append(rec)
        if i % 400 == 0:
            print(f"  ...{i}/{len(rows)}", flush=True)

    def pick(seasons: set[int], pred) -> List[Dict[str, Any]]:
        return [r for r in records if r["season"] in seasons and pred(r)]

    hold_play = pick(HOLDOUT_SEASONS, lambda r: r["play"])
    hold_agree = pick(HOLDOUT_SEASONS, lambda r: r["play"] and r["agree_7d"])
    hold_fade = pick(HOLDOUT_SEASONS, lambda r: r["play"] and r["disagree_7d"])
    hold_agree_1d = pick(HOLDOUT_SEASONS, lambda r: r["play"] and r["agree_1d"])
    conf_play = pick(CONFIRM_SEASONS, lambda r: r["play"])
    conf_agree = pick(CONFIRM_SEASONS, lambda r: r["play"] and r["agree_7d"])

    hold_play_s = _slice_stats(hold_play)
    hold_agree_s = _slice_stats(hold_agree)
    lift = None
    if hold_play_s["ats"] is not None and hold_agree_s["ats"] is not None:
        lift = round(hold_agree_s["ats"] - hold_play_s["ats"], 4)
    promote_filter = bool(
        hold_agree_s["n"] >= 80
        and lift is not None
        and lift >= ATS_LIFT_MIN
        and (hold_agree_s["roi"] or 0) > 0
    )

    def residual_pair(seasons: set[int]) -> Tuple[Optional[float], int]:
        xs = []
        ys = []
        for r in records:
            if r["season"] not in seasons or r["steam_hf"] is None:
                continue
            xs.append(float(r["steam_hf"]))
            ys.append(float(r["residual"]))
        return _corr(xs, ys), len(xs)

    corr_conf, n_conf = residual_pair(CONFIRM_SEASONS)
    corr_hold, n_hold = residual_pair(HOLDOUT_SEASONS)
    same_sign = (
        corr_conf is not None
        and corr_hold is not None
        and ((corr_conf > 0) == (corr_hold > 0))
    )
    fit_v5 = bool(
        corr_conf is not None
        and abs(corr_conf) >= RESIDUAL_CORR_MIN
        and same_sign
        and n_hold >= 80
    )

    clv_hold = [r["clv"] for r in hold_play if r.get("clv") is not None]
    report = {
        "generated_at": date.today().isoformat(),
        "product": False,
        "close_label": "true_close_jsonl_plus_nflverse",
        "lake": {k: lake_stats.get(k) for k in ("games", "matched", "matched_with_close_spread", "lookup_keys")},
        "sample": {
            "schedule_2020_2025": len(rows),
            "owned_join": sum(1 for r in records if r["owned"]),
            "steam_pre7d": sum(1 for r in records if r.get("steam_source") == "pre7d"),
            "steam_open_to_close": sum(1 for r in records if r.get("steam_source") == "open_to_close"),
            "holdout_seasons": sorted(HOLDOUT_SEASONS),
            "confirm_seasons": sorted(CONFIRM_SEASONS),
        },
        "play_band": {"abs_edge_min": 2.5, "abs_edge_max": 7.0, "min_steam_pts": 1.0},
        "holdout_2024_2025": {
            "play_all": hold_play_s,
            "play_agree_steam_7d": hold_agree_s,
            "play_fade_steam_7d": _slice_stats(hold_fade),
            "play_agree_steam_1d": _slice_stats(hold_agree_1d),
            "ats_lift_agree_vs_play": lift,
            "clv_vs_open_n": len(clv_hold),
            "clv_vs_open_avg": round(sum(clv_hold) / len(clv_hold), 4) if clv_hold else None,
            "clv_positive_rate": (
                round(sum(1 for x in clv_hold if x > 0) / len(clv_hold), 4) if clv_hold else None
            ),
        },
        "confirm_2020_2023": {
            "play_all": _slice_stats(conf_play),
            "play_agree_steam_7d": _slice_stats(conf_agree),
        },
        "residual": {
            "corr_steam7_vs_model_error_confirm": None if corr_conf is None else round(corr_conf, 4),
            "corr_steam7_vs_model_error_holdout": None if corr_hold is None else round(corr_hold, 4),
            "n_confirm": n_conf,
            "n_holdout": n_hold,
        },
        "gates": {
            "promote_steam_agree_filter": promote_filter,
            "fit_supervised_path_v5": fit_v5,
            "change_blend_weights": False,
            "ungate_weekly_props": False,
            "note": (
                "Filter promote needs holdout n>=80, +2pp ATS vs PLAY, ROI>0. "
                "v5 fit needs |corr|>=0.08 on 2020-23 and same sign on 2024-25."
            ),
        },
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump(report, fh, indent=2)
        fh.write("\n")
    print(json.dumps(report, indent=2))
    print(f"\nWrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
