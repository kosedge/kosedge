#!/usr/bin/env python3
"""Event-chain counterfactuals on frozen RZ schedules (instrument only).

Re-runs generic-pass and fourth-decision arms with post-state re-derived only
on edited snaps. Parent path uses recorded event post-states.
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
    rz_rush_state_key,
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


def _sample_stall_outcome(
    bucket: Any, rng: random.Random, *, allow_incomplete: bool = True
) -> tuple[str, int]:
    if bucket is None or bucket.n == 0:
        return ("incomplete", 0) if allow_incomplete else ("short_gain", 1)
    draw = rng.random() * bucket.n
    cumulative = 0.0
    outcome = "short_gain"
    options = (
        ([("incomplete", bucket.incomplete)] if allow_incomplete else [])
        + [
            ("touchdown", bucket.touchdown),
            ("first_down", bucket.first_down),
            ("short_gain", bucket.short),
        ]
    )
    for name, count in options:
        cumulative += count
        if draw <= cumulative:
            outcome = name
            break
    yards = 0 if outcome == "incomplete" else max(1, min(6, 6))
    if outcome == "touchdown":
        yards = max(6, 6)
    elif outcome == "first_down":
        yards = 6
    elif outcome == "short_gain":
        yards = 3
    return outcome, yards


def _generic_pass_draw(
    snap: Any,
    mode: str,
    stalls: Mapping[str, Any],
    incompletion_priors: Mapping[str, Any],
    fg_mod: Any,
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
    return fg_mod._parent_outcome(snap)


def _finish_fourth(
    yardline: int,
    distance: int,
    *,
    fourth_mode: str,
    drive: Any,
    decision_priors: Mapping[str, Any],
    fg_mod: Any,
    replay_mod: Any,
    rng: random.Random,
) -> Any:
    if fourth_mode == "parent":
        if drive.reached_fourth:
            terminal = str(drive.terminal or "fourth_down")
            return replay_mod.EventChainWalkResult(
                reached_fourth=True,
                fg_exit=bool(drive.fourth_fg) or terminal == "field_goal",
                terminal=terminal,
            )
        return replay_mod.EventChainWalkResult(
            reached_fourth=True, terminal="fourth_down"
        )

    decision = fg_mod._resolve_fourth_decision(
        yardline,
        distance,
        mode="train",
        parent_drive=drive,
        decision_priors=decision_priors,
        rng=rng,
    )
    if decision == "field_goal":
        return replay_mod.EventChainWalkResult(
            reached_fourth=True, fg_exit=True, terminal="field_goal"
        )
    if decision == "go":
        return replay_mod.EventChainWalkResult(
            reached_fourth=True, terminal="fourth_go"
        )
    return replay_mod.EventChainWalkResult(reached_fourth=True, terminal="fourth_punt")


def walk_event_chain_arm(
    drive: Any,
    replay_mod: Any,
    fg_mod: Any,
    *,
    generic_pass_mode: str,
    fourth_mode: str,
    stalls: Mapping[str, Any],
    incompletion_priors: Mapping[str, Any],
    decision_priors: Mapping[str, Any],
    rng: random.Random,
) -> Any:
    if generic_pass_mode == "parent" and fourth_mode == "parent":
        return replay_mod.walk_parent_event_chain(drive)

    if generic_pass_mode == "parent" and fourth_mode == "train":
        base = replay_mod.walk_parent_event_chain(drive)
        if base.reached_fourth and drive.snaps:
            snap = drive.snaps[-1]
            yardline = snap.post_yardline or snap.pre_yardline
            distance = snap.post_distance or snap.pre_distance
            fourth = _finish_fourth(
                yardline,
                distance,
                fourth_mode="train",
                drive=drive,
                decision_priors=decision_priors,
                fg_mod=fg_mod,
                replay_mod=replay_mod,
                rng=rng,
            )
            base.fg_exit = fourth.fg_exit
            base.terminal = fourth.terminal
        return base

    result = replay_mod.EventChainWalkResult()
    if not drive.snaps:
        result.terminal = "empty"
        return result

    dirty = False
    post_y: int | None = None
    post_d: int | None = None
    post_dist: int | None = None
    edited = False

    for snap in drive.snaps:
        if dirty and post_y is not None:
            pre_y, pre_d, pre_dist = post_y, post_d, post_dist
        else:
            pre_y, pre_d, pre_dist = (
                snap.pre_yardline,
                snap.pre_down,
                snap.pre_distance,
            )

        redraw = generic_pass_mode != "parent" and snap.route == "generic_pass_rz"
        if redraw:
            edited = True
            outcome, yards = _generic_pass_draw(
                snap,
                generic_pass_mode,
                stalls,
                incompletion_priors,
                fg_mod,
                rng,
            )
        elif not dirty:
            if snap.touchdown:
                result.reached_fourth = bool(drive.reached_fourth)
                result.td_before_fourth = not drive.reached_fourth
                result.terminal = "touchdown"
                return result
            if snap.post_down is None:
                continue
            post_y, post_d, post_dist = (
                snap.post_yardline,
                snap.post_down,
                snap.post_distance,
            )
            continue
        else:
            outcome, yards = fg_mod._parent_outcome(snap)
            if outcome == "short":
                outcome = "short_gain"

        if outcome == "short":
            outcome = "short_gain"
        post_y, post_d, post_dist, terminal = fg_mod._advance(
            pre_y, pre_d, pre_dist, outcome, yards
        )
        dirty = True

        if terminal == "touchdown":
            result.td_before_fourth = True
            result.terminal = "touchdown"
            return result
        if terminal == "turnover":
            result.terminal = "turnover"
            return result
        if post_d is not None and post_d >= 4:
            fourth = _finish_fourth(
                post_y or pre_y,
                post_dist or pre_dist,
                fourth_mode=fourth_mode,
                drive=drive,
                decision_priors=decision_priors,
                fg_mod=fg_mod,
                replay_mod=replay_mod,
                rng=rng,
            )
            fourth.td_before_fourth = result.td_before_fourth
            return fourth

    if not edited and fourth_mode == "parent":
        return replay_mod.walk_parent_event_chain(drive)

    if fourth_mode == "parent" and drive.reached_fourth:
        result.reached_fourth = True
        result.terminal = str(drive.terminal or "fourth_down")
        result.fg_exit = bool(drive.fourth_fg) or result.terminal == "field_goal"
        return result

    result.terminal = str(drive.terminal or "drive_end")
    return result


def _summarize(results: list[Any], entries: int) -> dict[str, Any]:
    reached = sum(1 for item in results if item.reached_fourth)
    fg_exit = sum(1 for item in results if item.fg_exit)
    td_before = sum(1 for item in results if item.td_before_fourth)
    return {
        "rz_entries": entries,
        "reached_fourth_rate": reached / entries if entries else 0.0,
        "fg_exit_rate": fg_exit / entries if entries else 0.0,
        "td_before_fourth_rate": td_before / entries if entries else 0.0,
        "terminal_mix": dict(Counter(item.terminal for item in results)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--historical-pbp", type=Path, required=True)
    parser.add_argument("--incompletion-priors", type=Path, required=True)
    parser.add_argument("--fourth-decision-priors", type=Path, required=True)
    parser.add_argument("--games-per-case", type=int, default=128)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-sha", type=str, required=True)
    args = parser.parse_args()

    replay = _load_module(FOURTH_ARRIVAL, "rz_fourth_arrival")
    fg_mod = _load_module(FOURTH_FG, "rz_fourth_fg")
    config_payload = _load_json(args.config.resolve())
    inputs_payload = _load_json(args.inputs.resolve())
    config = ClockPlayConfig.from_mapping(replay._engine_config(config_payload))
    stalls = replay._train_generic_pass_stalls(args.historical_pbp.resolve())
    incompletion_priors = _load_json(args.incompletion_priors.resolve())["priors"]
    decision_priors = _load_json(args.fourth_decision_priors.resolve())["priors"]

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
    arms = {
        "parent_event_chain": ("parent", "parent"),
        "generic_pass_pbp_stall_chain": ("pbp_stall", "train"),
        "generic_pass_train_path_chain": ("train_pass_path", "train"),
        "parent_snaps_train_fourth_decision": ("parent", "train"),
    }
    rng = random.Random(640221)
    walk_results: dict[str, list[Any]] = {name: [] for name in arms}

    for drive in parent_drives:
        for name, (pass_mode, fourth_mode) in arms.items():
            walk_results[name].append(
                walk_event_chain_arm(
                    drive,
                    replay,
                    fg_mod,
                    generic_pass_mode=pass_mode,
                    fourth_mode=fourth_mode,
                    stalls=stalls,
                    incompletion_priors=incompletion_priors,
                    decision_priors=decision_priors,
                    rng=rng,
                )
            )

    payload = {
        "artifact_id": str(config_payload.get("artifact_id")),
        "contract": {
            "parent_path": "Recorded post-state on unedited snaps; parser fourth flags.",
            "edited_snaps": "Generic-pass counterfactuals re-derive post-state via _advance.",
            "synthetic_fourth": "Train RZ fourth-decision priors when walk hits down>=4 on edited path.",
            "fourth_only_arm": "parent_snaps_train_fourth_decision keeps snaps, train fourth at synthetic/parent fourth.",
        },
        "parent_event_parser": replay._summarize_drives(parent_drives),
        "arms": {
            name: _summarize(walk_results[name], entries) for name in arms
        },
        "source_sha": args.source_sha,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
