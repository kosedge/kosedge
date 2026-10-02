#!/usr/bin/env python3
"""Event-linked state chain walk on frozen RZ schedules (instrument only).

Uses post-play state recorded on each snap from parent events instead of the
`_advance` heuristic so reach-fourth parity matches the parent event parser.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.nfl_clock_play_simulator import (  # noqa: E402
    ClockPlayConfig,
    derive_replicate_seed,
    simulate_clock_play_game,
)

FOURTH_ARRIVAL = ROOT / "scripts/nfl/replay_clock_play_rz_fixed_schedule_fourth_arrival.py"
FOURTH_FG = ROOT / "scripts/nfl/replay_clock_play_rz_fixed_schedule_fourth_fg_decision.py"


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


def _heuristic_reach_fourth(drive: Any, fg_mod: Any) -> bool:
    trace = fg_mod._walk_drive(
        drive,
        fourth_mode="legacy_stop",
        decision_priors={},
        rng=__import__("random").Random(0),
    )
    return trace.reached_fourth


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--games-per-case", type=int, default=128)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-sha", type=str, required=True)
    args = parser.parse_args()

    replay = _load_module(FOURTH_ARRIVAL, "rz_fourth_arrival")
    fg_mod = _load_module(FOURTH_FG, "rz_fourth_fg")
    config_payload = _load_json(args.config.resolve())
    inputs_payload = _load_json(args.inputs.resolve())
    config = ClockPlayConfig.from_mapping(replay._engine_config(config_payload))

    parent_drives: list[Any] = []
    for case in inputs_payload.get("cases") or []:
        game = replay._as_game(case)
        root_seed = int(config_payload["freeze_run"]["root_seeds"][case["case_id"]])
        for index in range(args.games_per_case):
            seed = derive_replicate_seed(root_seed, case["case_id"], index)
            result = simulate_clock_play_game(
                game, seed=seed, config=config, collect_events=True
            )
            parent_drives.extend(replay._parse_rz_drives(result.get("events") or []))

    entries = len(parent_drives)
    sim_reach = 0
    heuristic_reach = 0
    chain_reach = 0
    chain_fg_exit = 0
    buckets: Counter[str] = Counter()
    snaps_with_post = 0
    snaps_total = 0
    chain_mismatches = 0

    for drive in parent_drives:
        sim_fourth = bool(drive.reached_fourth)
        if sim_fourth:
            sim_reach += 1
        if _heuristic_reach_fourth(drive, fg_mod):
            heuristic_reach += 1
        chain = replay.walk_parent_event_chain(drive)
        if chain.reached_fourth:
            chain_reach += 1
        if chain.terminal == "field_goal" or drive.fourth_fg:
            chain_fg_exit += 1
        for snap in drive.snaps:
            snaps_total += 1
            if snap.post_down is not None:
                snaps_with_post += 1
        if sim_fourth and not chain.reached_fourth:
            buckets["sim_only"] += 1
        elif not sim_fourth and chain.reached_fourth:
            buckets["chain_only"] += 1
        elif sim_fourth and chain.reached_fourth:
            buckets["both"] += 1
        else:
            buckets["neither"] += 1
        if drive.snaps:
            for index in range(1, len(drive.snaps)):
                prev_post = drive.snaps[index - 1]
                cur = drive.snaps[index]
                if (
                    prev_post.post_yardline is None
                    or cur.post_down is None
                ):
                    continue
                if (
                    cur.pre_yardline != prev_post.post_yardline
                    or cur.pre_down != prev_post.post_down
                    or cur.pre_distance != prev_post.post_distance
                ):
                    chain_mismatches += 1

    payload = {
        "artifact_id": str(config_payload.get("artifact_id")),
        "contract": {
            "state_chain": (
                "Each snap carries post_yardline/post_down/post_distance from "
                "parent events; fourth arrival after snaps uses drive.reached_fourth "
                "when fourth_down_decision was not preceded by post_down>=4 on snaps."
            ),
            "counterfactual_ready": (
                "Future arms should replace snap outcomes then re-derive post-state "
                "only on edited snaps; frozen parent post-state used elsewhere."
            ),
        },
        "parent_event_parser": replay._summarize_drives(parent_drives),
        "reach_fourth_rates": {
            "sim_event_parser": sim_reach / entries if entries else 0.0,
            "heuristic_advance_walk": heuristic_reach / entries if entries else 0.0,
            "event_chain_walk": chain_reach / entries if entries else 0.0,
        },
        "fg_exit_rate_event_chain": chain_fg_exit / entries if entries else 0.0,
        "sim_vs_event_chain_buckets": dict(buckets),
        "snap_post_state_coverage": {
            "snaps": snaps_total,
            "with_post_state": snaps_with_post,
        },
        "pre_to_post_chain_breaks": chain_mismatches,
        "source_sha": args.source_sha,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
