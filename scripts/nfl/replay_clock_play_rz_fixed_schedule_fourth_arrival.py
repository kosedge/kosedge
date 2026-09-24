#!/usr/bin/env python3
"""Fixed-schedule RZ drive replay isolating fourth-down arrival (instrument only).

Parent candidate `a3a8e5b2f` possession boundaries and snap order are frozen.
The replay re-walks each parent red-zone drive on its recorded pre-snap
schedule and attributes fourth-down arrival. A counterfactual arm replaces only
generic red-zone pass outcomes with train-only bucket stall draws while keeping
rush transitions, pre-entry continuations, and fourth-down decisions on the
parent path.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.nfl_clock_play_simulator import (  # noqa: E402
    ClockPlayConfig,
    ClockPlayGameInputs,
    ClockPlayTeamInput,
    derive_replicate_seed,
    rz_goal_to_go,
    rz_rush_state_key,
    simulate_clock_play_game,
)

TRAIN_SEASONS = frozenset(range(2013, 2024))


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _engine_config(config_payload: Mapping[str, Any]) -> dict[str, Any]:
    engine = dict(config_payload.get("engine_config") or {})
    for config_key, engine_key in (
        ("fourth_down_continuation_priors_path", "fourth_down_continuation_priors"),
        ("clock_flow_priors_path", "clock_flow_priors"),
        ("red_zone_rush_transition_priors_path", "red_zone_rush_transition_priors"),
        ("red_zone_pass_transition_priors_path", "red_zone_pass_transition_priors"),
        ("red_zone_generic_pass_incompletion_priors_path", "red_zone_generic_pass_incompletion_priors"),
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


def _offensive_yardline(payload: Mapping[str, Any]) -> int | None:
    yardline_100 = _number(payload.get("yardline_100"))
    if yardline_100 is None:
        return None
    return max(1, min(99, int(round(100 - yardline_100))))


def _is_pass_play_type(play_type: str) -> bool:
    return play_type in {"pass", "red_zone_pass_transition"} or play_type.startswith(
        "pre_entry_pass_rz_pass"
    )


def _classify_snap(play_type: str) -> str:
    if play_type.startswith("pre_entry_pass_rz"):
        return "pre_entry"
    if play_type == "red_zone_rush_transition":
        return "rz_rush_transition"
    if play_type == "pass" or play_type == "red_zone_pass_transition":
        return "generic_pass_rz"
    if play_type == "run":
        return "generic_run_rz"
    return "other"


@dataclass
class SnapRecord:
    pre_yardline: int
    pre_down: int
    pre_distance: int
    route: str
    touchdown: bool
    yards: int
    incomplete: bool
    transition_bucket: str | None = None
    sim_outcome: str | None = None
    post_yardline: int | None = None
    post_down: int | None = None
    post_distance: int | None = None


@dataclass
class RzDrive:
    snaps: list[SnapRecord] = field(default_factory=list)
    reached_fourth: bool = False
    fourth_fg: bool = False
    terminal: str = "open"
    terminating_route: str | None = None


def _pre_state_from_scrimmage(event: Mapping[str, Any]) -> tuple[int, int, int]:
    state = event.get("state") or {}
    post_yardline = int(state.get("yardline") or 1)
    down = int(state.get("down") or 1)
    distance = int(state.get("distance") or 10)
    yards = int(event.get("yards") or 0)
    touchdown = bool(event.get("touchdown"))
    if touchdown:
        return post_yardline, down, distance
    pre_yardline = max(1, min(99, post_yardline - yards))
    pre_down = max(1, down - 1) if down > 1 else 1
    if yards >= distance and not touchdown:
        pre_down = down
        if down > 1:
            pre_down = down - 1
    # Reconstruct pre-down from post when not first down gained
    if not touchdown and yards < distance:
        pre_down = down - 1 if down > 1 else 1
    else:
        if yards >= distance:
            pre_down = down if down > 1 else 1
    pre_distance = distance
    if not touchdown:
        if yards >= distance:
            pre_distance = max(yards, distance)
        else:
            pre_distance = distance + yards if down > 1 else distance
    return pre_yardline, max(1, pre_down), max(1, pre_distance)


def _post_state_from_event(state: Mapping[str, Any]) -> tuple[int, int, int]:
    return (
        int(state.get("yardline") or 1),
        int(state.get("down") or 1),
        int(state.get("distance") or 10),
    )


@dataclass
class EventChainWalkResult:
    reached_fourth: bool = False
    td_before_fourth: bool = False
    terminal: str = "open"


def walk_parent_event_chain(drive: RzDrive) -> EventChainWalkResult:
    """Follow parent post-states on frozen snaps; fourth from parser events.

    Snap ``post_*`` fields thread state for counterfactual edits. Reach-fourth
    follows ``drive.reached_fourth`` (``fourth_down_decision``), not
    ``post_down >= 4`` alone, so parent walk matches the event parser.
    """

    result = EventChainWalkResult()
    if not drive.snaps:
        result.terminal = "empty"
        return result

    for snap in drive.snaps:
        if snap.touchdown:
            result.reached_fourth = bool(drive.reached_fourth)
            result.td_before_fourth = not drive.reached_fourth
            result.terminal = "touchdown"
            return result

    result.reached_fourth = bool(drive.reached_fourth)
    if drive.reached_fourth:
        result.terminal = str(drive.terminal or "fourth_down")
        return result
    if drive.terminal and drive.terminal != "open":
        result.terminal = str(drive.terminal)
        return result
    result.terminal = "drive_end"
    return result


def _parse_rz_drives(events: Iterable[Mapping[str, Any]]) -> list[RzDrive]:
    drives: list[RzDrive] = []
    current: RzDrive | None = None
    in_possession = False
    pending_rz_rush: Mapping[str, Any] | None = None

    for event in events:
        event_type = str(event.get("event_type") or "")
        state = event.get("state") or {}
        yardline = int(state.get("yardline") or 0)

        if event_type == "possession_start":
            in_possession = True
            current = None
            continue
        if event_type in {"punt", "kickoff"} and in_possession:
            if current is not None and current.terminal == "open":
                current.terminal = "possession_change"
            current = None
            continue

        if event_type == "incomplete_pass":
            if current is None and yardline >= 80:
                current = RzDrive()
                drives.append(current)
            if current is not None:
                pre_down = int(state.get("down") or 1)
                pre_distance = int(state.get("distance") or 10)
                pre_yardline = int(state.get("yardline") or yardline)
                post_down = min(4, pre_down + 1)
                current.snaps.append(
                    SnapRecord(
                        pre_yardline=pre_yardline,
                        pre_down=pre_down,
                        pre_distance=pre_distance,
                        route="generic_pass_rz",
                        touchdown=False,
                        yards=0,
                        incomplete=True,
                        post_yardline=pre_yardline,
                        post_down=post_down,
                        post_distance=pre_distance,
                    )
                )
            continue

        if event_type == "red_zone_rush_transition":
            pending_rz_rush = {
                "outcome": event.get("outcome"),
                "state": event.get("state") or {},
                "transition_bucket": event.get("transition_bucket"),
            }
            continue

        if event_type == "scrimmage_play":
            play_type = str(event.get("play_type") or "")
            if play_type == "red_zone_rush_transition" and pending_rz_rush is not None:
                pre_state = pending_rz_rush.get("state") or {}
                pre_y = int(pre_state.get("yardline") or 1)
                pre_d = int(pre_state.get("down") or 1)
                pre_dist = int(pre_state.get("distance") or 10)
                transition_bucket = pending_rz_rush.get("transition_bucket")
                sim_outcome = pending_rz_rush.get("outcome")
                pending_rz_rush = None
            else:
                pre_y, pre_d, pre_dist = _pre_state_from_scrimmage(event)
                transition_bucket = None
                sim_outcome = None
            if pre_y < 80 and yardline < 80:
                if current is not None and current.terminal == "open":
                    current.terminal = "left_rz"
                current = None
                continue
            if pre_y >= 80 or yardline >= 80:
                if current is None:
                    current = RzDrive()
                    drives.append(current)
                route = _classify_snap(play_type)
                post_y, post_d, post_dist = _post_state_from_event(state)
                snap = SnapRecord(
                    pre_yardline=pre_y if pre_y >= 80 else yardline,
                    pre_down=pre_d,
                    pre_distance=pre_dist,
                    route=route,
                    touchdown=bool(event.get("touchdown")),
                    yards=int(event.get("yards") or 0),
                    incomplete=False,
                    transition_bucket=(
                        str(transition_bucket) if transition_bucket is not None else None
                    ),
                    sim_outcome=str(sim_outcome) if sim_outcome is not None else None,
                    post_yardline=post_y,
                    post_down=post_d,
                    post_distance=post_dist,
                )
                current.snaps.append(snap)
                if snap.touchdown:
                    current.terminal = "touchdown"
                    current.terminating_route = route
                continue

        if event_type == "fourth_down_decision" and yardline >= 80:
            if current is None:
                current = RzDrive()
                drives.append(current)
            current.reached_fourth = True
            decision = str(event.get("decision") or "")
            if decision == "field_goal":
                current.fourth_fg = True
                current.terminal = "field_goal"
            elif decision == "go":
                current.terminal = "fourth_go"
            else:
                current.terminal = "fourth_punt"
            continue

        if event_type == "turnover" and current is not None and current.terminal == "open":
            current.terminal = "turnover"
        if event_type == "turnover_on_downs" and current is not None:
            current.terminal = "turnover_on_downs"

    for drive in drives:
        if drive.terminal == "open" and drive.snaps:
            drive.terminal = "open_drive_end"
        if not drive.reached_fourth and drive.terminating_route is None and drive.snaps:
            last = drive.snaps[-1]
            if drive.terminal in {"open", "open_drive_end", "left_rz", "possession_change"}:
                drive.terminating_route = last.route
    return drives


@dataclass
class StallBucket:
    incomplete: int = 0
    touchdown: int = 0
    first_down: int = 0
    short: int = 0
    n: int = 0

    def add(self, outcome: str) -> None:
        self.n += 1
        if outcome == "incomplete":
            self.incomplete += 1
        elif outcome == "touchdown":
            self.touchdown += 1
        elif outcome == "first_down":
            self.first_down += 1
        else:
            self.short += 1


def _train_generic_pass_stalls(pbp: Path) -> dict[str, StallBucket]:
    buckets: dict[str, StallBucket] = defaultdict(StallBucket)
    drive_seen: dict[tuple[str, int, str], bool] = {}
    active_crossing: dict[tuple[str, int, str], bool] = {}

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
            drive = _number(payload.get("fixed_drive"))
            posteam = str(payload.get("posteam") or "")
            if not game_id or drive is None or not posteam:
                continue
            key = (game_id, int(drive), posteam)
            yardline = _offensive_yardline(payload)
            if yardline is None:
                continue
            if yardline >= 80 and not drive_seen.get(key, False):
                drive_seen[key] = True
                first_rz = True
            else:
                first_rz = False
            if payload.get("play_type") != "pass" or int(_number(payload.get("down")) or 0) >= 4:
                if yardline is not None and 70 <= yardline <= 79 and payload.get("play_type") == "pass":
                    active_crossing[key] = True
                elif payload.get("play_type") in {"pass", "run"}:
                    active_crossing[key] = False
                continue
            if yardline < 80 or yardline > 99:
                continue
            owned = first_rz and active_crossing.get(key, False)
            if owned:
                active_crossing[key] = False
                continue
            down = max(1, int(_number(payload.get("down")) or 1))
            distance = max(1, int(_number(payload.get("ydstogo")) or 10))
            yards = int(_number(payload.get("yards_gained")) or 0)
            bucket_key = rz_rush_state_key(
                yardline=yardline,
                down=down,
                distance=distance,
                goal_to_go=rz_goal_to_go(yardline, distance),
            )
            if _number(payload.get("incomplete_pass")) == 1.0:
                outcome = "incomplete"
            elif _number(payload.get("touchdown")) == 1.0:
                outcome = "touchdown"
            elif _number(payload.get("first_down")) == 1.0 or yards >= distance:
                outcome = "first_down"
            else:
                outcome = "short"
            buckets[bucket_key].add(outcome)
            if yardline >= 80:
                drive_seen[key] = True
            if yardline is not None and 70 <= yardline <= 79:
                active_crossing[key] = True
            elif payload.get("play_type") in {"pass", "run"}:
                active_crossing[key] = False
    return dict(buckets)


def _advance_state(
    yardline: int, down: int, distance: int, outcome: str, yards: int
) -> tuple[int, int, int, bool]:
    if outcome == "touchdown":
        return yardline, down, distance, True
    if outcome == "incomplete":
        return yardline, min(4, down + 1), distance, False
    if outcome == "first_down" or yards >= distance:
        new_yardline = min(99, yardline + max(yards, distance))
        return new_yardline, 1, min(10, 100 - new_yardline), False
    new_yardline = min(99, max(1, yardline + yards))
    return new_yardline, min(4, down + 1), max(1, distance - yards), False


def _counterfactual_reach_fourth(
    drive: RzDrive, stalls: Mapping[str, StallBucket], rng: random.Random
) -> bool:
    if not drive.snaps:
        return False
    first = drive.snaps[0]
    yardline, down, distance = first.pre_yardline, first.pre_down, first.pre_distance
    for snap in drive.snaps:
        yardline, down, distance = snap.pre_yardline, snap.pre_down, snap.pre_distance
        if snap.route == "generic_pass_rz":
            bucket = stalls.get(
                rz_rush_state_key(
                    yardline=yardline,
                    down=down,
                    distance=distance,
                    goal_to_go=rz_goal_to_go(yardline, distance),
                )
            )
            if bucket is None or bucket.n == 0:
                bucket = StallBucket(incomplete=1, n=1)
            draw = rng.random() * bucket.n
            cumulative = 0.0
            outcome = "short"
            for name, count in (
                ("incomplete", bucket.incomplete),
                ("touchdown", bucket.touchdown),
                ("first_down", bucket.first_down),
                ("short", bucket.short),
            ):
                cumulative += count
                if draw <= cumulative:
                    outcome = name
                    break
            yards = 0 if outcome == "incomplete" else max(1, min(6, distance - 1))
            yardline, down, distance, td = _advance_state(
                yardline, down, distance, outcome, yards
            )
            if td:
                return False
            if down >= 4:
                return True
            continue
        if snap.touchdown:
            return False
        yardline, down, distance, _ = _advance_state(
            yardline, down, distance, "first_down" if snap.yards >= distance else "short", snap.yards
        )
        if down >= 4:
            return True
    return False


def _summarize_drives(drives: list[RzDrive]) -> dict[str, Any]:
    entries = len(drives)
    reached = sum(1 for drive in drives if drive.reached_fourth)
    fg_exit = sum(1 for drive in drives if drive.fourth_fg)
    terminal = Counter(drive.terminal for drive in drives)
    terminate_route = Counter(
        route
        for drive in drives
        if not drive.reached_fourth
        for route in ([drive.terminating_route] if drive.terminating_route else [])
    )
    return {
        "rz_entries": entries,
        "reached_fourth": reached,
        "reached_fourth_rate": reached / entries if entries else 0.0,
        "fg_exit_rate": fg_exit / entries if entries else 0.0,
        "terminal_mix": dict(terminal),
        "terminate_before_fourth_route": dict(terminate_route),
    }


def _historical_drives(pbp: Path) -> dict[str, Any]:
    drives: list[RzDrive] = []
    active: dict[tuple[str, int, str], RzDrive | None] = {}
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
            drive_n = _number(payload.get("fixed_drive"))
            posteam = str(payload.get("posteam") or "")
            if not game_id or drive_n is None or not posteam:
                continue
            key = (game_id, int(drive_n), posteam)
            yardline = _offensive_yardline(payload)
            if yardline is None:
                continue
            if yardline >= 80 and active.get(key) is None:
                rz = RzDrive()
                active[key] = rz
                drives.append(rz)
            rz = active.get(key)
            if rz is None:
                continue
            down = int(_number(payload.get("down")) or 1)
            if down == 4 and yardline >= 80:
                rz.reached_fourth = True
                play_type = str(payload.get("play_type") or "")
                if play_type == "field_goal":
                    rz.fourth_fg = True
                    rz.terminal = "field_goal"
                elif play_type == "punt":
                    rz.terminal = "fourth_punt"
                else:
                    rz.terminal = "fourth_go"
                active[key] = None
                continue
            if (
                _number(payload.get("touchdown")) == 1.0
                and payload.get("td_team") == posteam
            ):
                rz.terminal = "touchdown"
                rz.terminating_route = (
                    "pass" if payload.get("play_type") == "pass" else "run"
                )
                active[key] = None
    return _summarize_drives(drives)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--historical-pbp", type=Path, required=True)
    parser.add_argument("--games-per-case", type=int, default=128)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-sha", type=str, required=True)
    parser.add_argument(
        "--skip-counterfactual",
        action="store_true",
        help="Skip train-stall counterfactual arm (faster instrument pass)",
    )
    args = parser.parse_args()

    config_payload = _load_json(args.config.resolve())
    inputs_payload = _load_json(args.inputs.resolve())
    config = ClockPlayConfig.from_mapping(_engine_config(config_payload))
    stalls: dict[str, StallBucket] = {}
    if not args.skip_counterfactual:
        stalls = _train_generic_pass_stalls(args.historical_pbp.resolve())

    parent_drives: list[RzDrive] = []
    counterfactual_hits = 0
    rng = random.Random(114729)

    for case in inputs_payload.get("cases") or []:
        game = _as_game(case)
        for index in range(args.games_per_case):
            seed = derive_replicate_seed(
                int(config_payload["freeze_run"]["root_seeds"][case["case_id"]]),
                case["case_id"],
                index,
            )
            result = simulate_clock_play_game(
                game, seed=seed, config=config, collect_events=True
            )
            drives = _parse_rz_drives(result.get("events") or [])
            parent_drives.extend(drives)
            if not args.skip_counterfactual:
                for drive in drives:
                    if _counterfactual_reach_fourth(drive, stalls, rng):
                        counterfactual_hits += 1

    historical = _historical_drives(args.historical_pbp.resolve())
    parent_summary = _summarize_drives(parent_drives)
    if not args.skip_counterfactual:
        parent_summary["counterfactual_reach_fourth_rate"] = (
            counterfactual_hits / parent_summary["rz_entries"]
            if parent_summary["rz_entries"]
            else 0.0
        )

    payload = {
        "artifact_id": str(config_payload.get("artifact_id")),
        "contract": {
            "frozen": [
                "possession boundaries",
                "parent snap schedule per RZ drive",
                "rush transition outcomes",
                "pre-entry continuations",
                "fourth-down decision policy",
            ],
            "counterfactual": (
                "generic red-zone pass snaps re-drawn from train stall buckets only"
            ),
        },
        "historical_train": historical,
        "parent_simulation": parent_summary,
        "source_sha": args.source_sha,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
