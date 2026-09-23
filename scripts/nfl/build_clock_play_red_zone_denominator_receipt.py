#!/usr/bin/env python3
"""Lock PBP denominators used by the Clock-Play red-zone experiment."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping

TRAIN_SEASONS = tuple(range(2013, 2024))
CORE_PLAY_TYPES = frozenset({"pass", "run", "field_goal", "punt"})


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_one(value: Any) -> bool:
    return _number(value) == 1.0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pbp", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    games: set[str] = set()
    basic_drives: set[tuple[str, int]] = set()
    red_zone_drives: set[tuple[str, int]] = set()
    goal_to_go_drives: set[tuple[str, int]] = set()
    offensive_td_drives: set[tuple[str, int]] = set()
    offensive_td_count = 0
    ot_drives: set[tuple[str, int]] = set()
    final_quarter_by_drive: dict[tuple[str, int], int] = {}

    with args.pbp.open(encoding="utf-8") as handle:
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
            drive = _number(payload.get("fixed_drive"))
            if not game_id or drive is None:
                continue
            games.add(game_id)
            key = (game_id, int(drive))
            play_type = payload.get("play_type")
            basic_core = play_type in CORE_PLAY_TYPES
            state_core = basic_core or (
                play_type == "no_play"
                and (_is_one(payload.get("pass")) or _is_one(payload.get("rush")))
            )
            if basic_core:
                basic_drives.add(key)
            quarter = _number(payload.get("qtr"))
            if quarter is not None:
                final_quarter_by_drive[key] = max(
                    int(quarter), final_quarter_by_drive.get(key, 0)
                )
                if basic_core and quarter > 4:
                    ot_drives.add(key)
            yardline_100 = _number(payload.get("yardline_100"))
            if state_core and yardline_100 is not None and yardline_100 <= 20:
                red_zone_drives.add(key)
            if state_core and _is_one(payload.get("goal_to_go")):
                goal_to_go_drives.add(key)
            offensive_td = _is_one(payload.get("touchdown")) and (
                payload.get("td_team") == payload.get("posteam")
            )
            if offensive_td:
                offensive_td_count += 1
                offensive_td_drives.add(key)

    n_games = len(games)
    red_zone_td_drives = red_zone_drives & offensive_td_drives
    goal_to_go_td_drives = goal_to_go_drives & offensive_td_drives
    end_half_or_game_drives = sum(
        quarter in {2, 4} for key, quarter in final_quarter_by_drive.items() if key in basic_drives
    )
    payload = {
        "artifact_id": "Clock-Play Red-Zone Historical Denominator Receipt",
        "train_seasons": list(TRAIN_SEASONS),
        "season_type": "REG",
        "historical_source": args.pbp.as_posix(),
        "metric_definitions": {
            "games": "unique game_id in train REG PBP",
            "offensive_td": "every PBP row where touchdown == 1 and td_team == posteam",
            "drive": "unique (game_id, fixed_drive) with pass/run/field_goal/punt core play",
            "red_zone_entry": "unique fixed_drive with an in-drive core or nullified pass/rush state at yardline_100 <= 20",
            "goal_to_go_entry": "unique fixed_drive with an in-drive core or nullified pass/rush state where goal_to_go == 1",
            "td_per_entry": "offensive TD on any PBP row in a drive that entered the named state",
            "ot": "core drive with qtr > 4; included in all drive state denominators",
            "kickoff_first_snap": "kickoff rows are excluded; a drive is counted only upon its first core snap",
            "end_half_game": "core drive whose final observed core quarter is 2 or 4 remains counted",
        },
        "counts": {
            "games": n_games,
            "offensive_touchdowns": offensive_td_count,
            "core_drives": len(basic_drives),
            "red_zone_entry_drives": len(red_zone_drives),
            "red_zone_td_drives": len(red_zone_td_drives),
            "goal_to_go_entry_drives": len(goal_to_go_drives),
            "goal_to_go_td_drives": len(goal_to_go_td_drives),
            "ot_core_drives": len(ot_drives),
            "end_half_or_game_core_drives": end_half_or_game_drives,
        },
        "rates": {
            "offensive_td_per_game": offensive_td_count / n_games,
            "drives_per_game": len(basic_drives) / n_games,
            "red_zone_entries_per_game": len(red_zone_drives) / n_games,
            "td_per_red_zone_entry": len(red_zone_td_drives) / len(red_zone_drives),
            "goal_to_go_entries_per_game": len(goal_to_go_drives) / n_games,
            "td_per_goal_to_go_entry": len(goal_to_go_td_drives) / len(goal_to_go_drives),
            "ot_core_drives_per_game": len(ot_drives) / n_games,
            "end_half_or_game_core_drives_per_game": end_half_or_game_drives / n_games,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
