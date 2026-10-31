#!/usr/bin/env python3
"""Audit-only: holdout ID checksum + frozen-method μ/h by season.

Does not select parameters or score a new holdout protocol.
Reads the existing 2014–2025 team-game EPA parquet and the rematerialized
validation report. Writes artifacts under data/ops/cfb-research-opp-adj-epa-20260915/.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MS = ROOT / "services" / "model-service"
if str(MS) not in sys.path:
    sys.path.insert(0, str(MS))

OPS = ROOT / "data" / "ops" / "cfb-research-opp-adj-epa-20260915"
HIST = ROOT / "data" / "cfb" / "research" / "pbp_hist" / "as_of_20260915"


def _sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main() -> int:
    from src.services.cfb_warehouse.research_hist_features import (
        load_restored_epa_games,
        rows_to_team_game_epa,
    )
    from src.services.cfb_warehouse.research_opp_adj import AdjParams
    from src.services.cfb_warehouse.research_opp_adj_validate import (
        HOLDOUT_SEASON,
        VAL_SEASONS,
        _season_raw_means,
        _std_to_date,
        build_season_finals,
    )

    games = rows_to_team_game_epa(load_restored_epa_games(HIST))
    holdout = [
        g
        for g in games
        if g.season == HOLDOUT_SEASON and not g.fcs_offense
    ]
    lines = [
        f"{g.season}\t{g.week}\t{g.game_id}\t{g.offense}\t{g.defense}\t{g.home:.6f}"
        for g in sorted(
            holdout, key=lambda g: (g.week, g.game_id, g.offense, g.defense)
        )
    ]
    blob = "\n".join(lines) + "\n"
    (OPS / "holdout_2025_obs_keys.tsv").write_text(blob, encoding="utf-8")
    key_sha = _sha_text(blob)

    week_n = {}
    for g in holdout:
        week_n[int(g.week)] = week_n.get(int(g.week), 0) + 1

    prior_raw_off, prior_raw_def = _season_raw_means(games, HOLDOUT_SEASON - 1)
    off_mu_fallback = def_mu_fallback = 0
    for week in sorted(week_n):
        std_off, std_def, _n_g, _n_d = _std_to_date(
            games, season=HOLDOUT_SEASON, week=week
        )
        for g in holdout:
            if g.week != week:
                continue
            if g.offense not in std_off and g.offense not in prior_raw_off:
                off_mu_fallback += 1
            if g.defense not in std_def and g.defense not in prior_raw_def:
                def_mu_fallback += 1

    frozen = AdjParams(lam=40.0, prior_n0=4.0, prior_decay=0.75, iters=12)
    seasons = sorted({g.season for g in games if g.season <= HOLDOUT_SEASON})
    finals = build_season_finals(games, seasons, frozen)
    season_mh = [
        {
            "season": int(season),
            "mu": fit.mu,
            "hfa": fit.hfa,
            "n_obs": fit.n_obs,
            "n_teams": fit.n_teams,
            "n_fbs": fit.n_fbs,
        }
        for season, fit in sorted(finals.items())
    ]

    report = json.loads((OPS / "validation_report.json").read_text())
    prefix_weeks = {
        "2025w1": 229,
        "2025w2": 130,
        "2025w3": 115,
        "2025w4": 111,
        "2025w5": 102,
        "2025w6": 100,
        "2025w7": 110,
        "2025w8": 117,
        "2025w9": 105,
        "2025w10": 103,
        "2025w11": 101,
        "2025w12": 116,
    }
    remat_weeks = {
        k: v["n"] for k, v in (report.get("holdout") or {}).get("by_week_head", {}).items()
    }

    payload = {
        "audit_only": True,
        "production_promote": False,
        "holdout_season": HOLDOUT_SEASON,
        "selection_seasons": list(VAL_SEASONS),
        "n_holdout_obs": len(holdout),
        "n_unique_games": len({g.game_id for g in holdout}),
        "obs_key": "season,week,game_id,offense,defense,home",
        "obs_keys_sha256": key_sha,
        "obs_keys_path": str(OPS / "holdout_2025_obs_keys.tsv"),
        "week_n": dict(sorted(week_n.items())),
        "prefix_by_week_head_n": prefix_weeks,
        "rematerialized_by_week_head_n": remat_weeks,
        "week_head_n_match_prefix": remat_weeks == prefix_weeks,
        "baseline_mu_fallback": {
            "note": (
                "Unadj/blend fall back to adj-model μ when a team has no "
                "same-season STD and no prior-season raw mean. Offense MAE "
                "was bit-identical pre-fix vs rematerialize; defense MAE moved."
            ),
            "offense_rows_using_mu": off_mu_fallback,
            "defense_rows_using_mu": def_mu_fallback,
        },
        "frozen_season_mu_hfa": season_mh,
        "hfa_units": "EPA/play on the offense observation",
        "home_coding": "home=1 if offense is the home team else 0 (neutral/unknown=0)",
    }
    (OPS / "ryan_audit_560.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"n={len(holdout)} games={payload['n_unique_games']} "
        f"sha={key_sha} week_match={payload['week_head_n_match_prefix']} "
        f"mu_fallback off/def={off_mu_fallback}/{def_mu_fallback}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
