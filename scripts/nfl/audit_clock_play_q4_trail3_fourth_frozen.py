#!/usr/bin/env python3
"""Frozen-state audit: Q4 trail−3 fourth-down actions vs train PBP."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.nfl_clock_play_simulator import (  # noqa: E402
    ClockPlayConfig,
    ClockPlayGameInputs,
    ClockPlaySimulator,
    ClockPlayState,
    ClockPlayTeamInput,
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


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _bucket_clock(seconds: float | None) -> str:
    if seconds is None:
        return "unknown"
    if seconds <= ENDGAME:
        return "endgame_le_180"
    if seconds <= 600:
        return "q4_mid"
    return "q4_early"


def _train_action(play_type: str, payload: Mapping[str, Any]) -> str:
    if play_type == "field_goal":
        return "field_goal"
    if play_type in {"run", "pass"}:
        return "go"
    if play_type == "punt":
        return "punt"
    return "other"


def _frozen_rows(pbp: Path, fg_max: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
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
            if payload.get("qtr") != 4:
                continue
            down = int(_number(payload.get("down")) or 0)
            if down != 4:
                continue
            posteam_score = _number(payload.get("posteam_score"))
            defteam_score = _number(payload.get("defteam_score"))
            if posteam_score is None or defteam_score is None:
                continue
            gap = int(round(posteam_score - defteam_score))
            if gap != -3:
                continue
            y100 = _number(payload.get("yardline_100"))
            if y100 is None:
                continue
            yardline = max(1, min(99, int(round(100 - y100))))
            fg_dist = 117 - yardline
            if fg_dist > fg_max:
                continue
            seconds = _number(payload.get("game_seconds_remaining"))
            play_type = str(payload.get("play_type") or "")
            posteam = str(payload.get("posteam") or "")
            home_team = str(payload.get("home_team") or "")
            offense = "home" if posteam == home_team else "away"
            if offense == "home":
                home_score, away_score = int(posteam_score), int(defteam_score)
            else:
                home_score, away_score = int(defteam_score), int(posteam_score)
            distance = int(_number(payload.get("ydstogo")) or 1)
            rows.append(
                {
                    "action": _train_action(play_type, payload),
                    "yardline": yardline,
                    "distance": distance,
                    "clock_seconds": float(seconds or 0),
                    "clock_bucket": _bucket_clock(seconds),
                    "in_rz": yardline >= 80,
                    "offense": offense,
                    "home_score": home_score,
                    "away_score": away_score,
                }
            )
    return rows


def _sim_decision(config: ClockPlayConfig, frozen: Mapping[str, Any]) -> str:
    offense = str(frozen["offense"])
    simulator = ClockPlaySimulator(
        ClockPlayGameInputs(
            game_id="frozen",
            home_team="H",
            away_team="A",
        ),
        seed=1,
        config=config,
    )
    home = int(frozen["home_score"])
    away = int(frozen["away_score"])
    simulator.state = ClockPlayState(
        quarter=4,
        clock_seconds=float(frozen["clock_seconds"]),
        possession=offense,
        yardline=int(frozen["yardline"]),
        down=4,
        distance=int(frozen["distance"]),
        home_score=home,
        away_score=away,
    )
    return simulator._fourth_down_decision(offense)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--historical-pbp", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-sha", type=str, required=True)
    args = parser.parse_args()

    config_payload = _load_json(args.config.resolve())
    config = ClockPlayConfig.from_mapping(_engine_config(config_payload))
    fg_max = int(config.field_goal_max_distance)
    rows = _frozen_rows(args.historical_pbp.resolve(), fg_max)

    train_actions = Counter(r["action"] for r in rows)
    train_go = train_actions.get("go", 0)
    train_fg = train_actions.get("field_goal", 0)
    eligible = train_go + train_fg + train_actions.get("punt", 0)
    go_share = train_go / eligible if eligible else 0.0

    by_slice: dict[str, Counter[str]] = defaultdict(Counter)
    sim_on_train: Counter[str] = Counter()
    mismatch_go: list[dict[str, Any]] = []
    for frozen in rows:
        if frozen["action"] not in {"go", "field_goal"}:
            continue
        slice_key = (
            f"rz={frozen['in_rz']}|{frozen['clock_bucket']}|dist={frozen['distance']}"
        )
        by_slice[slice_key][frozen["action"]] += 1
        decision = _sim_decision(config, frozen)
        sim_on_train[decision] += 1
        if frozen["action"] == "go" and decision != "go":
            mismatch_go.append(
                {
                    "yardline": frozen["yardline"],
                    "distance": frozen["distance"],
                    "clock_seconds": frozen["clock_seconds"],
                    "in_rz": frozen["in_rz"],
                    "sim_decision": decision,
                }
            )

    slice_summary = []
    for key, counts in sorted(by_slice.items()):
        fg = counts.get("field_goal", 0)
        go = counts.get("go", 0)
        denom = fg + go
        if denom < 5:
            continue
        slice_summary.append(
            {
                "slice": key,
                "n": denom,
                "train_fg_share": fg / denom,
                "train_go_share": go / denom,
            }
        )

    payload = {
        "component": "q4_trail3_fourth_frozen_audit",
        "source_sha": args.source_sha,
        "frozen_snapshots": len(rows),
        "train_action_counts": dict(train_actions),
        "train_go_share_fg_or_go": go_share,
        "sim_decision_on_train_frozen_states": dict(sim_on_train),
        "sim_overrides_train_go_count": len(mismatch_go),
        "sample_train_go_overridden": mismatch_go[:12],
        "train_slices_min5_fg_or_go": slice_summary,
        "verdict": (
            "TRAIL3_FOURTH_GO_ZERO_IS_OVER_FORCE"
            if train_go > 0
            and sim_on_train.get("go", 0) == 0
            and sim_on_train.get("field_goal", 0) >= train_fg
            else "TRAIL3_FOURTH_GO_ZERO_NOT_OVER_FORCE"
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
