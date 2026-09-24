#!/usr/bin/env python3
"""Train-only mechanism comparison for the Clock-Play v1.1 policy candidate."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

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
CORE_PLAY_TYPES = frozenset(
    {"pass", "run", "field_goal", "punt", "qb_kneel", "qb_spike"}
)


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_one(value: Any) -> bool:
    numeric = _number(value)
    return numeric is not None and numeric == 1.0


def _as_game(raw: Mapping[str, Any]) -> ClockPlayGameInputs:
    return ClockPlayGameInputs(
        game_id=str(raw["case_id"]),
        home_team=str(raw["home_team"]),
        away_team=str(raw["away_team"]),
        home=ClockPlayTeamInput(**dict(raw["home"])),
        away=ClockPlayTeamInput(**dict(raw["away"])),
        regular_season=True,
    )


def _engine_config(config_payload: Mapping[str, Any]) -> dict[str, Any]:
    engine = dict(config_payload.get("engine_config") or {})
    for config_key, engine_key, label in (
        (
            "fourth_down_continuation_priors_path",
            "fourth_down_continuation_priors",
            "Fourth-down continuation",
        ),
        ("clock_flow_priors_path", "clock_flow_priors", "Clock-flow"),
        (
            "red_zone_rush_transition_priors_path",
            "red_zone_rush_transition_priors",
            "Red-zone rush transition",
        ),
        (
            "red_zone_fourth_decision_priors_path",
            "red_zone_fourth_decision_priors",
            "Red-zone fourth decision",
        ),
        ("pass_state_priors_path", "pass_state_priors", "Pass state"),
        (
            "special_teams_state_priors_path",
            "special_teams_state_priors",
            "Special-teams state",
        ),
    ):
        raw_path = config_payload.get(config_key)
        if raw_path is None:
            continue
        priors_payload = json.loads((ROOT / str(raw_path)).read_text(encoding="utf-8"))
        priors = priors_payload.get("priors")
        if not isinstance(priors, Mapping):
            raise SystemExit(f"{label} priors need a priors object")
        if label == "Pass state":
            priors = priors.get("pass")
        elif label == "Special-teams state":
            priors = priors.get("special_teams")
        if not isinstance(priors, Mapping):
            raise SystemExit(f"{label} priors need the expected state family")
        engine[engine_key] = dict(priors)
    return engine


def _per_game(count: float, games: int) -> float:
    return count / games if games else 0.0


def _rate(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def _quantile(values: list[float], probability: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[round((len(ordered) - 1) * probability)]


def _summary(
    *,
    games: int,
    counts: Counter[str],
    plays: list[float],
    totals: list[float],
    margins: list[float],
) -> dict[str, float]:
    field_goal_attempts = counts["field_goal_attempt"]
    touchdown_count = counts["touchdown"]
    fourth_decisions = counts["fourth_down_decision"]
    third_attempts = counts["third_down_attempt"]
    pass_attempts = counts["pass_attempt"]
    completions = counts["pass_completion"]
    return {
        "plays_per_game": _per_game(sum(plays), games),
        "drives_per_game": _per_game(counts["drive"], games),
        "offensive_td_per_game": _per_game(touchdown_count, games),
        "pat_attempts_per_td": _rate(counts["pat_try"], touchdown_count),
        "pat_make_rate": _rate(counts["pat_make"], counts["pat_try"]),
        "two_point_attempts_per_td": _rate(counts["two_point_try"], touchdown_count),
        "two_point_make_rate": _rate(counts["two_point_make"], counts["two_point_try"]),
        "total_try_attempts_per_td": _rate(
            counts["pat_try"] + counts["two_point_try"], touchdown_count
        ),
        "field_goal_attempts_per_game": _per_game(field_goal_attempts, games),
        "field_goal_makes_per_game": _per_game(counts["field_goal_made"], games),
        "field_goal_make_rate": _rate(counts["field_goal_made"], field_goal_attempts),
        "blocked_field_goals_per_game": _per_game(
            counts["field_goal_blocked"], games
        ),
        "punts_per_game": _per_game(counts["punt"], games),
        "punt_return_opportunities_per_game": _per_game(
            counts["punt_return"] + counts["punt_return_touchdown"], games
        ),
        "punt_return_touchdowns_per_game": _per_game(
            counts["punt_return_touchdown"], games
        ),
        "blocked_punts_per_game": _per_game(counts["blocked_punt"], games),
        "kickoffs_per_game": _per_game(counts["kickoff"], games),
        "kickoff_return_opportunities_per_game": _per_game(
            counts["kickoff_return"] + counts["kickoff_return_touchdown"], games
        ),
        "kickoff_return_touchdowns_per_game": _per_game(
            counts["kickoff_return_touchdown"], games
        ),
        "safeties_per_game": _per_game(counts["safety"], games),
        "non_offensive_touchdowns_per_game": _per_game(
            counts["non_offensive_touchdown"], games
        ),
        "pass_attempts_per_game": _per_game(pass_attempts, games),
        "completion_rate": _rate(completions, pass_attempts),
        "yards_per_completion": _rate(counts["pass_completion_yards"], completions),
        "yards_per_pass_attempt": _rate(counts["pass_completion_yards"], pass_attempts),
        "sacks_per_game": _per_game(counts["sack"], games),
        "sack_rate": _rate(counts["sack"], pass_attempts),
        "sack_yards_lost_per_game": _per_game(counts["sack_yards_lost"], games),
        "scrambles_per_game": _per_game(counts["scramble"], games),
        "scramble_yards_per_game": _per_game(counts["scramble_yards"], games),
        "interceptions_per_game": _per_game(counts["interception"], games),
        "fumbles_per_game": _per_game(counts["fumble"], games),
        "pass_touchdowns_per_game": _per_game(counts["pass_touchdown"], games),
        "turnovers_excluding_downs_per_game": _per_game(
            counts["turnover"], games
        ),
        "turnovers_on_downs_per_game": _per_game(counts["turnover_on_downs"], games),
        "all_turnovers_per_game": _per_game(
            counts["turnover"] + counts["turnover_on_downs"], games
        ),
        "third_down_conversion_rate": _rate(
            counts["third_down_conversion"], third_attempts
        ),
        "fourth_down_decisions_per_game": _per_game(fourth_decisions, games),
        "fourth_down_fg_share": _rate(counts["fourth_down_field_goal"], fourth_decisions),
        "fourth_down_punt_share": _rate(counts["fourth_down_punt"], fourth_decisions),
        "fourth_down_go_share": _rate(counts["fourth_down_go"], fourth_decisions),
        "q4_late_trailing_timeouts_per_game": _per_game(
            counts["q4_late_trailing_timeout"], games
        ),
        "overtime_games_rate": _rate(counts["overtime_game"], games),
        "q4_tied_non_fourth_made_fg_per_game": _per_game(
            counts["q4_tied_non_fourth_made_fg"], games
        ),
        "final_total_mean": _per_game(sum(totals), games),
        "final_total_p10": _quantile(totals, 0.10),
        "final_total_p50": _quantile(totals, 0.50),
        "final_total_p90": _quantile(totals, 0.90),
        "absolute_margin_mean": _per_game(sum(margins), games),
        "absolute_margin_p10": _quantile(margins, 0.10),
        "absolute_margin_p50": _quantile(margins, 0.50),
        "absolute_margin_p90": _quantile(margins, 0.90),
        "exact_final_margin_3_rate": _rate(counts["margin_3"], games),
        "exact_final_margin_7_rate": _rate(counts["margin_7"], games),
    }


def _simulation_metrics(
    *,
    config: ClockPlayConfig,
    cases: Iterable[Mapping[str, Any]],
    root_seeds: Mapping[str, Any],
    replicates: int,
) -> tuple[dict[str, float], int]:
    counts: Counter[str] = Counter()
    plays: list[float] = []
    totals: list[float] = []
    margins: list[float] = []
    games = 0

    for raw_case in cases:
        game = _as_game(raw_case)
        case_id = game.game_id
        for replicate_index in range(replicates):
            result = simulate_clock_play_game(
                game,
                seed=derive_replicate_seed(
                    int(root_seeds[case_id]), case_id, replicate_index
                ),
                config=config,
            )
            event_counts = Counter(result["event_counts"])
            counts["drive"] += event_counts["possession_start"]
            counts["touchdown"] += event_counts["touchdown"]
            counts["pat_try"] += event_counts["pat_try"]
            counts["pat_make"] += event_counts["pat_made"]
            counts["two_point_try"] += event_counts["two_point_try"]
            counts["two_point_make"] += event_counts["two_point_made"]
            counts["field_goal_attempt"] += (
                event_counts["field_goal_made"] + event_counts["field_goal_missed"]
            )
            counts["field_goal_made"] += event_counts["field_goal_made"]
            counts["field_goal_blocked"] += event_counts["field_goal_blocked"]
            counts["punt"] += event_counts["punt"]
            counts["punt_return"] += event_counts["punt_return"]
            counts["punt_return_touchdown"] += event_counts[
                "punt_return_touchdown"
            ]
            counts["blocked_punt"] += event_counts["blocked_punt"]
            counts["kickoff"] += event_counts["kickoff"]
            counts["kickoff_return"] += event_counts["kickoff_return"]
            counts["kickoff_return_touchdown"] += event_counts[
                "kickoff_return_touchdown"
            ]
            counts["safety"] += event_counts["safety"]
            counts["non_offensive_touchdown"] += event_counts[
                "non_offensive_touchdown"
            ]
            counts["pass_attempt"] += event_counts["pass_attempt"]
            counts["pass_completion"] += event_counts["pass_outcome_completion"]
            counts["pass_completion_yards"] += event_counts[
                "pass_completion_yards"
            ]
            counts["sack"] += event_counts["pass_outcome_sack"]
            counts["sack_yards_lost"] += event_counts["sack_yards_lost"]
            counts["scramble"] += event_counts["pass_outcome_scramble"]
            counts["scramble_yards"] += event_counts["scramble_yards"]
            counts["interception"] += event_counts["pass_outcome_interception"]
            counts["fumble"] += event_counts["pass_outcome_fumble"]
            counts["pass_touchdown"] += event_counts["pass_touchdown"]
            counts["turnover"] += event_counts["turnover"]
            counts["turnover_on_downs"] += event_counts["turnover_on_downs"]
            counts["third_down_attempt"] += event_counts["third_down_attempt"]
            counts["third_down_conversion"] += event_counts["third_down_conversion"]
            counts["fourth_down_decision"] += event_counts["fourth_down_decision"]
            counts["fourth_down_go"] += event_counts["fourth_down_go"]
            counts["fourth_down_field_goal"] += event_counts["fourth_down_field_goal"]
            counts["fourth_down_punt"] += event_counts["fourth_down_punt"]
            counts["q4_late_trailing_timeout"] += event_counts["timeout"]
            counts["q4_tied_non_fourth_made_fg"] += event_counts[
                "late_tied_non_fourth_field_goal_made"
            ]
            counts["overtime_game"] += event_counts["overtime_start"]
            home_score = float(result["home_score"])
            away_score = float(result["away_score"])
            total = home_score + away_score
            margin = abs(home_score - away_score)
            totals.append(total)
            margins.append(margin)
            if margin == 3:
                counts["margin_3"] += 1
            if margin == 7:
                counts["margin_7"] += 1
            plays.append(float(result["play_count"]))
            games += 1

    return _summary(
        games=games, counts=counts, plays=plays, totals=totals, margins=margins
    ), games


def _historical_metrics(pbp_path: Path) -> tuple[dict[str, float], int, int]:
    counts: Counter[str] = Counter()
    drives: set[tuple[str, int]] = set()
    finals: dict[str, tuple[float, float]] = {}
    games: set[str] = set()
    overtime_games: set[str] = set()
    teams: dict[str, tuple[str, str]] = {}
    scores: dict[str, dict[str, float]] = {}
    pbp_rows = 0

    with pbp_path.open(encoding="utf-8") as handle:
        for raw_line in handle:
            row = json.loads(raw_line)
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
            games.add(game_id)
            home_team = str(payload.get("home_team") or "")
            away_team = str(payload.get("away_team") or "")
            if home_team and away_team:
                teams[game_id] = (home_team, away_team)
                scores.setdefault(game_id, {home_team: 0.0, away_team: 0.0})
            home_score = _number(payload.get("home_score"))
            away_score = _number(payload.get("away_score"))
            if home_score is not None and away_score is not None:
                finals[game_id] = (home_score, away_score)

            posteam = payload.get("posteam")
            defteam = payload.get("defteam")
            posteam_score_post = _number(payload.get("posteam_score_post"))
            defteam_score_post = _number(payload.get("defteam_score_post"))
            if isinstance(posteam, str) and posteam_score_post is not None:
                scores.setdefault(game_id, {})[posteam] = posteam_score_post
            if isinstance(defteam, str) and defteam_score_post is not None:
                scores.setdefault(game_id, {})[defteam] = defteam_score_post

            quarter = _number(payload.get("qtr"))
            if quarter is not None and quarter > 4:
                overtime_games.add(game_id)
            seconds = _number(payload.get("quarter_seconds_remaining"))
            timeout_team = payload.get("timeout_team")
            game_teams = teams.get(game_id)
            timeout_scores = scores.get(game_id, {})
            timeout_opponent = (
                game_teams[1]
                if game_teams is not None and timeout_team == game_teams[0]
                else game_teams[0]
                if game_teams is not None and timeout_team == game_teams[1]
                else None
            )
            if (
                _is_one(payload.get("timeout"))
                and quarter == 4
                and seconds is not None
                and seconds <= 130
                and isinstance(timeout_team, str)
                and timeout_opponent is not None
                and timeout_scores.get(timeout_team, 0.0)
                < timeout_scores.get(timeout_opponent, 0.0)
            ):
                counts["q4_late_trailing_timeout"] += 1

            play_type = payload.get("play_type")
            is_core_play = play_type in CORE_PLAY_TYPES or (
                play_type == "no_play"
                and (
                    _is_one(payload.get("pass"))
                    or _is_one(payload.get("rush"))
                )
            )
            if _is_one(payload.get("extra_point_attempt")):
                counts["pat_try"] += 1
                if payload.get("extra_point_result") == "good":
                    counts["pat_make"] += 1
            if _is_one(payload.get("two_point_attempt")):
                counts["two_point_try"] += 1
                if payload.get("two_point_conv_result") == "success":
                    counts["two_point_make"] += 1
            if _is_one(payload.get("safety")):
                counts["safety"] += 1
            if (
                _is_one(payload.get("touchdown"))
                and payload.get("td_team") != payload.get("posteam")
            ):
                counts["non_offensive_touchdown"] += 1
            if play_type == "kickoff":
                counts["kickoff"] += 1
                returned_for_touchdown = _is_one(payload.get("touchdown")) and (
                    payload.get("td_team") == payload.get("defteam")
                )
                if returned_for_touchdown:
                    counts["kickoff_return_touchdown"] += 1
                elif not _is_one(payload.get("touchback")):
                    counts["kickoff_return"] += 1
            if not is_core_play:
                continue
            pbp_rows += 1
            counts["play"] += 1
            fixed_drive = _number(payload.get("fixed_drive"))
            if fixed_drive is not None:
                drives.add((game_id, int(fixed_drive)))
            if _is_one(payload.get("touchdown")) and payload.get("td_team") == payload.get("posteam"):
                counts["touchdown"] += 1
            is_called_pass = play_type == "pass" or _is_one(
                payload.get("qb_scramble")
            )
            if is_called_pass:
                counts["pass_attempt"] += 1
                yards = int(round(_number(payload.get("yards_gained")) or 0.0))
                if _is_one(payload.get("interception")):
                    counts["interception"] += 1
                elif _is_one(payload.get("fumble_lost")):
                    counts["fumble"] += 1
                elif _is_one(payload.get("sack")):
                    counts["sack"] += 1
                    counts["sack_yards_lost"] += max(0, -yards)
                elif _is_one(payload.get("qb_scramble")):
                    counts["scramble"] += 1
                    counts["scramble_yards"] += yards
                elif not _is_one(payload.get("incomplete_pass")):
                    counts["pass_completion"] += 1
                    counts["pass_completion_yards"] += yards
                if (
                    _is_one(payload.get("touchdown"))
                    and payload.get("td_team") == payload.get("posteam")
                ):
                    counts["pass_touchdown"] += 1
            if play_type == "field_goal":
                counts["field_goal_attempt"] += 1
                if payload.get("field_goal_result") == "made":
                    counts["field_goal_made"] += 1
                if (
                    payload.get("field_goal_result") == "blocked"
                    or _is_one(payload.get("blocked_field_goal"))
                ):
                    counts["field_goal_blocked"] += 1
            if play_type == "punt":
                counts["punt"] += 1
                blocked = _is_one(payload.get("punt_blocked")) or _is_one(
                    payload.get("blocked_punt")
                )
                returned_for_touchdown = _is_one(payload.get("touchdown")) and (
                    payload.get("td_team") == payload.get("defteam")
                )
                if blocked:
                    counts["blocked_punt"] += 1
                if returned_for_touchdown:
                    counts["punt_return_touchdown"] += 1
                elif not blocked and _number(payload.get("return_yards")) is not None:
                    counts["punt_return"] += 1
            if _is_one(payload.get("interception")) or _is_one(payload.get("fumble_lost")):
                counts["turnover"] += 1
            if _is_one(payload.get("fourth_down_failed")):
                counts["turnover_on_downs"] += 1
            if _is_one(payload.get("third_down_converted")):
                counts["third_down_conversion"] += 1
                counts["third_down_attempt"] += 1
            elif _is_one(payload.get("third_down_failed")):
                counts["third_down_attempt"] += 1

            down = _number(payload.get("down"))
            if down == 4:
                counts["fourth_down_decision"] += 1
                if play_type == "field_goal":
                    counts["fourth_down_field_goal"] += 1
                elif play_type == "punt":
                    counts["fourth_down_punt"] += 1
                else:
                    counts["fourth_down_go"] += 1

            if (
                play_type == "field_goal"
                and payload.get("field_goal_result") == "made"
                and quarter == 4
                and seconds is not None
                and 0 < seconds <= 10
                and down in {1, 2, 3}
                and _number(payload.get("posteam_score")) is not None
                and _number(payload.get("posteam_score"))
                == _number(payload.get("defteam_score"))
            ):
                counts["q4_tied_non_fourth_made_fg"] += 1
    counts["drive"] = len(drives)
    counts["overtime_game"] = len(overtime_games)
    totals = [home + away for home, away in finals.values()]
    margins = [abs(home - away) for home, away in finals.values()]
    for margin in margins:
        if margin == 3:
            counts["margin_3"] += 1
        if margin == 7:
            counts["margin_7"] += 1
    return _summary(
        games=len(games), counts=counts, plays=[float(counts["play"])], totals=totals, margins=margins
    ), len(games), pbp_rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--historical-pbp", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    config_payload = json.loads(args.config.read_text(encoding="utf-8"))
    inputs_payload = json.loads(args.inputs.read_text(encoding="utf-8"))
    run_spec = config_payload["freeze_run"]
    candidate, games_simulated = _simulation_metrics(
        config=ClockPlayConfig.from_mapping(_engine_config(config_payload)),
        cases=inputs_payload["cases"],
        root_seeds=run_spec["root_seeds"],
        replicates=int(run_spec["replicates_per_case"]),
    )
    historical, historical_games, historical_rows = _historical_metrics(args.historical_pbp)
    comparison = {
        metric: {
            "historical": historical[metric],
            "candidate": candidate[metric],
            "ratio": _rate(candidate[metric], historical[metric]),
            "error": candidate[metric] - historical[metric],
        }
        for metric in candidate
    }
    output = {
        "artifact_id": config_payload["artifact_id"],
        "train_window": "2013-2023 regular season",
        "historical_source": args.historical_pbp.as_posix(),
        "historical_games": historical_games,
        "historical_core_pbp_rows": historical_rows,
        "simulated_games": games_simulated,
        "historical": historical,
        "candidate": candidate,
        "comparison": comparison,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
