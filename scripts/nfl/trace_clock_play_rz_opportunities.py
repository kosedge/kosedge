#!/usr/bin/env python3
"""Trace train-only red-zone opportunity volume in Clock-Play replays.

This diagnostic is intentionally isolated from the production simulator.  It
replays the committed synthetic cases with the committed seed manifest, then
compares their red-zone opportunity chain to 2013-23 regular-season PBP:

* first red-zone opportunity in a possession, classified by its entry origin;
* state / route mix for each red-zone snap;
* first downs and fourth-down arrivals; and
* offensive touchdown and field-goal exits.

The trace changes no simulation decision.  Its receipt makes the pre-change
candidate, input seed schedule, and historical source explicit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
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
    rz_rush_state_key,
    simulate_clock_play_game,
)

TRAIN_SEASONS = frozenset(range(2013, 2024))
FOURTH_DOWN_CORE_PLAY_TYPES = frozenset(
    {"pass", "run", "qb_kneel", "qb_spike", "field_goal", "punt"}
)


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if numeric == numeric else None


def _is_one(value: Any) -> bool:
    return _number(value) == 1.0


def _is_offensive_touchdown(payload: Mapping[str, Any]) -> bool:
    return _is_one(payload.get("touchdown")) and payload.get("td_team") == payload.get(
        "posteam"
    )


def _is_pass_call(payload: Mapping[str, Any]) -> bool:
    return (
        not _is_one(payload.get("two_point_attempt"))
        and not _is_one(payload.get("qb_spike"))
        and (
            payload.get("play_type") == "pass" or _is_one(payload.get("qb_scramble"))
        )
    )


def _is_rush_call(payload: Mapping[str, Any]) -> bool:
    return (
        payload.get("play_type") == "run"
        and not _is_one(payload.get("two_point_attempt"))
        and not _is_one(payload.get("qb_scramble"))
        and not _is_one(payload.get("qb_kneel"))
        and not _is_one(payload.get("qb_spike"))
    )


def _route_for_historical_play(payload: Mapping[str, Any]) -> str | None:
    down = _number(payload.get("down"))
    play_type = payload.get("play_type")
    if down == 4:
        if play_type not in FOURTH_DOWN_CORE_PLAY_TYPES:
            return None
        if play_type == "field_goal":
            return "field_goal"
        if play_type == "punt":
            return "punt"
        return "fourth_down_go"
    if _is_pass_call(payload):
        return "pass"
    if _is_rush_call(payload):
        return "red_zone_rush"
    return None


def _historical_last_route(payload: Mapping[str, Any]) -> str | None:
    route = _route_for_historical_play(payload)
    if route == "red_zone_rush":
        return "designed_rush"
    return route


def _field_goal_exit(payload: Mapping[str, Any]) -> str:
    result = str(payload.get("field_goal_result") or "unknown").lower()
    if result == "made":
        return "made"
    if result == "blocked" or _is_one(payload.get("blocked_field_goal")):
        return "blocked"
    return "missed_or_other"


def _historical_transition(
    payload: Mapping[str, Any], *, route: str, distance: int
) -> str:
    """Classify one resolved RZ route without following later drive rows."""

    if route == "pass":
        if _is_one(payload.get("interception")):
            return "interception"
        if _is_one(payload.get("fumble_lost")):
            return "fumble"
        if _is_one(payload.get("sack")):
            return "sack"
        if _is_one(payload.get("qb_scramble")):
            return "scramble"
        if _is_one(payload.get("incomplete_pass")):
            return "incompletion"
        if _is_offensive_touchdown(payload):
            return "touchdown"
        if _is_one(payload.get("first_down")) or (
            (_number(payload.get("yards_gained")) or 0.0) >= distance
        ):
            return "first_down"
        return "advance"
    if route == "red_zone_rush":
        if _is_offensive_touchdown(payload):
            return "touchdown"
        if _is_one(payload.get("fumble_lost")) or _is_one(payload.get("interception")):
            return "turnover"
        yards = int(round(_number(payload.get("yards_gained")) or 0.0))
        if _is_one(payload.get("first_down")) or yards >= distance:
            return "first_down"
        if yards < 0:
            return "loss"
        if yards == 0:
            return "zero"
        if yards <= 2:
            return "one_two"
        return "short_gain"
    if route == "field_goal":
        return _field_goal_exit(payload)
    if route == "punt":
        if _is_one(payload.get("touchback")):
            return "touchback"
        if _is_one(payload.get("punt_fair_catch")) or _is_one(payload.get("fair_catch")):
            return "fair_catch"
        if any(
            _is_one(payload.get(field))
            for field in ("punt_downed", "punt_out_of_bounds", "punt_in_endzone")
        ):
            return "dead_ball"
        return "return"
    if route == "fourth_down_go":
        if _is_offensive_touchdown(payload):
            return "touchdown"
        if _is_one(payload.get("first_down")) or (
            (_number(payload.get("yards_gained")) or 0.0) >= distance
        ):
            return "converted"
        return "not_converted"
    return "unknown"


def _state_key(*, yardline: int, down: int, distance: int) -> str:
    return rz_rush_state_key(
        yardline=yardline,
        down=down,
        distance=distance,
        goal_to_go=distance >= 100 - yardline,
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _per_game(value: int | float, games: int) -> float:
    return float(value) / games if games else 0.0


def _count_table(counts: Counter[str], *, games: int, denominator: int) -> dict[str, Any]:
    return {
        key: {
            "count": int(value),
            "per_game": _per_game(value, games),
            "share": float(value) / denominator if denominator else 0.0,
        }
        for key, value in sorted(counts.items())
    }


@dataclass
class RzTraceCounts:
    games: int = 0
    entries: int = 0
    opportunities: int = 0
    first_downs: int = 0
    fourth_down_arrivals: int = 0
    touchdown_exits: int = 0
    field_goal_exits: int = 0
    entry_origins: Counter[str] = field(default_factory=Counter)
    routes: Counter[str] = field(default_factory=Counter)
    states: Counter[str] = field(default_factory=Counter)
    state_routes: Counter[str] = field(default_factory=Counter)
    entry_origin_routes: Counter[str] = field(default_factory=Counter)
    entry_origin_route_transitions: Counter[str] = field(default_factory=Counter)
    entry_crossing_starts: Counter[str] = field(default_factory=Counter)
    pre_entry_route_starts: Counter[str] = field(default_factory=Counter)
    field_goal_exit_types: Counter[str] = field(default_factory=Counter)

    def add_opportunity(
        self, *, entry_origin: str, state_key: str, route: str
    ) -> None:
        self.opportunities += 1
        self.routes[route] += 1
        self.states[state_key] += 1
        self.state_routes[f"{state_key}|{route}"] += 1
        self.entry_origin_routes[f"{entry_origin}|{route}"] += 1

    def add_transition(
        self, *, entry_origin: str, route: str, transition: str
    ) -> None:
        self.entry_origin_route_transitions[
            f"{entry_origin}|{route}|{transition}"
        ] += 1

    def summary(self) -> dict[str, Any]:
        games = self.games
        return {
            "games": games,
            "rz_entries": {
                "count": self.entries,
                "per_game": _per_game(self.entries, games),
            },
            "rz_opportunities": {
                "count": self.opportunities,
                "per_game": _per_game(self.opportunities, games),
            },
            "entry_origins": _count_table(
                self.entry_origins, games=games, denominator=self.entries
            ),
            "state_mix": _count_table(
                self.states, games=games, denominator=self.opportunities
            ),
            "route_mix": _count_table(
                self.routes, games=games, denominator=self.opportunities
            ),
            "state_route_mix": _count_table(
                self.state_routes, games=games, denominator=self.opportunities
            ),
            "entry_origin_route_mix": _count_table(
                self.entry_origin_routes, games=games, denominator=self.opportunities
            ),
            "entry_origin_route_transition_mix": _count_table(
                self.entry_origin_route_transitions,
                games=games,
                denominator=self.opportunities,
            ),
            "entry_crossing_start_mix": _count_table(
                self.entry_crossing_starts, games=games, denominator=self.entries
            ),
            "pre_entry_route_start_mix": _count_table(
                self.pre_entry_route_starts, games=games, denominator=games
            ),
            "entry_crossing_rates": self._crossing_rates(),
            "first_downs": {
                "count": self.first_downs,
                "per_game": _per_game(self.first_downs, games),
                "per_opportunity": (
                    self.first_downs / self.opportunities if self.opportunities else 0.0
                ),
            },
            "fourth_down_arrivals": {
                "count": self.fourth_down_arrivals,
                "per_game": _per_game(self.fourth_down_arrivals, games),
                "per_opportunity": (
                    self.fourth_down_arrivals / self.opportunities
                    if self.opportunities
                    else 0.0
                ),
            },
            "touchdown_exits": {
                "count": self.touchdown_exits,
                "per_game": _per_game(self.touchdown_exits, games),
                "per_opportunity": (
                    self.touchdown_exits / self.opportunities
                    if self.opportunities
                    else 0.0
                ),
            },
            "field_goal_exits": {
                "count": self.field_goal_exits,
                "per_game": _per_game(self.field_goal_exits, games),
                "per_opportunity": (
                    self.field_goal_exits / self.opportunities
                    if self.opportunities
                    else 0.0
                ),
                "by_result": _count_table(
                    self.field_goal_exit_types,
                    games=games,
                    denominator=self.field_goal_exits,
                ),
            },
        }

    def _crossing_rates(self) -> dict[str, Any]:
        rates: dict[str, Any] = {}
        for crossing_key, crossings in sorted(self.entry_crossing_starts.items()):
            origin, start_yardline = crossing_key.rsplit("|", 1)
            if not origin.startswith("crossed_by:"):
                continue
            route = origin.removeprefix("crossed_by:")
            starts = self.pre_entry_route_starts[f"{route}|{start_yardline}"]
            rates[crossing_key] = {
                "crossings": int(crossings),
                "starts": int(starts),
                "crossing_rate": float(crossings) / starts if starts else None,
            }
        return rates


def _as_game(raw: Mapping[str, Any]) -> ClockPlayGameInputs:
    return ClockPlayGameInputs(
        game_id=str(raw["case_id"]),
        home_team=str(raw["home_team"]),
        away_team=str(raw["away_team"]),
        home=ClockPlayTeamInput(**dict(raw["home"])),
        away=ClockPlayTeamInput(**dict(raw["away"])),
        regular_season=True,
    )


def _load_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"Expected a JSON object in {path}")
    return payload


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
        (
            "fourth_down_decision_priors_path",
            "fourth_down_decision_priors",
            "Fourth-down decision",
        ),
        ("pass_state_priors_path", "pass_state_priors", "Pass state"),
        (
            "called_play_state_priors_path",
            "called_play_state_priors",
            "Called-play state",
        ),
        (
            "designed_rush_state_priors_path",
            "designed_rush_state_priors",
            "Designed rush state",
        ),
        (
            "special_teams_state_priors_path",
            "special_teams_state_priors",
            "Special-teams state",
        ),
    ):
        raw_path = config_payload.get(config_key)
        if raw_path is None:
            continue
        priors_payload = _load_json_object(ROOT / str(raw_path))
        priors = priors_payload.get("priors")
        if not isinstance(priors, Mapping):
            raise SystemExit(f"{label} priors need a priors object")
        if label == "Pass state":
            priors = priors.get("pass")
        elif label == "Fourth-down decision":
            priors = priors.get("fourth_down_decision")
        elif label == "Called-play state":
            priors = priors.get("called_play")
        elif label == "Designed rush state":
            priors = priors.get("designed_rush")
        elif label == "Special-teams state":
            priors = priors.get("special_teams")
        if not isinstance(priors, Mapping):
            raise SystemExit(f"{label} priors need the expected state family")
        engine[engine_key] = dict(priors)
    return engine


def _trace_simulated_game(events: Iterable[Mapping[str, Any]], counts: RzTraceCounts) -> None:
    """Extract one replay's RZ chain from its non-mutating simulator events."""

    possession_start_yardline = 25
    possession_origin = "unknown"
    entry_origin = "unknown"
    last_route_start_yardline: int | None = None
    seen_rz_in_possession = False
    last_route: str | None = None
    active: dict[str, Any] | None = None

    def event_state(event: Mapping[str, Any]) -> Mapping[str, Any]:
        state = event.get("state")
        return state if isinstance(state, Mapping) else {}

    def start_opportunity(event: Mapping[str, Any], *, route: str | None) -> None:
        nonlocal active, entry_origin, seen_rz_in_possession
        state = event_state(event)
        yardline = int(_number(state.get("yardline")) or 0)
        down = int(_number(state.get("down")) or 0)
        distance = int(_number(state.get("distance")) or 1)
        if yardline < 80 or not 1 <= down <= 4:
            return
        key = _state_key(yardline=yardline, down=down, distance=distance)
        if not seen_rz_in_possession:
            counts.entries += 1
            if possession_start_yardline >= 80:
                entry_origin = f"possession_start:{possession_origin}"
            else:
                entry_origin = f"crossed_by:{last_route or 'unknown'}"
                counts.entry_crossing_starts[
                    f"{entry_origin}|{last_route_start_yardline or 'unknown'}"
                ] += 1
            counts.entry_origins[entry_origin] += 1
            seen_rz_in_possession = True
        if down == 4:
            counts.fourth_down_arrivals += 1
        active = {
            "play_count": int(_number(state.get("play_count")) or -1),
            "state_key": key,
            "route": route,
            "first_down_recorded": False,
            "exit_recorded": False,
            "transition_recorded": False,
        }
        if route is not None:
            counts.add_opportunity(
                entry_origin=entry_origin, state_key=key, route=route
            )

    def set_active_route(route: str) -> None:
        nonlocal last_route, last_route_start_yardline
        last_route = route
        if active is None or active.get("route") is not None:
            return
        active["route"] = route
        counts.add_opportunity(
            entry_origin=entry_origin,
            state_key=str(active["state_key"]),
            route=route,
        )

    def set_active_transition(transition: str) -> None:
        if (
            active is None
            or active.get("route") is None
            or bool(active.get("transition_recorded"))
        ):
            return
        counts.add_transition(
            entry_origin=entry_origin,
            route=str(active["route"]),
            transition=transition,
        )
        active["transition_recorded"] = True

    for event in events:
        event_type = str(event.get("event_type") or "")
        state = event_state(event)
        if event_type == "possession_start":
            possession_start_yardline = int(_number(state.get("yardline")) or 25)
            possession_origin = str(event.get("reason") or "unknown")
            seen_rz_in_possession = False
            entry_origin = "unknown"
            last_route_start_yardline = None
            last_route = None
            active = None
            continue

        if event_type == "play_call":
            family = str(event.get("family") or "")
            start_opportunity(event, route="pass" if family == "pass" else None)
            start_yardline = int(_number(state.get("yardline")) or 0)
            route = "pass" if family == "pass" else "designed_rush"
            if 1 <= start_yardline < 80:
                counts.pre_entry_route_starts[f"{route}|{start_yardline}"] += 1
            if family == "pass":
                last_route = "pass"
                last_route_start_yardline = start_yardline
            elif family == "rush":
                last_route = "designed_rush"
                last_route_start_yardline = start_yardline
            continue

        if event_type == "fourth_down_decision":
            decision = str(event.get("decision") or "")
            route = {
                "field_goal": "field_goal",
                "punt": "punt",
                "go": "fourth_down_go",
            }.get(decision)
            start_opportunity(event, route=route)
            if route is not None:
                last_route = route
                start_yardline = int(_number(state.get("yardline")) or 0)
                last_route_start_yardline = start_yardline
                if 1 <= start_yardline < 80:
                    counts.pre_entry_route_starts[f"{route}|{start_yardline}"] += 1
            continue

        if event_type == "late_field_goal_decision":
            start_opportunity(event, route="field_goal")
            last_route = "field_goal"
            last_route_start_yardline = int(_number(state.get("yardline")) or 0)
            continue

        if event_type == "red_zone_rush_transition":
            set_active_route("red_zone_rush")
            last_route = "red_zone_rush"
            last_route_start_yardline = int(_number(state.get("yardline")) or 0)
            set_active_transition(str(event.get("outcome") or "unknown"))
            continue

        if event_type == "designed_rush_attempt":
            set_active_route("designed_rush")
            last_route = "designed_rush"
            last_route_start_yardline = int(_number(state.get("yardline")) or 0)
            set_active_transition(str(event.get("outcome") or "unknown"))
            continue

        if active is None:
            continue
        current_play_count = int(_number(state.get("play_count")) or -2)
        if current_play_count != active["play_count"]:
            continue

        if event_type == "pass_attempt":
            set_active_transition(str(event.get("outcome") or "unknown"))
            continue

        if event_type == "punt":
            set_active_transition(str(event.get("outcome") or "unknown"))
            continue

        if event_type == "scrimmage_play":
            if active.get("route") is None:
                inferred = str(event.get("route") or event.get("play_type") or "")
                if inferred:
                    set_active_route(inferred)
            if active.get("route") == "fourth_down_go":
                if bool(event.get("touchdown")):
                    set_active_transition("touchdown")
                elif int(_number(event.get("yards")) or 0) >= int(
                    _number(state.get("distance")) or 1
                ):
                    set_active_transition("converted")
                else:
                    set_active_transition("advance")
            if (
                not bool(event.get("touchdown"))
                and int(_number(state.get("down")) or 0) == 1
                and not active["first_down_recorded"]
            ):
                counts.first_downs += 1
                active["first_down_recorded"] = True
            continue

        if event_type == "touchdown" and not active["exit_recorded"]:
            counts.touchdown_exits += 1
            active["exit_recorded"] = True
            continue

        if event_type in {"field_goal_made", "field_goal_missed", "field_goal_blocked"}:
            set_active_transition(
                {
                    "field_goal_made": "made",
                    "field_goal_missed": "missed_or_other",
                    "field_goal_blocked": "blocked",
                }[event_type]
            )
            if not active["exit_recorded"]:
                counts.field_goal_exits += 1
                exit_type = {
                    "field_goal_made": "made",
                    "field_goal_missed": "missed_or_other",
                    "field_goal_blocked": "blocked",
                }[event_type]
                counts.field_goal_exit_types[exit_type] += 1
                active["exit_recorded"] = True


def _simulated_trace(
    *,
    config: ClockPlayConfig,
    cases: Iterable[Mapping[str, Any]],
    root_seeds: Mapping[str, Any],
    replicates: int,
) -> RzTraceCounts:
    counts = RzTraceCounts()
    for raw_case in cases:
        game = _as_game(raw_case)
        case_id = game.game_id
        if case_id not in root_seeds:
            raise SystemExit(f"Missing root seed for case {case_id!r}")
        for replicate_index in range(replicates):
            result = simulate_clock_play_game(
                game,
                seed=derive_replicate_seed(
                    int(root_seeds[case_id]), case_id, replicate_index
                ),
                config=config,
                collect_events=True,
            )
            _trace_simulated_game(result["events"], counts)
            counts.games += 1
    return counts


def _drive_start_inside_red_zone(payload: Mapping[str, Any]) -> bool:
    start = str(payload.get("drive_start_yard_line") or "").strip()
    posteam = str(payload.get("posteam") or "").strip()
    parts = start.split()
    if len(parts) != 2 or not posteam:
        return False
    try:
        marker = int(parts[1])
    except ValueError:
        return False
    return parts[0] != posteam and marker <= 20


def _historical_trace(pbp_path: Path) -> tuple[RzTraceCounts, str]:
    counts = RzTraceCounts()
    games: set[str] = set()
    drive_seen_rz: dict[tuple[str, str, str], bool] = {}
    drive_started_inside: dict[tuple[str, str, str], bool] = {}
    drive_start_origin: dict[tuple[str, str, str], str] = {}
    drive_last_route: dict[tuple[str, str, str], str | None] = {}
    drive_last_route_start_yardline: dict[tuple[str, str, str], int | None] = {}
    drive_entry_origin: dict[tuple[str, str, str], str] = {}
    digest = hashlib.sha256()

    with pbp_path.open("rb") as handle:
        for raw_line in handle:
            digest.update(raw_line)
            try:
                row = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"Invalid JSON in historical PBP: {exc}") from exc
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
            fixed_drive = _number(payload.get("fixed_drive"))
            posteam = str(payload.get("posteam") or "")
            if not game_id or fixed_drive is None or not posteam:
                continue
            drive_key = (game_id, str(int(fixed_drive)), posteam)
            if drive_key not in drive_seen_rz:
                drive_seen_rz[drive_key] = False
                drive_started_inside[drive_key] = _drive_start_inside_red_zone(payload)
                drive_start_origin[drive_key] = str(
                    payload.get("drive_start_transition") or "unknown"
                ).lower()
                drive_last_route[drive_key] = None
                drive_last_route_start_yardline[drive_key] = None
                drive_entry_origin[drive_key] = "unknown"

            yardline_100 = _number(payload.get("yardline_100"))
            play_yardline = (
                max(1, min(99, int(round(100 - yardline_100))))
                if yardline_100 is not None
                else None
            )
            down = _number(payload.get("down"))
            distance = _number(payload.get("ydstogo"))
            route = _route_for_historical_play(payload)
            if (
                route is not None
                and yardline_100 is not None
                and down is not None
                and distance is not None
                and yardline_100 <= 20
            ):
                yardline = max(80, min(99, int(round(100 - yardline_100))))
                down_int = int(round(down))
                distance_int = max(1, int(round(distance)))
                key = _state_key(
                    yardline=yardline, down=down_int, distance=distance_int
                )
                if not drive_seen_rz[drive_key]:
                    counts.entries += 1
                    if drive_started_inside[drive_key]:
                        origin = f"possession_start:{drive_start_origin[drive_key]}"
                    else:
                        origin = f"crossed_by:{drive_last_route[drive_key] or 'unknown'}"
                        counts.entry_crossing_starts[
                            f"{origin}|"
                            f"{drive_last_route_start_yardline[drive_key] or 'unknown'}"
                        ] += 1
                    counts.entry_origins[origin] += 1
                    drive_entry_origin[drive_key] = origin
                    drive_seen_rz[drive_key] = True
                entry_origin = drive_entry_origin[drive_key]
                counts.add_opportunity(
                    entry_origin=entry_origin, state_key=key, route=route
                )
                counts.add_transition(
                    entry_origin=entry_origin,
                    route=route,
                    transition=_historical_transition(
                        payload, route=route, distance=distance_int
                    ),
                )
                if down_int == 4:
                    counts.fourth_down_arrivals += 1
                if (
                    not _is_offensive_touchdown(payload)
                    and (
                        _is_one(payload.get("first_down"))
                        or (
                            _number(payload.get("yards_gained")) is not None
                            and _number(payload.get("yards_gained")) >= distance_int
                        )
                    )
                ):
                    counts.first_downs += 1
                if _is_offensive_touchdown(payload):
                    counts.touchdown_exits += 1
                if route == "field_goal":
                    counts.field_goal_exits += 1
                    counts.field_goal_exit_types[_field_goal_exit(payload)] += 1

            last_route = _historical_last_route(payload)
            if last_route is not None:
                drive_last_route[drive_key] = last_route
                drive_last_route_start_yardline[drive_key] = play_yardline
                if play_yardline is not None and play_yardline < 80:
                    counts.pre_entry_route_starts[
                        f"{last_route}|{play_yardline}"
                    ] += 1

    counts.games = len(games)
    return counts, digest.hexdigest()


def _compact_metrics(summary: Mapping[str, Any]) -> dict[str, float]:
    def per_game(name: str) -> float:
        section = summary.get(name)
        return float(section.get("per_game", 0.0)) if isinstance(section, Mapping) else 0.0

    return {
        "rz_entries_per_game": per_game("rz_entries"),
        "rz_opportunities_per_game": per_game("rz_opportunities"),
        "rz_first_downs_per_game": per_game("first_downs"),
        "rz_fourth_arrivals_per_game": per_game("fourth_down_arrivals"),
        "rz_touchdown_exits_per_game": per_game("touchdown_exits"),
        "rz_field_goal_exits_per_game": per_game("field_goal_exits"),
    }


def _comparison(
    historical: Mapping[str, Any], simulated: Mapping[str, Any]
) -> dict[str, Any]:
    historical_metrics = _compact_metrics(historical)
    simulated_metrics = _compact_metrics(simulated)
    return {
        metric: {
            "historical": historical_metrics[metric],
            "simulated": simulated_metrics[metric],
            "error": simulated_metrics[metric] - historical_metrics[metric],
            "ratio": (
                simulated_metrics[metric] / historical_metrics[metric]
                if historical_metrics[metric]
                else None
            ),
        }
        for metric in sorted(historical_metrics)
    }


def run(
    *,
    config_path: Path,
    inputs_path: Path,
    historical_pbp_path: Path,
    output_path: Path,
    source_sha: str,
) -> dict[str, Any]:
    config_payload = _load_json_object(config_path)
    inputs_payload = _load_json_object(inputs_path)
    run_spec = config_payload.get("freeze_run")
    if not isinstance(run_spec, Mapping):
        raise SystemExit("Config needs a freeze_run object")
    cases = inputs_payload.get("cases")
    root_seeds = run_spec.get("root_seeds")
    if not isinstance(cases, list) or not cases:
        raise SystemExit("Inputs need non-empty cases")
    if not isinstance(root_seeds, Mapping):
        raise SystemExit("Config needs root_seeds")
    if inputs_payload.get("held_out_data") is not False:
        raise SystemExit("Inputs must explicitly assert held_out_data=false")
    if inputs_payload.get("market_data") is not False:
        raise SystemExit("Inputs must explicitly assert market_data=false")
    if config_payload.get("scope", {}).get("held_out_data") is not False:
        raise SystemExit("Trace config must explicitly assert held_out_data=false")
    if config_payload.get("scope", {}).get("market_data") is not False:
        raise SystemExit("Trace config must explicitly assert market_data=false")

    replicates = int(run_spec.get("replicates_per_case", 0))
    if replicates < 1:
        raise SystemExit("replicates_per_case must be positive")
    engine_config = ClockPlayConfig.from_mapping(_engine_config(config_payload))
    simulated = _simulated_trace(
        config=engine_config,
        cases=cases,
        root_seeds=root_seeds,
        replicates=replicates,
    ).summary()
    historical_counts, historical_sha256 = _historical_trace(historical_pbp_path)
    historical = historical_counts.summary()
    lineage = config_payload.get("lineage")
    parent_source_sha = (
        str(lineage.get("parent_commit") or "").strip()
        if isinstance(lineage, Mapping)
        else ""
    )
    result = {
        "artifact_id": str(
            config_payload.get("artifact_id") or "Clock-Play RZ Opportunity Trace"
        ),
        "trace_contract": {
            "train_window": "2013-2023 regular season",
            "held_out_data": False,
            "market_data": False,
            "production_data": False,
            "route_scope": (
                "non-fourth selected pass/red-zone-rush routes plus fourth-down "
                "decision routes; no decision policy is changed"
            ),
        },
        "precode_receipt": {
            "source_sha": source_sha,
            "parent_source_sha": parent_source_sha or None,
            "candidate_config": {
                "path": config_path.as_posix(),
                "sha256": _sha256_file(config_path),
            },
            "synthetic_inputs": {
                "path": inputs_path.as_posix(),
                "sha256": _sha256_file(inputs_path),
                "held_out_data": False,
                "market_data": False,
            },
            "historical_pbp": {
                "path": historical_pbp_path.as_posix(),
                "sha256": historical_sha256,
                "seasons": "2013-2023 regular season",
            },
            "seed_schedule": {
                "case_count": len(cases),
                "replicates_per_case": replicates,
                "simulated_games": len(cases) * replicates,
                "root_seeds": dict(sorted(root_seeds.items())),
            },
        },
        "historical": historical,
        "simulated": simulated,
        "comparison": _comparison(historical, simulated),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Trace red-zone opportunity volume against train PBP"
    )
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--historical-pbp", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    args = parser.parse_args()
    result = run(
        config_path=args.config,
        inputs_path=args.inputs,
        historical_pbp_path=args.historical_pbp,
        output_path=args.output,
        source_sha=str(args.source_sha),
    )
    print(
        json.dumps(
            {
                "artifact_id": result["artifact_id"],
                "historical_games": result["historical"]["games"],
                "simulated_games": result["simulated"]["games"],
                "comparison": result["comparison"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
