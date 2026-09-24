#!/usr/bin/env python3
"""Endgame trail−3 fourth-down arrival vs FG share by yardline band (train vs sim)."""

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
TRAIN_GAMES = 2863
ENDGAME = 180
BANDS = ("yl_ge_80", "yl_55_79")


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


def _yard_band(yardline: int) -> str | None:
    if yardline >= 80:
        return "yl_ge_80"
    if yardline >= 55:
        return "yl_55_79"
    return None


@dataclass
class BandStats:
    arrivals: int = 0
    fg_decisions: int = 0


@dataclass
class SplitStats:
    by_band: dict[str, BandStats] = field(
        default_factory=lambda: {b: BandStats() for b in BANDS}
    )


def _summarize(stats: SplitStats, games: int) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for band in BANDS:
        b = stats.by_band[band]
        arr_pg = b.arrivals / games if games else 0.0
        fg_pg = b.fg_decisions / games if games else 0.0
        share = b.fg_decisions / b.arrivals if b.arrivals else None
        rows.append(
            {
                "yardline_band": band,
                "arrivals": b.arrivals,
                "fg_decisions": b.fg_decisions,
                "arrivals_per_game": arr_pg,
                "fg_decisions_per_game": fg_pg,
                "fg_share_given_arrival": share,
            }
        )
    return {"games": games, "by_band": rows}


def _train_split(pbp: Path, fg_max: int) -> SplitStats:
    stats = SplitStats()
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
            if ps is None or ds is None or int(ps - ds) != -3:
                continue
            clock = float(payload.get("game_seconds_remaining") or 0)
            if clock > ENDGAME:
                continue
            down = int(float(payload.get("down") or 0))
            if down != 4:
                continue
            y100 = payload.get("yardline_100")
            if y100 is None:
                continue
            yardline = max(1, min(99, int(round(100 - float(y100)))))
            band = _yard_band(yardline)
            if band is None:
                continue
            fg_dist = 117 - yardline
            if fg_dist > fg_max:
                continue
            stats.by_band[band].arrivals += 1
            if str(payload.get("play_type") or "") == "field_goal":
                stats.by_band[band].fg_decisions += 1
    return stats


def _sim_split(
    config: ClockPlayConfig,
    inputs_payload: Mapping[str, Any],
    config_payload: Mapping[str, Any],
    games_per_case: int,
) -> tuple[SplitStats, int]:
    stats = SplitStats()
    cases = inputs_payload.get("cases") or []
    total_games = games_per_case * len(cases)
    fg_max = config.field_goal_max_distance

    for case in cases:
        game = _as_game(case)
        root_seed = int(config_payload["freeze_run"]["root_seeds"][case["case_id"]])
        for index in range(games_per_case):
            seed = derive_replicate_seed(root_seed, case["case_id"], index)
            result = simulate_clock_play_game(
                game, seed=seed, config=config, collect_events=True
            )
            for event in result.get("events") or []:
                if str(event.get("event_type") or "") != "fourth_down_decision":
                    continue
                state = event.get("state") or {}
                if state.get("quarter") != 4:
                    continue
                clock = float(state.get("clock_seconds") or 0)
                if clock > ENDGAME:
                    continue
                score = state.get("score") or {}
                offense = str(state.get("possession") or event.get("offense") or "")
                if offense not in {"home", "away"}:
                    continue
                home, away = float(score.get("home", 0)), float(score.get("away", 0))
                gap = int(round(home - away)) if offense == "home" else int(
                    round(away - home)
                )
                if gap != -3:
                    continue
                yardline = int(state.get("yardline") or 1)
                band = _yard_band(yardline)
                if band is None:
                    continue
                if (117 - yardline) > fg_max:
                    continue
                stats.by_band[band].arrivals += 1
                if str(event.get("decision") or "") == "field_goal":
                    stats.by_band[band].fg_decisions += 1
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

    hist = _summarize(_train_split(args.historical_pbp.resolve(), fg_max), TRAIN_GAMES)
    sim_stats, sim_games = _sim_split(
        config, inputs_payload, config_payload, args.games_per_case
    )
    sim = _summarize(sim_stats, sim_games)

    delta: dict[str, dict[str, float | None]] = {}
    for band in BANDS:
        ht = next(r for r in hist["by_band"] if r["yardline_band"] == band)
        st = next(r for r in sim["by_band"] if r["yardline_band"] == band)
        delta[band] = {
            "arrivals_per_game": st["arrivals_per_game"] - ht["arrivals_per_game"],
            "fg_decisions_per_game": st["fg_decisions_per_game"]
            - ht["fg_decisions_per_game"],
            "fg_share_given_arrival": (
                (st["fg_share_given_arrival"] or 0) - (ht["fg_share_given_arrival"] or 0)
                if ht["fg_share_given_arrival"] is not None
                and st["fg_share_given_arrival"] is not None
                else None
            ),
        }

    payload = {
        "component": "q4_endgame_trail3_fourth_split",
        "source_sha": args.source_sha,
        "historical_train": hist,
        "simulated": sim,
        "sim_minus_train": delta,
        "verdict": "Q4_ENDGAME_TRAIL3_FOURTH_SPLIT_TRACED",
    }
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
