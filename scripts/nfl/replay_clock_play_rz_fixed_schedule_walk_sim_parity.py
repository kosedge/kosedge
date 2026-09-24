#!/usr/bin/env python3
"""Walk vs full-sim parity on frozen RZ schedules (instrument only).

Diagnoses pre-fourth reach-fourth gap between simplified walk and parent event
parser. Active candidate `a3a8e5b2f`; no simulator changes.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections import Counter
from dataclasses import dataclass
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


@dataclass
class WalkTrace:
    reached_fourth: bool = False
    terminal: str = "open"
    td_before_fourth: bool = False
    state_mismatches: int = 0
    last_route: str | None = None
    post_yardline: int = 0
    post_down: int = 0
    post_distance: int = 0


def _walk_with_trace(drive: Any, fg_mod: Any) -> WalkTrace:
    trace = WalkTrace()
    if not drive.snaps:
        trace.terminal = "empty"
        return trace

    post_yardline = drive.snaps[0].pre_yardline
    post_down = drive.snaps[0].pre_down
    post_distance = drive.snaps[0].pre_distance

    for index, snap in enumerate(drive.snaps):
        trace.last_route = snap.route
        if index > 0:
            if (
                snap.pre_yardline != post_yardline
                or snap.pre_down != post_down
                or snap.pre_distance != post_distance
            ):
                trace.state_mismatches += 1

        yardline, down, distance = snap.pre_yardline, snap.pre_down, snap.pre_distance
        outcome, yards = fg_mod._parent_outcome(snap)
        if outcome == "short":
            outcome = "short_gain"
        yardline, down, distance, terminal = fg_mod._advance(
            yardline, down, distance, outcome, yards
        )
        post_yardline, post_down, post_distance = yardline, down, distance
        trace.post_yardline, trace.post_down, trace.post_distance = (
            post_yardline,
            post_down,
            post_distance,
        )

        if terminal == "touchdown":
            trace.td_before_fourth = True
            trace.terminal = "touchdown"
            return trace
        if terminal == "turnover":
            trace.terminal = "turnover"
            return trace
        if down >= 4:
            trace.reached_fourth = True
            trace.terminal = "fourth_down"
            return trace

    trace.terminal = "drive_end"
    return trace


def _mismatch_bucket(sim_fourth: bool, walk_fourth: bool) -> str:
    if sim_fourth and walk_fourth:
        return "both_reach_fourth"
    if sim_fourth and not walk_fourth:
        return "sim_only_reach_fourth"
    if not sim_fourth and walk_fourth:
        return "walk_only_reach_fourth"
    return "neither_reach_fourth"


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
    buckets: Counter[str] = Counter()
    sim_only_by_terminal: Counter[str] = Counter()
    sim_only_by_last_route: Counter[str] = Counter()
    sim_only_walk_terminal: Counter[str] = Counter()
    walk_only_by_route: Counter[str] = Counter()
    mismatch_at_route: Counter[str] = Counter()
    snap_counts_sim_only: list[int] = []
    state_mismatches_total = 0
    sim_reach = 0
    walk_reach = 0
    oracle_schedule_reach = 0

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

    for drive in parent_drives:
        walk = _walk_with_trace(drive, fg_mod)
        sim_fourth = bool(drive.reached_fourth)
        if sim_fourth:
            sim_reach += 1
        if walk.reached_fourth:
            walk_reach += 1
        if sim_fourth or walk.reached_fourth:
            oracle_schedule_reach += 1 if sim_fourth else 0

        bucket = _mismatch_bucket(sim_fourth, walk.reached_fourth)
        buckets[bucket] += 1
        state_mismatches_total += walk.state_mismatches

        if bucket == "sim_only_reach_fourth":
            sim_only_by_terminal[str(drive.terminal)] += 1
            sim_only_by_last_route[
                drive.terminating_route or walk.last_route or "unknown"
            ] += 1
            sim_only_walk_terminal[walk.terminal] += 1
            snap_counts_sim_only.append(len(drive.snaps))
            if walk.state_mismatches > 0 and walk.last_route:
                mismatch_at_route[walk.last_route] += 1
        if bucket == "walk_only_reach_fourth" and walk.last_route:
            walk_only_by_route[walk.last_route] += 1

    entries = len(parent_drives)
    sim_only = buckets["sim_only_reach_fourth"]
    gap = sim_reach - walk_reach
    sim_only_drive_end = sim_only_walk_terminal.get("drive_end", 0)
    extended_walk_reach = walk_reach + sim_only_drive_end
    payload = {
        "artifact_id": str(config_payload.get("artifact_id")),
        "parent_event_parser": replay._summarize_drives(parent_drives),
        "parity": {
            "rz_entries": entries,
            "sim_reach_fourth_rate": sim_reach / entries if entries else 0.0,
            "walk_reach_fourth_rate": walk_reach / entries if entries else 0.0,
            "reach_fourth_gap_pp": 100.0 * (gap / entries) if entries else 0.0,
            "mismatch_buckets": dict(buckets),
            "sim_only_reach_fourth": {
                "count": sim_only,
                "share_of_gap": sim_only / gap if gap > 0 else 0.0,
                "by_sim_terminal": dict(sim_only_by_terminal),
                "by_terminating_or_last_route": dict(sim_only_by_last_route),
                "walk_terminal_when_sim_reached_fourth": dict(sim_only_walk_terminal),
                "mean_snaps_on_drive": (
                    sum(snap_counts_sim_only) / len(snap_counts_sim_only)
                    if snap_counts_sim_only
                    else 0.0
                ),
                "drives_with_state_mismatch_before_last_snap": dict(mismatch_at_route),
            },
            "walk_only_reach_fourth": {
                "count": buckets["walk_only_reach_fourth"],
                "by_last_route": dict(walk_only_by_route),
            },
            "walk_state_mismatches_vs_next_snap_pre": state_mismatches_total,
            "extended_walk_if_sim_fourth_on_drive_end": {
                "description": (
                    "Count sim_only drives whose walk ended drive_end; crediting "
                    "parent reached_fourth closes most of the reach-fourth gap "
                    "without changing sim policy."
                ),
                "additional_reach_fourth": sim_only_drive_end,
                "reach_fourth_rate": (
                    extended_walk_reach / entries if entries else 0.0
                ),
            },
        },
        "pre_fourth_terminations": dict(
            Counter(
                drive.terminating_route or "none"
                for drive in parent_drives
                if not drive.reached_fourth
            )
        ),
        "source_sha": args.source_sha,
        "verdict_hint": (
            "sim_only_reach_fourth drives end with walk terminal drive_end because "
            "fourth arrival is recorded on fourth_down_decision events without a "
            "matching down>=4 transition on the snap walk, and/or walk advance "
            "state diverges from the next snap pre-state."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
