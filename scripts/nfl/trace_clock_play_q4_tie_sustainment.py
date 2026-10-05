#!/usr/bin/env python3
"""Q4 equalizing TD and mid-quarter tie sustainment vs train PBP."""

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


def _offense_gap(payload: Mapping[str, Any]) -> int | None:
    posteam_score = _number(payload.get("posteam_score"))
    defteam_score = _number(payload.get("defteam_score"))
    if posteam_score is None or defteam_score is None:
        return None
    return int(round(posteam_score - defteam_score))


@dataclass
class GameTieSustain:
    tied_at_q4_start: bool | None = None
    q4_tie_created_mid: bool = False
    q4_tied_scrimmage_snaps: int = 0
    q4_tied_endgame_scrimmage_snaps: int = 0
    q4_equalizing_td: int = 0
    q4_equalizing_fg: int = 0
    q4_tie_breaking_td: int = 0
    q4_tie_breaking_fg: int = 0
    q4_trail6_offense_snaps: int = 0
    q4_trail6_rz_snaps: int = 0
    overtime: bool = False
    mid_tie_reached_endgame_tied: bool = False


def _summarize(games: dict[str, GameTieSustain]) -> dict[str, Any]:
    n = len(games) or 1

    def rate(flag: str) -> float:
        return sum(1 for g in games.values() if getattr(g, flag)) / n

    def mean_of(attr: str) -> float:
        return sum(getattr(g, attr) for g in games.values()) / n

    tied_snaps = sum(g.q4_tied_scrimmage_snaps for g in games.values()) or 1
    break_td = sum(g.q4_tie_breaking_td for g in games.values())
    break_fg = sum(g.q4_tie_breaking_fg for g in games.values())
    trail6 = sum(g.q4_trail6_offense_snaps for g in games.values())

    return {
        "games": len(games),
        "per_game": {
            "q4_equalizing_touchdowns": mean_of("q4_equalizing_td"),
            "q4_equalizing_field_goals": mean_of("q4_equalizing_fg"),
            "q4_tie_breaking_touchdowns": mean_of("q4_tie_breaking_td"),
            "q4_tie_breaking_field_goals": mean_of("q4_tie_breaking_fg"),
            "q4_tied_scrimmage_snaps": mean_of("q4_tied_scrimmage_snaps"),
            "q4_trail6_offense_snaps": mean_of("q4_trail6_offense_snaps"),
            "q4_trail6_rz_offense_snaps": mean_of("q4_trail6_rz_snaps"),
        },
        "rates_per_game": {
            "q4_tie_created_after_q4_start": rate("q4_tie_created_mid"),
            "mid_tie_reached_endgame_tied_scrimmage": rate("mid_tie_reached_endgame_tied"),
            "overtime": rate("overtime"),
        },
        "conditional": {
            "equalizing_td_per_trail6_offense_snap": (
                sum(g.q4_equalizing_td for g in games.values()) / trail6 if trail6 else None
            ),
            "tie_breaking_td_per_tied_scrimmage_snap": break_td / tied_snaps,
            "tie_breaking_fg_per_tied_scrimmage_snap": break_fg / tied_snaps,
            "endgame_tied_snap_share_of_all_q4_tied_snaps": (
                sum(g.q4_tied_endgame_scrimmage_snaps for g in games.values()) / tied_snaps
            ),
        },
    }


def _historical_games(pbp: Path) -> dict[str, GameTieSustain]:
    games: dict[str, GameTieSustain] = {}
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
            g = games.setdefault(game_id, GameTieSustain())
            if payload.get("qtr") == 5:
                g.overtime = True
            if payload.get("qtr") != 4:
                continue

            gap = _offense_gap(payload)
            ps = _number(payload.get("posteam_score"))
            ds = _number(payload.get("defteam_score"))
            if gap is None or ps is None or ds is None:
                continue

            seconds = _number(payload.get("game_seconds_remaining"))
            play_type = str(payload.get("play_type") or "")
            yardline_100 = _number(payload.get("yardline_100"))
            yardline = None
            if yardline_100 is not None:
                yardline = max(1, min(99, int(round(100 - yardline_100))))

            if not saw_q4.get(game_id):
                saw_q4[game_id] = True
                g.tied_at_q4_start = ps == ds

            tied = ps == ds
            if tied:
                if g.tied_at_q4_start is False:
                    g.q4_tie_created_mid = True
                if play_type in {"run", "pass"}:
                    g.q4_tied_scrimmage_snaps += 1
                    if seconds is not None and seconds <= ENDGAME_WINDOW:
                        g.q4_tied_endgame_scrimmage_snaps += 1
                        if g.q4_tie_created_mid:
                            g.mid_tie_reached_endgame_tied = True

            if gap == -6 and play_type in {"run", "pass"}:
                g.q4_trail6_offense_snaps += 1
                if yardline is not None and yardline >= 80:
                    g.q4_trail6_rz_snaps += 1

            if payload.get("touchdown") in {1, True, "1"}:
                if gap == -6:
                    g.q4_equalizing_td += 1
                if ps == ds:
                    g.q4_tie_breaking_td += 1
            if play_type == "field_goal" and payload.get("field_goal_result") == "made":
                if gap == -3:
                    g.q4_equalizing_fg += 1
                if ps == ds:
                    g.q4_tie_breaking_fg += 1

    for g in games.values():
        if g.tied_at_q4_start is None:
            g.tied_at_q4_start = False
    return games


def _simulate(
    config: ClockPlayConfig,
    inputs_payload: Mapping[str, Any],
    config_payload: Mapping[str, Any],
    games_per_case: int,
) -> dict[str, GameTieSustain]:
    games: dict[str, GameTieSustain] = {}
    cases = inputs_payload.get("cases") or []

    for case in cases:
        game = _as_game(case)
        root_seed = int(config_payload["freeze_run"]["root_seeds"][case["case_id"]])
        for index in range(games_per_case):
            key = f"{case['case_id']}:{index}"
            g = GameTieSustain()
            seed = derive_replicate_seed(root_seed, case["case_id"], index)
            result = simulate_clock_play_game(
                game, seed=seed, config=config, collect_events=True
            )
            if any(
                str(e.get("event_type")) == "overtime_start" for e in (result.get("events") or [])
            ):
                g.overtime = True

            for event in result.get("events") or []:
                et = str(event.get("event_type") or "")
                state = event.get("state") or {}
                if state.get("quarter") != 4:
                    continue
                score = state.get("score") or {}
                home = float(score.get("home") or 0)
                away = float(score.get("away") or 0)
                offense = str(state.get("possession") or event.get("offense") or "")
                if offense not in {"home", "away"}:
                    continue
                gap = int(round(home - away)) if offense == "home" else int(round(away - home))
                clock = float(state.get("clock_seconds") or 0)
                yardline = int(state.get("yardline") or 1)
                tied = home == away

                if et == "quarter_start":
                    g.tied_at_q4_start = tied

                if et in {"scrimmage_play", "incomplete_pass"}:
                    if tied:
                        if g.tied_at_q4_start is False:
                            g.q4_tie_created_mid = True
                        g.q4_tied_scrimmage_snaps += 1
                        if clock <= ENDGAME_WINDOW:
                            g.q4_tied_endgame_scrimmage_snaps += 1
                            if g.q4_tie_created_mid:
                                g.mid_tie_reached_endgame_tied = True
                    if gap == -6:
                        g.q4_trail6_offense_snaps += 1
                        if yardline >= 80:
                            g.q4_trail6_rz_snaps += 1

                if et == "touchdown":
                    points = 6
                    if offense == "home":
                        pre_gap = int(round((home - points) - away))
                    else:
                        pre_gap = int(round((away - points) - home))
                    if pre_gap == -6:
                        g.q4_equalizing_td += 1
                    if offense == "home":
                        pre_tied = (home - points) == away
                    else:
                        pre_tied = (away - points) == home
                    if pre_tied:
                        g.q4_tie_breaking_td += 1

                if et == "field_goal_made":
                    if offense == "home":
                        pre_gap = int(round((home - 3) - away))
                        pre_tied = (home - 3) == away
                    else:
                        pre_gap = int(round((away - 3) - home))
                        pre_tied = (away - 3) == home
                    if pre_gap == -3:
                        g.q4_equalizing_fg += 1
                    if pre_tied:
                        g.q4_tie_breaking_fg += 1

            if g.tied_at_q4_start is None:
                g.tied_at_q4_start = False
            games[key] = g
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

    hist = _summarize(_historical_games(args.historical_pbp.resolve()))
    sim = _summarize(
        _simulate(config, inputs_payload, config_payload, args.games_per_case)
    )
    delta_pg = {
        k: sim["per_game"][k] - hist["per_game"][k] for k in hist["per_game"]
    }
    delta_rates = {
        k: sim["rates_per_game"][k] - hist["rates_per_game"][k]
        for k in hist["rates_per_game"]
    }

    payload = {
        "component": "q4_tie_sustainment_equalizing_td",
        "source_sha": args.source_sha,
        "historical_train": hist,
        "simulated": sim,
        "sim_minus_train_per_game": delta_pg,
        "sim_minus_train_rates": delta_rates,
        "verdict": "Q4_TIE_SUSTAINMENT_TRACED",
    }
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
