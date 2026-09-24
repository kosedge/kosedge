#!/usr/bin/env python3
"""Train-only incomplete-pass rate for non-handoff red-zone generic passes."""

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
    rz_goal_to_go,
    rz_rush_state_key,
)

TRAIN_SEASONS = frozenset(range(2013, 2024))
PARENT_PSEUDO_PASSES = 40.0


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


@dataclass
class Crossing:
    pre_entry_yardline: int


@dataclass
class Samples:
    n: int = 0
    incomplete: int = 0

    def add(self, incomplete: bool) -> None:
        self.n += 1
        if incomplete:
            self.incomplete += 1

    def rate(self) -> float:
        return self.incomplete / self.n if self.n else 0.0


def _parent_key(full_key: str) -> str:
    field, down, _distance, goal = full_key.split("|")
    return "|".join((field, down, goal))


def _estimate(child: Samples, parent: Samples, global_samples: Samples, bucket: str) -> dict[str, Any]:
    global_rate = global_samples.rate()
    parent_rate = (
        parent.incomplete + PARENT_PSEUDO_PASSES * global_rate
    ) / (parent.n + PARENT_PSEUDO_PASSES)
    rate = (
        child.incomplete + PARENT_PSEUDO_PASSES * parent_rate
    ) / (child.n + PARENT_PSEUDO_PASSES)
    return {
        "bucket": bucket,
        "incomplete_probability": rate,
        "sample": {
            "passes": child.n,
            "incomplete": child.incomplete,
            "incomplete_probability": child.rate(),
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
    active_crossings: dict[tuple[str, int, str], Crossing | None] = {}
    drive_seen_rz: dict[tuple[str, int, str], bool] = {}
    drive_started_inside: dict[tuple[str, int, str], bool] = {}
    excluded_pre_entry = 0
    passes = 0
    rows = 0

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
            rows += 1
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
            route = _route(payload)
            if (
                route == "pass"
                and yardline is not None
                and 80 <= yardline <= 99
            ):
                first_rz = not drive_seen_rz[drive_key]
                owned = (
                    first_rz
                    and active_crossings[drive_key] is not None
                    and not drive_started_inside[drive_key]
                )
                if owned:
                    excluded_pre_entry += 1
                else:
                    down = max(1, int(_number(payload.get("down")) or 1))
                    distance = max(1, int(_number(payload.get("ydstogo")) or 10))
                    key = rz_rush_state_key(
                        yardline=yardline,
                        down=down,
                        distance=distance,
                        goal_to_go=rz_goal_to_go(yardline, distance),
                    )
                    incomplete = _is_one(payload.get("incomplete_pass"))
                    global_samples.add(incomplete)
                    parents[_parent_key(key)].add(incomplete)
                    buckets[key].add(incomplete)
                    passes += 1

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
        raise SystemExit("No eligible non-handoff RZ generic pass samples found")

    default = _estimate(global_samples, global_samples, global_samples, "default")
    payload = {
        "accounting": {
            "eligible_non_handoff_rz_passes": passes,
            "excluded_pre_entry_owned_first_rz": excluded_pre_entry,
        },
        "artifact_id": "Clock-Play RZ Generic Pass Incompletion Priors",
        "historical_rows_examined": rows,
        "historical_source": args.pbp.as_posix(),
        "population": (
            "non-fourth red-zone pass routes excluding the joint pre-entry "
            "first-RZ continuation"
        ),
        "priors": {
            "default": default,
            "buckets": {
                key: _estimate(
                    sample, parents[_parent_key(key)], global_samples, key
                )
                for key, sample in sorted(buckets.items())
            },
        },
        "train_window": "2013-2023 regular season",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
