from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "nfl" / "trace_clock_play_rz_opportunities.py"


def _trace_module():
    spec = importlib.util.spec_from_file_location("rz_opportunity_trace", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _state(*, yardline: int, down: int, distance: int, play_count: int) -> dict[str, int]:
    return {
        "yardline": yardline,
        "down": down,
        "distance": distance,
        "play_count": play_count,
    }


def test_simulated_trace_keeps_entry_route_first_down_and_exit_chain_separate() -> None:
    trace = _trace_module()
    counts = trace.RzTraceCounts()
    trace._trace_simulated_game(
        [
            {
                "event_type": "possession_start",
                "reason": "opening_kickoff",
                "state": _state(yardline=25, down=1, distance=10, play_count=0),
            },
            {
                "event_type": "play_call",
                "family": "pass",
                "state": _state(yardline=79, down=1, distance=2, play_count=1),
            },
            {
                "event_type": "scrimmage_play",
                "route": "pass",
                "touchdown": False,
                "state": _state(yardline=82, down=1, distance=10, play_count=1),
            },
            {
                "event_type": "play_call",
                "family": "rush",
                "state": _state(yardline=82, down=1, distance=10, play_count=2),
            },
            {
                "event_type": "red_zone_rush_transition",
                "state": _state(yardline=82, down=1, distance=10, play_count=2),
            },
            {
                "event_type": "scrimmage_play",
                "play_type": "red_zone_rush_transition",
                "touchdown": False,
                "state": _state(yardline=90, down=1, distance=10, play_count=2),
            },
            {
                "event_type": "fourth_down_decision",
                "decision": "field_goal",
                "state": _state(yardline=84, down=4, distance=4, play_count=3),
            },
            {
                "event_type": "field_goal_made",
                "state": _state(yardline=84, down=4, distance=4, play_count=3),
            },
        ],
        counts,
    )
    counts.games = 1
    summary = counts.summary()

    assert summary["rz_entries"]["count"] == 1
    assert summary["entry_origins"]["crossed_by:pass"]["count"] == 1
    assert summary["route_mix"]["red_zone_rush"]["count"] == 1
    assert summary["route_mix"]["field_goal"]["count"] == 1
    assert (
        summary["entry_origin_route_mix"]["crossed_by:pass|red_zone_rush"]["count"]
        == 1
    )
    assert (
        summary["entry_origin_route_transition_mix"][
            "crossed_by:pass|red_zone_rush|unknown"
        ]["count"]
        == 1
    )
    assert (
        summary["entry_origin_route_transition_mix"][
            "crossed_by:pass|field_goal|made"
        ]["count"]
        == 1
    )
    assert summary["first_downs"]["count"] == 1
    assert summary["fourth_down_arrivals"]["count"] == 1
    assert summary["field_goal_exits"]["by_result"]["made"]["count"] == 1


def test_historical_trace_uses_prior_play_for_entry_and_counts_only_train_seasons(
    tmp_path: Path,
) -> None:
    trace = _trace_module()
    pbp = tmp_path / "pbp.ndjson"
    rows = [
        {
            "object_type": "pbp_play",
            "payload": {
                "season": 2013,
                "season_type": "REG",
                "game_id": "2013_01_TEST",
                "fixed_drive": 1,
                "posteam": "HME",
                "drive_start_yard_line": "HME 25",
                "drive_start_transition": "KICKOFF",
                "play_type": "pass",
                "yardline_100": 21,
                "down": 1,
                "ydstogo": 2,
                "yards_gained": 3,
                "first_down": 1,
                "touchdown": 0,
            },
        },
        {
            "object_type": "pbp_play",
            "payload": {
                "season": 2013,
                "season_type": "REG",
                "game_id": "2013_01_TEST",
                "fixed_drive": 1,
                "posteam": "HME",
                "drive_start_yard_line": "HME 25",
                "drive_start_transition": "KICKOFF",
                "play_type": "run",
                "yardline_100": 18,
                "down": 1,
                "ydstogo": 10,
                "yards_gained": 8,
                "first_down": 0,
                "touchdown": 0,
                "qb_scramble": 0,
                "qb_kneel": 0,
                "qb_spike": 0,
                "two_point_attempt": 0,
            },
        },
        {
            "object_type": "pbp_play",
            "payload": {
                "season": 2013,
                "season_type": "REG",
                "game_id": "2013_01_TEST",
                "fixed_drive": 1,
                "posteam": "HME",
                "drive_start_yard_line": "HME 25",
                "drive_start_transition": "KICKOFF",
                "play_type": "field_goal",
                "yardline_100": 10,
                "down": 4,
                "ydstogo": 2,
                "yards_gained": 0,
                "first_down": 0,
                "touchdown": 0,
                "field_goal_result": "made",
            },
        },
        {
            "object_type": "pbp_play",
            "payload": {
                "season": 2024,
                "season_type": "REG",
                "game_id": "2024_01_HELD",
                "fixed_drive": 1,
                "posteam": "HME",
                "drive_start_yard_line": "AWY 10",
                "drive_start_transition": "INTERCEPTION",
                "play_type": "run",
                "yardline_100": 10,
                "down": 1,
                "ydstogo": 10,
                "yards_gained": 10,
                "first_down": 1,
                "touchdown": 1,
                "td_team": "HME",
            },
        },
    ]
    pbp.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )

    counts, source_sha256 = trace._historical_trace(pbp)
    summary = counts.summary()

    assert len(source_sha256) == 64
    assert summary["games"] == 1
    assert summary["rz_entries"]["count"] == 1
    assert summary["entry_origins"]["crossed_by:pass"]["count"] == 1
    assert summary["route_mix"]["red_zone_rush"]["count"] == 1
    assert summary["route_mix"]["field_goal"]["count"] == 1
    assert (
        summary["entry_origin_route_mix"]["crossed_by:pass|red_zone_rush"]["count"]
        == 1
    )
    assert (
        summary["entry_origin_route_transition_mix"][
            "crossed_by:pass|red_zone_rush|first_down"
        ]["count"]
        == 1
    )
    assert (
        summary["entry_origin_route_transition_mix"][
            "crossed_by:pass|field_goal|made"
        ]["count"]
        == 1
    )
    assert summary["field_goal_exits"]["by_result"]["made"]["count"] == 1


def test_simulated_trace_groups_pass_transition_by_possession_start_origin() -> None:
    trace = _trace_module()
    counts = trace.RzTraceCounts()
    trace._trace_simulated_game(
        [
            {
                "event_type": "possession_start",
                "reason": "interception_return",
                "state": _state(yardline=88, down=1, distance=10, play_count=0),
            },
            {
                "event_type": "play_call",
                "family": "pass",
                "state": _state(yardline=88, down=1, distance=10, play_count=1),
            },
            {
                "event_type": "pass_attempt",
                "outcome": "completion",
                "state": _state(yardline=88, down=1, distance=10, play_count=1),
            },
            {
                "event_type": "scrimmage_play",
                "route": "pass",
                "touchdown": False,
                "state": _state(yardline=92, down=2, distance=6, play_count=1),
            },
        ],
        counts,
    )
    counts.games = 1
    summary = counts.summary()

    assert (
        summary["entry_origin_route_mix"][
            "possession_start:interception_return|pass"
        ]["count"]
        == 1
    )
    assert (
        summary["entry_origin_route_transition_mix"][
            "possession_start:interception_return|pass|completion"
        ]["count"]
        == 1
    )
