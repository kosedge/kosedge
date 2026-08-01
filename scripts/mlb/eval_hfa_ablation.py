#!/usr/bin/env python3
"""Ablate HOME_FIELD_OFFENSE_MUL candidates (no DB / Odds credits).

Compares synthetic Brier vs a 0.54 home-win prior, mean home win prob,
totals neutrality, and a market-relative CLV proxy (market=0.535).

Usage:
  PYTHONPATH=services/model-service python3 scripts/mlb/eval_hfa_ablation.py
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
from src.services.mlb_simulator import MlbGameInputs, simulate_mlb_game  # noqa: E402

CANDIDATES = (1.035, 1.025, 1.02, 1.0)


def _brier(probs: list[float], outcomes: list[int]) -> float:
    return sum((p - y) ** 2 for p, y in zip(probs, outcomes)) / max(1, len(probs))


def _slate(seed: int, n: int) -> list[MlbGameInputs]:
    rng = random.Random(seed)
    games: list[MlbGameInputs] = []
    for i in range(n):
        games.append(
            MlbGameInputs(
                game_id=f"hfa-{i}",
                home_team="Home",
                away_team="Away",
                offense_home=1.0 + rng.uniform(-0.06, 0.06),
                offense_away=1.0 + rng.uniform(-0.06, 0.06),
                starter_quality_home=1.0 + rng.uniform(-0.08, 0.08),
                starter_quality_away=1.0 + rng.uniform(-0.08, 0.08),
            )
        )
    return games


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--games", type=int, default=100)
    parser.add_argument("--simulations", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--home-win-rate", type=float, default=0.54)
    parser.add_argument("--market-home", type=float, default=0.535)
    args = parser.parse_args()

    games = _slate(args.seed, args.games)
    rng = random.Random(args.seed + 99)
    outcomes = [1 if rng.random() < args.home_win_rate else 0 for _ in games]

    prior_home = mlb_sim.HOME_FIELD_OFFENSE_MUL
    prior_away = mlb_sim.AWAY_FIELD_OFFENSE_MUL
    rows = []
    try:
        for hfa in CANDIDATES:
            mlb_sim.HOME_FIELD_OFFENSE_MUL = float(hfa)
            mlb_sim.AWAY_FIELD_OFFENSE_MUL = 1.0 / float(hfa) if hfa else 1.0
            probs: list[float] = []
            totals: list[float] = []
            for g in games:
                markets = simulate_mlb_game(
                    g, simulations=args.simulations, seed=hash(g.game_id) % 10_000
                )["markets"]
                probs.append(float(markets["fg_home_win_prob"]))
                totals.append(float(markets["fg_total_mean"]))
            clv_proxy = sum(
                (p - args.market_home) * (2 * y - 1) for p, y in zip(probs, outcomes)
            ) / len(probs)
            rows.append(
                {
                    "hfa_home_mul": hfa,
                    "avg_model_home_win_prob": round(sum(probs) / len(probs), 6),
                    "avg_fg_total_mean": round(sum(totals) / len(totals), 4),
                    "brier_ml": round(_brier(probs, outcomes), 6),
                    "clv_proxy_vs_market": round(clv_proxy, 6),
                    "mean_abs_vs_market": round(
                        sum(abs(p - args.market_home) for p in probs) / len(probs), 6
                    ),
                }
            )
    finally:
        mlb_sim.HOME_FIELD_OFFENSE_MUL = prior_home
        mlb_sim.AWAY_FIELD_OFFENSE_MUL = prior_away

    # Policy: reject 1.035 after production CLV regression; pick best remaining
    # by (brier, then |avg_home - 0.54|, then clv_proxy).
    eligible = [r for r in rows if r["hfa_home_mul"] != 1.035]
    ranked = sorted(
        eligible,
        key=lambda r: (
            r["brier_ml"],
            abs(r["avg_model_home_win_prob"] - args.home_win_rate),
            -r["clv_proxy_vs_market"],
        ),
    )
    winner = ranked[0] if ranked else rows[0]
    report = {
        "games": args.games,
        "simulations": args.simulations,
        "assumed_home_win_rate": args.home_win_rate,
        "market_home": args.market_home,
        "candidates": rows,
        "production_note": (
            "PR #48 HFA=1.035 improved synthetic/walkforward Brier slightly but "
            "regressed densify-window ML CLV +0.023→+0.007. Treat 1.035 as failed "
            "CLV trade until unused-holdout proves otherwise."
        ),
        "selected_hfa_home_mul": winner["hfa_home_mul"],
        "selection_rule": (
            "Exclude 1.035 per production CLV failure; among remainder minimize "
            "Brier, then distance of mean home win to 0.54, then maximize CLV proxy."
        ),
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
