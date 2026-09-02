#!/usr/bin/env python3
"""Smoke: print NHL Ch6 dark board summary (no rematerialize)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.nhl_season_engine.nhl_props import build_dark_props_board  # noqa: E402


def main() -> None:
    board = build_dark_props_board(limit=40)
    skaters = [r for r in board["lines"] if r.get("player_type") == "skater"][:5]
    goalies = [r for r in board["lines"] if r.get("player_type") == "goalie"][:3]
    print(
        json.dumps(
            {
                "props_version": board.get("props_version"),
                "count": board.get("count"),
                "play_n": board.get("play_n"),
                "lean_n": board.get("lean_n"),
                "dark_only": board.get("dark_only"),
                "STARTER_GATE": board.get("STARTER_GATE"),
                "skater_sample": [
                    {
                        "player": r.get("player_name"),
                        "team": r.get("team"),
                        "mkt": r.get("market_key"),
                        "mean": r.get("model_mean"),
                        "best": r.get("best"),
                        "tag": r.get("tag"),
                    }
                    for r in skaters
                ],
                "goalie_sample": [
                    {
                        "player": r.get("player_name"),
                        "mean": r.get("model_mean"),
                        "best": r.get("best"),
                        "reason": (r.get("diagnostics") or {}).get("reason"),
                    }
                    for r in goalies
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
