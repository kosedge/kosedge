#!/usr/bin/env python3
"""Decompose regulation path into Q4 tied states (clock-flow funnel owner)."""

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
class GameTieEntry:
    tied_at_q4_start: bool | None = None
    any_q4_tied_snap: bool = False
    any_q4_tied_endgame_snap: bool = False
    q4_tied_scrimmage_snaps: int = 0
    q4_tie_breaking_td: int = 0
    q4_tie_breaking_fg: int = 0
    q4_equalizing_td: int = 0
    q4_equalizing_fg: int = 0
    q4_tie_created_in_quarter: bool = False
    final_margin: int | None = None
    overtime: bool = False
    regulation_one_score_or_less: bool = False


def _was_tied_before_score(
    home: float, away: float, offense: str, points: int
) -> bool:
    if offense == "home":
        return (home - points) == away
    return home == (away - points)


def _became_tied_after_score(
    home: float, away: float, offense: str, points: int
) -> bool:
    if home != away:
        return False
    if offense == "home":
        return (home - points) != away
    return home != (away - points)


def _summarize(games: dict[str, GameTieEntry]) -> dict[str, Any]:
    n = len(games) or 1
    tied_at_start = [g for g in games.values() if g.tied_at_q4_start]
    with_q4_tied = [g for g in games.values() if g.any_q4_tied_snap]

    def rate(flag: str) -> float:
        return sum(1 for g in games.values() if getattr(g, flag)) / n

    def mean_int(getter) -> float | None:
        values = [getter(g) for g in games.values()]
        return sum(values) / len(values) if values else None

    return {
        "games": len(games),
        "rates_per_game": {
            "tied_at_q4_start": rate("tied_at_q4_start")
            if any(g.tied_at_q4_start is not None for g in games.values())
            else None,
            "any_q4_tied_snap": rate("any_q4_tied_snap"),
            "any_q4_tied_endgame_snap": rate("any_q4_tied_endgame_snap"),
            "q4_tie_created_after_q4_start": rate("q4_tie_created_in_quarter"),
            "overtime": rate("overtime"),
            "regulation_margin_le_3": rate("regulation_one_score_or_less"),
        },
        "mean_per_game": {
            "q4_tied_scrimmage_snaps": mean_int(lambda g: g.q4_tied_scrimmage_snaps),
            "q4_tie_breaking_touchdowns": mean_int(lambda g: g.q4_tie_breaking_td),
            "q4_tie_breaking_field_goals": mean_int(lambda g: g.q4_tie_breaking_fg),
            "q4_equalizing_touchdowns": mean_int(lambda g: g.q4_equalizing_td),
            "q4_equalizing_field_goals": mean_int(lambda g: g.q4_equalizing_fg),
        },
        "conditional": {
            "share_tied_at_q4_start_with_any_q4_tied_snap": (
                sum(1 for g in tied_at_start if g.any_q4_tied_snap) / len(tied_at_start)
                if tied_at_start
                else None
            ),
            "share_q4_tied_snap_without_tied_at_q4_start": (
                sum(
                    1
                    for g in with_q4_tied
                    if g.tied_at_q4_start is False
                )
                / len(with_q4_tied)
                if with_q4_tied
                else None
            ),
        },
    }


def _historical_games(pbp: Path) -> dict[str, GameTieEntry]:
    games: dict[str, GameTieEntry] = {}
    saw_q4: dict[str, bool] = {}

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
            entry = games.setdefault(game_id, GameTieEntry())
            quarter = payload.get("qtr")
            if quarter == 5 or str(quarter) == "5":
                entry.overtime = True

            home = _number(payload.get("posteam_score"))
            away = _number(payload.get("defteam_score"))
            if home is None or away is None:
                continue

            seconds = _number(payload.get("game_seconds_remaining"))
            play_type = str(payload.get("play_type") or "")

            if quarter == 4 and not saw_q4.get(game_id):
                saw_q4[game_id] = True
                entry.tied_at_q4_start = home == away

            if quarter == 4 and home == away:
                entry.any_q4_tied_snap = True
                if seconds is not None and seconds <= ENDGAME_WINDOW:
                    entry.any_q4_tied_endgame_snap = True
                if play_type in {"run", "pass"}:
                    entry.q4_tied_scrimmage_snaps += 1

            if quarter == 4 and entry.tied_at_q4_start is False and home == away:
                entry.q4_tie_created_in_quarter = True

            posteam = str(payload.get("posteam") or "")
            home_team = str(payload.get("home_team") or "")
            offense = "home" if posteam == home_team else "away"
            if quarter == 4:
                if payload.get("touchdown") in {1, True, "1"}:
                    if _was_tied_before_score(home, away, offense, 6):
                        entry.q4_tie_breaking_td += 1
                    elif _became_tied_after_score(home, away, offense, 6):
                        entry.q4_equalizing_td += 1
                if (
                    play_type == "field_goal"
                    and payload.get("field_goal_result") == "made"
                ):
                    if _was_tied_before_score(home, away, offense, 3):
                        entry.q4_tie_breaking_fg += 1
                    elif _became_tied_after_score(home, away, offense, 3):
                        entry.q4_equalizing_fg += 1

            total_home = _number(payload.get("total_home_score"))
            total_away = _number(payload.get("total_away_score"))
            if total_home is not None and total_away is not None:
                entry.final_margin = int(abs(total_home - total_away))

    for entry in games.values():
        if entry.tied_at_q4_start is None:
            entry.tied_at_q4_start = False
        if entry.final_margin is not None:
            entry.regulation_one_score_or_less = entry.final_margin <= 3
    return games


def _simulate_games(
    config: ClockPlayConfig,
    inputs_payload: Mapping[str, Any],
    config_payload: Mapping[str, Any],
    games_per_case: int,
) -> dict[str, GameTieEntry]:
    games: dict[str, GameTieEntry] = {}
    cases = inputs_payload.get("cases") or []

    for case in cases:
        game = _as_game(case)
        root_seed = int(config_payload["freeze_run"]["root_seeds"][case["case_id"]])
        for index in range(games_per_case):
            key = f"{case['case_id']}:{index}"
            entry = GameTieEntry()
            seed = derive_replicate_seed(root_seed, case["case_id"], index)
            result = simulate_clock_play_game(
                game, seed=seed, config=config, collect_events=True
            )
            if any(
                str(event.get("event_type")) == "overtime_start"
                for event in (result.get("events") or [])
            ):
                entry.overtime = True

            home_final = float(result.get("home_score") or 0)
            away_final = float(result.get("away_score") or 0)
            margin = int(abs(home_final - away_final))
            entry.final_margin = margin
            entry.regulation_one_score_or_less = margin <= 3

            for event in result.get("events") or []:
                event_type = str(event.get("event_type") or "")
                state = event.get("state") or {}
                quarter = state.get("quarter")

                if event_type == "quarter_start" and quarter == 4:
                    score = state.get("score") or {}
                    home = float(score.get("home") or 0)
                    away = float(score.get("away") or 0)
                    entry.tied_at_q4_start = home == away

                if event_type in {"scrimmage_play", "incomplete_pass"} and quarter == 4:
                    score = state.get("score") or {}
                    home = float(score.get("home") or 0)
                    away = float(score.get("away") or 0)
                    clock = float(state.get("clock_seconds") or 0)
                    if home == away:
                        entry.any_q4_tied_snap = True
                        if clock <= ENDGAME_WINDOW:
                            entry.any_q4_tied_endgame_snap = True
                        entry.q4_tied_scrimmage_snaps += 1

                if event_type == "touchdown" and quarter == 4:
                    offense = str(event.get("offense") or "")
                    score = state.get("score") or {}
                    home = float(score.get("home") or 0)
                    away = float(score.get("away") or 0)
                    if _was_tied_before_score(home, away, offense, 6):
                        entry.q4_tie_breaking_td += 1
                    elif _became_tied_after_score(home, away, offense, 6):
                        entry.q4_equalizing_td += 1

                if event_type == "field_goal_made" and quarter == 4:
                    offense = str(event.get("offense") or "")
                    score = state.get("score") or {}
                    home = float(score.get("home") or 0)
                    away = float(score.get("away") or 0)
                    if _was_tied_before_score(home, away, offense, 3):
                        entry.q4_tie_breaking_fg += 1
                    elif _became_tied_after_score(home, away, offense, 3):
                        entry.q4_equalizing_fg += 1

            if entry.tied_at_q4_start is False and entry.any_q4_tied_snap:
                entry.q4_tie_created_in_quarter = True
            if entry.tied_at_q4_start is None:
                entry.tied_at_q4_start = False

            games[key] = entry

    return games


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

    historical = _summarize(_historical_games(args.historical_pbp.resolve()))
    simulated = _summarize(
        _simulate_games(config, inputs_payload, config_payload, args.games_per_case)
    )

    hist_rates = historical["rates_per_game"]
    sim_rates = simulated["rates_per_game"]
    delta = {
        key: (sim_rates.get(key) or 0.0) - (hist_rates.get(key) or 0.0)
        for key in hist_rates
        if hist_rates.get(key) is not None and sim_rates.get(key) is not None
    }
    mean_delta = {
        key: simulated["mean_per_game"][key] - historical["mean_per_game"][key]
        for key in historical["mean_per_game"]
        if historical["mean_per_game"][key] is not None
        and simulated["mean_per_game"][key] is not None
    }

    payload = {
        "artifact_id": str(config_payload.get("artifact_id")),
        "component": "q4_tie_entry_decomposition",
        "historical_train": historical,
        "simulated": simulated,
        "sim_minus_train_rates_per_game": delta,
        "sim_minus_train_mean_per_game": mean_delta,
        "clock_flow_runtime_scale": config.clock_flow_runtime_scale,
        "verdict": "Q4_TIE_ENTRY_DECOMPOSED",
        "source_sha": args.source_sha,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
