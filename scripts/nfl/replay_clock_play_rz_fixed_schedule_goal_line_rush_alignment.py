#!/usr/bin/env python3
"""Goal-line rush bucket alignment on frozen parent schedules (instrument only).

Diagnoses yard/outcome attribution for rush-transition bucket `5-3|1|3-5|gtg`.
Compares legacy scrimmage reconstruction vs authoritative transition events.
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
FOCUS_BUCKET = "5-3|1|3-5|gtg"


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


def _legacy_key(snap: Any) -> str:
    return rz_rush_state_key(
        yardline=snap.pre_yardline,
        down=snap.pre_down,
        distance=snap.pre_distance,
        goal_to_go=rz_goal_to_go(snap.pre_yardline, snap.pre_distance),
    )


def _classify_from_yards(snap: Any) -> str:
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
    parser.add_argument("--focus-bucket", type=str, default=FOCUS_BUCKET)
    parser.add_argument("--games-per-case", type=int, default=128)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-sha", type=str, required=True)
    args = parser.parse_args()

    replay = _load_module(FOURTH_ARRIVAL, "rz_fourth_arrival")
    config_payload = _load_json(args.config.resolve())
    inputs_payload = _load_json(args.inputs.resolve())
    config = ClockPlayConfig.from_mapping(replay._engine_config(config_payload))
    prior_bucket = _load_json(args.rush_priors.resolve())["priors"]["buckets"][
        args.focus_bucket
    ]
    prior_probs = prior_bucket["outcome_probabilities"]
    prior_yards = prior_bucket.get("yard_value_weights") or {}

    legacy_snaps: list[Any] = []
    authoritative_snaps: list[Any] = []
    yards_by_outcome: dict[str, Counter[int]] = defaultdict(Counter)

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
                    if _legacy_key(snap) == args.focus_bucket:
                        legacy_snaps.append(snap)
                    if snap.transition_bucket == args.focus_bucket:
                        authoritative_snaps.append(snap)
                        outcome = snap.sim_outcome or _classify_from_yards(snap)
                        yards_by_outcome[outcome][snap.yards] += 1

    def _td_rate(snaps: list[Any]) -> float:
        if not snaps:
            return 0.0
        td = sum(
            1
            for snap in snaps
            if (snap.sim_outcome or _classify_from_yards(snap)) == "touchdown"
        )
        return td / len(snaps)

    def _outcome_mix(snaps: list[Any]) -> dict[str, float]:
        counts: Counter[str] = Counter()
        for snap in snaps:
            counts[snap.sim_outcome or _classify_from_yards(snap)] += 1
        total = sum(counts.values()) or 1
        return {name: counts[name] / total for name in sorted(counts)}

    yard_compare = {}
    for outcome, yard_hist in yards_by_outcome.items():
        train = prior_yards.get(outcome)
        if not isinstance(train, Mapping):
            continue
        yard_compare[outcome] = {
            "sim_yard_counts": dict(sorted(yard_hist.items())),
            "train_yard_weights": {str(k): float(v) for k, v in train.items()},
        }

    payload = {
        "artifact_id": str(config_payload.get("artifact_id")),
        "focus_bucket": args.focus_bucket,
        "attribution": {
            "legacy_reconstructed_key": {
                "snaps": len(legacy_snaps),
                "touchdown_rate": _td_rate(legacy_snaps),
                "outcome_mix": _outcome_mix(legacy_snaps),
            },
            "authoritative_transition_bucket": {
                "snaps": len(authoritative_snaps),
                "touchdown_rate": _td_rate(authoritative_snaps),
                "outcome_mix": _outcome_mix(authoritative_snaps),
            },
            "phantom_td_inflation_pp": round(
                100.0
                * (
                    _td_rate(legacy_snaps) - _td_rate(authoritative_snaps)
                ),
                2,
            ),
        },
        "train_prior_outcome_probabilities": dict(prior_probs),
        "yard_alignment": yard_compare,
        "verdict": (
            "GOAL_LINE_BUCKET_ALIGNED"
            if abs(_td_rate(authoritative_snaps) - float(prior_probs["touchdown"]))
            < 0.03
            else "GOAL_LINE_BUCKET_MISALIGNED"
        ),
        "source_sha": args.source_sha,
        "notes": (
            "Legacy key uses post-play scrimmage reconstruction and mis-tags "
            "goal-to-go vs non-gtg on rush transitions; frozen replays must use "
            "transition_bucket and sim_outcome from red_zone_rush_transition events."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
