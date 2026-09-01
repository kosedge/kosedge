#!/usr/bin/env python3
"""Smoke: print Ch6 dark board summary (no rematerialize)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.nba_season_engine.nba_props import build_dark_props_board  # noqa: E402


def main() -> None:
    board = build_dark_props_board(limit=20, market_key="pts")
    print(
        json.dumps(
            {
                "props_version": board.get("props_version"),
                "count": board.get("count"),
                "play_n": board.get("play_n"),
                "dark_only": board.get("dark_only"),
                "sample": [
                    {
                        "player": r.get("player_name"),
                        "team": r.get("team"),
                        "mean": r.get("model_mean"),
                        "line": r.get("line"),
                        "tag": r.get("tag"),
                    }
                    for r in (board.get("lines") or [])[:5]
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
