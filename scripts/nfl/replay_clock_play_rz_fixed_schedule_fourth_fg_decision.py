#!/usr/bin/env python3
"""Frozen-schedule RZ walk with fourth-down FG/go decision (instrument only).

Freezes parent `a3a8e5b2f` snap schedules. After synthetic fourth arrival,
applies train RZ fourth-decision priors or parent-recorded decisions so
field-goal exits are included in the walk (closing the prior fourth_down-only
terminal gap).
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
    rz_fourth_decision_state_key,
    rz_goal_to_go,
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


def _sample_weighted(weights: Mapping[str, Any], rng: random.Random) -> str:
    values = {str(k): max(0.0, float(v)) for k, v in weights.items()}
    total = sum(values.values())
    if total <= 0:
        raise ValueError("empty weight map")
    draw = rng.random() * total
    cumulative = 0.0
    for name in sorted(values):
        cumulative += values[name]
        if draw <= cumulative:
            return name
    return sorted(values)[-1]


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
    if snap.yards <= 2:
        return "one_two", snap.yards
    return "short_gain", snap.yards


def _fourth_decision_key(yardline: int, distance: int) -> str:
    return rz_fourth_decision_state_key(
        yardline=yardline,
        distance=distance,
        goal_to_go=rz_goal_to_go(yardline, distance),
    )


def _parent_recorded_decision(drive: Any) -> str | None:
    if not drive.reached_fourth:
        return None
    terminal = str(drive.terminal or "")
    if terminal == "field_goal":
        return "field_goal"
    if terminal == "fourth_go":
        return "go"
    if terminal == "fourth_punt":
        return "punt"
    return None


def _resolve_fourth_decision(
    yardline: int,
    distance: int,
    *,
    mode: str,
    parent_drive: Any,
    decision_priors: Mapping[str, Any],
    rng: random.Random,
) -> str:
    if mode == "parent_recorded":
        recorded = _parent_recorded_decision(parent_drive)
        if recorded is not None:
            return recorded
    key = _fourth_decision_key(yardline, distance)
    prior = _prior_bucket(decision_priors, key)
    return _sample_weighted(prior["action_probabilities"], rng)


@dataclass
class WalkResult:
    reached_fourth: bool = False
    fg_exit: bool = False
    td_before_fourth: bool = False
    terminal: str = "open"


def _walk_drive(
    drive: Any,
    *,
    fourth_mode: str,
    decision_priors: Mapping[str, Any],
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
            if fourth_mode == "legacy_stop":
                result.terminal = "fourth_down"
                return result
            decision = _resolve_fourth_decision(
                yardline,
                distance,
                mode=fourth_mode,
                parent_drive=drive,
                decision_priors=decision_priors,
                rng=rng,
            )
            if decision == "field_goal":
                result.fg_exit = True
                result.terminal = "field_goal"
            elif decision == "go":
                result.terminal = "fourth_go"
            elif decision == "punt":
                result.terminal = "fourth_punt"
            else:
                result.terminal = "fourth_other"
            return result

    result.terminal = "drive_end"
    return result


def _summarize_walks(walks: list[WalkResult], entries: int) -> dict[str, Any]:
    reached = sum(1 for walk in walks if walk.reached_fourth)
    fg_exit = sum(1 for walk in walks if walk.fg_exit)
    td_before = sum(1 for walk in walks if walk.td_before_fourth)
    return {
        "rz_entries": entries,
        "reached_fourth_rate": reached / entries if entries else 0.0,
        "fg_exit_rate": fg_exit / entries if entries else 0.0,
        "td_before_fourth_rate": td_before / entries if entries else 0.0,
        "terminal_mix": dict(Counter(walk.terminal for walk in walks)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--fourth-decision-priors", type=Path, required=True)
    parser.add_argument("--games-per-case", type=int, default=128)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-sha", type=str, required=True)
    args = parser.parse_args()

    replay = _load_fourth_arrival_module()
    config_payload = _load_json(args.config.resolve())
    inputs_payload = _load_json(args.inputs.resolve())
    config = ClockPlayConfig.from_mapping(replay._engine_config(config_payload))
    decision_root = _load_json(args.fourth_decision_priors.resolve())
    decision_priors = decision_root["priors"]

    parent_drives: list[Any] = []
    walks: dict[str, list[WalkResult]] = {
        "legacy_fourth_stop": [],
        "train_fourth_decision": [],
        "parent_recorded_decision": [],
    }
    rng = random.Random(882441)

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
            for arm, fourth_mode in (
                ("legacy_fourth_stop", "legacy_stop"),
                ("train_fourth_decision", "train"),
                ("parent_recorded_decision", "parent_recorded"),
            ):
                for drive in drives:
                    walks[arm].append(
                        _walk_drive(
                            drive,
                            fourth_mode=fourth_mode,
                            decision_priors=decision_priors,
                            rng=rng,
                        )
                    )

    entries = len(parent_drives)
    payload = {
        "artifact_id": str(config_payload.get("artifact_id")),
        "contract": {
            "frozen": [
                "parent RZ snap schedule and outcomes",
                "rush transition metadata",
                "pre-entry continuations",
            ],
            "fourth_policy": {
                "legacy_fourth_stop": "synthetic fourth ends as fourth_down only",
                "train_fourth_decision": (
                    "sample joint RZ fourth-decision priors at synthetic fourth"
                ),
                "parent_recorded_decision": (
                    "use parent sim fourth terminal when parent reached fourth; "
                    "else train sample"
                ),
            },
        },
        "parent_event_parser": replay._summarize_drives(parent_drives),
        "walk_arms": {
            name: _summarize_walks(results, entries) for name, results in walks.items()
        },
        "source_sha": args.source_sha,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
