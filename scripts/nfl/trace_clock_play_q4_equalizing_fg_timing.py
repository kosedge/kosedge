#!/usr/bin/env python3
"""Clock-at-equalizing-FG distribution in Q4 (train vs sim)."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.nfl_clock_play_simulator import (  # noqa: E402
    ClockPlayConfig,
    ClockPlayGameInputs,
    ClockPlayTeamInput,
    derive_replicate_seed,
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
        ("red_zone_fourth_decision_priors_path", "red_zone_fourth_decision_priors"),
        ("pre_entry_pass_rz_priors_path", "pre_entry_pass_rz_priors"),
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


def _bucket(clock: float) -> str:
    if clock <= 180:
        return "le_180"
    if clock <= 360:
        return "181_360"
    if clock <= 600:
        return "361_600"
    return "gt_600"


def _train_clocks(pbp: Path) -> list[float]:
    clocks: list[float] = []
    with pbp.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            payload = row.get("payload") if row.get("object_type") == "pbp_play" else None
            if not isinstance(payload, Mapping):
                continue
            season = payload.get("season")
            if season not in TRAIN_SEASONS and int(season or 0) not in TRAIN_SEASONS:
                continue
            if payload.get("season_type") != "REG" or payload.get("qtr") != 4:
                continue
            ps, ds = payload.get("posteam_score"), payload.get("defteam_score")
            if ps is None or ds is None:
                continue
            if (
                payload.get("play_type") == "field_goal"
                and payload.get("field_goal_result") == "made"
                and int(ps - ds) == -3
            ):
                clocks.append(float(payload.get("game_seconds_remaining") or 0))
    return clocks


def _sim_clocks(
    config: ClockPlayConfig,
    inputs_payload: Mapping[str, Any],
    config_payload: Mapping[str, Any],
    games_per_case: int,
) -> list[float]:
    clocks: list[float] = []
    for case in inputs_payload.get("cases") or []:
        game = _as_game(case)
        root_seed = int(config_payload["freeze_run"]["root_seeds"][case["case_id"]])
        for index in range(games_per_case):
            seed = derive_replicate_seed(root_seed, case["case_id"], index)
            result = simulate_clock_play_game(
                game, seed=seed, config=config, collect_events=True
            )
            for event in result.get("events") or []:
                if event.get("event_type") != "field_goal_made":
                    continue
                state = event.get("state") or {}
                if state.get("quarter") != 4:
                    continue
                score = state.get("score") or {}
                h, a = float(score.get("home", 0)), float(score.get("away", 0))
                off = event.get("offense") or state.get("possession")
                pre = int((h - 3) - a) if off == "home" else int((a - 3) - h)
                if pre == -3:
                    clocks.append(float(state.get("clock_seconds") or 0))
    return clocks


def _summary(clocks: list[float], games: int) -> dict[str, Any]:
    buckets = Counter(_bucket(c) for c in clocks)
    n = len(clocks) or 1
    return {
        "count": len(clocks),
        "per_game": len(clocks) / games if games else 0.0,
        "mean_clock_seconds": sum(clocks) / n if clocks else None,
        "bucket_share": {k: buckets.get(k, 0) / n for k in ("gt_600", "361_600", "181_360", "le_180")},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--historical-pbp", type=Path, required=True)
    parser.add_argument("--games-per-case", type=int, default=128)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-sha", type=str, required=True)
    args = parser.parse_args()

    config_payload = _load_json(args.config.resolve())
    inputs_payload = _load_json(args.inputs.resolve())
    config = ClockPlayConfig.from_mapping(_engine_config(config_payload))
    games = args.games_per_case * len(inputs_payload.get("cases") or [])

    hist = _summary(_train_clocks(args.historical_pbp.resolve()), 2863)
    sim = _summary(
        _sim_clocks(config, inputs_payload, config_payload, args.games_per_case), games
    )

    payload = {
        "component": "q4_equalizing_fg_timing",
        "source_sha": args.source_sha,
        "historical_train": hist,
        "simulated": sim,
        "verdict": "Q4_EQUALIZING_FG_TIMING_TRACED",
    }
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
