#!/usr/bin/env python3
"""Frozen-schedule RZ fourth-arrival vs generic-pass path (instrument only).

Freezes parent `a3a8e5b2f` RZ snap schedules. Counterfactuals re-draw only
`generic_pass_rz` snaps using train PBP stall buckets and/or train incompletion
priors. No pass-transition simulator bundle.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import random
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.nfl_clock_play_simulator import (  # noqa: E402
    ClockPlayConfig,
    derive_replicate_seed,
    rz_goal_to_go,
    rz_rush_state_key,
    simulate_clock_play_game,
)

FOURTH_ARRIVAL = ROOT / "scripts/nfl/replay_clock_play_rz_fixed_schedule_fourth_arrival.py"


def _load_fourth_arrival_module():
    spec = importlib.util.spec_from_file_location("rz_fourth_arrival", FOURTH_ARRIVAL)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load fourth-arrival replay module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _prior_bucket(priors: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    buckets = priors.get("buckets")
    fallback = priors.get("default")
    if isinstance(buckets, Mapping) and isinstance(buckets.get(key), Mapping):
        return buckets[key]
    if isinstance(fallback, Mapping):
        return fallback
    raise KeyError(f"Missing prior bucket {key}")


def _state_key(yardline: int, down: int, distance: int) -> str:
    return rz_rush_state_key(
        yardline=yardline,
        down=down,
        distance=distance,
        goal_to_go=rz_goal_to_go(yardline, distance),
    )


def _advance(
    yardline: int, down: int, distance: int, outcome: str, yards: int
) -> tuple[int, int, int, str | None]:
    if outcome == "touchdown":
        return yardline, down, distance, "touchdown"
    if outcome == "turnover":
        return yardline, down, distance, "turnover"
    if outcome == "incomplete":
        return yardline, min(4, down + 1), distance, None
    if outcome == "first_down" or yards >= distance:
        new_yardline = min(99, yardline + max(yards, distance))
        return new_yardline, 1, min(10, 100 - new_yardline), None
    if outcome == "loss":
        yards = min(-1, yards)
    elif outcome == "zero":
        yards = 0
    new_yardline = min(99, max(1, yardline + yards))
    return new_yardline, min(4, down + 1), max(1, distance - max(0, yards)), None


def _parent_outcome(snap: Any) -> tuple[str, int]:
    sim_outcome = getattr(snap, "sim_outcome", None)
    if sim_outcome:
        if sim_outcome == "turnover":
            return "turnover", 0
        if sim_outcome == "touchdown":
            return "touchdown", max(snap.yards, 100 - snap.pre_yardline)
        if sim_outcome in {"first_down", "loss", "zero", "one_two", "short_gain"}:
            return sim_outcome, snap.yards
    if snap.incomplete:
        return "incomplete", 0
    if snap.touchdown:
        return "touchdown", max(snap.yards, 100 - snap.pre_yardline)
    if snap.yards >= snap.pre_distance:
        return "first_down", snap.yards
    if snap.yards < 0:
        return "loss", snap.yards
    return "short", snap.yards


def _sample_stall_outcome(
    bucket: Any, rng: random.Random, *, allow_incomplete: bool = True
) -> tuple[str, int]:
    if bucket is None or bucket.n == 0:
        return ("incomplete", 0) if allow_incomplete else ("short", 1)
    draw = rng.random() * bucket.n
    cumulative = 0.0
    options = (
        [("incomplete", bucket.incomplete)]
        if allow_incomplete
        else []
    ) + [
        ("touchdown", bucket.touchdown),
        ("first_down", bucket.first_down),
        ("short", bucket.short),
    ]
    outcome = "short"
    for name, count in options:
        cumulative += count
        if draw <= cumulative:
            outcome = name
            break
    yards = 0 if outcome == "incomplete" else max(1, min(6, 6))
    if outcome == "touchdown":
        yards = 6
    elif outcome == "first_down":
        yards = 6
    elif outcome == "short":
        yards = max(1, min(5, 3))
    return outcome, yards


def _generic_pass_counterfactual(
    snap: Any,
    mode: str,
    stalls: Mapping[str, Any],
    incompletion_priors: Mapping[str, Any],
    rng: random.Random,
) -> tuple[str, int]:
    key = _state_key(snap.pre_yardline, snap.pre_down, snap.pre_distance)
    stall = stalls.get(key)
    if mode == "pbp_stall":
        return _sample_stall_outcome(stall, rng, allow_incomplete=True)
    if mode == "train_pass_path":
        inc_prior = float(
            _prior_bucket(incompletion_priors, key).get("incomplete_probability", 0.35)
        )
        if rng.random() < inc_prior:
            return "incomplete", 0
        return _sample_stall_outcome(stall, rng, allow_incomplete=False)
    return _parent_outcome(snap)


@dataclass
class WalkResult:
    reached_fourth: bool = False
    terminal: str = "open"
    td_before_fourth: bool = False


def _walk_drive(
    drive: Any,
    *,
    mode: str,
    stalls: Mapping[str, Any],
    incompletion_priors: Mapping[str, Any],
    rng: random.Random,
) -> WalkResult:
    result = WalkResult()
    if not drive.snaps:
        return result
    yardline = drive.snaps[0].pre_yardline
    down = drive.snaps[0].pre_down
    distance = drive.snaps[0].pre_distance

    for snap in drive.snaps:
        yardline, down, distance = snap.pre_yardline, snap.pre_down, snap.pre_distance
        if snap.route == "generic_pass_rz" and mode != "parent":
            outcome, yards = _generic_pass_counterfactual(
                snap, mode, stalls, incompletion_priors, rng
            )
        else:
            outcome, yards = _parent_outcome(snap)

        if outcome == "short":
            outcome = "short_gain"
        yardline, down, distance, terminal = _advance(
            yardline, down, distance, outcome, yards
        )
        if terminal == "touchdown":
            result.td_before_fourth = True
            result.terminal = "touchdown"
            return result
        if terminal == "turnover":
            result.terminal = "turnover"
            return result
        if down >= 4:
            result.reached_fourth = True
            result.terminal = "fourth_down"
            return result

    result.terminal = "drive_end"
    return result


def _summarize_walks(walks: list[WalkResult], entries: int) -> dict[str, Any]:
    reached = sum(1 for walk in walks if walk.reached_fourth)
    td_before = sum(1 for walk in walks if walk.td_before_fourth)
    return {
        "rz_entries": entries,
        "reached_fourth_rate": reached / entries if entries else 0.0,
        "td_before_fourth_rate": td_before / entries if entries else 0.0,
        "terminal_mix": dict(Counter(walk.terminal for walk in walks)),
    }


def _generic_pass_snap_metrics(
    drives: list[Any],
    incompletion_priors: Mapping[str, Any],
    stalls: Mapping[str, Any],
) -> dict[str, Any]:
    snaps = 0
    incomplete = 0
    touchdowns = 0
    inc_prior_weighted = 0.0
    stall_td_weighted = 0.0
    for drive in drives:
        for snap in drive.snaps:
            if snap.route != "generic_pass_rz":
                continue
            snaps += 1
            if snap.incomplete:
                incomplete += 1
            if snap.touchdown:
                touchdowns += 1
            key = _state_key(snap.pre_yardline, snap.pre_down, snap.pre_distance)
            inc_prior_weighted += float(
                _prior_bucket(incompletion_priors, key).get("incomplete_probability", 0.0)
            )
            bucket = stalls.get(key)
            if bucket is not None and bucket.n > 0:
                stall_td_weighted += bucket.touchdown / bucket.n
    return {
        "snaps": snaps,
        "incomplete_rate": incomplete / snaps if snaps else 0.0,
        "touchdown_rate": touchdowns / snaps if snaps else 0.0,
        "mean_train_incomplete_probability": inc_prior_weighted / snaps if snaps else 0.0,
        "mean_train_stall_touchdown_rate": stall_td_weighted / snaps if snaps else 0.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--historical-pbp", type=Path, required=True)
    parser.add_argument("--incompletion-priors", type=Path, required=True)
    parser.add_argument("--games-per-case", type=int, default=128)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-sha", type=str, required=True)
    args = parser.parse_args()

    replay = _load_fourth_arrival_module()
    config_payload = _load_json(args.config.resolve())
    inputs_payload = _load_json(args.inputs.resolve())
    config = ClockPlayConfig.from_mapping(replay._engine_config(config_payload))
    stalls = replay._train_generic_pass_stalls(args.historical_pbp.resolve())
    incompletion_root = _load_json(args.incompletion_priors.resolve())
    incompletion_priors = incompletion_root["priors"]

    parent_drives: list[Any] = []
    walks: dict[str, list[WalkResult]] = {
        "parent_schedule": [],
        "generic_pass_pbp_stall": [],
        "generic_pass_train_path": [],
    }
    rng = random.Random(551903)

    for case in inputs_payload.get("cases") or []:
        game = replay._as_game(case)
        root_seed = int(config_payload["freeze_run"]["root_seeds"][case["case_id"]])
        for index in range(args.games_per_case):
            seed = derive_replicate_seed(root_seed, case["case_id"], index)
            result = simulate_clock_play_game(
                game, seed=seed, config=config, collect_events=True
            )
            drives = replay._parse_rz_drives(result.get("events") or [])
            parent_drives.extend(drives)
            for arm, mode in (
                ("parent_schedule", "parent"),
                ("generic_pass_pbp_stall", "pbp_stall"),
                ("generic_pass_train_path", "train_pass_path"),
            ):
                for drive in drives:
                    walks[arm].append(
                        _walk_drive(
                            drive,
                            mode=mode,
                            stalls=stalls,
                            incompletion_priors=incompletion_priors,
                            rng=rng,
                        )
                    )

    entries = len(parent_drives)
    payload = {
        "artifact_id": str(config_payload.get("artifact_id")),
        "contract": {
            "frozen": [
                "parent RZ snap schedule",
                "rush transition outcomes (authoritative event metadata)",
                "pre-entry continuations",
                "fourth-down policy not re-simulated on synthetic fourth",
            ],
            "counterfactuals": {
                "generic_pass_pbp_stall": (
                    "train PBP stall buckets on generic_pass_rz snaps only"
                ),
                "generic_pass_train_path": (
                    "train incompletion prior then PBP stall completions "
                    "(no pass-transition bundle)"
                ),
            },
        },
        "parent_event_parser": replay._summarize_drives(parent_drives),
        "generic_pass_parent_snaps": _generic_pass_snap_metrics(
            parent_drives, incompletion_priors, stalls
        ),
        "walk_arms": {
            name: _summarize_walks(results, entries) for name, results in walks.items()
        },
        "source_sha": args.source_sha,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
