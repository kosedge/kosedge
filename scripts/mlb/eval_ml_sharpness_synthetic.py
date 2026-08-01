#!/usr/bin/env python3
"""Focused synthetic moneyline sharpness check (no DB / Odds credits).

Compares Brier under a home-win base rate of ~0.54 — the historical MLB
home-field prior the PA sim previously ignored (~0.50 on a neutral slate).

Usage:
  PYTHONPATH=services/model-service python3 scripts/mlb/eval_ml_sharpness_synthetic.py
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

import src.services.mlb_simulator as mlb_sim  # noqa: E402
from src.services.mlb_simulator import (  # noqa: E402
    AWAY_FIELD_OFFENSE_MUL,
    HOME_FIELD_OFFENSE_MUL,
    MlbGameInputs,
    simulate_mlb_game,
)


def _brier(probs: list[float], outcomes: list[int]) -> float:
    return sum((p - y) ** 2 for p, y in zip(probs, outcomes)) / max(1, len(probs))


def _slate(seed: int, n: int) -> list[MlbGameInputs]:
    rng = random.Random(seed)
    games: list[MlbGameInputs] = []
    for i in range(n):
        # Mild team / SP asymmetry so the slate is not pure HFA.
        home_off = 1.0 + rng.uniform(-0.06, 0.06)
        away_off = 1.0 + rng.uniform(-0.06, 0.06)
        sp_home = 1.0 + rng.uniform(-0.08, 0.08)
        sp_away = 1.0 + rng.uniform(-0.08, 0.08)
        games.append(
            MlbGameInputs(
                game_id=f"synth-{i}",
                home_team="Home",
                away_team="Away",
                offense_home=home_off,
                offense_away=away_off,
                starter_quality_home=sp_home,
                starter_quality_away=sp_away,
            )
        )
    return games


def _run_slate(
    games: list[MlbGameInputs],
    *,
    simulations: int,
) -> tuple[list[float], list[float]]:
    probs: list[float] = []
    totals: list[float] = []
    for g in games:
        markets = simulate_mlb_game(g, simulations=simulations, seed=hash(g.game_id) % 10_000)[
            "markets"
        ]
        probs.append(float(markets["fg_home_win_prob"]))
        totals.append(float(markets["fg_total_mean"]))
    return probs, totals


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--games", type=int, default=80)
    parser.add_argument("--simulations", type=int, default=2500)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--home-win-rate", type=float, default=0.54)
    args = parser.parse_args()

    games = _slate(args.seed, args.games)
    rng = random.Random(args.seed + 99)
    # Outcomes drawn from MLB-like home base rate (not model-dependent).
    outcomes = [1 if rng.random() < args.home_win_rate else 0 for _ in games]

    # After (current HFA constants).
    probs_after, totals_after = _run_slate(games, simulations=args.simulations)

    # Before: temporarily neutralize HFA multipliers in-module.
    prior_home = mlb_sim.HOME_FIELD_OFFENSE_MUL
    prior_away = mlb_sim.AWAY_FIELD_OFFENSE_MUL
    mlb_sim.HOME_FIELD_OFFENSE_MUL = 1.0
    mlb_sim.AWAY_FIELD_OFFENSE_MUL = 1.0
    try:
        probs_before, totals_before = _run_slate(games, simulations=args.simulations)
    finally:
        mlb_sim.HOME_FIELD_OFFENSE_MUL = prior_home
        mlb_sim.AWAY_FIELD_OFFENSE_MUL = prior_away

    report = {
        "games": args.games,
        "simulations": args.simulations,
        "assumed_home_win_rate": args.home_win_rate,
        "hfa_home_mul": HOME_FIELD_OFFENSE_MUL,
        "hfa_away_mul": AWAY_FIELD_OFFENSE_MUL,
        "before_no_hfa": {
            "avg_model_home_win_prob": round(sum(probs_before) / len(probs_before), 6),
            "avg_fg_total_mean": round(sum(totals_before) / len(totals_before), 4),
            "brier_ml": round(_brier(probs_before, outcomes), 6),
        },
        "after_hfa": {
            "avg_model_home_win_prob": round(sum(probs_after) / len(probs_after), 6),
            "avg_fg_total_mean": round(sum(totals_after) / len(totals_after), 4),
            "brier_ml": round(_brier(probs_after, outcomes), 6),
        },
        "delta_brier_ml": round(
            _brier(probs_after, outcomes) - _brier(probs_before, outcomes), 6
        ),
        "delta_avg_total_mean": round(
            (sum(totals_after) / len(totals_after)) - (sum(totals_before) / len(totals_before)),
            4,
        ),
        "brier_coin_flip_0_5": round(_brier([0.5] * len(outcomes), outcomes), 6),
        "brier_constant_home_prior": round(
            _brier([args.home_win_rate] * len(outcomes), outcomes), 6
        ),
        "note": (
            "Synthetic labels use a fixed home-win prior; this is a wiring / HFA "
            "sanity check, not a walkforward holdout grade. Negative delta_brier is better."
        ),
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
