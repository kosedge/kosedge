#!/usr/bin/env python3
"""Fixed-schedule RZ terminal replay: rush vs generic-pass arms (instrument only).

Freezes parent `a3a8e5b2f` RZ snap schedules. Counterfactuals re-draw outcomes
only on `rz_rush_transition` or `generic_pass_rz` snaps from committed train
priors. No pass-transition simulator bundle is enabled.
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


def _sample_yards(prior: Mapping[str, Any], outcome: str, rng: random.Random) -> int:
    weights = prior.get("yard_value_weights")
    if not isinstance(weights, Mapping):
        return 0
    bucket = weights.get(outcome)
    if not isinstance(bucket, Mapping):
        return 0
    return int(round(float(_sample_weighted(bucket, rng))))


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


@dataclass
class WalkResult:
    reached_fourth: bool = False
    terminal: str = "open"
    td_before_fourth: bool = False


def _walk_drive(
    drive: Any,
    *,
    mode: str,
    rush_priors: Mapping[str, Any],
    pass_priors: Mapping[str, Any],
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
        redraw_rush = mode in {"rush", "both"} and snap.route == "rz_rush_transition"
        redraw_pass = mode in {"pass", "both"} and snap.route == "generic_pass_rz"

        if redraw_rush:
            prior = _prior_bucket(rush_priors, _state_key(yardline, down, distance))
            outcome = _sample_weighted(prior["outcome_probabilities"], rng)
            yards = _sample_yards(prior, outcome, rng)
        elif redraw_pass:
            prior = _prior_bucket(pass_priors, _state_key(yardline, down, distance))
            outcome = _sample_weighted(prior["outcome_probabilities"], rng)
            yards = 0 if outcome == "incomplete" else _sample_yards(prior, outcome, rng)
        else:
            outcome, yards = _parent_outcome(snap)

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


def _parent_snap_td_rates(drives: list[Any]) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    tds: Counter[str] = Counter()
    for drive in drives:
        for snap in drive.snaps:
            if snap.route not in {"rz_rush_transition", "generic_pass_rz"}:
                continue
            counts[snap.route] += 1
            if snap.touchdown or (snap.incomplete is False and snap.yards >= 100 - snap.pre_yardline):
                if snap.touchdown:
                    tds[snap.route] += 1
    return {
        route: {
            "snaps": counts[route],
            "touchdowns": tds[route],
            "td_rate": tds[route] / counts[route] if counts[route] else 0.0,
        }
        for route in ("rz_rush_transition", "generic_pass_rz")
    }


def _summarize_walks(walks: list[WalkResult], entries: int) -> dict[str, Any]:
    reached = sum(1 for walk in walks if walk.reached_fourth)
    td_before = sum(1 for walk in walks if walk.td_before_fourth)
    return {
        "rz_entries": entries,
        "reached_fourth_rate": reached / entries if entries else 0.0,
        "td_before_fourth_rate": td_before / entries if entries else 0.0,
        "terminal_mix": dict(Counter(walk.terminal for walk in walks)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--rush-priors", type=Path, required=True)
    parser.add_argument("--pass-priors", type=Path, required=True)
    parser.add_argument("--games-per-case", type=int, default=128)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-sha", type=str, required=True)
    args = parser.parse_args()

    replay = _load_fourth_arrival_module()
    config_payload = _load_json(args.config.resolve())
    inputs_payload = _load_json(args.inputs.resolve())
    config = ClockPlayConfig.from_mapping(replay._engine_config(config_payload))
    rush_priors = _load_json(args.rush_priors.resolve())["priors"]
    pass_priors = _load_json(args.pass_priors.resolve())["priors"]

    parent_drives: list[Any] = []
    walks: dict[str, list[WalkResult]] = {
        "parent_schedule": [],
        "rush_train_redraw": [],
        "pass_train_redraw": [],
    }
    rng = random.Random(443917)

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
            for mode in walks:
                cf_mode = "parent" if mode == "parent_schedule" else mode.split("_")[0]
                for drive in drives:
                    walks[mode].append(
                        _walk_drive(
                            drive,
                            mode=cf_mode,
                            rush_priors=rush_priors,
                            pass_priors=pass_priors,
                            rng=rng,
                        )
                    )

    entries = len(parent_drives)
    payload = {
        "artifact_id": str(config_payload.get("artifact_id")),
        "contract": {
            "frozen": [
                "parent RZ snap schedule and pre-snap states",
                "pre-entry continuations",
                "fourth-down policy after synthetic fourth arrival",
            ],
            "arms": {
                "parent_schedule": "parent snap outcomes on frozen schedule",
                "rush_train_redraw": "train rush-transition priors on rz_rush_transition snaps only",
                "pass_train_redraw": "train pass outcome priors on generic_pass_rz snaps only (no sim bundle)",
            },
        },
        "parent_snap_td_rates": _parent_snap_td_rates(parent_drives),
        "parent_event_parser": replay._summarize_drives(parent_drives),
        "walk_arms": {
            name: _summarize_walks(results, entries) for name, results in walks.items()
        },
        "source_sha": args.source_sha,
        "train_prior_defaults": {
            "rush_touchdown_rate": rush_priors["default"]["outcome_probabilities"][
                "touchdown"
            ],
            "pass_touchdown_rate": pass_priors["default"]["outcome_probabilities"][
                "touchdown"
            ],
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
