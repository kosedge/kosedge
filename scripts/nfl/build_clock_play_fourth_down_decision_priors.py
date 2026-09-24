#!/usr/bin/env python3
"""Build train-only non-red-zone fourth-down decision priors."""

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

from src.services.nfl_clock_play_simulator import (  # noqa: E402
    fourth_down_decision_state_key,
)

TRAIN_SEASONS = frozenset(range(2013, 2024))
ACTIONS = ("field_goal", "go", "punt")
PARENT_PSEUDO_DECISIONS = 30.0


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if numeric == numeric else None


def _is_one(value: Any) -> bool:
    return _number(value) == 1.0


def _is_go_attempt(payload: Mapping[str, Any]) -> bool:
    play_type = payload.get("play_type")
    return play_type in {"pass", "run", "qb_kneel", "qb_spike"} or (
        play_type == "no_play"
        and (_is_one(payload.get("pass")) or _is_one(payload.get("rush")))
    )


def _action(payload: Mapping[str, Any]) -> str | None:
    play_type = payload.get("play_type")
    if play_type == "field_goal":
        return "field_goal"
    if play_type == "punt":
        return "punt"
    if _is_go_attempt(payload):
        return "go"
    return None


def _parent_key(full_key: str) -> str:
    urgency, _distance, field = full_key.split("|")
    return f"{urgency}|{field}"


@dataclass
class DecisionSamples:
    n: int = 0
    actions: Counter[str] = field(default_factory=Counter)

    def add(self, action: str) -> None:
        self.n += 1
        self.actions[action] += 1


def _estimate(
    *,
    child: DecisionSamples,
    parent: DecisionSamples,
    global_samples: DecisionSamples,
    bucket: str,
) -> dict[str, Any]:
    global_probabilities = {
        action: global_samples.actions[action] / global_samples.n
        for action in ACTIONS
    }
    parent_probabilities = {
        action: (
            parent.actions[action]
            + PARENT_PSEUDO_DECISIONS * global_probabilities[action]
        )
        / (parent.n + PARENT_PSEUDO_DECISIONS)
        for action in ACTIONS
    }
    raw = {
        action: (
            child.actions[action]
            + PARENT_PSEUDO_DECISIONS * parent_probabilities[action]
        )
        / (child.n + PARENT_PSEUDO_DECISIONS)
        for action in ACTIONS
    }
    total = sum(raw.values())
    return {
        "bucket": bucket,
        "sample": {
            "decisions": child.n,
            "actions": {action: child.actions[action] for action in ACTIONS},
        },
        "action_probabilities": {
            action: raw[action] / total for action in ACTIONS
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pbp", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    global_samples = DecisionSamples()
    parents: defaultdict[str, DecisionSamples] = defaultdict(DecisionSamples)
    buckets: defaultdict[str, DecisionSamples] = defaultdict(DecisionSamples)
    games: set[str] = set()
    rows_examined = 0
    eligible_decisions = 0

    with args.pbp.open(encoding="utf-8") as handle:
        for raw_line in handle:
            row = json.loads(raw_line)
            payload = (
                row.get("payload") if row.get("object_type") == "pbp_play" else None
            )
            if not isinstance(payload, Mapping):
                continue
            season = _number(payload.get("season"))
            if season is None or int(season) not in TRAIN_SEASONS:
                continue
            if payload.get("season_type") != "REG":
                continue
            rows_examined += 1
            action = _action(payload)
            down = _number(payload.get("down"))
            yardline_100 = _number(payload.get("yardline_100"))
            distance = _number(payload.get("ydstogo"))
            if (
                action is None
                or down != 4
                or yardline_100 is None
                or distance is None
                or yardline_100 <= 20
            ):
                continue
            game_id = str(payload.get("game_id") or "")
            if game_id:
                games.add(game_id)
            yardline = max(1, min(79, int(round(100 - yardline_100))))
            distance_int = max(1, int(round(distance)))
            score_gap = int(
                round(
                    (_number(payload.get("posteam_score")) or 0.0)
                    - (_number(payload.get("defteam_score")) or 0.0)
                )
            )
            key = fourth_down_decision_state_key(
                yardline=yardline,
                distance=distance_int,
                goal_to_go=distance_int >= 100 - yardline,
                quarter=int(_number(payload.get("qtr")) or 1),
                clock_seconds=_number(payload.get("quarter_seconds_remaining")) or 0.0,
                score_gap=score_gap,
            )
            for samples in (
                global_samples,
                parents[_parent_key(key)],
                buckets[key],
            ):
                samples.add(action)
            eligible_decisions += 1

    if not global_samples.n:
        raise SystemExit("Historical PBP did not contain eligible fourth-down decisions")

    payload = {
        "artifact_id": "Clock-Play Non-Red-Zone Fourth-Down Decision Priors",
        "train_window": "2013-2023 regular season",
        "historical_source": args.pbp.as_posix(),
        "historical_games": len(games),
        "historical_rows_examined": rows_examined,
        "eligible_non_red_zone_fourth_down_decisions": eligible_decisions,
        "routing_contract": {
            "population": (
                "fourth-down field_goal, punt, or go attempt outside the opponent 20"
            ),
            "field_goal": "play_type=field_goal",
            "punt": "play_type=punt",
            "go": "pass, run, qb_kneel, qb_spike, or eligible no_play",
            "red_zone": "excluded; owned by the red-zone fourth-down decision family",
        },
        "shrinkage": {
            "parent_pseudo_decisions": PARENT_PSEUDO_DECISIONS,
            "parent": "urgency × field position",
        },
        "priors": {
            "fourth_down_decision": {
                "default": _estimate(
                    child=global_samples,
                    parent=global_samples,
                    global_samples=global_samples,
                    bucket="default",
                ),
                "buckets": {
                    key: _estimate(
                        child=samples,
                        parent=parents[_parent_key(key)],
                        global_samples=global_samples,
                        bucket=key,
                    )
                    for key, samples in sorted(buckets.items())
                },
            }
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
