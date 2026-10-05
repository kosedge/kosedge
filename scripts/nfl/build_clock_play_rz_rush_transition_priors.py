#!/usr/bin/env python3
"""Build train-only non-fourth red-zone rush transition priors."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
import sys

sys.path.insert(0, str(ROOT / "services" / "model-service"))
from src.services.nfl_clock_play_simulator import rz_rush_state_key  # noqa: E402

TRAIN_SEASONS = frozenset(range(2013, 2024))
OUTCOMES = (
    "touchdown",
    "turnover",
    "loss",
    "zero",
    "one_two",
    "short_gain",
    "first_down",
)
OUTCOME_PARENT_PSEUDO_RUSHES = 30.0
YARD_PARENT_PSEUDO_RUSHES = 12.0


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_one(value: Any) -> bool:
    return _number(value) == 1.0


def _outcome(payload: Mapping[str, Any], yards: int, distance: int) -> str:
    if _is_one(payload.get("touchdown")) and payload.get("td_team") == payload.get("posteam"):
        return "touchdown"
    if _is_one(payload.get("interception")) or _is_one(payload.get("fumble_lost")):
        return "turnover"
    if _is_one(payload.get("first_down")) or yards >= distance:
        return "first_down"
    if yards < 0:
        return "loss"
    if yards == 0:
        return "zero"
    if yards <= 2:
        return "one_two"
    return "short_gain"


@dataclass
class Samples:
    n: int = 0
    outcomes: Counter[str] = field(default_factory=Counter)
    yards: dict[str, Counter[int]] = field(
        default_factory=lambda: defaultdict(Counter)
    )

    def add(self, outcome: str, yards: int) -> None:
        self.n += 1
        self.outcomes[outcome] += 1
        self.yards[outcome][yards] += 1

    def raw(self) -> dict[str, Any]:
        return {
            "rushes": self.n,
            "outcomes": {outcome: self.outcomes[outcome] for outcome in OUTCOMES},
            "outcome_probabilities": {
                outcome: self.outcomes[outcome] / self.n if self.n else 0.0
                for outcome in OUTCOMES
            },
        }


def _parent_key(full_key: str) -> str:
    field, down, _distance, goal = full_key.split("|")
    return "|".join((field, down, goal))


def _probabilities(child: Samples, parent: Samples, global_samples: Samples) -> dict[str, float]:
    global_probs = {
        outcome: global_samples.outcomes[outcome] / global_samples.n
        for outcome in OUTCOMES
    }
    parent_probs = {
        outcome: (
            parent.outcomes[outcome]
            + OUTCOME_PARENT_PSEUDO_RUSHES * global_probs[outcome]
        )
        / (parent.n + OUTCOME_PARENT_PSEUDO_RUSHES)
        for outcome in OUTCOMES
    }
    raw = {
        outcome: (
            child.outcomes[outcome]
            + OUTCOME_PARENT_PSEUDO_RUSHES * parent_probs[outcome]
        )
        / (child.n + OUTCOME_PARENT_PSEUDO_RUSHES)
        for outcome in OUTCOMES
    }
    total = sum(raw.values())
    return {outcome: raw[outcome] / total for outcome in OUTCOMES}


def _yard_weights(child: Samples, parent: Samples, outcome: str) -> dict[str, float]:
    values: Counter[int] = Counter()
    values.update(child.yards[outcome])
    parent_total = sum(parent.yards[outcome].values())
    if parent_total:
        for yards, count in parent.yards[outcome].items():
            values[yards] += (
                YARD_PARENT_PSEUDO_RUSHES * count / parent_total
            )
    if not values:
        values[0] = 1.0
    return {str(yards): float(count) for yards, count in sorted(values.items())}


def _estimate(
    *, child: Samples, parent: Samples, global_samples: Samples, bucket: str
) -> dict[str, Any]:
    return {
        "bucket": bucket,
        "sample": child.raw(),
        "outcome_probabilities": _probabilities(child, parent, global_samples),
        "yard_value_weights": {
            outcome: _yard_weights(child, parent, outcome) for outcome in OUTCOMES
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pbp", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    global_samples = Samples()
    parents: defaultdict[str, Samples] = defaultdict(Samples)
    buckets: defaultdict[str, Samples] = defaultdict(Samples)
    games: set[str] = set()
    rows_examined = 0
    rushes = 0

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
            if payload.get("play_type") != "run":
                continue
            down = _number(payload.get("down"))
            yardline_100 = _number(payload.get("yardline_100"))
            distance = _number(payload.get("ydstogo"))
            yards = _number(payload.get("yards_gained"))
            if None in {down, yardline_100, distance, yards}:
                continue
            if int(down) >= 4 or yardline_100 > 20:
                continue
            game = str(payload.get("game_id") or "")
            if game:
                games.add(game)
            yardline = max(80, min(99, int(round(100 - yardline_100))))
            distance_int = max(1, int(round(distance)))
            goal_to_go = _is_one(payload.get("goal_to_go"))
            key = rz_rush_state_key(
                yardline=yardline,
                down=int(down),
                distance=distance_int,
                goal_to_go=goal_to_go,
            )
            outcome = _outcome(payload, int(round(yards)), distance_int)
            value = int(round(yards))
            global_samples.add(outcome, value)
            parents[_parent_key(key)].add(outcome, value)
            buckets[key].add(outcome, value)
            rushes += 1

    default = _estimate(
        child=global_samples,
        parent=global_samples,
        global_samples=global_samples,
        bucket="default",
    )
    payload = {
        "artifact_id": "Clock-Play Non-Fourth Red-Zone Rush Transition Priors",
        "train_window": "2013-2023 regular season",
        "historical_source": args.pbp.as_posix(),
        "historical_games_with_rz_rush": len(games),
        "historical_rows_examined": rows_examined,
        "eligible_non_fourth_red_zone_rushes": rushes,
        "outcome_definition": {
            "population": "play_type=run, down<4, yardline_100<=20",
            "touchdown": "offensive touchdown",
            "turnover": "lost fumble or interception",
            "first_down": "first_down flag or yards_gained >= ydstogo after TD/turnover removal",
            "loss": "yards_gained < 0",
            "zero": "yards_gained == 0",
            "one_two": "yards_gained in {1,2} without first down",
            "short_gain": "positive non-first-down gain above two yards",
        },
        "shrinkage": {
            "outcome_parent_pseudo_rushes": OUTCOME_PARENT_PSEUDO_RUSHES,
            "yard_parent_pseudo_rushes": YARD_PARENT_PSEUDO_RUSHES,
            "parent": "red-zone-only field × down × goal-to-go",
        },
        "priors": {
            "default": default,
            "buckets": {
                key: _estimate(
                    child=samples,
                    parent=parents[_parent_key(key)],
                    global_samples=global_samples,
                    bucket=key,
                )
                for key, samples in sorted(buckets.items())
            },
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
