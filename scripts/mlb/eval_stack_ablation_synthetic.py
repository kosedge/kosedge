#!/usr/bin/env python3
"""Synthetic sanity check for stack ablation flags (no DB / Odds credits).

Usage:
  PYTHONPATH=services/model-service python3 scripts/mlb/eval_stack_ablation_synthetic.py
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

import src.services.mlb_data as mlb_data  # noqa: E402
import src.services.mlb_simulator as mlb_sim  # noqa: E402
from src.services.mlb_simulator import MlbGameInputs, simulate_mlb_game  # noqa: E402

CONFIGS = {
    "S0": {"matchup": True, "wind_dir": True, "quality": "era_whip"},
    "S1": {"matchup": False, "wind_dir": True, "quality": "era_whip"},
    "S2": {"matchup": False, "wind_dir": False, "quality": "era_whip"},
    "S3": {"matchup": False, "wind_dir": True, "quality": "kbb_only"},
}


def _slate(n: int, seed: int) -> list[MlbGameInputs]:
    rng = random.Random(seed)
    games: list[MlbGameInputs] = []
    for i in range(n):
        games.append(
            MlbGameInputs(
                game_id=f"stack-{i}",
                home_team="Home",
                away_team="Away",
                offense_home=1.0 + rng.uniform(-0.07, 0.07),
                offense_away=1.0 + rng.uniform(-0.07, 0.07),
                offense_split_home=1.0 + rng.uniform(-0.05, 0.05),
                offense_split_away=1.0 + rng.uniform(-0.05, 0.05),
                recent_form_index_home=1.0 + rng.uniform(-0.06, 0.06),
                recent_form_index_away=1.0 + rng.uniform(-0.06, 0.06),
                starter_quality_home=1.0 + rng.uniform(-0.10, 0.10),
                starter_quality_away=1.0 + rng.uniform(-0.10, 0.10),
                starter_k_factor_home=1.0 + rng.uniform(-0.12, 0.12),
                starter_k_factor_away=1.0 + rng.uniform(-0.12, 0.12),
                starter_bb_factor_home=1.0 + rng.uniform(-0.10, 0.10),
                starter_bb_factor_away=1.0 + rng.uniform(-0.10, 0.10),
                starter_gb_factor_home=1.0 + rng.uniform(-0.08, 0.08),
                starter_gb_factor_away=1.0 + rng.uniform(-0.08, 0.08),
                weather_temp_f=72.0 + rng.uniform(-10, 14),
                weather_wind_mph=8.0 + rng.uniform(-4, 8),
                weather_wind_dir_deg=rng.choice([90.0, 180.0, 210.0, 300.0]),
                weather_humidity_pct=50.0 + rng.uniform(-15, 20),
                park_factor_runs=1.0 + rng.uniform(-0.08, 0.08),
            )
        )
    return games


def main() -> int:
    games = _slate(80, seed=11)
    rows = []
    prior_flags = mlb_sim.get_stack_ablation_flags()
    prior_mode = mlb_data.get_starter_quality_mode()
    try:
        for name, cfg in CONFIGS.items():
            mlb_sim.apply_stack_ablation_flags(
                matchup_mul_enabled=cfg["matchup"],
                weather_wind_dir_mul_enabled=cfg["wind_dir"],
            )
            mlb_data.apply_starter_quality_mode(cfg["quality"])
            probs = []
            totals = []
            for g in games:
                markets = simulate_mlb_game(
                    g, simulations=1200, seed=hash(g.game_id) % 10_000
                )["markets"]
                probs.append(float(markets["fg_home_win_prob"]))
                totals.append(float(markets["fg_total_mean"]))
            rows.append(
                {
                    "config": name,
                    **cfg,
                    "avg_home_win_prob": round(sum(probs) / len(probs), 6),
                    "avg_total_mean": round(sum(totals) / len(totals), 4),
                    "home_win_std": round(
                        (sum((p - sum(probs) / len(probs)) ** 2 for p in probs) / len(probs))
                        ** 0.5,
                        6,
                    ),
                }
            )
    finally:
        mlb_sim.apply_stack_ablation_flags(
            matchup_mul_enabled=prior_flags["matchup_mul_enabled"],
            weather_wind_dir_mul_enabled=prior_flags["weather_wind_dir_mul_enabled"],
        )
        mlb_data.apply_starter_quality_mode(prior_mode)

    by = {r["config"]: r for r in rows}
    report = {
        "games": len(games),
        "candidates": rows,
        "sanity": {
            "s1_differs_from_s0": by["S1"]["avg_home_win_prob"] != by["S0"]["avg_home_win_prob"]
            or by["S1"]["avg_total_mean"] != by["S0"]["avg_total_mean"],
            "s2_totals_can_differ_s1": by["S2"]["avg_total_mean"] != by["S1"]["avg_total_mean"],
            "note": (
                "Synthetic only — production grade is densify force-resim + "
                "intersection CLV via run_mlb_stack_ablation."
            ),
        },
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
