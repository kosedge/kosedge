#!/usr/bin/env python3
"""Snap-level calibration: parent RZ rush-transition outcomes vs train priors.

Instrument only. Freezes schedules from parent sim at `a3a8e5b2f` and compares
empirical outcome mix on `rz_rush_transition` snaps to the committed train
bucket probabilities (same keys the simulator uses).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections import Counter, defaultdict
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
def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
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
    raise KeyError(key)


def _state_key(yardline: int, down: int, distance: int) -> str:
    return rz_rush_state_key(
        yardline=yardline,
        down=down,
        distance=distance,
        goal_to_go=rz_goal_to_go(yardline, distance),
    )


def _classify_outcome(snap: Any) -> str:
    if snap.touchdown:
        return "touchdown"
    if snap.yards >= snap.pre_distance:
        return "first_down"
    if snap.yards < 0:
        return "loss"
    if snap.yards == 0:
        return "zero"
    if snap.yards <= 2:
        return "one_two"
    return "short_gain"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--rush-priors", type=Path, required=True)
    parser.add_argument("--games-per-case", type=int, default=128)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-sha", type=str, required=True)
    args = parser.parse_args()

    replay = _load_module(FOURTH_ARRIVAL, "rz_fourth_arrival")
    config_payload = _load_json(args.config.resolve())
    inputs_payload = _load_json(args.inputs.resolve())
    config = ClockPlayConfig.from_mapping(replay._engine_config(config_payload))
    rush_root = _load_json(args.rush_priors.resolve())
    rush_priors = rush_root["priors"]

    empirical: Counter[str] = Counter()
    expected_td_weighted = 0.0
    bucket_counts: Counter[str] = Counter()
    bucket_empirical: dict[str, Counter[str]] = defaultdict(Counter)
    snaps = 0

    for case in inputs_payload.get("cases") or []:
        game = replay._as_game(case)
        root_seed = int(config_payload["freeze_run"]["root_seeds"][case["case_id"]])
        for index in range(args.games_per_case):
            seed = derive_replicate_seed(root_seed, case["case_id"], index)
            result = simulate_clock_play_game(
                game, seed=seed, config=config, collect_events=True
            )
            drives = replay._parse_rz_drives(result.get("events") or [])
            for drive in drives:
                for snap in drive.snaps:
                    if snap.route != "rz_rush_transition":
                        continue
                    snaps += 1
                    key = _state_key(snap.pre_yardline, snap.pre_down, snap.pre_distance)
                    bucket_counts[key] += 1
                    outcome = _classify_outcome(snap)
                    empirical[outcome] += 1
                    bucket_empirical[key][outcome] += 1
                    prior = _prior_bucket(rush_priors, key)
                    probs = prior["outcome_probabilities"]
                    expected_td_weighted += float(probs.get("touchdown") or 0.0)

    empirical_td = empirical["touchdown"] / snaps if snaps else 0.0
    prior_td = expected_td_weighted / snaps if snaps else 0.0

    bucket_deltas = []
    for key, count in bucket_counts.most_common(50):
        prior = _prior_bucket(rush_priors, key)
        probs = prior["outcome_probabilities"]
        emp = bucket_empirical[key]
        emp_td = emp["touchdown"] / count if count else 0.0
        bucket_deltas.append(
            {
                "bucket": key,
                "snaps": count,
                "empirical_touchdown_rate": emp_td,
                "prior_touchdown_rate": float(probs.get("touchdown") or 0.0),
                "delta_td": emp_td - float(probs.get("touchdown") or 0.0),
            }
        )

    payload = {
        "artifact_id": str(config_payload.get("artifact_id")),
        "rz_rush_transition_snaps": snaps,
        "empirical_outcome_mix": dict(empirical),
        "empirical_touchdown_rate": empirical_td,
        "per_snap_prior_touchdown_rate_mean": prior_td,
        "touchdown_rate_delta_empirical_minus_prior": empirical_td - prior_td,
        "top_bucket_touchdown_deltas": bucket_deltas,
        "source_sha": args.source_sha,
        "notes": (
            "Simulator already draws rush transitions from these priors; deltas "
            "reflect sampling and yard-based outcome classification vs train labels."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
