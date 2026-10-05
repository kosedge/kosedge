#!/usr/bin/env python3
"""Train-only trace: RZ entry fourth-down arrival and FG take given arrival."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.nfl_clock_play_simulator import (  # noqa: E402
    ClockPlayConfig,
    ClockPlayGameInputs,
    ClockPlayTeamInput,
    derive_replicate_seed,
    rz_fourth_decision_state_key,
    rz_goal_to_go,
    simulate_clock_play_game,
)

TRAIN_SEASONS = frozenset(range(2013, 2024))


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _engine_config(config_payload: Mapping[str, Any]) -> dict[str, Any]:
    engine = dict(config_payload.get("engine_config") or {})
    for config_key, engine_key in (
        ("fourth_down_continuation_priors_path", "fourth_down_continuation_priors"),
        ("clock_flow_priors_path", "clock_flow_priors"),
        ("red_zone_rush_transition_priors_path", "red_zone_rush_transition_priors"),
        ("red_zone_pass_transition_priors_path", "red_zone_pass_transition_priors"),
        ("red_zone_fourth_decision_priors_path", "red_zone_fourth_decision_priors"),
        ("pre_entry_pass_rz_priors_path", "pre_entry_pass_rz_priors"),
        (
            "red_zone_generic_pass_incompletion_priors_path",
            "red_zone_generic_pass_incompletion_priors",
        ),
    ):
        raw_path = config_payload.get(config_key)
        if raw_path is None:
            continue
        priors_payload = _load_json((ROOT / str(raw_path)).resolve())
        priors = priors_payload.get("priors")
        if isinstance(priors, Mapping):
            engine[engine_key] = dict(priors)
    return engine


def _as_game(raw: Mapping[str, Any]) -> ClockPlayGameInputs:
    return ClockPlayGameInputs(
        game_id=str(raw["case_id"]),
        home_team=str(raw["home_team"]),
        away_team=str(raw["away_team"]),
        home=ClockPlayTeamInput(**dict(raw["home"])),
        away=ClockPlayTeamInput(**dict(raw["away"])),
        regular_season=True,
    )


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _historical_rz_metrics(pbp: Path) -> dict[str, Any]:
    entries = 0
    fourth_arrivals = 0
    fg_actions = 0
    decisions_by_key: Counter[str] = Counter()
    fg_by_key: Counter[str] = Counter()
    go_by_key: Counter[str] = Counter()
    drive_seen_rz: dict[tuple[str, int, str], bool] = defaultdict(bool)

    with pbp.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            payload = row.get("payload") if row.get("object_type") == "pbp_play" else None
            if not isinstance(payload, Mapping):
                continue
            season = _number(payload.get("season"))
            if season is None or int(season) not in TRAIN_SEASONS:
                continue
            if payload.get("season_type") != "REG":
                continue
            game_id = str(payload.get("game_id") or "")
            drive = _number(payload.get("fixed_drive"))
            posteam = str(payload.get("posteam") or "")
            if not game_id or drive is None or not posteam:
                continue
            drive_key = (game_id, int(drive), posteam)
            yardline_100 = _number(payload.get("yardline_100"))
            if yardline_100 is None:
                continue
            yardline = max(80, min(99, int(round(100 - yardline_100))))
            if yardline < 80:
                continue
            if not drive_seen_rz[drive_key]:
                drive_seen_rz[drive_key] = True
                entries += 1
            down = _number(payload.get("down"))
            if down != 4:
                continue
            fourth_arrivals += 1
            distance = max(1, int(_number(payload.get("ydstogo")) or 10))
            key = rz_fourth_decision_state_key(
                yardline=yardline,
                distance=distance,
                goal_to_go=rz_goal_to_go(yardline, distance),
            )
            play_type = str(payload.get("play_type") or "")
            if play_type == "field_goal":
                action = "field_goal"
                fg_actions += 1
            elif play_type == "punt":
                action = "punt"
            else:
                action = "go"
            decisions_by_key[key] += 1
            if action == "field_goal":
                fg_by_key[key] += 1
            elif action == "go":
                go_by_key[key] += 1

    games = len({key[0] for key in drive_seen_rz})
    fg_take = {
        key: fg_by_key[key] / decisions_by_key[key]
        for key in decisions_by_key
        if decisions_by_key[key]
    }
    return {
        "games": games,
        "rz_entries": entries,
        "rz_fourth_arrivals": fourth_arrivals,
        "rz_fg_actions": fg_actions,
        "fourth_per_entry": fourth_arrivals / entries if entries else 0.0,
        "fg_per_entry": fg_actions / entries if entries else 0.0,
        "fg_take_given_fourth": fg_actions / fourth_arrivals if fourth_arrivals else 0.0,
        "fg_take_by_key": dict(sorted(fg_take.items())),
    }


def _simulate_metrics(
    config: ClockPlayConfig, inputs_payload: Mapping[str, Any], games: int
) -> dict[str, Any]:
    entries = 0
    fourth_arrivals = 0
    fg_actions = 0
    decisions_by_key: Counter[str] = Counter()
    fg_by_key: Counter[str] = Counter()
    root_seed = 114729

    for index in range(games):
        case = inputs_payload["cases"][0]
        game = _as_game(case)
        seed = derive_replicate_seed(root_seed, case["case_id"], index)
        result = simulate_clock_play_game(
            game, seed=seed, config=config, collect_events=True
        )
        possession_entered_rz = False
        for event in result.get("events") or []:
            event_type = str(event.get("event_type") or "")
            if event_type == "possession_start":
                possession_entered_rz = False
                continue
            state = event.get("state") or {}
            yardline = int(state.get("yardline") or 0)
            if event_type == "scrimmage_play" and yardline >= 80:
                if not possession_entered_rz:
                    possession_entered_rz = True
                    entries += 1
            if event_type == "fourth_down_decision" and yardline >= 80:
                fourth_arrivals += 1
                distance = max(1, int(state.get("distance") or 1))
                key = rz_fourth_decision_state_key(
                    yardline=yardline,
                    distance=distance,
                    goal_to_go=rz_goal_to_go(yardline, distance),
                )
                decisions_by_key[key] += 1
                decision = str(event.get("decision") or "")
                if decision == "field_goal":
                    fg_actions += 1
                    fg_by_key[key] += 1

    fg_take = {
        key: fg_by_key[key] / decisions_by_key[key]
        for key in decisions_by_key
        if decisions_by_key[key]
    }
    return {
        "games_simulated": games,
        "rz_entries": entries,
        "rz_fourth_arrivals": fourth_arrivals,
        "rz_fg_actions": fg_actions,
        "fourth_per_entry": fourth_arrivals / entries if entries else 0.0,
        "fg_per_entry": fg_actions / entries if entries else 0.0,
        "fg_take_given_fourth": fg_actions / fourth_arrivals if fourth_arrivals else 0.0,
        "fg_take_by_key": dict(sorted(fg_take.items())),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--historical-pbp", type=Path, required=True)
    parser.add_argument("--games", type=int, default=512)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-sha", type=str, required=True)
    args = parser.parse_args()

    config_payload = _load_json(args.config.resolve())
    inputs_payload = _load_json(args.inputs.resolve())
    config = ClockPlayConfig.from_mapping(_engine_config(config_payload))
    historical = _historical_rz_metrics(args.historical_pbp.resolve())
    simulated = _simulate_metrics(config, inputs_payload, args.games)
    payload = {
        "artifact_id": str(config_payload.get("artifact_id") or "Clock-Play RZ fourth trace"),
        "source_sha": args.source_sha,
        "historical_train": historical,
        "simulated": simulated,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
