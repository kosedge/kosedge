#!/usr/bin/env python3
"""Build train-only football-state priors for non-offensive scoring events."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

TRAIN_SEASONS = frozenset(range(2013, 2024))


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_one(value: Any) -> bool:
    return _number(value) == 1.0


def rate(numerator: int, denominator: int) -> dict[str, float | int]:
    return {
        "opportunities": denominator,
        "scores": numerator,
        "rate": numerator / denominator if denominator else 0.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pbp", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    opportunities = Counter()
    scores = Counter()
    safety_buckets = {"own_1_5": Counter(), "own_6_10": Counter()}
    games: set[str] = set()
    rows = 0
    seen_td: set[tuple[str, Any]] = set()

    with args.pbp.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            p = row.get("payload") if row.get("object_type") == "pbp_play" else None
            if not isinstance(p, Mapping):
                continue
            season = _number(p.get("season"))
            if season is None or int(season) not in TRAIN_SEASONS:
                continue
            if p.get("season_type") != "REG":
                continue
            rows += 1
            game = str(p.get("game_id") or "")
            if game:
                games.add(game)
            play_type = str(p.get("play_type") or "")
            td = _is_one(p.get("touchdown")) and p.get("td_team") != p.get("posteam")
            td_key = (game, p.get("play_id"))
            if td and td_key in seen_td:
                td = False
            elif td:
                seen_td.add(td_key)

            if _is_one(p.get("interception")) or _is_one(p.get("fumble_lost")):
                opportunities["turnover_return"] += 1
                scores["turnover_return"] += int(td)
            if play_type == "kickoff":
                opportunities["kickoff_return"] += 1
                scores["kickoff_return"] += int(td)
            if play_type == "punt":
                opportunities["punt_return"] += 1
                scores["punt_return"] += int(td)
            if (
                (_is_one(p.get("punt_blocked")) or _is_one(p.get("field_goal_attempt")) and p.get("blocked_player_id"))
            ):
                opportunities["blocked_return"] += 1
                scores["blocked_return"] += int(td)

            yardline_100 = _number(p.get("yardline_100"))
            yards_gained = _number(p.get("yards_gained"))
            if (
                yardline_100 is not None
                and yards_gained is not None
                and yardline_100 >= 90
                and yards_gained <= -(100 - yardline_100)
            ):
                bucket = "own_1_5" if yardline_100 >= 95 else "own_6_10"
                safety_buckets[bucket]["opportunities"] += 1
                safety_buckets[bucket]["scores"] += int(_is_one(p.get("safety")))

    priors = {
        family: {"default": rate(scores[family], opportunities[family])}
        for family in (
            "turnover_return",
            "kickoff_return",
            "punt_return",
            "blocked_return",
        )
    }
    priors["safety"] = {
        "default": rate(
            sum(bucket["scores"] for bucket in safety_buckets.values()),
            sum(bucket["opportunities"] for bucket in safety_buckets.values()),
        ),
        "buckets": {
            name: rate(values["scores"], values["opportunities"])
            for name, values in safety_buckets.items()
        },
    }
    payload = {
        "artifact_id": "Clock-Play Non-Offensive Scoring Priors",
        "train_window": "2013-2023 regular season",
        "historical_source": args.pbp.as_posix(),
        "historical_games": len(games),
        "historical_rows_examined": rows,
        "event_families": {
            "turnover_return": "interception or lost fumble branches to ordinary turnover or return TD",
            "kickoff_return": "kickoff branches to ordinary receiving possession or return TD",
            "punt_return": "punt branches to ordinary receiving possession or return TD",
            "blocked_return": "blocked kick opportunity branches to ordinary recovery or return TD",
            "safety": "backed-up play with yards_gained crossing the offense's goal line can score safety",
        },
        "priors": priors,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
