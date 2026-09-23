#!/usr/bin/env python3
"""Build train-only red-zone fourth-down action priors."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))
from src.services.nfl_clock_play_simulator import rz_fourth_decision_state_key  # noqa: E402

TRAIN_SEASONS = frozenset(range(2013, 2024))
CORE = frozenset({"pass", "run", "qb_kneel", "qb_spike", "field_goal", "punt"})
ACTIONS = ("field_goal", "go", "punt")
PARENT_PSEUDO_DECISIONS = 30.0


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_one(value: Any) -> bool:
    return _number(value) == 1.0


@dataclass
class Samples:
    n: int = 0
    actions: Counter[str] = field(default_factory=Counter)

    def add(self, action: str) -> None:
        self.n += 1
        self.actions[action] += 1

    def raw(self) -> dict[str, Any]:
        return {
            "decisions": self.n,
            "actions": {action: self.actions[action] for action in ACTIONS},
            "action_probabilities": {
                action: self.actions[action] / self.n if self.n else 0.0
                for action in ACTIONS
            },
        }


def _parent(key: str) -> str:
    return key.split("|")[0]


def estimate(child: Samples, parent: Samples, global_sample: Samples, bucket: str) -> dict[str, Any]:
    global_probs = {
        action: global_sample.actions[action] / global_sample.n for action in ACTIONS
    }
    parent_probs = {
        action: (
            parent.actions[action] + PARENT_PSEUDO_DECISIONS * global_probs[action]
        )
        / (parent.n + PARENT_PSEUDO_DECISIONS)
        for action in ACTIONS
    }
    raw = {
        action: (
            child.actions[action] + PARENT_PSEUDO_DECISIONS * parent_probs[action]
        )
        / (child.n + PARENT_PSEUDO_DECISIONS)
        for action in ACTIONS
    }
    total = sum(raw.values())
    return {
        "bucket": bucket,
        "sample": child.raw(),
        "action_probabilities": {action: raw[action] / total for action in ACTIONS},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pbp", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    global_sample = Samples()
    parents: defaultdict[str, Samples] = defaultdict(Samples)
    buckets: defaultdict[str, Samples] = defaultdict(Samples)
    games: set[str] = set()
    rows = 0

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
            play_type = str(p.get("play_type") or "")
            yardline_100 = _number(p.get("yardline_100"))
            if (
                play_type not in CORE
                or _number(p.get("down")) != 4
                or yardline_100 is None
                or yardline_100 > 20
            ):
                continue
            game = str(p.get("game_id") or "")
            if game:
                games.add(game)
            yardline = max(80, min(99, int(round(100 - yardline_100))))
            distance = max(1, int(_number(p.get("ydstogo")) or 10))
            key = rz_fourth_decision_state_key(
                yardline=yardline,
                distance=distance,
                goal_to_go=_is_one(p.get("goal_to_go")),
            )
            action = (
                "field_goal"
                if play_type == "field_goal"
                else "punt"
                if play_type == "punt"
                else "go"
            )
            global_sample.add(action)
            parents[_parent(key)].add(action)
            buckets[key].add(action)

    default = estimate(global_sample, global_sample, global_sample, "default")
    payload = {
        "artifact_id": "Clock-Play Red-Zone Fourth-Down Decision Priors",
        "train_window": "2013-2023 regular season",
        "historical_source": args.pbp.as_posix(),
        "historical_games_with_rz_fourth": len(games),
        "historical_rows_examined": rows,
        "shrinkage": {
            "parent": "red-zone field bucket",
            "parent_pseudo_decisions": PARENT_PSEUDO_DECISIONS,
        },
        "priors": {
            "default": default,
            "buckets": {
                key: estimate(
                    sample, parents[_parent(key)], global_sample, key
                )
                for key, sample in sorted(buckets.items())
            },
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
