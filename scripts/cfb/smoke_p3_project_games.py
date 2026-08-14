#!/usr/bin/env python3
"""P3 research smoke — a handful of project-game distributions.

Does not publish lines. used_in_spread stays false.

Usage:
  python scripts/cfb/smoke_p3_project_games.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.cfb_season_engine import (  # noqa: E402
    DEFAULT_SEASON_ENGINE_VERSION,
    build_packaged_universe,
    project_game_preview,
    project_game_to_dict,
)

MATCHUPS = [
    {"home": "OSU", "away": "BALL", "week": 1, "neutral": False, "label": "G5 @ blue blood"},
    {"home": "UGA", "away": "FSU", "week": 1, "neutral": False, "label": "open QB vs open QB"},
    {"home": "TEX", "away": "OSU", "week": 1, "neutral": True, "label": "neutral incumbents"},
    {"home": "MICH", "away": "MASS", "week": 1, "neutral": False, "label": "open camp vs G5"},
    {"home": "LSU", "away": "RICE", "week": 1, "neutral": False, "label": "open QB home"},
    {"home": "ALA", "away": "BALL", "week": 1, "neutral": False, "label": "open camp vs G5"},
]


def main() -> int:
    universe = build_packaged_universe(2026)
    rows = []
    for spec in MATCHUPS:
        proj = project_game_preview(
            universe,
            home_team=spec["home"],
            away_team=spec["away"],
            week=spec["week"],
            neutral_site=spec["neutral"],
            n_sims=2000,
            seed=20260813,
        )
        payload = project_game_to_dict(proj)
        row = {
            "label": spec["label"],
            "matchup": f"{spec['away']} @ {spec['home']}"
            + (" (neutral)" if spec["neutral"] else ""),
            "spread_home": payload["fair_spread"],
            "total": payload["fair_total"],
            "wp_home": payload["home_win_prob"],
            "team_total_home": payload["team_total_home"],
            "team_total_away": payload["team_total_away"],
            "margin_sd": payload["margin_sd"],
            "total_sd": payload["uncertainty"]["effective_total_sd"],
            "n_sims": payload["n_sims"],
            "home_qb": payload["uncertainty"]["open_qb"]["home_class"],
            "away_qb": payload["uncertainty"]["open_qb"]["away_class"],
            "used_in_spread": payload["used_in_spread"],
        }
        rows.append(row)
        print(
            f"{row['matchup']:28}  spr {row['spread_home']:+6.1f}  "
            f"tot {row['total']:5.1f}  wp {row['wp_home']:.1%}  "
            f"mσ {row['margin_sd']:4.1f}  tσ {row['total_sd']:4.1f}  "
            f"QB {row['away_qb']}/{row['home_qb']}"
        )

    out = {
        "engine_version": DEFAULT_SEASON_ENGINE_VERSION,
        "n_sims": 2000,
        "used_in_spread": False,
        "method": (
            "independent Gaussian margin (strength→margin + HFA) and "
            "Gaussian total (pace × off_env × explosiveness)"
        ),
        "weather": "not applied",
        "official_2026_fbs_schedule": False,
        "rows": rows,
    }
    dest = ROOT / "data" / "ops" / "cfb-p3-smoke-20260813.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
