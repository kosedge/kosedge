#!/usr/bin/env python3
"""Regulation endgame funnel: tie, clock, and field position vs train PBP."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
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
ENDGAME_WINDOW = 180


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


@dataclass
class GameFunnel:
    q4_tied_snap: bool = False
    q4_tied_clock_le_endgame: bool = False
    q4_tied_clock_le_late: bool = False
    q4_tied_late_fg_range: bool = False
    q4_tied_late_eligible: bool = False
    q4_tied_late_out_of_fg_range: bool = False
    overtime: bool = False
    tied_late_yardlines: list[int] = field(default_factory=list)


def _update_funnel(
    funnel: GameFunnel,
    *,
    quarter: Any,
    clock_seconds: float,
    down: int,
    yardline: int,
    home_score: float,
    away_score: float,
    fg_max_distance: int,
) -> None:
    if quarter != 4 or home_score != away_score:
        return
    funnel.q4_tied_snap = True
    if clock_seconds <= ENDGAME_WINDOW:
        funnel.q4_tied_clock_le_endgame = True
    if 0 < clock_seconds <= LATE_FG_WINDOW:
        funnel.q4_tied_clock_le_late = True
        fg_dist = 117 - yardline
        funnel.tied_late_yardlines.append(yardline)
        if fg_dist <= fg_max_distance:
            funnel.q4_tied_late_fg_range = True
            if down < 4:
                funnel.q4_tied_late_eligible = True
        else:
            funnel.q4_tied_late_out_of_fg_range = True


def _summarize_funnels(
    funnels: dict[str, GameFunnel], fg_max_distance: int
) -> dict[str, Any]:
    games = len(funnels) or 1
    yards: list[int] = []
    for funnel in funnels.values():
        yards.extend(funnel.tied_late_yardlines)

    def rate(flag: str) -> float:
        return sum(1 for funnel in funnels.values() if getattr(funnel, flag)) / games

    fg_ok = sum(1 for y in yards if (117 - y) <= fg_max_distance)
    return {
        "games": games,
        "rates_per_game": {
            "q4_tied_snap": rate("q4_tied_snap"),
            "q4_tied_clock_le_endgame": rate("q4_tied_clock_le_endgame"),
            "q4_tied_clock_le_late_window": rate("q4_tied_clock_le_late"),
            "q4_tied_late_fg_range_any_down": rate("q4_tied_late_fg_range"),
            "q4_tied_late_full_eligible": rate("q4_tied_late_eligible"),
            "q4_tied_late_out_of_fg_range": rate("q4_tied_late_out_of_fg_range"),
            "overtime": rate("overtime"),
        },
        "tied_late_snap_count": len(yards),
        "tied_late_fg_range_share_of_snaps": fg_ok / len(yards) if yards else 0.0,
        "mean_yardline_when_tied_late": sum(yards) / len(yards) if yards else None,
    }


def _historical_funnels(pbp: Path, fg_max_distance: int) -> dict[str, Any]:
    funnels: dict[str, GameFunnel] = {}
    overtime_games: set[str] = set()

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
            if not game_id:
                continue
            funnel = funnels.setdefault(game_id, GameFunnel())
            quarter = payload.get("qtr")
            seconds = _number(payload.get("game_seconds_remaining"))
            if seconds is None:
                continue
            down = int(_number(payload.get("down")) or 1)
            yardline_100 = _number(payload.get("yardline_100"))
            if yardline_100 is None:
                continue
            yardline = max(1, min(99, int(round(100 - yardline_100))))
            home = _number(payload.get("posteam_score"))
            away = _number(payload.get("defteam_score"))
            if home is None or away is None:
                continue
            _update_funnel(
                funnel,
                quarter=quarter,
                clock_seconds=float(seconds),
                down=down,
                yardline=yardline,
                home_score=home,
                away_score=away,
                fg_max_distance=fg_max_distance,
            )
            if quarter == 5 or str(payload.get("qtr")) == "5":
                overtime_games.add(game_id)

    for game_id in overtime_games:
        funnels.setdefault(game_id, GameFunnel()).overtime = True

    summary = _summarize_funnels(funnels, fg_max_distance)
    summary["overtime_from_qtr5_flag"] = len(overtime_games) / (len(funnels) or 1)
    return summary


def _simulate_funnels(
    config: ClockPlayConfig,
    inputs_payload: Mapping[str, Any],
    config_payload: Mapping[str, Any],
    games_per_case: int,
) -> dict[str, Any]:
    funnels: dict[str, GameFunnel] = {}
    cases = inputs_payload.get("cases") or []
    game_index = 0

    for case in cases:
        game = _as_game(case)
        root_seed = int(config_payload["freeze_run"]["root_seeds"][case["case_id"]])
        for index in range(games_per_case):
            game_key = f"{case['case_id']}:{index}"
            funnel = GameFunnel()
            seed = derive_replicate_seed(root_seed, case["case_id"], index)
            result = simulate_clock_play_game(
                game, seed=seed, config=config, collect_events=True
            )
            if result.get("result_reason") == "overtime_expired_tie" or any(
                str(event.get("event_type")) == "overtime_start"
                for event in (result.get("events") or [])
            ):
                funnel.overtime = True

            for event in result.get("events") or []:
                if str(event.get("event_type")) not in {
                    "scrimmage_play",
                    "incomplete_pass",
                }:
                    continue
                state = event.get("state") or {}
                quarter = state.get("quarter")
                clock = float(state.get("clock_seconds") or 0)
                down = int(state.get("down") or 1)
                yardline = int(state.get("yardline") or 1)
                score = state.get("score") or {}
                home = float(score.get("home") or 0)
                away = float(score.get("away") or 0)
                _update_funnel(
                    funnel,
                    quarter=quarter,
                    clock_seconds=clock,
                    down=down,
                    yardline=yardline,
                    home_score=home,
                    away_score=away,
                    fg_max_distance=config.field_goal_max_distance,
                )

            funnels[game_key] = funnel
            game_index += 1

    return _summarize_funnels(funnels, config.field_goal_max_distance)


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

    historical = _historical_funnels(args.historical_pbp.resolve(), fg_max)
    simulated = _simulate_funnels(
        config, inputs_payload, config_payload, args.games_per_case
    )

    hist_rates = historical["rates_per_game"]
    sim_rates = simulated["rates_per_game"]
    funnel_delta = {
        key: sim_rates.get(key, 0.0) - hist_rates.get(key, 0.0)
        for key in hist_rates
    }

    payload = {
        "artifact_id": str(config_payload.get("artifact_id")),
        "component": "regulation_endgame_funnel",
        "historical_train": historical,
        "simulated": simulated,
        "sim_minus_train_per_game": funnel_delta,
        "clock_flow_runtime_scale": config.clock_flow_runtime_scale,
        "source_sha": args.source_sha,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
