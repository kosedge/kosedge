#!/usr/bin/env python3
"""Build train-only pass-or-rush call priors for the Clock-Play loop."""

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
    called_play_state_key,
)

TRAIN_SEASONS = frozenset(range(2013, 2024))
CALL_FAMILIES = ("pass", "rush")
PARENT_PSEUDO_CALLS = 60.0


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


def _parent_key(full_key: str) -> str:
    return "|".join(full_key.split("|")[:4])


def _called_family(payload: Mapping[str, Any]) -> str | None:
    """Mirror the simulator's non-fourth offensive family-routing boundary."""

    if _is_one(payload.get("two_point_attempt")) or _is_one(payload.get("qb_spike")):
        return None
    play_type = payload.get("play_type")
    if play_type == "pass" or _is_one(payload.get("qb_scramble")):
        return "pass"
    if play_type == "run" and not _is_one(payload.get("qb_kneel")):
        return "rush"
    return None


@dataclass
class CallSamples:
    n: int = 0
    calls: Counter[str] = field(default_factory=Counter)

    def add(self, family: str) -> None:
        self.n += 1
        self.calls[family] += 1


def _estimate(
    *,
    child: CallSamples,
    parent: CallSamples,
    global_samples: CallSamples,
    bucket: str,
) -> dict[str, Any]:
    global_probabilities = {
        family: global_samples.calls[family] / global_samples.n
        for family in CALL_FAMILIES
    }
    parent_probabilities = {
        family: (
            parent.calls[family] + PARENT_PSEUDO_CALLS * global_probabilities[family]
        )
        / (parent.n + PARENT_PSEUDO_CALLS)
        for family in CALL_FAMILIES
    }
    raw = {
        family: (
            child.calls[family] + PARENT_PSEUDO_CALLS * parent_probabilities[family]
        )
        / (child.n + PARENT_PSEUDO_CALLS)
        for family in CALL_FAMILIES
    }
    total = sum(raw.values())
    return {
        "bucket": bucket,
        "sample": {
            "eligible_calls": child.n,
            "families": {family: child.calls[family] for family in CALL_FAMILIES},
        },
        "call_probabilities": {
            family: raw[family] / total for family in CALL_FAMILIES
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pbp", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    global_samples = CallSamples()
    parents: defaultdict[str, CallSamples] = defaultdict(CallSamples)
    buckets: defaultdict[str, CallSamples] = defaultdict(CallSamples)
    games: set[str] = set()
    rows_examined = 0
    eligible_calls = 0

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
            family = _called_family(payload)
            if family is None:
                continue
            down = _number(payload.get("down"))
            yardline_100 = _number(payload.get("yardline_100"))
            distance = _number(payload.get("ydstogo"))
            if (
                down is None
                or yardline_100 is None
                or distance is None
                or not 1 <= int(down) <= 3
            ):
                continue
            game_id = str(payload.get("game_id") or "")
            if game_id:
                games.add(game_id)
            yardline = max(1, min(99, int(round(100 - yardline_100))))
            distance_int = max(1, int(round(distance)))
            score_gap = int(
                round(
                    (_number(payload.get("posteam_score")) or 0.0)
                    - (_number(payload.get("defteam_score")) or 0.0)
                )
            )
            key = called_play_state_key(
                yardline=yardline,
                down=int(down),
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
                samples.add(family)
            eligible_calls += 1

    if not global_samples.n:
        raise SystemExit("Historical PBP did not contain eligible play calls")

    payload = {
        "artifact_id": "Clock-Play Called Play State Priors",
        "train_window": "2013-2023 regular season",
        "historical_source": args.pbp.as_posix(),
        "historical_games": len(games),
        "historical_rows_examined": rows_examined,
        "eligible_non_fourth_calls": eligible_calls,
        "routing_contract": {
            "selection": (
                "one pass-or-rush family before any pass, designed-rush, or "
                "red-zone-rush outcome is resolved"
            ),
            "pass": "play_type=pass or qb_scramble, excluding spikes and tries",
            "rush": (
                "play_type=run, excluding qb_scramble, qb_kneel, spikes, and tries"
            ),
            "fourth_down": "excluded because fourth-down decision owns that snap",
        },
        "shrinkage": {
            "parent_pseudo_calls": PARENT_PSEUDO_CALLS,
            "parent": "field-position × down × distance × goal-to-go",
        },
        "priors": {
            "called_play": {
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
