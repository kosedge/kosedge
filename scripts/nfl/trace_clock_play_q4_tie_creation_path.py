#!/usr/bin/env python3
"""Regulation/clock paths into Q4 ties: creation, clock at tie, endgame carry."""

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
ENDGAME = 180
CLOSE_MARGIN = 8


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
class GamePath:
    tied_at_q4_start: bool | None = None
    q4_start_margin: int | None = None
    q4_start_close: bool = False
    mid_q4_tie_created: bool = False
    first_mid_tie_clock: float | None = None
    mid_tie_reached_endgame_still_tied: bool = False
    equalizing_fg: int = 0
    equalizing_td: int = 0
    q4_close_untied_snaps: int = 0
    q4_trail3_untied_snaps: int = 0
    q4_clock_elapsed_while_close_untied: float = 0.0
    last_close_untied_clock: float | None = None
    was_tied_q4: bool = False


def _summarize(games: dict[str, GamePath]) -> dict[str, Any]:
    n = len(games) or 1
    mid = [g for g in games.values() if g.mid_q4_tie_created]
    clocks = [g.first_mid_tie_clock for g in mid if g.first_mid_tie_clock is not None]

    def rate(flag: str) -> float:
        return sum(1 for g in games.values() if getattr(g, flag)) / n

    def mean(attr: str) -> float:
        return sum(getattr(g, attr) for g in games.values()) / n

    return {
        "games": len(games),
        "per_game": {
            "equalizing_fg": mean("equalizing_fg"),
            "equalizing_td": mean("equalizing_td"),
            "q4_close_untied_snaps": mean("q4_close_untied_snaps"),
            "q4_trail3_untied_snaps": mean("q4_trail3_untied_snaps"),
            "q4_clock_elapsed_close_untied": mean("q4_clock_elapsed_while_close_untied"),
        },
        "rates_per_game": {
            "q4_start_close_margin_le_8": rate("q4_start_close"),
            "mid_q4_tie_created": rate("mid_q4_tie_created"),
            "mid_tie_reached_endgame_still_tied": rate("mid_tie_reached_endgame_still_tied"),
        },
        "conditional": {
            "mean_clock_at_first_mid_q4_tie": (
                sum(clocks) / len(clocks) if clocks else None
            ),
            "share_mid_tie_with_first_clock_le_180": (
                sum(1 for g in mid if (g.first_mid_tie_clock or 999) <= ENDGAME)
                / len(mid)
                if mid
                else None
            ),
            "mean_q4_start_margin": (
                sum(g.q4_start_margin or 0 for g in games.values()) / n
            ),
        },
    }


def _historical(pbp: Path) -> dict[str, GamePath]:
    games: dict[str, GamePath] = {}
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
            if payload.get("qtr") != 4:
                continue

            g = games.setdefault(game_id, GamePath())
            th = _number(payload.get("total_home_score"))
            ta = _number(payload.get("total_away_score"))
            if th is None or ta is None:
                continue
            home, away = int(th), int(ta)
            margin = abs(home - away)
            tied = home == away
            seconds = _number(payload.get("game_seconds_remaining"))
            clock = float(seconds or 0)
            play_type = str(payload.get("play_type") or "")

            if not saw_q4.get(game_id):
                saw_q4[game_id] = True
                g.tied_at_q4_start = tied
                g.q4_start_margin = margin
                g.q4_start_close = margin <= CLOSE_MARGIN
                g.was_tied_q4 = tied

            if tied:
                g.was_tied_q4 = True
                if g.tied_at_q4_start is False and not g.mid_q4_tie_created:
                    g.mid_q4_tie_created = True
                    g.first_mid_tie_clock = clock
                if g.mid_q4_tie_created and clock <= ENDGAME:
                    g.mid_tie_reached_endgame_still_tied = True

            gap = _number(payload.get("posteam_score"))
            dg = _number(payload.get("defteam_score"))
            if gap is not None and dg is not None:
                ogap = int(round(gap - dg))
                if payload.get("touchdown") in {1, True, "1"} and ogap == -6:
                    g.equalizing_td += 1
                if (
                    play_type == "field_goal"
                    and payload.get("field_goal_result") == "made"
                    and ogap == -3
                ):
                    g.equalizing_fg += 1

            if not tied and margin <= CLOSE_MARGIN and play_type in {"run", "pass"}:
                g.q4_close_untied_snaps += 1
                if margin == 3:
                    g.q4_trail3_untied_snaps += 1
                if g.last_close_untied_clock is not None and clock < g.last_close_untied_clock:
                    g.q4_clock_elapsed_while_close_untied += (
                        g.last_close_untied_clock - clock
                    )
                g.last_close_untied_clock = clock
            elif tied or margin > CLOSE_MARGIN:
                g.last_close_untied_clock = None

    for g in games.values():
        if g.tied_at_q4_start is None:
            g.tied_at_q4_start = False
    return games


def _simulate(
    config: ClockPlayConfig,
    inputs_payload: Mapping[str, Any],
    config_payload: Mapping[str, Any],
    games_per_case: int,
) -> dict[str, GamePath]:
    games: dict[str, GamePath] = {}
    cases = inputs_payload.get("cases") or []

    for case in cases:
        game = _as_game(case)
        root_seed = int(config_payload["freeze_run"]["root_seeds"][case["case_id"]])
        for index in range(games_per_case):
            key = f"{case['case_id']}:{index}"
            g = GamePath()
            seed = derive_replicate_seed(root_seed, case["case_id"], index)
            result = simulate_clock_play_game(
                game, seed=seed, config=config, collect_events=True
            )
            prev_clock: float | None = None

            for event in result.get("events") or []:
                et = str(event.get("event_type") or "")
                state = event.get("state") or {}
                if state.get("quarter") != 4:
                    continue
                score = state.get("score") or {}
                home = int(score.get("home") or 0)
                away = int(score.get("away") or 0)
                margin = abs(home - away)
                tied = home == away
                clock = float(state.get("clock_seconds") or 0)
                offense = str(state.get("possession") or event.get("offense") or "")

                if et == "quarter_start":
                    g.tied_at_q4_start = tied
                    g.q4_start_margin = margin
                    g.q4_start_close = margin <= CLOSE_MARGIN
                    g.was_tied_q4 = tied
                    prev_clock = clock

                if tied:
                    g.was_tied_q4 = True
                    if g.tied_at_q4_start is False and not g.mid_q4_tie_created:
                        g.mid_q4_tie_created = True
                        g.first_mid_tie_clock = clock
                    if g.mid_q4_tie_created and clock <= ENDGAME:
                        g.mid_tie_reached_endgame_still_tied = True

                if et == "touchdown" and offense in {"home", "away"}:
                    if offense == "home":
                        pre = int((home - 6) - away)
                    else:
                        pre = int((away - 6) - home)
                    if pre == -6:
                        g.equalizing_td += 1

                if et == "field_goal_made" and offense in {"home", "away"}:
                    if offense == "home":
                        pre = int((home - 3) - away)
                    else:
                        pre = int((away - 3) - home)
                    if pre == -3:
                        g.equalizing_fg += 1

                if (
                    et in {"scrimmage_play", "incomplete_pass"}
                    and not tied
                    and margin <= CLOSE_MARGIN
                ):
                    g.q4_close_untied_snaps += 1
                    if margin == 3:
                        g.q4_trail3_untied_snaps += 1
                    if prev_clock is not None and clock < prev_clock:
                        g.q4_clock_elapsed_while_close_untied += prev_clock - clock
                    prev_clock = clock
                elif et in {"scrimmage_play", "incomplete_pass"}:
                    prev_clock = clock

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

    hist = _summarize(_historical(args.historical_pbp.resolve()))
    sim = _summarize(_simulate(config, inputs_payload, config_payload, args.games_per_case))

    payload = {
        "component": "q4_tie_creation_clock_path",
        "source_sha": args.source_sha,
        "historical_train": hist,
        "simulated": sim,
        "sim_minus_train_per_game": {
            k: sim["per_game"][k] - hist["per_game"][k] for k in hist["per_game"]
        },
        "sim_minus_train_rates": {
            k: sim["rates_per_game"][k] - hist["rates_per_game"][k]
            for k in hist["rates_per_game"]
        },
        "verdict": "Q4_TIE_CREATION_CLOCK_PATH_TRACED",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
