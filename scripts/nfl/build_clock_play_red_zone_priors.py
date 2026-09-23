#!/usr/bin/env python3
"""Build train-only red-zone scrimmage transition priors from owned NFL PBP."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.nfl_clock_play_simulator import (  # noqa: E402
    red_zone_field_bucket,
    red_zone_situation_key,
)

TRAIN_SEASONS = frozenset(range(2013, 2024))
SCRIMMAGE_PLAY_TYPES = frozenset({"pass", "run", "qb_kneel", "qb_spike"})
OUTCOMES = (
    "touchdown",
    "first_down",
    "continue",
    "turnover",
    "turnover_on_downs",
)
OUTCOME_PARENT_PSEUDO_PLAYS = 30.0
YARDS_PARENT_PSEUDO_OBSERVATIONS = 15.0


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_one(value: Any) -> bool:
    return _number(value) == 1.0


def _mean(total: float, count: int, fallback: float) -> float:
    return total / count if count else fallback


def _stddev(total: float, squares: float, count: int, fallback: float) -> float:
    if count < 2:
        return fallback
    mean = total / count
    return max(0.25, math.sqrt(max(0.0, squares / count - mean * mean)))


@dataclass
class TransitionSamples:
    plays: int = 0
    outcomes: Counter[str] = field(default_factory=Counter)
    yard_sums: Counter[str] = field(default_factory=Counter)
    yard_squares: Counter[str] = field(default_factory=Counter)

    def add(self, *, outcome: str, yards: float) -> None:
        self.plays += 1
        self.outcomes[outcome] += 1
        self.yard_sums[outcome] += yards
        self.yard_squares[outcome] += yards * yards

    def raw(self) -> dict[str, Any]:
        return {
            "plays": self.plays,
            "outcomes": {outcome: self.outcomes[outcome] for outcome in OUTCOMES},
            "outcome_probabilities": {
                outcome: self.outcomes[outcome] / self.plays if self.plays else 0.0
                for outcome in OUTCOMES
            },
        }


def _shrunk(
    *, child_total: float, child_count: int, parent_mean: float, pseudo_count: float
) -> float:
    return (child_total + pseudo_count * parent_mean) / (child_count + pseudo_count)


def _estimate(
    *,
    child: TransitionSamples,
    parent: TransitionSamples,
    global_samples: TransitionSamples,
    bucket: str,
) -> dict[str, Any]:
    global_probs = {
        outcome: global_samples.outcomes[outcome] / global_samples.plays
        for outcome in OUTCOMES
    }
    parent_probs = {
        outcome: _shrunk(
            child_total=parent.outcomes[outcome],
            child_count=parent.plays,
            parent_mean=global_probs[outcome],
            pseudo_count=OUTCOME_PARENT_PSEUDO_PLAYS,
        )
        for outcome in OUTCOMES
    }
    raw_probs = {
        outcome: _shrunk(
            child_total=child.outcomes[outcome],
            child_count=child.plays,
            parent_mean=parent_probs[outcome],
            pseudo_count=OUTCOME_PARENT_PSEUDO_PLAYS,
        )
        for outcome in OUTCOMES
    }
    probability_total = sum(raw_probs.values())
    probabilities = {
        outcome: raw_probs[outcome] / probability_total for outcome in OUTCOMES
    }
    yards_by_outcome: dict[str, dict[str, float]] = {}
    for outcome in OUTCOMES:
        global_mean = _mean(
            global_samples.yard_sums[outcome],
            global_samples.outcomes[outcome],
            0.0,
        )
        parent_mean = _shrunk(
            child_total=parent.yard_sums[outcome],
            child_count=parent.outcomes[outcome],
            parent_mean=global_mean,
            pseudo_count=YARDS_PARENT_PSEUDO_OBSERVATIONS,
        )
        mean = _shrunk(
            child_total=child.yard_sums[outcome],
            child_count=child.outcomes[outcome],
            parent_mean=parent_mean,
            pseudo_count=YARDS_PARENT_PSEUDO_OBSERVATIONS,
        )
        parent_stddev = _stddev(
            parent.yard_sums[outcome],
            parent.yard_squares[outcome],
            parent.outcomes[outcome],
            _stddev(
                global_samples.yard_sums[outcome],
                global_samples.yard_squares[outcome],
                global_samples.outcomes[outcome],
                2.0,
            ),
        )
        yards_by_outcome[outcome] = {
            "mean": mean,
            "stddev": _stddev(
                child.yard_sums[outcome],
                child.yard_squares[outcome],
                child.outcomes[outcome],
                parent_stddev,
            ),
        }
    return {
        "bucket": bucket,
        "sample": child.raw(),
        "outcome_probabilities": probabilities,
        "yards_by_outcome": yards_by_outcome,
    }


def _outcome(payload: Mapping[str, Any]) -> str:
    offensive_td = _is_one(payload.get("touchdown")) and (
        payload.get("td_team") == payload.get("posteam")
    )
    if offensive_td:
        return "touchdown"
    if _is_one(payload.get("interception")) or _is_one(payload.get("fumble_lost")):
        return "turnover"
    if _number(payload.get("down")) == 4 and _is_one(
        payload.get("fourth_down_failed")
    ):
        return "turnover_on_downs"
    if _is_one(payload.get("first_down")):
        return "first_down"
    return "continue"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pbp", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    global_samples = TransitionSamples()
    parents: defaultdict[str, TransitionSamples] = defaultdict(TransitionSamples)
    buckets: defaultdict[str, TransitionSamples] = defaultdict(TransitionSamples)
    marginals: defaultdict[str, TransitionSamples] = defaultdict(TransitionSamples)
    games: set[str] = set()
    rows_examined = 0
    eligible_plays = 0

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
            if payload.get("play_type") not in SCRIMMAGE_PLAY_TYPES:
                continue
            yardline_100 = _number(payload.get("yardline_100"))
            down = _number(payload.get("down"))
            distance = _number(payload.get("ydstogo"))
            quarter = _number(payload.get("qtr"))
            seconds = _number(payload.get("quarter_seconds_remaining"))
            score_gap = _number(payload.get("score_differential"))
            yards = _number(payload.get("yards_gained"))
            if None in {yardline_100, down, distance, quarter, seconds, score_gap, yards}:
                continue
            yardline = max(1, min(99, int(round(100 - yardline_100))))
            if yardline < 80:
                continue
            game_id = str(payload.get("game_id") or "")
            if game_id:
                games.add(game_id)
            eligible_plays += 1
            down_int = int(round(down))
            distance_int = max(1, int(round(distance)))
            goal_to_go = _is_one(payload.get("goal_to_go"))
            key = red_zone_situation_key(
                yardline=yardline,
                down=down_int,
                distance=distance_int,
                goal_to_go=goal_to_go,
                quarter=int(round(quarter)),
                clock_seconds=seconds,
                score_gap=int(round(score_gap)),
            )
            urgency, field_bucket, goal_label, down_label, _ = key.split("|", 4)
            parent = "|".join((urgency, field_bucket, goal_label, down_label))
            outcome = _outcome(payload)
            global_samples.add(outcome=outcome, yards=float(yards))
            parents[parent].add(outcome=outcome, yards=float(yards))
            buckets[key].add(outcome=outcome, yards=float(yards))
            marginals[f"field:{red_zone_field_bucket(yardline)}"].add(
                outcome=outcome, yards=float(yards)
            )
            marginals[f"down:{down_int}"].add(outcome=outcome, yards=float(yards))
            marginals[
                f"goal_to_go:{'yes' if goal_to_go else 'no'}"
            ].add(outcome=outcome, yards=float(yards))

    default = _estimate(
        child=global_samples,
        parent=global_samples,
        global_samples=global_samples,
        bucket="default",
    )
    priors = {
        "default": default,
        "buckets": {
            key: _estimate(
                child=samples,
                parent=parents["|".join(key.split("|")[:4])],
                global_samples=global_samples,
                bucket=key,
            )
            for key, samples in sorted(buckets.items())
        },
    }
    payload = {
        "artifact_id": "Clock-Play Red-Zone Transition Priors",
        "train_window": "2013-2023 regular season",
        "historical_source": args.pbp.as_posix(),
        "historical_games_with_red_zone_scrimmage": len(games),
        "historical_rows_examined": rows_examined,
        "eligible_red_zone_scrimmage_plays": eligible_plays,
        "outcome_definition": {
            "population": "pass/run/qb kneel/qb spike at yardline_100 <= 20",
            "touchdown": "offensive touchdown",
            "turnover": "interception or lost fumble",
            "turnover_on_downs": "fourth_down_failed on fourth down",
            "first_down": "first_down flag after TD/turnover outcomes are removed",
            "continue": "all remaining valid red-zone scrimmage transitions",
        },
        "shrinkage": {
            "method": "hierarchical Dirichlet-style outcome pooling plus normal-mean yards pooling",
            "parent_to_bucket_outcome_pseudo_plays": OUTCOME_PARENT_PSEUDO_PLAYS,
            "parent_to_bucket_yards_pseudo_observations": YARDS_PARENT_PSEUDO_OBSERVATIONS,
        },
        "marginal_samples": {
            key: samples.raw() for key, samples in sorted(marginals.items())
        },
        "priors": priors,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
