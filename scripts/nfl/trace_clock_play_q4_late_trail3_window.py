#!/usr/bin/env python3
"""Share of games with any Q4 trail−3 offensive snap at or inside 180s (train vs sim)."""

from __future__ import annotations

import argparse
import json
import sys
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
ENDGAME = 180


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


def _margin_bucket(gap: int) -> str:
    if gap <= -9:
        return "trail_ge_9"
    if gap == -3:
        return "trail_3"
    if gap == 0:
        return "tied"
    if gap >= 9:
        return "lead_ge_9"
    return "other"


def _train_window_rate(pbp: Path) -> dict[str, Any]:
    games: set[str] = set()
    trail3_games: set[str] = set()
    first_snap_margin: dict[str, int] = {
        "trail_ge_9": 0,
        "trail_3": 0,
        "tied": 0,
        "lead_ge_9": 0,
        "other": 0,
    }
    first_snap_recorded: set[str] = set()

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
            game_id = str(payload.get("game_id") or "")
            if not game_id:
                continue
            games.add(game_id)
            clock = float(payload.get("game_seconds_remaining") or 0)
            if clock > ENDGAME:
                continue
            posteam = str(payload.get("posteam") or "")
            home_team = str(payload.get("home_team") or "")
            offense = "home" if posteam == home_team else "away"
            if not posteam:
                continue
            ps, ds = payload.get("posteam_score"), payload.get("defteam_score")
            if ps is None or ds is None:
                continue
            gap = int(round(float(ps) - float(ds)))
            if gap == -3:
                trail3_games.add(game_id)
            if game_id not in first_snap_recorded:
                first_snap_recorded.add(game_id)
                first_snap_margin[_margin_bucket(gap)] += 1

    game_count = len(games)
    return {
        "games": game_count,
        "games_with_trail3_snap_le_180": len(trail3_games),
        "share_games_with_trail3_snap_le_180": (
            len(trail3_games) / game_count if game_count else 0.0
        ),
        "first_endgame_offensive_snap_margin_share": {
            key: (value / len(first_snap_recorded) if first_snap_recorded else 0.0)
            for key, value in first_snap_margin.items()
        },
    }


def _sim_window_rate(
    config: ClockPlayConfig,
    inputs_payload: Mapping[str, Any],
    config_payload: Mapping[str, Any],
    games_per_case: int,
) -> dict[str, Any]:
    cases = inputs_payload.get("cases") or []
    total_games = games_per_case * len(cases)
    trail3_games = 0
    first_snap_margin: dict[str, int] = {
        "trail_ge_9": 0,
        "trail_3": 0,
        "tied": 0,
        "lead_ge_9": 0,
        "other": 0,
    }

    for case in cases:
        game = _as_game(case)
        root_seed = int(config_payload["freeze_run"]["root_seeds"][case["case_id"]])
        for index in range(games_per_case):
            seed = derive_replicate_seed(root_seed, case["case_id"], index)
            result = simulate_clock_play_game(
                game, seed=seed, config=config, collect_events=True
            )
            saw_trail3 = False
            recorded_first = False
            for event in result.get("events") or []:
                state = event.get("state") or {}
                if state.get("quarter") != 4:
                    continue
                clock = float(state.get("clock_seconds") or 0)
                if clock > ENDGAME:
                    continue
                offense = str(event.get("offense") or state.get("possession") or "")
                gap = _offense_gap(state.get("score") or {}, offense)
                if gap is None:
                    continue
                if not recorded_first:
                    first_snap_margin[_margin_bucket(gap)] += 1
                    recorded_first = True
                if gap == -3:
                    saw_trail3 = True
            if saw_trail3:
                trail3_games += 1

    return {
        "games": total_games,
        "games_with_trail3_snap_le_180": trail3_games,
        "share_games_with_trail3_snap_le_180": (
            trail3_games / total_games if total_games else 0.0
        ),
        "first_endgame_offensive_snap_margin_share": {
            key: (value / total_games if total_games else 0.0)
            for key, value in first_snap_margin.items()
        },
    }


def _offense_gap(score: Mapping[str, Any], offense: str) -> int | None:
    if offense not in {"home", "away"}:
        return None
    home = float(score.get("home", 0))
    away = float(score.get("away", 0))
    return int(round(home - away)) if offense == "home" else int(round(away - home))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--inputs", required=True)
    parser.add_argument("--historical-pbp", required=True)
    parser.add_argument("--games-per-case", type=int, default=128)
    parser.add_argument("--output", required=True)
    parser.add_argument("--source-sha", required=True)
    args = parser.parse_args()

    config_payload = _load_json(Path(args.config))
    inputs_payload = _load_json(Path(args.inputs))
    config = ClockPlayConfig.from_mapping(_engine_config(config_payload))

    payload = {
        "component": "q4_late_trail3_window",
        "source_sha": args.source_sha,
        "historical_train": _train_window_rate(Path(args.historical_pbp)),
        "simulated": _sim_window_rate(
            config, inputs_payload, config_payload, args.games_per_case
        ),
        "verdict": "Q4_LATE_TRAIL3_WINDOW_TRACED",
    }
    Path(args.output).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
