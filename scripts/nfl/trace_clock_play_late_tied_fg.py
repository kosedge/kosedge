#!/usr/bin/env python3
"""Trace late tied non-fourth field-goal component vs train PBP."""

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
LATE_FG_WINDOW = 10


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


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_one(value: Any) -> bool:
    return _number(value) == 1.0


def _eligible_tied_late_fg(
    *,
    quarter: Any,
    clock_seconds: float,
    down: int,
    yardline: int,
    home_score: float,
    away_score: float,
    fg_max_distance: int,
) -> bool:
    return (
        quarter == 4
        and 0 < clock_seconds <= LATE_FG_WINDOW
        and down < 4
        and home_score == away_score
        and (117 - yardline) <= fg_max_distance
    )


def _historical_metrics(pbp: Path, fg_max_distance: int) -> dict[str, Any]:
    games = set()
    opportunities = 0
    made = 0
    attempts = 0

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
            if game_id:
                games.add(game_id)
            quarter = payload.get("qtr")
            seconds = _number(payload.get("game_seconds_remaining"))
            down = int(_number(payload.get("down")) or 0)
            yardline_100 = _number(payload.get("yardline_100"))
            if yardline_100 is None:
                continue
            yardline = max(1, min(99, int(round(100 - yardline_100))))
            home = _number(payload.get("posteam_score"))
            away = _number(payload.get("defteam_score"))
            if home is None or away is None:
                continue
            if _eligible_tied_late_fg(
                quarter=quarter,
                clock_seconds=float(seconds or 0),
                down=down,
                yardline=yardline,
                home_score=home,
                away_score=away,
                fg_max_distance=fg_max_distance,
            ):
                opportunities += 1
            play_type = payload.get("play_type")
            if (
                play_type == "field_goal"
                and payload.get("field_goal_result") == "made"
                and quarter == 4
                and seconds is not None
                and 0 < seconds <= LATE_FG_WINDOW
                and down in {1, 2, 3}
                and home == away
            ):
                made += 1
            if play_type == "field_goal" and quarter == 4 and home == away:
                if seconds is not None and 0 < seconds <= LATE_FG_WINDOW and down < 4:
                    attempts += 1

    game_count = len(games) or 1
    return {
        "games": game_count,
        "eligible_snap_opportunities": opportunities,
        "eligible_opportunities_per_game": opportunities / game_count,
        "made_fg_per_game": made / game_count,
        "fg_attempts_per_game": attempts / game_count,
        "made_fg_per_opportunity": made / opportunities if opportunities else 0.0,
    }


def _simulate_metrics(
    config: ClockPlayConfig,
    inputs_payload: Mapping[str, Any],
    config_payload: Mapping[str, Any],
    games_per_case: int,
) -> dict[str, Any]:
    opportunities = 0
    attempts = 0
    made = 0
    tied_q4_last_10_entries = 0
    cases = inputs_payload.get("cases") or []

    for case in cases:
        game = _as_game(case)
        root_seed = int(config_payload["freeze_run"]["root_seeds"][case["case_id"]])
        for index in range(games_per_case):
            seed = derive_replicate_seed(root_seed, case["case_id"], index)
            result = simulate_clock_play_game(
                game, seed=seed, config=config, collect_events=True
            )
            counts = result.get("event_counts") or {}
            attempts += int(counts.get("late_tied_non_fourth_field_goal_attempt") or 0)
            made += int(counts.get("late_tied_non_fourth_field_goal_made") or 0)

            for event in result.get("events") or []:
                event_type = str(event.get("event_type") or "")
                state = event.get("state") or {}
                quarter = state.get("quarter")
                clock = float(state.get("clock_seconds") or 0)
                down = int(state.get("down") or 1)
                yardline = int(state.get("yardline") or 1)
                score = state.get("score") or {}
                home = float(score.get("home") or 0)
                away = float(score.get("away") or 0)
                if quarter == 4 and 0 < clock <= LATE_FG_WINDOW and home == away:
                    tied_q4_last_10_entries += 1
                if event_type not in {"scrimmage_play", "incomplete_pass"}:
                    continue
                if _eligible_tied_late_fg(
                    quarter=quarter,
                    clock_seconds=clock,
                    down=down,
                    yardline=yardline,
                    home_score=home,
                    away_score=away,
                    fg_max_distance=config.field_goal_max_distance,
                ):
                    opportunities += 1

    total_games = games_per_case * len(cases) or 1
    return {
        "games_simulated": total_games,
        "eligible_snap_opportunities": opportunities,
        "eligible_opportunities_per_game": opportunities / total_games,
        "late_tied_fg_attempts_per_game": attempts / total_games,
        "late_tied_fg_made_per_game": made / total_games,
        "tied_q4_last_10_snap_events": tied_q4_last_10_entries,
        "made_per_opportunity": made / opportunities if opportunities else 0.0,
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
    fg_max = int(config.field_goal_max_distance)

    historical = _historical_metrics(args.historical_pbp.resolve(), fg_max)
    simulated = _simulate_metrics(
        config, inputs_payload, config_payload, args.games_per_case
    )

    payload = {
        "artifact_id": str(config_payload.get("artifact_id")),
        "component": "late_tied_non_fourth_field_goal",
        "certify_anchor": "q4_tied_non_fourth_made_fg_per_game",
        "historical_train": historical,
        "simulated": simulated,
        "source_sha": args.source_sha,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
