#!/usr/bin/env python3
"""Q4 trailing equalization paths (especially FG that ties from a deficit) vs train."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
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


def _offense_gap(posteam_score: float, defteam_score: float) -> int:
    return int(round(posteam_score - defteam_score))


def _became_tied_after_fg(home: float, away: float, offense: str) -> bool:
    return _became_tied_after_score(home, away, offense, 3)


def _became_tied_after_score(
    home: float, away: float, offense: str, points: int
) -> bool:
    if home != away:
        return False
    if offense == "home":
        return (home - points) != away
    return home != (away - points)


def _offense_from_posteam(payload: Mapping[str, Any]) -> str:
    posteam = str(payload.get("posteam") or "")
    home_team = str(payload.get("home_team") or "")
    return "home" if posteam == home_team else "away"


@dataclass
class TrailingEqualization:
    equalizing_fg_made: int = 0
    equalizing_td: int = 0
    trail3_fg_attempts: int = 0
    trail3_fg_made: int = 0
    trail3_fg_made_equalizing: int = 0
    trail3_fourth_in_fg_range: int = 0
    trail3_fourth_fg_decision: int = 0
    trail3_fourth_go_decision: int = 0
    trail3_endgame_fourth_in_fg_range: int = 0
    trail3_endgame_fourth_fg_decision: int = 0
    equalizing_fg_in_rz: int = 0
    equalizing_fg_outside_rz: int = 0
    deficit_at_equalizing_fg: dict[str, int] = field(
        default_factory=lambda: defaultdict(int)
    )


def _per_game(stats: TrailingEqualization, games: int) -> dict[str, Any]:
    g = games or 1
    return {
        "games": games,
        "per_game": {
            "equalizing_fg_made": stats.equalizing_fg_made / g,
            "equalizing_td": stats.equalizing_td / g,
            "trail3_fg_attempts": stats.trail3_fg_attempts / g,
            "trail3_fg_made": stats.trail3_fg_made / g,
            "trail3_fg_made_equalizing": stats.trail3_fg_made_equalizing / g,
            "trail3_fourth_in_fg_range": stats.trail3_fourth_in_fg_range / g,
            "trail3_fourth_fg_decision": stats.trail3_fourth_fg_decision / g,
            "trail3_fourth_go_decision": stats.trail3_fourth_go_decision / g,
            "trail3_endgame_fourth_in_fg_range": stats.trail3_endgame_fourth_in_fg_range
            / g,
            "trail3_endgame_fourth_fg_decision": stats.trail3_endgame_fourth_fg_decision
            / g,
            "equalizing_fg_in_rz": stats.equalizing_fg_in_rz / g,
            "equalizing_fg_outside_rz": stats.equalizing_fg_outside_rz / g,
        },
        "deficit_points_before_equalizing_fg": dict(stats.deficit_at_equalizing_fg),
        "conditional": {
            "trail3_fg_attempt_rate_given_fourth_in_range": (
                stats.trail3_fg_attempts / stats.trail3_fourth_in_fg_range
                if stats.trail3_fourth_in_fg_range
                else None
            ),
            "trail3_equalizing_rate_given_fg_made": (
                stats.trail3_fg_made_equalizing / stats.trail3_fg_made
                if stats.trail3_fg_made
                else None
            ),
            "fg_decision_share_trail3_endgame_fourth_in_range": (
                stats.trail3_endgame_fourth_fg_decision
                / stats.trail3_endgame_fourth_in_fg_range
                if stats.trail3_endgame_fourth_in_fg_range
                else None
            ),
        },
    }


def _historical_v2(pbp: Path, fg_max: int) -> tuple[TrailingEqualization, int]:
    stats = TrailingEqualization()
    games: set[str] = set()

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
            if payload.get("qtr") != 4:
                continue

            home = _number(payload.get("posteam_score"))
            away = _number(payload.get("defteam_score"))
            if home is None or away is None:
                continue
            gap = _offense_gap(home, away)
            seconds = _number(payload.get("game_seconds_remaining"))
            down = int(_number(payload.get("down")) or 0)
            yardline_100 = _number(payload.get("yardline_100"))
            if yardline_100 is None:
                continue
            yardline = max(1, min(99, int(round(100 - yardline_100))))
            fg_dist = 117 - yardline
            offense = _offense_from_posteam(payload)
            play_type = str(payload.get("play_type") or "")

            if down == 4 and gap == -3 and fg_dist <= fg_max:
                stats.trail3_fourth_in_fg_range += 1
                if seconds is not None and seconds <= ENDGAME_WINDOW:
                    stats.trail3_endgame_fourth_in_fg_range += 1
                if play_type == "field_goal":
                    stats.trail3_fourth_fg_decision += 1
                    if seconds is not None and seconds <= ENDGAME_WINDOW:
                        stats.trail3_endgame_fourth_fg_decision += 1
                elif play_type in {"run", "pass"}:
                    stats.trail3_fourth_go_decision += 1

            if play_type == "field_goal" and gap == -3:
                stats.trail3_fg_attempts += 1
                if payload.get("field_goal_result") == "made":
                    stats.trail3_fg_made += 1
                    stats.trail3_fg_made_equalizing += 1
                    stats.equalizing_fg_made += 1
                    stats.deficit_at_equalizing_fg["3"] += 1
                    if yardline >= 80:
                        stats.equalizing_fg_in_rz += 1
                    else:
                        stats.equalizing_fg_outside_rz += 1

            if payload.get("touchdown") in {1, True, "1"} and _became_tied_after_score(
                home, away, offense, 6
            ):
                stats.equalizing_td += 1

    return stats, len(games)


def _simulate(
    config: ClockPlayConfig,
    inputs_payload: Mapping[str, Any],
    config_payload: Mapping[str, Any],
    games_per_case: int,
) -> tuple[TrailingEqualization, int]:
    stats = TrailingEqualization()
    cases = inputs_payload.get("cases") or []
    total_games = games_per_case * len(cases)

    for case in cases:
        game = _as_game(case)
        root_seed = int(config_payload["freeze_run"]["root_seeds"][case["case_id"]])
        for index in range(games_per_case):
            seed = derive_replicate_seed(root_seed, case["case_id"], index)
            result = simulate_clock_play_game(
                game, seed=seed, config=config, collect_events=True
            )
            for event in result.get("events") or []:
                event_type = str(event.get("event_type") or "")
                state = event.get("state") or {}
                quarter = state.get("quarter")
                if quarter != 4:
                    continue
                score = state.get("score") or {}
                home = float(score.get("home") or 0)
                away = float(score.get("away") or 0)
                offense = str(state.get("possession") or event.get("offense") or "")
                if offense not in {"home", "away"}:
                    continue
                gap = int(round(home - away)) if offense == "home" else int(
                    round(away - home)
                )
                clock = float(state.get("clock_seconds") or 0)
                yardline = int(state.get("yardline") or 1)
                down = int(state.get("down") or 1)
                fg_dist = 117 - yardline
                fg_max = config.field_goal_max_distance

                if down == 4 and gap == -3 and fg_dist <= fg_max:
                    stats.trail3_fourth_in_fg_range += 1
                    if clock <= ENDGAME_WINDOW:
                        stats.trail3_endgame_fourth_in_fg_range += 1

                if event_type == "fourth_down_decision" and gap == -3 and fg_dist <= fg_max:
                    decision = str(event.get("decision") or "")
                    if decision == "field_goal":
                        stats.trail3_fourth_fg_decision += 1
                        if clock <= ENDGAME_WINDOW:
                            stats.trail3_endgame_fourth_fg_decision += 1
                    elif decision == "go":
                        stats.trail3_fourth_go_decision += 1

                if event_type in {"field_goal_made", "field_goal_missed"}:
                    points = 3 if event_type == "field_goal_made" else 0
                    if offense == "home":
                        pre_gap = int(round((home - points) - away))
                    else:
                        pre_gap = int(round((away - points) - home))
                    if pre_gap == -3:
                        stats.trail3_fg_attempts += 1
                    if event_type == "field_goal_made" and pre_gap == -3:
                        stats.trail3_fg_made += 1
                        if _became_tied_after_fg(home, away, offense):
                            stats.trail3_fg_made_equalizing += 1
                    if event_type == "field_goal_made" and _became_tied_after_fg(
                        home, away, offense
                    ):
                        stats.equalizing_fg_made += 1
                        stats.deficit_at_equalizing_fg[str(abs(pre_gap))] += 1
                        if yardline >= 80:
                            stats.equalizing_fg_in_rz += 1
                        else:
                            stats.equalizing_fg_outside_rz += 1

                if event_type == "touchdown" and _became_tied_after_score(
                    home, away, offense, 6
                ):
                    stats.equalizing_td += 1

    return stats, total_games


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

    hist_stats, hist_games = _historical_v2(args.historical_pbp.resolve(), fg_max)
    sim_stats, sim_games = _simulate(
        config, inputs_payload, config_payload, args.games_per_case
    )

    historical = _per_game(hist_stats, hist_games)
    simulated = _per_game(sim_stats, sim_games)
    delta = {
        key: simulated["per_game"][key] - historical["per_game"][key]
        for key in historical["per_game"]
    }

    payload = {
        "artifact_id": str(config_payload.get("artifact_id")),
        "component": "q4_trailing_equalization",
        "historical_train": historical,
        "simulated": simulated,
        "sim_minus_train_per_game": delta,
        "mechanism_note": (
            "Sim routes yardline>=80 fourth downs through RZ joint priors, "
            "which do not condition on trailing-by-three endgame urgency; "
            "non-RZ Q4 endgame trailing-by-three uses deterministic FG branch."
        ),
        "verdict": "Q4_TRAILING_EQUALIZATION_TRACED",
        "source_sha": args.source_sha,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
