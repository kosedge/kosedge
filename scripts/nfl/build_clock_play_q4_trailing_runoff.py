#!/usr/bin/env python3
"""Train-only mean Q4 trailing offense play clock runoff."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

TRAIN_SEASONS = frozenset(range(2013, 2024))


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--historical-pbp", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    deltas: list[float] = []
    last_clock: dict[str, float] = {}
    last_trailing: dict[str, bool] = {}

    with args.historical_pbp.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            payload = row.get("payload") if row.get("object_type") == "pbp_play" else None
            if not isinstance(payload, Mapping):
                continue
            season = _number(payload.get("season"))
            if season is None or int(season) not in TRAIN_SEASONS:
                continue
            if payload.get("season_type") != "REG" or payload.get("qtr") != 4:
                continue
            game_id = str(payload.get("game_id") or "")
            if not game_id:
                continue
            ps = _number(payload.get("posteam_score"))
            ds = _number(payload.get("defteam_score"))
            seconds = _number(payload.get("game_seconds_remaining"))
            if ps is None or ds is None or seconds is None:
                continue
            trailing = ps < ds
            play_type = str(payload.get("play_type") or "")
            if play_type not in {"run", "pass", "qb_kneel", "qb_spike"}:
                continue
            if not trailing:
                last_trailing[game_id] = False
                last_clock[game_id] = seconds
                continue
            if last_trailing.get(game_id) and game_id in last_clock:
                delta = last_clock[game_id] - seconds
                if 0 < delta < 80:
                    deltas.append(delta)
            last_trailing[game_id] = True
            last_clock[game_id] = seconds

    mean = sum(deltas) / len(deltas) if deltas else 0.0
    payload = {
        "component": "q4_trailing_runoff_train",
        "sample_play_pairs": len(deltas),
        "mean_seconds_per_trailing_play": mean,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n")


if __name__ == "__main__":
    main()
