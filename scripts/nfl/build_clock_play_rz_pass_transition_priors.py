#!/usr/bin/env python3
"""Build train-only non-fourth red-zone pass transition priors.

Population: same-drive red-zone pass routes at offensive yardline 80-99 with
down<4, excluding the first red-zone continuation owned by the joint pre-entry
pass/RZ handoff (pass at 70-79 immediately before the drive's first red-zone
route when the drive did not start inside the red zone).
"""

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

from src.services.nfl_clock_play_simulator import rz_rush_state_key  # noqa: E402

TRAIN_SEASONS = frozenset(range(2013, 2024))
OUTCOMES = (
    "touchdown",
    "turnover",
    "incomplete",
    "loss",
    "zero",
    "one_two",
    "short_gain",
    "first_down",
)
OUTCOME_PARENT_PSEUDO_PASSES = 30.0
YARD_PARENT_PSEUDO_PASSES = 12.0


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_one(value: Any) -> bool:
    return _number(value) == 1.0


def _offensive_yardline(payload: Mapping[str, Any]) -> int | None:
    yardline_100 = _number(payload.get("yardline_100"))
    if yardline_100 is None:
        return None
    return max(1, min(99, int(round(100 - yardline_100))))


def _is_pass_call(payload: Mapping[str, Any]) -> bool:
    return (
        not _is_one(payload.get("two_point_attempt"))
        and not _is_one(payload.get("qb_spike"))
        and (
            payload.get("play_type") == "pass" or _is_one(payload.get("qb_scramble"))
        )
    )


def _is_rush_call(payload: Mapping[str, Any]) -> bool:
    return (
        payload.get("play_type") == "run"
        and not _is_one(payload.get("two_point_attempt"))
        and not _is_one(payload.get("qb_scramble"))
        and not _is_one(payload.get("qb_kneel"))
        and not _is_one(payload.get("qb_spike"))
    )


def _route(payload: Mapping[str, Any]) -> str | None:
    down = _number(payload.get("down"))
    if down == 4:
        play_type = str(payload.get("play_type") or "")
        if play_type == "field_goal":
            return "field_goal"
        if play_type == "punt":
            return "punt"
        if play_type in {"pass", "run"}:
            return "fourth_down_go"
        return None
    if _is_pass_call(payload):
        return "pass"
    if _is_rush_call(payload):
        return "run"
    return None


def _drive_started_inside_red_zone(payload: Mapping[str, Any]) -> bool:
    start = str(payload.get("drive_start_yard_line") or "").strip()
    posteam = str(payload.get("posteam") or "").strip()
    parts = start.split()
    if len(parts) != 2 or not posteam:
        return False
    try:
        yards_from_own = int(parts[1])
    except ValueError:
        return False
    team = parts[0]
    if team == posteam:
        return yards_from_own >= 80
    return (100 - yards_from_own) >= 80


def _outcome(payload: Mapping[str, Any], yards: int, distance: int) -> str:
    if _is_one(payload.get("incomplete_pass")):
        return "incomplete"
    if _is_one(payload.get("touchdown")) and payload.get("td_team") == payload.get(
        "posteam"
    ):
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
            "passes": self.n,
            "outcomes": {outcome: self.outcomes[outcome] for outcome in OUTCOMES},
            "outcome_probabilities": {
                outcome: self.outcomes[outcome] / self.n if self.n else 0.0
                for outcome in OUTCOMES
            },
        }


@dataclass
class Crossing:
    pre_entry_yardline: int


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
            + OUTCOME_PARENT_PSEUDO_PASSES * global_probs[outcome]
        )
        / (parent.n + OUTCOME_PARENT_PSEUDO_PASSES)
        for outcome in OUTCOMES
    }
    raw = {
        outcome: (
            child.outcomes[outcome]
            + OUTCOME_PARENT_PSEUDO_PASSES * parent_probs[outcome]
        )
        / (child.n + OUTCOME_PARENT_PSEUDO_PASSES)
        for outcome in OUTCOMES
    }
    total = sum(raw.values())
    return {outcome: raw[outcome] / total for outcome in OUTCOMES}


def _yard_weights(child: Samples, parent: Samples, outcome: str) -> dict[str, float]:
    if outcome == "incomplete":
        return {"0": 1.0}
    values: Counter[int] = Counter()
    values.update(child.yards[outcome])
    parent_total = sum(parent.yards[outcome].values())
    if parent_total:
        for yards, count in parent.yards[outcome].items():
            values[yards] += YARD_PARENT_PSEUDO_PASSES * count / parent_total
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
    passes = 0
    excluded_pre_entry_owned = 0
    active_crossings: dict[tuple[str, int, str], Crossing | None] = {}
    drive_seen_rz: dict[tuple[str, int, str], bool] = {}
    drive_started_inside: dict[tuple[str, int, str], bool] = {}

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
            game_id = str(payload.get("game_id") or "")
            fixed_drive = _number(payload.get("fixed_drive"))
            posteam = str(payload.get("posteam") or "")
            if not game_id or fixed_drive is None or not posteam:
                continue
            drive_key = (game_id, int(fixed_drive), posteam)
            drive_seen_rz.setdefault(drive_key, False)
            active_crossings.setdefault(drive_key, None)
            drive_started_inside.setdefault(
                drive_key, _drive_started_inside_red_zone(payload)
            )
            yardline = _offensive_yardline(payload)
            down = _number(payload.get("down"))
            distance = _number(payload.get("ydstogo"))
            yards = _number(payload.get("yards_gained"))
            route = _route(payload)

            if (
                route == "pass"
                and yardline is not None
                and down is not None
                and yards is not None
                and 80 <= yardline <= 99
                and int(down) < 4
            ):
                first_rz = not drive_seen_rz[drive_key]
                owned_by_pre_entry = (
                    first_rz
                    and active_crossings[drive_key] is not None
                    and not drive_started_inside[drive_key]
                )
                if owned_by_pre_entry:
                    excluded_pre_entry_owned += 1
                else:
                    distance_int = max(1, int(round(distance)))
                    goal_to_go = _is_one(payload.get("goal_to_go"))
                    key = rz_rush_state_key(
                        yardline=yardline,
                        down=int(down),
                        distance=distance_int,
                        goal_to_go=goal_to_go,
                    )
                    outcome = _outcome(payload, int(round(yards)), distance_int)
                    value = 0 if outcome == "incomplete" else int(round(yards))
                    global_samples.add(outcome, value)
                    parents[_parent_key(key)].add(outcome, value)
                    buckets[key].add(outcome, value)
                    passes += 1
                    games.add(game_id)

            if yardline is not None and yardline >= 80:
                drive_seen_rz[drive_key] = True

            if route is not None:
                if route == "pass" and yardline is not None and 70 <= yardline <= 79:
                    active_crossings[drive_key] = Crossing(
                        pre_entry_yardline=yardline
                    )
                else:
                    active_crossings[drive_key] = None

    if not global_samples.n:
        raise SystemExit("No eligible non-handoff red-zone pass transitions found")

    default = _estimate(
        child=global_samples,
        parent=global_samples,
        global_samples=global_samples,
        bucket="default",
    )
    payload = {
        "accounting": {
            "eligible_non_handoff_rz_passes": passes,
            "excluded_pre_entry_owned_first_rz": excluded_pre_entry_owned,
        },
        "artifact_id": "Clock-Play Non-Fourth Red-Zone Pass Transition Priors",
        "train_window": "2013-2023 regular season",
        "historical_source": args.pbp.as_posix(),
        "historical_games_with_rz_pass": len(games),
        "historical_rows_examined": rows_examined,
        "outcome_definition": {
            "population": (
                "pass routes at offensive yardline 80-99 with down<4, excluding "
                "the joint pre-entry first-RZ continuation"
            ),
            "incomplete": "incomplete_pass flag",
            "touchdown": "offensive touchdown",
            "turnover": "lost fumble or interception",
            "first_down": "first_down flag or yards_gained >= ydstogo",
            "loss": "yards_gained < 0",
            "zero": "yards_gained == 0",
            "one_two": "yards_gained in {1,2} without first down",
            "short_gain": "positive non-first-down gain above two yards",
        },
        "shrinkage": {
            "outcome_parent_pseudo_passes": OUTCOME_PARENT_PSEUDO_PASSES,
            "yard_parent_pseudo_passes": YARD_PARENT_PSEUDO_PASSES,
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
