#!/usr/bin/env python3
"""Build train-only joint priors for 70-79 pass entries into the red zone.

The modeled handoff begins when the PBP route immediately preceding a drive's
first red-zone snap is a pass from the opponent 30-21. It owns that first
non-fourth red-zone pass or run. It intentionally does not estimate the
pre-entry pass crossing rate, later red-zone snaps, or fourth-down routes.
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

from src.services.nfl_clock_play_simulator import (  # noqa: E402
    pre_entry_pass_rz_state_key,
)

TRAIN_SEASONS = frozenset(range(2013, 2024))
ROUTES = ("pass", "run")
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
ROUTE_PARENT_PSEUDO_CONTINUATIONS = 40.0
OUTCOME_PARENT_PSEUDO_CONTINUATIONS = 30.0
YARD_PARENT_PSEUDO_CONTINUATIONS = 12.0


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


def _offensive_touchdown(payload: Mapping[str, Any]) -> bool:
    return _is_one(payload.get("touchdown")) and (
        payload.get("td_team") == payload.get("posteam")
    )


def _turnover(payload: Mapping[str, Any]) -> bool:
    return _is_one(payload.get("interception")) or _is_one(
        payload.get("fumble_lost")
    )


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
        marker = int(parts[1])
    except ValueError:
        return False
    return parts[0] != posteam and marker <= 20


def _outcome(payload: Mapping[str, Any], *, route: str, yards: int, distance: int) -> str:
    if _offensive_touchdown(payload):
        return "touchdown"
    if _turnover(payload):
        return "turnover"
    if route == "pass" and _is_one(payload.get("incomplete_pass")):
        return "incomplete"
    if _is_one(payload.get("first_down")) or yards >= distance:
        return "first_down"
    if yards < 0:
        return "loss"
    if yards == 0:
        return "zero"
    if yards <= 2:
        return "one_two"
    return "short_gain"


@dataclass(frozen=True)
class Crossing:
    pre_entry_yardline: int


@dataclass
class Samples:
    n: int = 0
    routes: Counter[str] = field(default_factory=Counter)
    outcomes: dict[str, Counter[str]] = field(
        default_factory=lambda: {route: Counter() for route in ROUTES}
    )
    yards: dict[str, dict[str, Counter[int]]] = field(
        default_factory=lambda: {
            route: {outcome: Counter() for outcome in OUTCOMES} for route in ROUTES
        }
    )

    def add(self, *, route: str, outcome: str, yards: int) -> None:
        self.n += 1
        self.routes[route] += 1
        self.outcomes[route][outcome] += 1
        self.yards[route][outcome][yards] += 1

    def raw(self) -> dict[str, Any]:
        return {
            "continuations": self.n,
            "routes": {route: self.routes[route] for route in ROUTES},
            "route_probabilities": {
                route: self.routes[route] / self.n if self.n else 0.0
                for route in ROUTES
            },
            "outcomes": {
                route: {
                    outcome: self.outcomes[route][outcome] for outcome in OUTCOMES
                }
                for route in ROUTES
            },
            "outcome_probabilities": {
                route: {
                    outcome: (
                        self.outcomes[route][outcome] / self.routes[route]
                        if self.routes[route]
                        else 0.0
                    )
                    for outcome in OUTCOMES
                }
                for route in ROUTES
            },
        }


def _parent_key(full_key: str) -> str:
    pre_entry, field, _down, _distance, _goal = full_key.split("|")
    return "|".join((pre_entry, field))


def _route_probabilities(
    child: Samples, parent: Samples, global_samples: Samples
) -> dict[str, float]:
    global_probabilities = {
        route: global_samples.routes[route] / global_samples.n for route in ROUTES
    }
    parent_probabilities = {
        route: (
            parent.routes[route]
            + ROUTE_PARENT_PSEUDO_CONTINUATIONS * global_probabilities[route]
        )
        / (parent.n + ROUTE_PARENT_PSEUDO_CONTINUATIONS)
        for route in ROUTES
    }
    values = {
        route: (
            child.routes[route]
            + ROUTE_PARENT_PSEUDO_CONTINUATIONS * parent_probabilities[route]
        )
        / (child.n + ROUTE_PARENT_PSEUDO_CONTINUATIONS)
        for route in ROUTES
    }
    total = sum(values.values())
    return {route: values[route] / total for route in ROUTES}


def _outcome_probabilities(
    child: Samples, parent: Samples, global_samples: Samples, *, route: str
) -> dict[str, float]:
    global_total = global_samples.routes[route]
    global_probabilities = {
        outcome: global_samples.outcomes[route][outcome] / global_total
        for outcome in OUTCOMES
    }
    parent_total = parent.routes[route]
    parent_probabilities = {
        outcome: (
            parent.outcomes[route][outcome]
            + OUTCOME_PARENT_PSEUDO_CONTINUATIONS * global_probabilities[outcome]
        )
        / (parent_total + OUTCOME_PARENT_PSEUDO_CONTINUATIONS)
        for outcome in OUTCOMES
    }
    child_total = child.routes[route]
    values = {
        outcome: (
            child.outcomes[route][outcome]
            + OUTCOME_PARENT_PSEUDO_CONTINUATIONS * parent_probabilities[outcome]
        )
        / (child_total + OUTCOME_PARENT_PSEUDO_CONTINUATIONS)
        for outcome in OUTCOMES
    }
    total = sum(values.values())
    return {outcome: values[outcome] / total for outcome in OUTCOMES}


def _yard_weights(
    child: Samples, parent: Samples, *, route: str, outcome: str
) -> dict[str, float]:
    values: Counter[int | float] = Counter()
    values.update(child.yards[route][outcome])
    parent_counts = parent.yards[route][outcome]
    parent_total = sum(parent_counts.values())
    if parent_total:
        for yards, count in parent_counts.items():
            values[yards] += YARD_PARENT_PSEUDO_CONTINUATIONS * count / parent_total
    if not values:
        values[0] = 1.0
    return {str(yards): float(count) for yards, count in sorted(values.items())}


def _estimate(
    *, child: Samples, parent: Samples, global_samples: Samples, bucket: str
) -> dict[str, Any]:
    return {
        "bucket": bucket,
        "sample": child.raw(),
        "route_probabilities": _route_probabilities(child, parent, global_samples),
        "outcome_probabilities": {
            route: _outcome_probabilities(
                child, parent, global_samples, route=route
            )
            for route in ROUTES
        },
        "yard_value_weights": {
            route: {
                outcome: _yard_weights(
                    child, parent, route=route, outcome=outcome
                )
                for outcome in OUTCOMES
            }
            for route in ROUTES
        },
    }


def _add_continuation(
    *,
    crossing: Crossing,
    payload: Mapping[str, Any],
    route: str,
    global_samples: Samples,
    parents: defaultdict[str, Samples],
    buckets: defaultdict[str, Samples],
) -> bool:
    yardline = _offensive_yardline(payload)
    down = _number(payload.get("down"))
    distance = _number(payload.get("ydstogo"))
    yards = _number(payload.get("yards_gained"))
    if (
        not route
        or yardline is None
        or down is None
        or distance is None
        or yards is None
        or not 80 <= yardline <= 99
        or int(down) >= 4
    ):
        return False
    key = pre_entry_pass_rz_state_key(
        pre_entry_yardline=crossing.pre_entry_yardline,
        yardline=yardline,
        down=int(down),
        distance=max(1, int(round(distance))),
        goal_to_go=_is_one(payload.get("goal_to_go")),
    )
    outcome = _outcome(
        payload,
        route=route,
        yards=int(round(yards)),
        distance=max(1, int(round(distance))),
    )
    value = int(round(yards))
    global_samples.add(route=route, outcome=outcome, yards=value)
    parents[_parent_key(key)].add(route=route, outcome=outcome, yards=value)
    buckets[key].add(route=route, outcome=outcome, yards=value)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build joint 70-79 pass-entry / first RZ-continuation priors"
    )
    parser.add_argument("--pbp", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    global_samples = Samples()
    parents: defaultdict[str, Samples] = defaultdict(Samples)
    buckets: defaultdict[str, Samples] = defaultdict(Samples)
    active_crossings: dict[tuple[str, int, str], Crossing | None] = {}
    drive_seen_rz: dict[tuple[str, int, str], bool] = {}
    drive_started_inside: dict[tuple[str, int, str], bool] = {}
    games: set[str] = set()
    historical_games_with_crossing: set[str] = set()
    rows_examined = 0
    accounting: Counter[str] = Counter()

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
            games.add(game_id)
            drive_key = (game_id, int(fixed_drive), posteam)
            drive_seen_rz.setdefault(drive_key, False)
            active_crossings.setdefault(drive_key, None)
            drive_started_inside.setdefault(
                drive_key, _drive_started_inside_red_zone(payload)
            )
            route = _route(payload)
            yardline = _offensive_yardline(payload)

            if (
                route is not None
                and yardline is not None
                and yardline >= 80
                and not drive_seen_rz[drive_key]
            ):
                drive_seen_rz[drive_key] = True
                crossing = active_crossings[drive_key]
                if crossing is not None and not drive_started_inside[drive_key]:
                    accounting["pass_crossings_to_rz"] += 1
                    historical_games_with_crossing.add(game_id)
                    down = _number(payload.get("down"))
                    if down is None or int(down) >= 4:
                        accounting["excluded_fourth_down_continuation"] += 1
                    elif route not in ROUTES:
                        accounting["excluded_non_pass_run_continuation"] += 1
                    elif _add_continuation(
                        crossing=crossing,
                        payload=payload,
                        route=route,
                        global_samples=global_samples,
                        parents=parents,
                        buckets=buckets,
                    ):
                        accounting["eligible_joint_continuations"] += 1
                    else:
                        accounting["excluded_non_red_zone_continuation"] += 1

            if route is not None:
                if route == "pass" and yardline is not None and 70 <= yardline <= 79:
                    accounting["eligible_pass_starts_70_79"] += 1
                    active_crossings[drive_key] = Crossing(
                        pre_entry_yardline=yardline
                    )
                else:
                    active_crossings[drive_key] = None
    if not global_samples.n:
        raise SystemExit("No eligible joint pre-entry pass/RZ continuations found")

    default = _estimate(
        child=global_samples,
        parent=global_samples,
        global_samples=global_samples,
        bucket="default",
    )
    payload = {
        "artifact_id": "Clock-Play Joint Pre-Entry Pass-to-RZ Continuation Priors",
        "train_window": "2013-2023 regular season",
        "historical_source": args.pbp.as_posix(),
        "historical_games": len(games),
        "historical_games_with_crossing": len(historical_games_with_crossing),
        "historical_rows_examined": rows_examined,
        "accounting": dict(sorted(accounting.items())),
        "population_definition": {
            "pre_entry": (
                "pass route at offensive yardline 70-79 immediately before "
                "the drive's first red-zone route; drive did not start inside "
                "the red zone"
            ),
            "continuation": (
                "first same-drive red-zone route; play_type in {pass,run}; "
                "offensive yardline 80-99; down<4"
            ),
            "exclusions": (
                "The process does not own fourth-down, non-red-zone, "
                "non-pass/run, terminal, or later-continuation states."
            ),
        },
        "shrinkage": {
            "route_parent_pseudo_continuations": ROUTE_PARENT_PSEUDO_CONTINUATIONS,
            "outcome_parent_pseudo_continuations": OUTCOME_PARENT_PSEUDO_CONTINUATIONS,
            "yard_parent_pseudo_continuations": YARD_PARENT_PSEUDO_CONTINUATIONS,
            "parent": "pre-entry start bucket × first-RZ field bucket",
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
