#!/usr/bin/env python3
"""Build train-only sack and blocked-punt state priors."""

from __future__ import annotations

import json
import argparse
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

TRAIN = frozenset(range(2013, 2024))


def num(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def one(value: Any) -> bool:
    return num(value) == 1.0


def rate(scores: int, opportunities: int) -> dict[str, Any]:
    return {"opportunities": opportunities, "scores": scores, "rate": scores / opportunities if opportunities else 0.0}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pbp", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    counts = Counter()
    sack_losses = Counter()
    games = set()
    rows = 0
    with args.pbp.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            p = row.get("payload") if row.get("object_type") == "pbp_play" else None
            if not isinstance(p, Mapping):
                continue
            season = num(p.get("season"))
            if season is None or int(season) not in TRAIN or p.get("season_type") != "REG":
                continue
            rows += 1
            if p.get("game_id"):
                games.add(p["game_id"])
            if p.get("play_type") == "pass":
                counts["pass"] += 1
                if one(p.get("sack")):
                    counts["sack"] += 1
                    sack_losses[int(round(num(p.get("yards_gained")) or -6))] += 1
            if p.get("play_type") == "punt":
                counts["punt"] += 1
                counts["blocked_punt"] += int(one(p.get("punt_blocked")))
    payload = {
        "artifact_id": "Clock-Play Special State Priors",
        "train_window": "2013-2023 regular season",
        "historical_games": len(games),
        "historical_rows_examined": rows,
        "priors": {
            "sack": {
                **rate(counts["sack"], counts["pass"]),
                "yard_loss_weights": {str(k): v for k, v in sorted(sack_losses.items())},
            },
            "blocked_punt": rate(counts["blocked_punt"], counts["punt"]),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
