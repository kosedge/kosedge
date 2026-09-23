#!/usr/bin/env python3
"""Build train-only PBP clock-flow priors for the Clock-Play state loop."""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

TRAIN_SEASONS = frozenset(range(2013, 2024))
CORE_TYPES = frozenset({"pass", "run", "qb_kneel", "qb_spike", "field_goal", "punt"})
MAX_INTERVAL_SECONDS = 90.0
KIND_PARENT_PSEUDO_INTERVALS = 100.0


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_one(value: Any) -> bool:
    return _number(value) == 1.0


def _game_seconds(payload: Mapping[str, Any]) -> float | None:
    quarter = _number(payload.get("qtr"))
    seconds = _number(payload.get("quarter_seconds_remaining"))
    if quarter is None or seconds is None or not 1 <= quarter <= 4:
        return None
    return (4 - int(quarter)) * 900 + seconds


def _kind(payload: Mapping[str, Any]) -> str:
    if _is_one(payload.get("incomplete_pass")):
        return "incomplete_pass"
    if _is_one(payload.get("sack")):
        return "sack"
    if _is_one(payload.get("out_of_bounds")):
        return "out_of_bounds"
    if _is_one(payload.get("touchdown")):
        return "post_touchdown"
    if _is_one(payload.get("interception")) or _is_one(payload.get("fumble_lost")):
        return "turnover"
    if _number(payload.get("down")) == 4 and _is_one(payload.get("fourth_down_failed")):
        return "turnover_on_downs"
    play_type = str(payload.get("play_type") or "")
    if play_type == "punt":
        return "punt"
    if play_type == "field_goal":
        return "field_goal"
    if _is_one(payload.get("first_down")):
        return "first_down"
    if play_type == "pass":
        return "pass"
    if play_type in {"run", "qb_kneel", "qb_spike"}:
        return "run"
    return "default"


@dataclass
class Moments:
    count: int = 0
    total: float = 0.0
    squares: float = 0.0

    def add(self, value: float) -> None:
        self.count += 1
        self.total += value
        self.squares += value * value

    def summary(self, fallback_mean: float, fallback_stddev: float) -> dict[str, float | int]:
        if not self.count:
            return {
                "sample_size": 0,
                "mean_seconds": fallback_mean,
                "stddev_seconds": fallback_stddev,
            }
        mean = self.total / self.count
        stddev = (
            math.sqrt(max(0.0, self.squares / self.count - mean * mean))
            if self.count > 1
            else fallback_stddev
        )
        return {
            "sample_size": self.count,
            "mean_seconds": mean,
            "stddev_seconds": max(0.25, stddev),
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pbp", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    moments: defaultdict[str, Moments] = defaultdict(Moments)
    observed_kinds: defaultdict[str, int] = defaultdict(int)
    prior_core: dict[tuple[str, int], tuple[str, float]] = {}
    games: set[str] = set()
    rows_examined = 0

    with args.pbp.open(encoding="utf-8") as handle:
        for raw_line in handle:
            row = json.loads(raw_line)
            payload = row.get("payload") if row.get("object_type") == "pbp_play" else None
            if not isinstance(payload, Mapping):
                continue
            season = _number(payload.get("season"))
            if season is None or int(season) not in TRAIN_SEASONS:
                continue
            if payload.get("season_type") != "REG":
                continue
            rows_examined += 1
            game = str(payload.get("game_id") or "")
            drive = _number(payload.get("fixed_drive"))
            if not game or drive is None:
                continue
            games.add(game)
            play_type = str(payload.get("play_type") or "")
            if play_type == "no_play":
                observed_kinds["no_play_rows"] += 1
            if play_type not in CORE_TYPES:
                continue
            seconds = _game_seconds(payload)
            if seconds is None:
                continue
            key = (game, int(drive))
            previous = prior_core.get(key)
            if previous is not None:
                kind, previous_seconds = previous
                elapsed = previous_seconds - seconds
                if 0.0 < elapsed <= MAX_INTERVAL_SECONDS:
                    moments[kind].add(elapsed)
            kind = _kind(payload)
            observed_kinds[kind] += 1
            prior_core[key] = (kind, seconds)

    all_samples = Moments()
    for sample in moments.values():
        all_samples.count += sample.count
        all_samples.total += sample.total
        all_samples.squares += sample.squares
    default = all_samples.summary(28.0, 8.0)
    kinds: dict[str, dict[str, float | int]] = {}
    for kind, moment in sorted(moments.items()):
        raw = moment.summary(
            float(default["mean_seconds"]), float(default["stddev_seconds"])
        )
        sample_size = int(raw["sample_size"])
        raw_mean = float(raw["mean_seconds"])
        shrunk_mean = (
            (moment.total + KIND_PARENT_PSEUDO_INTERVALS * float(default["mean_seconds"]))
            / (sample_size + KIND_PARENT_PSEUDO_INTERVALS)
        )
        kinds[kind] = {
            **raw,
            "raw_mean_seconds": raw_mean,
            "mean_seconds": shrunk_mean,
        }
    payload = {
        "artifact_id": "Clock-Play Clock-Flow Priors",
        "train_window": "2013-2023 regular season",
        "historical_source": args.pbp.as_posix(),
        "historical_games": len(games),
        "historical_rows_examined": rows_examined,
        "interval_definition": (
            "elapsed game seconds from a core snap to the next core snap in the "
            "same fixed drive; 0 < elapsed <= 90 seconds"
        ),
        "runtime_mapping": {
            "pass": "pass",
            "run": "run",
            "incomplete_pass": "incomplete_pass",
            "turnover": "turnover",
            "punt": "punt",
            "field_goal": "field_goal",
            "fourth_down_go": "fourth_down_go",
            "fallback": "default",
        },
        "shrinkage": {
            "method": "conditional clock-interval mean shrinkage to all within-drive core intervals",
            "kind_parent_pseudo_intervals": KIND_PARENT_PSEUDO_INTERVALS,
        },
        "observed_kind_rows": dict(sorted(observed_kinds.items())),
        "priors": {"default": default, "kinds": kinds},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
