#!/usr/bin/env python3
"""Build train-only exclusive designed-rush priors for the Clock-Play loop."""

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
    designed_rush_state_key,
)

TRAIN_SEASONS = frozenset(range(2013, 2024))
RUSH_OUTCOMES = (
    "touchdown",
    "fumble",
    "first_down",
    "loss",
    "zero",
    "short_gain",
)
OUTCOME_PARENT_PSEUDO_RUSHES = 60.0
YARD_PARENT_PSEUDO_RUSHES = 20.0


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


def _counter_weights(
    child: Counter[int], parent: Counter[int], *, fallback: int = 0
) -> dict[str, float]:
    weights: Counter[int] = Counter(child)
    parent_total = sum(parent.values())
    if parent_total:
        for value, count in parent.items():
            weights[value] += YARD_PARENT_PSEUDO_RUSHES * count / parent_total
    if not weights:
        weights[fallback] = 1.0
    return {str(value): float(count) for value, count in sorted(weights.items())}


@dataclass
class RushSamples:
    n: int = 0
    outcomes: Counter[str] = field(default_factory=Counter)
    yards: dict[str, Counter[int]] = field(
        default_factory=lambda: defaultdict(Counter)
    )
    return_yards: Counter[int] = field(default_factory=Counter)
    return_touchdowns: int = 0

    def add(
        self,
        *,
        outcome: str,
        yards: int,
        return_yards: int,
        return_touchdown: bool,
    ) -> None:
        self.n += 1
        self.outcomes[outcome] += 1
        self.yards[outcome][yards] += 1
        if outcome == "fumble":
            self.return_yards[return_yards] += 1
            self.return_touchdowns += int(return_touchdown)


def _outcome(payload: Mapping[str, Any], yards: int, distance: int) -> str:
    if _is_one(payload.get("fumble_lost")):
        return "fumble"
    if _is_one(payload.get("touchdown")) and payload.get("td_team") == payload.get(
        "posteam"
    ):
        return "touchdown"
    if _is_one(payload.get("first_down")) or yards >= distance:
        return "first_down"
    if yards < 0:
        return "loss"
    if yards == 0:
        return "zero"
    return "short_gain"


def _parent_key(full_key: str) -> str:
    return "|".join(full_key.split("|")[:4])


def _estimate(
    *,
    child: RushSamples,
    parent: RushSamples,
    global_samples: RushSamples,
    bucket: str,
) -> dict[str, Any]:
    global_probs = {
        outcome: global_samples.outcomes[outcome] / global_samples.n
        for outcome in RUSH_OUTCOMES
    }
    parent_probs = {
        outcome: (
            parent.outcomes[outcome] + OUTCOME_PARENT_PSEUDO_RUSHES * global_probs[outcome]
        )
        / (parent.n + OUTCOME_PARENT_PSEUDO_RUSHES)
        for outcome in RUSH_OUTCOMES
    }
    raw = {
        outcome: (
            child.outcomes[outcome] + OUTCOME_PARENT_PSEUDO_RUSHES * parent_probs[outcome]
        )
        / (child.n + OUTCOME_PARENT_PSEUDO_RUSHES)
        for outcome in RUSH_OUTCOMES
    }
    total = sum(raw.values())
    return {
        "bucket": bucket,
        "sample": {
            "designed_rushes": child.n,
            "outcomes": {outcome: child.outcomes[outcome] for outcome in RUSH_OUTCOMES},
        },
        "outcome_probabilities": {
            outcome: raw[outcome] / total for outcome in RUSH_OUTCOMES
        },
        "yard_value_weights": {
            outcome: _counter_weights(
                child.yards[outcome],
                parent.yards[outcome],
                fallback=0,
            )
            for outcome in RUSH_OUTCOMES
        },
        "turnover_returns": {
            "fumble": {
                "touchdown_rate": (
                    child.return_touchdowns / child.outcomes["fumble"]
                    if child.outcomes["fumble"]
                    else (
                        parent.return_touchdowns / parent.outcomes["fumble"]
                        if parent.outcomes["fumble"]
                        else (
                            global_samples.return_touchdowns
                            / global_samples.outcomes["fumble"]
                            if global_samples.outcomes["fumble"]
                            else 0.0
                        )
                    )
                ),
                "return_yard_weights": _counter_weights(
                    child.return_yards,
                    parent.return_yards,
                ),
            }
        },
    }


def _is_designed_rush(payload: Mapping[str, Any]) -> bool:
    return (
        payload.get("play_type") == "run"
        and not _is_one(payload.get("qb_scramble"))
        and not _is_one(payload.get("qb_kneel"))
        and not _is_one(payload.get("two_point_attempt"))
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pbp", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    global_samples = RushSamples()
    parents: defaultdict[str, RushSamples] = defaultdict(RushSamples)
    buckets: defaultdict[str, RushSamples] = defaultdict(RushSamples)
    games: set[str] = set()
    rows_examined = 0
    eligible_rushes = 0

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
            if not _is_designed_rush(payload):
                continue
            down = _number(payload.get("down"))
            yardline_100 = _number(payload.get("yardline_100"))
            distance = _number(payload.get("ydstogo"))
            yards = _number(payload.get("yards_gained"))
            if None in {down, yardline_100, distance, yards}:
                continue
            if yardline_100 <= 20:
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
            key = designed_rush_state_key(
                yardline=yardline,
                down=int(down),
                distance=distance_int,
                goal_to_go=_is_one(payload.get("goal_to_go")),
                quarter=int(_number(payload.get("qtr")) or 1),
                clock_seconds=_number(payload.get("quarter_seconds_remaining")) or 0.0,
                score_gap=score_gap,
            )
            rush_yards = int(round(yards))
            outcome = _outcome(payload, rush_yards, distance_int)
            return_touchdown = _is_one(payload.get("touchdown")) and (
                payload.get("td_team") == payload.get("defteam")
            )
            sample_kwargs = {
                "outcome": outcome,
                "yards": rush_yards,
                "return_yards": int(round(_number(payload.get("return_yards")) or 0.0)),
                "return_touchdown": return_touchdown,
            }
            for samples in (
                global_samples,
                parents[_parent_key(key)],
                buckets[key],
            ):
                samples.add(**sample_kwargs)
            eligible_rushes += 1

    if not global_samples.n:
        raise SystemExit("Historical PBP did not contain eligible designed rushes")

    payload = {
        "artifact_id": "Clock-Play Exclusive Designed-Rush State Priors",
        "train_window": "2013-2023 regular season",
        "historical_source": args.pbp.as_posix(),
        "historical_games_with_designed_rush": len(games),
        "historical_rows_examined": rows_examined,
        "eligible_non_red_zone_designed_rushes": eligible_rushes,
        "routing_contract": {
            "called_pass": "pass_state only",
            "designed_rush": "designed_rush_state only outside the red zone",
            "red_zone_rush": "red_zone_rush_transition before designed_rush_state",
            "fourth_down": "decision and continuation before designed_rush_state",
            "fumble": "selected designed_rush_state fumble and its direct return only",
        },
        "outcome_definition": {
            "population": (
                "play_type=run, yardline_100>20, excluding qb_scramble, qb_kneel, "
                "and two_point_attempt"
            ),
            "fumble": "lost fumble",
            "touchdown": "offensive touchdown after lost-fumble removal",
            "first_down": (
                "first_down flag or yards_gained >= ydstogo after touchdown/fumble removal"
            ),
            "loss": "yards_gained < 0",
            "zero": "yards_gained == 0",
            "short_gain": "positive non-first-down gain",
        },
        "shrinkage": {
            "outcome_parent_pseudo_rushes": OUTCOME_PARENT_PSEUDO_RUSHES,
            "yard_parent_pseudo_rushes": YARD_PARENT_PSEUDO_RUSHES,
            "parent": "field-position × down × distance × goal-to-go",
        },
        "priors": {
            "designed_rush": {
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
