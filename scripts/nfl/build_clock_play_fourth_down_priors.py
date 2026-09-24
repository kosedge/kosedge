#!/usr/bin/env python3
"""Build train-only fourth-down GO continuation priors from owned NFL PBP."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.nfl_clock_play_simulator import (  # noqa: E402
    fourth_down_distance_bucket,
    fourth_down_field_bucket,
    fourth_down_situation_key,
)

TRAIN_SEASONS = frozenset(range(2013, 2024))
GO_PLAY_TYPES = frozenset({"pass", "run", "qb_kneel", "qb_spike"})
CONVERSION_PARENT_PSEUDO_ATTEMPTS = 20.0
TD_PARENT_PSEUDO_CONVERSIONS = 12.0
YARDS_PARENT_PSEUDO_OBSERVATIONS = 12.0


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_one(value: Any) -> bool:
    numeric = _number(value)
    return numeric is not None and numeric == 1.0


def _mean(total: float, count: int, fallback: float) -> float:
    return total / count if count else fallback


def _stddev(total: float, square_total: float, count: int, fallback: float) -> float:
    if count < 2:
        return fallback
    mean = total / count
    return max(0.5, math.sqrt(max(0.0, square_total / count - mean * mean)))


@dataclass
class Outcomes:
    attempts: int = 0
    conversions: int = 0
    touchdown_conversions: int = 0
    converted_non_td_count: int = 0
    converted_non_td_yards_sum: float = 0.0
    converted_non_td_yards_sq_sum: float = 0.0
    failures: int = 0
    failure_yards_sum: float = 0.0
    failure_yards_sq_sum: float = 0.0

    def add(self, *, converted: bool, touchdown: bool, yards: float) -> None:
        self.attempts += 1
        if converted:
            self.conversions += 1
            if touchdown:
                self.touchdown_conversions += 1
            else:
                self.converted_non_td_count += 1
                self.converted_non_td_yards_sum += yards
                self.converted_non_td_yards_sq_sum += yards * yards
            return
        self.failures += 1
        self.failure_yards_sum += yards
        self.failure_yards_sq_sum += yards * yards

    def raw(self) -> dict[str, float | int]:
        return {
            "attempts": self.attempts,
            "conversions": self.conversions,
            "conversion_rate": self.conversions / self.attempts if self.attempts else 0.0,
            "touchdown_conversions": self.touchdown_conversions,
            "td_given_conversion": (
                self.touchdown_conversions / self.conversions
                if self.conversions
                else 0.0
            ),
            "converted_non_td_count": self.converted_non_td_count,
            "failures": self.failures,
        }


def _shrunk_mean(
    *,
    child_total: float,
    child_count: int,
    parent_mean: float,
    pseudo_count: float,
) -> float:
    return (child_total + pseudo_count * parent_mean) / (child_count + pseudo_count)


def _estimate(
    *,
    child: Outcomes,
    parent: Outcomes,
    global_outcomes: Outcomes,
    bucket: str,
) -> dict[str, Any]:
    global_conversion = _mean(
        global_outcomes.conversions, global_outcomes.attempts, 0.5
    )
    parent_conversion = _shrunk_mean(
        child_total=parent.conversions,
        child_count=parent.attempts,
        parent_mean=global_conversion,
        pseudo_count=CONVERSION_PARENT_PSEUDO_ATTEMPTS,
    )
    conversion = _shrunk_mean(
        child_total=child.conversions,
        child_count=child.attempts,
        parent_mean=parent_conversion,
        pseudo_count=CONVERSION_PARENT_PSEUDO_ATTEMPTS,
    )
    global_td = _mean(
        global_outcomes.touchdown_conversions,
        global_outcomes.conversions,
        0.25,
    )
    parent_td = _shrunk_mean(
        child_total=parent.touchdown_conversions,
        child_count=parent.conversions,
        parent_mean=global_td,
        pseudo_count=TD_PARENT_PSEUDO_CONVERSIONS,
    )
    td_given_conversion = _shrunk_mean(
        child_total=child.touchdown_conversions,
        child_count=child.conversions,
        parent_mean=parent_td,
        pseudo_count=TD_PARENT_PSEUDO_CONVERSIONS,
    )

    global_converted_yards = _mean(
        global_outcomes.converted_non_td_yards_sum,
        global_outcomes.converted_non_td_count,
        4.0,
    )
    parent_converted_yards = _shrunk_mean(
        child_total=parent.converted_non_td_yards_sum,
        child_count=parent.converted_non_td_count,
        parent_mean=global_converted_yards,
        pseudo_count=YARDS_PARENT_PSEUDO_OBSERVATIONS,
    )
    converted_yards = _shrunk_mean(
        child_total=child.converted_non_td_yards_sum,
        child_count=child.converted_non_td_count,
        parent_mean=parent_converted_yards,
        pseudo_count=YARDS_PARENT_PSEUDO_OBSERVATIONS,
    )

    global_failure_yards = _mean(
        global_outcomes.failure_yards_sum, global_outcomes.failures, 0.0
    )
    parent_failure_yards = _shrunk_mean(
        child_total=parent.failure_yards_sum,
        child_count=parent.failures,
        parent_mean=global_failure_yards,
        pseudo_count=YARDS_PARENT_PSEUDO_OBSERVATIONS,
    )
    failure_yards = _shrunk_mean(
        child_total=child.failure_yards_sum,
        child_count=child.failures,
        parent_mean=parent_failure_yards,
        pseudo_count=YARDS_PARENT_PSEUDO_OBSERVATIONS,
    )

    return {
        "bucket": bucket,
        "sample": child.raw(),
        "conversion_rate": conversion,
        "td_given_conversion": td_given_conversion,
        "converted_non_td_yards": {
            "mean": converted_yards,
            "stddev": _stddev(
                child.converted_non_td_yards_sum,
                child.converted_non_td_yards_sq_sum,
                child.converted_non_td_count,
                _stddev(
                    parent.converted_non_td_yards_sum,
                    parent.converted_non_td_yards_sq_sum,
                    parent.converted_non_td_count,
                    2.0,
                ),
            ),
        },
        "failure_yards": {
            "mean": failure_yards,
            "stddev": _stddev(
                child.failure_yards_sum,
                child.failure_yards_sq_sum,
                child.failures,
                _stddev(
                    parent.failure_yards_sum,
                    parent.failure_yards_sq_sum,
                    parent.failures,
                    2.0,
                ),
            ),
        },
    }


def _is_go_play(payload: Mapping[str, Any]) -> bool:
    play_type = payload.get("play_type")
    if play_type in GO_PLAY_TYPES:
        return True
    return play_type == "no_play" and (
        _is_one(payload.get("pass")) or _is_one(payload.get("rush"))
    )


def _marginal_field_labels(
    *, yardline: int, goal_to_go: bool
) -> tuple[str, ...]:
    distance_to_goal = 100 - yardline
    labels = ["opponent_territory" if yardline >= 50 else "own_territory"]
    if yardline >= 80:
        labels.append("red_zone")
    if goal_to_go:
        labels.append("goal_to_go")
    if distance_to_goal <= 5:
        labels.append("inside_5")
    if distance_to_goal <= 1:
        labels.append("at_1")
    return tuple(labels)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pbp", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    global_outcomes = Outcomes()
    by_parent: defaultdict[str, Outcomes] = defaultdict(Outcomes)
    by_bucket: defaultdict[str, Outcomes] = defaultdict(Outcomes)
    marginals: defaultdict[str, Outcomes] = defaultdict(Outcomes)
    games: set[str] = set()
    rows_examined = 0
    eligible_go_attempts = 0

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
            if _number(payload.get("down")) != 4 or not _is_go_play(payload):
                continue
            distance = _number(payload.get("ydstogo"))
            yardline_100 = _number(payload.get("yardline_100"))
            quarter = _number(payload.get("qtr"))
            seconds = _number(payload.get("quarter_seconds_remaining"))
            score_gap = _number(payload.get("score_differential"))
            yards = _number(payload.get("yards_gained"))
            if None in {distance, yardline_100, quarter, seconds, score_gap, yards}:
                continue
            converted = _is_one(payload.get("fourth_down_converted"))
            failed = _is_one(payload.get("fourth_down_failed"))
            touchdown = _is_one(payload.get("touchdown")) and (
                payload.get("td_team") == payload.get("posteam")
            )
            converted = converted or touchdown
            if not converted and not failed:
                continue

            game_id = str(payload.get("game_id") or "")
            if game_id:
                games.add(game_id)
            eligible_go_attempts += 1
            yardline = max(1, min(99, int(round(100 - yardline_100))))
            goal_to_go = _is_one(payload.get("goal_to_go"))
            distance_int = max(1, int(round(distance)))
            score_gap_int = int(round(score_gap))
            bucket = fourth_down_situation_key(
                yardline=yardline,
                distance=distance_int,
                goal_to_go=goal_to_go,
                quarter=int(round(quarter)),
                clock_seconds=seconds,
                score_gap=score_gap_int,
            )
            urgency, distance_bucket, _ = bucket.split("|", 2)
            parent = f"{urgency}|{distance_bucket}"
            global_outcomes.add(
                converted=converted, touchdown=touchdown, yards=float(yards)
            )
            by_parent[parent].add(
                converted=converted, touchdown=touchdown, yards=float(yards)
            )
            by_bucket[bucket].add(
                converted=converted, touchdown=touchdown, yards=float(yards)
            )
            marginals[f"yards:{distance_bucket}"].add(
                converted=converted, touchdown=touchdown, yards=float(yards)
            )
            for label in _marginal_field_labels(
                yardline=yardline, goal_to_go=goal_to_go
            ):
                marginals[f"field:{label}"].add(
                    converted=converted, touchdown=touchdown, yards=float(yards)
                )

    default = _estimate(
        child=global_outcomes,
        parent=global_outcomes,
        global_outcomes=global_outcomes,
        bucket="default",
    )
    priors = {
        "default": default,
        "buckets": {
            bucket: _estimate(
                child=outcomes,
                parent=by_parent["|".join(bucket.split("|")[:2])],
                global_outcomes=global_outcomes,
                bucket=bucket,
            )
            for bucket, outcomes in sorted(by_bucket.items())
        },
    }
    payload = {
        "artifact_id": "Clock-Play v1.2 Fourth-Down Continuation Priors",
        "train_window": "2013-2023 regular season",
        "historical_source": args.pbp.as_posix(),
        "historical_games": len(games),
        "historical_rows_examined": rows_examined,
        "eligible_fourth_down_go_attempts": eligible_go_attempts,
        "outcome_definition": {
            "go_attempt": "fourth-down pass/run/qb kneel/qb spike with a recorded conversion or failure",
            "conversion": "fourth_down_converted or offensive touchdown",
            "touchdown": "touchdown with td_team == posteam",
            "failure": "fourth_down_failed",
            "failure_field_position": "recorded yards_gained applied to the pre-play line of scrimmage",
        },
        "shrinkage": {
            "method": "hierarchical beta-binomial for rates and normal-mean pooling for yards",
            "global_to_parent_conversion_pseudo_attempts": CONVERSION_PARENT_PSEUDO_ATTEMPTS,
            "parent_to_bucket_conversion_pseudo_attempts": CONVERSION_PARENT_PSEUDO_ATTEMPTS,
            "global_to_parent_td_pseudo_conversions": TD_PARENT_PSEUDO_CONVERSIONS,
            "parent_to_bucket_td_pseudo_conversions": TD_PARENT_PSEUDO_CONVERSIONS,
            "parent_to_bucket_yards_pseudo_observations": YARDS_PARENT_PSEUDO_OBSERVATIONS,
        },
        "marginal_samples": {
            key: outcomes.raw() for key, outcomes in sorted(marginals.items())
        },
        "priors": priors,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
