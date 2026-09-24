#!/usr/bin/env python3
"""Train vs sim equalizing-FG gap by clock bucket and yardline band."""

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
TRAIN_GAMES = 2863
BUCKETS = ("le_180", "181_360", "361_600", "gt_600")
YARD_BANDS = ("yl_ge_80", "yl_55_79", "yl_lt_55")


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


def _clock_bucket(clock: float) -> str:
    if clock <= 180:
        return "le_180"
    if clock <= 360:
        return "181_360"
    if clock <= 600:
        return "361_600"
    return "gt_600"


def _yard_band(yardline: float) -> str:
    if yardline >= 80:
        return "yl_ge_80"
    if yardline >= 55:
        return "yl_55_79"
    return "yl_lt_55"


def _train_yardline(payload: Mapping[str, Any]) -> float | None:
    y100 = payload.get("yardline_100")
    if y100 is not None:
        return 100.0 - float(y100)
    y = payload.get("yardline")
    if y is not None:
        return float(y)
    return None


def _train_cells(pbp: Path) -> Counter[str]:
    cells: Counter[str] = Counter()
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
                yl = _train_yardline(payload)
                if yl is None:
                    continue
                clock = float(payload.get("game_seconds_remaining") or 0)
                cells[f"{_clock_bucket(clock)}|{_yard_band(yl)}"] += 1
    return cells


def _sim_cells(
    config: ClockPlayConfig,
    inputs_payload: Mapping[str, Any],
    config_payload: Mapping[str, Any],
    games_per_case: int,
) -> Counter[str]:
    cells: Counter[str] = Counter()
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
                if pre != -3:
                    continue
                clock = float(state.get("clock_seconds") or 0)
                yl = float(state.get("yardline") or 0)
                cells[f"{_clock_bucket(clock)}|{_yard_band(yl)}"] += 1
    return cells


def _table(cells: Counter[str], games: int) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for cb in BUCKETS:
        for yb in YARD_BANDS:
            key = f"{cb}|{yb}"
            count = cells.get(key, 0)
            rows.append(
                {
                    "cell": key,
                    "clock_bucket": cb,
                    "yardline_band": yb,
                    "count": count,
                    "per_game": count / games if games else 0.0,
                }
            )
    total = sum(cells.values())
    return {
        "games": games,
        "total_count": total,
        "per_game": total / games if games else 0.0,
        "by_cell": rows,
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
    sim_games = args.games_per_case * len(inputs_payload.get("cases") or [])

    hist_cells = _train_cells(args.historical_pbp.resolve())
    sim_cells = _sim_cells(config, inputs_payload, config_payload, args.games_per_case)

    hist = _table(hist_cells, TRAIN_GAMES)
    sim = _table(sim_cells, sim_games)
    delta_by_cell = {
        row["cell"]: sim_cells.get(row["cell"], 0) / sim_games
        - hist_cells.get(row["cell"], 0) / TRAIN_GAMES
        for row in hist["by_cell"]
    }
    ranked = sorted(delta_by_cell.items(), key=lambda item: item[1])

    payload = {
        "component": "q4_equalizing_fg_decomposition",
        "source_sha": args.source_sha,
        "historical_train": hist,
        "simulated": sim,
        "sim_minus_train_per_game_by_cell": dict(delta_by_cell),
        "largest_shortfall_cells": [k for k, v in ranked[:5]],
        "verdict": "Q4_EQUALIZING_FG_DECOMPOSITION_TRACED",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
