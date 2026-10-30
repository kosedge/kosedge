#!/usr/bin/env python3
"""Prove Independent Fair can consume t4770u staged inputs without DATABASE_URL.

Diagnostic only. Not an E1 emit. market_blend=0 asserted. No C10/API.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MS = ROOT / "services" / "model-service"
PACK = ROOT / "data" / "ops" / "nfl-efficiency-2026-w1-w8-t4770u" / "w09_consume_pack.json"
OUT = ROOT / "data" / "ops" / "nfl-efficiency-2026-w1-w8-t4770u" / "if_consume_proof.json"

REQUIRED_20 = (
    "offense_index_home",
    "offense_index_away",
    "defense_index_home",
    "defense_index_away",
    "home_off_epa_5g",
    "away_off_epa_5g",
    "home_def_epa_allowed_5g",
    "away_def_epa_allowed_5g",
    "home_pass_rate_5g",
    "away_pass_rate_5g",
    "home_success_offense_5g",
    "away_success_offense_5g",
    "home_success_defense_allowed_5g",
    "away_success_defense_allowed_5g",
    "matchup_diff_off_epa_5g",
    "matchup_diff_def_epa_allowed_5g",
    "matchup_diff_success_rate_5g",
    "matchup_diff_pressure_generated_5g",
    "matchup_diff_pressure_allowed_5g",
    "matchup_diff_red_zone_td_rate_5g",
)


def main() -> int:
    os.environ.pop("DATABASE_URL", None)
    os.environ.pop("LAUNCH_RESEARCH_DATABASE_URL", None)
    sys.path.insert(0, str(MS))

    from src.services.nfl_simulator import (
        INDEPENDENT_FAIR_FORECAST_LABEL,
        NFL_INDEPENDENT_FAIR_PATH,
        NflGameInputs,
        independent_fair_mus,
        simulate_nfl_game_independent_fair,
    )

    pack = json.loads(PACK.read_text(encoding="utf-8"))
    rows = []
    for game in pack.get("games") or []:
        if game.get("row_status") != "ACCEPT":
            rows.append(
                {
                    "game_id": game.get("game_id"),
                    "consumed": False,
                    "row_status": game.get("row_status"),
                    "reject_reasons": game.get("reject_reasons"),
                }
            )
            continue
        missing = [name for name in REQUIRED_20 if game.get(name) is None]
        if missing:
            raise RuntimeError(f"{game.get('game_id')} ACCEPT row missing {missing}")
        inputs = NflGameInputs(
            game_id=str(game["game_id"]),
            home_team=str(game["home_team"]),
            away_team=str(game["away_team"]),
            offense_index_home=float(game["offense_index_home"]),
            offense_index_away=float(game["offense_index_away"]),
            defense_index_home=float(game["defense_index_home"]),
            defense_index_away=float(game["defense_index_away"]),
            rest_days_home=float(game["rest_days_home"]),
            rest_days_away=float(game["rest_days_away"]),
            matchup_season=2026,
            matchup_week=9,
            matchup_game_id=str(game["game_id"]),
            matchup_home_team=str(game["home_team"]),
            matchup_away_team=str(game["away_team"]),
            home_off_epa_5g=float(game["home_off_epa_5g"]),
            away_off_epa_5g=float(game["away_off_epa_5g"]),
            home_def_epa_allowed_5g=float(game["home_def_epa_allowed_5g"]),
            away_def_epa_allowed_5g=float(game["away_def_epa_allowed_5g"]),
            home_pass_rate_5g=float(game["home_pass_rate_5g"]),
            away_pass_rate_5g=float(game["away_pass_rate_5g"]),
            home_success_offense_5g=float(game["home_success_offense_5g"]),
            away_success_offense_5g=float(game["away_success_offense_5g"]),
            home_success_defense_allowed_5g=float(game["home_success_defense_allowed_5g"]),
            away_success_defense_allowed_5g=float(
                game["away_success_defense_allowed_5g"]
            ),
            matchup_diff_off_epa_5g=float(game["matchup_diff_off_epa_5g"]),
            matchup_diff_def_epa_allowed_5g=float(
                game["matchup_diff_def_epa_allowed_5g"]
            ),
            matchup_diff_success_rate_5g=float(game["matchup_diff_success_rate_5g"]),
            matchup_diff_pressure_generated_5g=float(
                game["matchup_diff_pressure_generated_5g"]
            ),
            matchup_diff_pressure_allowed_5g=float(
                game["matchup_diff_pressure_allowed_5g"]
            ),
            matchup_diff_red_zone_td_rate_5g=float(
                game["matchup_diff_red_zone_td_rate_5g"]
            ),
            weather_available=None,
            injury_nowcast_impact_home=None,
            injury_nowcast_impact_away=None,
            travel_available=None,
            travel_miles_home=None,
            travel_miles_away=None,
            travel_timezone_delta_home=None,
            travel_timezone_delta_away=None,
            info_velocity_home=None,
            info_velocity_away=None,
            hours_since_change_home=None,
            hours_since_change_away=None,
        )
        out = simulate_nfl_game_independent_fair(
            inputs,
            simulations=400,
            seed=4770,
            market_spread_home=None,
            market_total=None,
        )
        if out.get("forecast_label") != INDEPENDENT_FAIR_FORECAST_LABEL:
            raise RuntimeError("IF label missing")
        blend = out.get("independent_fair") or {}
        if blend.get("market_blend") != 0:
            raise RuntimeError("market_blend must be 0")
        margin_mu, total_mu = independent_fair_mus(out)
        rows.append(
            {
                "game_id": game["game_id"],
                "consumed": True,
                "row_status": "ACCEPT",
                "forecast_label": out.get("forecast_label"),
                "market_blend": blend.get("market_blend"),
                "margin_mu": margin_mu,
                "total_mu": total_mu,
                "as_of_week": game.get("as_of_week"),
                "rolling_as_of_week": game.get("rolling_as_of_week"),
            }
        )

    proof = {
        "ticket": "t4770u",
        "alex_contract_sha8": "24600552",
        "contract_bind": "NOT_FINAL",
        "imv_return": "d2587de7",
        "code_commit": "1b39f4e9f6b2e04c264a41831f3bb7273e475011",
        "entrypoint": "simulate_nfl_game_independent_fair",
        "market_blend": 0,
        "NFL_INDEPENDENT_FAIR_PATH": NFL_INDEPENDENT_FAIR_PATH,
        "DATABASE_URL_used": False,
        "c10_used": False,
        "scoring_admissible": False,
        "label": "DIAGNOSTIC consume proof on through-W7 panel; not E1 emit",
        "n_consumed": sum(1 for r in rows if r.get("consumed")),
        "n_games": len(rows),
        "games": rows,
    }
    OUT.write_text(json.dumps(proof, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "n_consumed": proof["n_consumed"], "path": str(OUT)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
