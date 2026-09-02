#!/usr/bin/env python3
"""Smoke: print NHL Ch7 fantasy board summary (no rematerialize)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.nhl_season_engine.nhl_fantasy import build_fantasy_board  # noqa: E402


def main() -> None:
    board = build_fantasy_board(limit=40)
    skaters = [r for r in board["rows"] if r.get("player_type") == "skater"][:5]
    goalies = [r for r in board["rows"] if r.get("player_type") == "goalie"][:3]
    print(
        json.dumps(
            {
                "fantasy_version": board.get("fantasy_version"),
                "count": board.get("count"),
                "view": board.get("view"),
                "scoring_map": board.get("scoring_map"),
                "max_team_g_drift": board.get("max_team_g_drift"),
                "goalie_start_share_ok": board.get("goalie_start_share_ok"),
                "skater_sample": [
                    {
                        "rank": r["rank"],
                        "name": r["player_name"],
                        "team": r["team"],
                        "G": r["G"],
                        "A": r["A"],
                        "SOG": r["SOG"],
                        "fantasy_pts": r["fantasy_pts"],
                    }
                    for r in skaters
                ],
                "goalie_sample": [
                    {
                        "rank": r["rank"],
                        "name": r["player_name"],
                        "team": r["team"],
                        "SAVES": r["SAVES"],
                        "fantasy_pts": r["fantasy_pts"],
                    }
                    for r in goalies
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
