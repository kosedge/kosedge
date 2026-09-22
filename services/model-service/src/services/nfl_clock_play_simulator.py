"""NFL Clock-Play Baseline v1 experimental state-loop simulator.

This module is intentionally isolated from production routes and the existing
Gaussian/snapshot simulators.  It models a game as a sequence of plays that
mutate possession, down, distance, field position, score, timeouts, and the
game clock.  Its structural priors are fixed in a versioned experiment config;
it accepts no market lines, actual outcomes, or calibration targets.

The committed kicker layer supplies the XP and banded field-goal priors.  It
is used only as a scoring component, never as a substitute for the temporal
state loop implemented here.
"""

from __future__ import annotations

import hashlib
import random
from collections import Counter
from dataclasses import asdict, dataclass, field
from typing import Any, Literal, Mapping, Optional

from src.services.nfl_season_engine.kicker_layer import (
    LEAGUE_FG_MAKE_RATE_BY_BAND,
    LEAGUE_XP_MAKE_RATE,
    TWO_POINT_ATTEMPT_RATE,
)

TeamSide = Literal["home", "away"]

DEFAULT_CLOCK_PLAY_MODEL_VERSION = "nfl-clock-play-v1.1-late-game-fourth-down-policy"
_OTHER_SIDE: dict[TeamSide, TeamSide] = {"home": "away", "away": "home"}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


@dataclass(frozen=True)
class ClockPlayTeamInput:
    """Synthetic or train-only team-strength inputs for one game path."""

    offense_rating: float = 1.0
    defense_rating: float = 1.0
    pace_factor: float = 1.0


@dataclass(frozen=True)
class ClockPlayGameInputs:
    game_id: str
    home_team: str
    away_team: str
    home: ClockPlayTeamInput = field(default_factory=ClockPlayTeamInput)
    away: ClockPlayTeamInput = field(default_factory=ClockPlayTeamInput)
    regular_season: bool = True


@dataclass(frozen=True)
class ClockPlayConfig:
    """Fixed structural priors for the baseline, not fitted coefficients."""

    regulation_quarter_seconds: int = 900
    overtime_seconds: int = 600
    timeouts_per_team: int = 3
    kickoff_touchback_yardline: int = 25
    max_plays_per_game: int = 360
    base_play_seconds: float = 28.0
    hurry_play_seconds: float = 15.0
    play_seconds_spread: float = 8.0
    base_yards: float = 4.2
    yards_spread: float = 6.8
    turnover_probability: float = 0.027
    incompletion_probability: float = 0.305
    explosive_play_probability: float = 0.105
    fourth_down_go_distance: int = 2
    field_goal_max_distance: int = 62
    endgame_window_seconds: int = 180
    timeout_window_seconds: int = 100
    late_trailing_timeout_max_deficit: int = 8
    late_field_goal_window_seconds: int = 10
    model_version: str = DEFAULT_CLOCK_PLAY_MODEL_VERSION

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "ClockPlayConfig":
        known = {name: raw[name] for name in cls.__dataclass_fields__ if name in raw}
        return cls(**known)


@dataclass
class ClockPlayState:
    quarter: int | str = 1
    clock_seconds: float = 900.0
    possession: TeamSide = "home"
    yardline: int = 25
    down: int = 1
    distance: int = 10
    home_score: int = 0
    away_score: int = 0
    home_timeouts: int = 3
    away_timeouts: int = 3
    overtime_possessions: dict[TeamSide, int] = field(
        default_factory=lambda: {"home": 0, "away": 0}
    )
    play_count: int = 0
    finished: bool = False
    result_reason: str = ""
    event_counts: Counter[str] = field(default_factory=Counter)
    transition_counts: Counter[str] = field(default_factory=Counter)

    @property
    def defense(self) -> TeamSide:
        return _OTHER_SIDE[self.possession]

    @property
    def score(self) -> dict[TeamSide, int]:
        return {"home": self.home_score, "away": self.away_score}

    def timeouts_for(self, side: TeamSide) -> int:
        return self.home_timeouts if side == "home" else self.away_timeouts

    def use_timeout(self, side: TeamSide) -> None:
        if side == "home":
            self.home_timeouts = max(0, self.home_timeouts - 1)
        else:
            self.away_timeouts = max(0, self.away_timeouts - 1)


class ClockPlaySimulator:
    """One deterministic seeded NFL play/drive simulator."""

    def __init__(
        self,
        inputs: ClockPlayGameInputs,
        *,
        seed: int,
        config: Optional[ClockPlayConfig] = None,
        collect_events: bool = False,
    ) -> None:
        self.inputs = inputs
        self.config = config or ClockPlayConfig()
        self.rng = random.Random(int(seed))
        self.seed = int(seed)
        self.collect_events = bool(collect_events)
        opening = "home" if self.rng.random() < 0.5 else "away"
        self.state = ClockPlayState(
            clock_seconds=float(self.config.regulation_quarter_seconds),
            possession=opening,
            home_timeouts=self.config.timeouts_per_team,
            away_timeouts=self.config.timeouts_per_team,
        )
        self.events: list[dict[str, Any]] = []
        self.invariant_failures: list[str] = []

    def _snapshot(self) -> dict[str, Any]:
        state = self.state
        return {
            "quarter": state.quarter,
            "clock_seconds": round(state.clock_seconds, 3),
            "possession": state.possession,
            "yardline": state.yardline,
            "down": state.down,
            "distance": state.distance,
            "score": state.score,
            "timeouts": {"home": state.home_timeouts, "away": state.away_timeouts},
        }

    def _event(self, event_type: str, **details: Any) -> None:
        self.state.event_counts[event_type] += 1
        if self.collect_events:
            self.events.append({"event_type": event_type, "state": self._snapshot(), **details})

    def _team(self, side: TeamSide) -> ClockPlayTeamInput:
        return self.inputs.home if side == "home" else self.inputs.away

    def _attack_factor(self, offense: TeamSide) -> float:
        attack = self._team(offense).offense_rating
        defense = self._team(_OTHER_SIDE[offense]).defense_rating
        return _clamp(float(attack) / max(0.5, float(defense)), 0.72, 1.30)

    def _pace_factor(self, offense: TeamSide) -> float:
        return _clamp(float(self._team(offense).pace_factor), 0.80, 1.20)

    def _is_endgame(self) -> bool:
        return self.state.quarter in {4, "OT"} and (
            self.state.clock_seconds <= self.config.endgame_window_seconds
        )

    def _is_trailing(self, side: TeamSide) -> bool:
        return self.state.score[side] < self.state.score[_OTHER_SIDE[side]]

    def _record_invariant_failure(self, message: str) -> None:
        if message not in self.invariant_failures:
            self.invariant_failures.append(message)

    def _validate_state(self) -> None:
        state = self.state
        if not (1 <= state.down <= 4):
            self._record_invariant_failure("down_out_of_bounds")
        if not (1 <= state.distance <= 99):
            self._record_invariant_failure("distance_out_of_bounds")
        if not (1 <= state.yardline <= 99):
            self._record_invariant_failure("yardline_out_of_bounds")
        if state.clock_seconds < 0:
            self._record_invariant_failure("negative_clock")
        if any(
            timeout < 0 or timeout > self.config.timeouts_per_team
            for timeout in (state.home_timeouts, state.away_timeouts)
        ):
            self._record_invariant_failure("timeout_out_of_bounds")

    def _consume_clock(self, seconds: float) -> None:
        self.state.clock_seconds = max(0.0, self.state.clock_seconds - max(0.0, seconds))

    def _play_seconds(self, offense: TeamSide, *, stopped_clock: bool) -> float:
        if stopped_clock:
            return _clamp(self.rng.uniform(5.0, 12.0), 1.0, 15.0)
        hurry = self._is_endgame() and self._is_trailing(offense)
        base = self.config.hurry_play_seconds if hurry else self.config.base_play_seconds
        seconds = self.rng.gauss(base / self._pace_factor(offense), self.config.play_seconds_spread)
        return _clamp(seconds, 6.0 if hurry else 16.0, 42.0)

    def _start_possession(
        self,
        offense: TeamSide,
        *,
        yardline: int,
        reason: str,
        overtime_possession: bool = False,
    ) -> None:
        self.state.possession = offense
        self.state.yardline = int(_clamp(float(yardline), 1.0, 99.0))
        self.state.down = 1
        self.state.distance = min(10, 100 - self.state.yardline)
        if overtime_possession:
            self.state.overtime_possessions[offense] += 1
        self._event(
            "possession_start",
            reason=reason,
            overtime_possession=bool(overtime_possession),
        )
        self._validate_state()

    def _kickoff(self, receiving_team: TeamSide, *, reason: str) -> None:
        return_yards = int(round(self.rng.uniform(-5.0, 8.0)))
        yardline = int(
            _clamp(
                float(self.config.kickoff_touchback_yardline + return_yards),
                15.0,
                40.0,
            )
        )
        self._event(
            "kickoff",
            receiving_team=receiving_team,
            reason=reason,
            receiving_yardline=yardline,
        )
        if reason == "after_field_goal":
            self.state.transition_counts["field_goal_to_kickoff"] += 1
        elif reason == "after_try":
            self.state.transition_counts["try_to_kickoff"] += 1
        self._start_possession(
            receiving_team,
            yardline=yardline,
            reason=reason,
            overtime_possession=self.state.quarter == "OT",
        )

    def _add_points(self, side: TeamSide, points: int) -> None:
        if side == "home":
            self.state.home_score += int(points)
        else:
            self.state.away_score += int(points)

    def _try_two_point(self, offense: TeamSide) -> bool:
        if not self._is_endgame():
            return self.rng.random() < TWO_POINT_ATTEMPT_RATE
        deficit = self.state.score[_OTHER_SIDE[offense]] - self.state.score[offense]
        return deficit in {1, 2, 4, 5, 8} or self.rng.random() < TWO_POINT_ATTEMPT_RATE

    def _resolve_try(self, offense: TeamSide) -> None:
        if self._try_two_point(offense):
            made = self.rng.random() < _clamp(0.47 * self._attack_factor(offense), 0.32, 0.62)
            self._add_points(offense, 2 if made else 0)
            self._event("two_point_try", offense=offense, made=made, points=2 if made else 0)
        else:
            made = self.rng.random() < LEAGUE_XP_MAKE_RATE
            self._add_points(offense, 1 if made else 0)
            self._event("pat_try", offense=offense, made=made, points=1 if made else 0)
        self.state.transition_counts["touchdown_to_try"] += 1
        if not self._maybe_finish_overtime_after_score():
            self._kickoff(_OTHER_SIDE[offense], reason="after_try")

    def _score_touchdown(self, offense: TeamSide, *, source: str) -> None:
        self._add_points(offense, 6)
        self._event("touchdown", offense=offense, source=source, points=6)
        self._resolve_try(offense)

    def _field_goal_band(self, distance: int) -> str:
        if distance <= 39:
            return "short"
        if distance <= 49:
            return "mid"
        return "long"

    def _maybe_finish_overtime_after_score(self) -> bool:
        if self.state.quarter != "OT":
            return False
        both_possessed = all(v >= 1 for v in self.state.overtime_possessions.values())
        if both_possessed and self.state.home_score != self.state.away_score:
            self.state.finished = True
            self.state.result_reason = "overtime_sudden_death_after_equal_possessions"
            self._event("game_end", reason=self.state.result_reason)
            return True
        return False

    def _attempt_field_goal(self, offense: TeamSide, *, source: str = "fourth_down") -> None:
        distance = int(117 - self.state.yardline)
        band = self._field_goal_band(distance)
        make_rate = LEAGUE_FG_MAKE_RATE_BY_BAND[band]
        make_rate = _clamp(make_rate * (0.96 + 0.04 * self._attack_factor(offense)), 0.30, 0.99)
        self._consume_clock(self._play_seconds(offense, stopped_clock=True))
        made = self.rng.random() < make_rate
        if made:
            self._add_points(offense, 3)
            self._event(
                "field_goal_made",
                offense=offense,
                field_goal_distance=distance,
                band=band,
                points=3,
                source=source,
            )
            if source == "late_tied_non_fourth":
                self.state.event_counts["late_tied_non_fourth_field_goal_made"] += 1
            # A made field goal gets an explicit post-score transition unless
            # the already-satisfied overtime equal-possession rule ends it.
            # Regulation period/game termination stays in the main clock loop.
            if not self._maybe_finish_overtime_after_score():
                self._kickoff(_OTHER_SIDE[offense], reason="after_field_goal")
            return
        next_yardline = max(20, 100 - self.state.yardline)
        self._event(
            "field_goal_missed",
            offense=offense,
            field_goal_distance=distance,
            band=band,
            source=source,
        )
        self._start_possession(
            _OTHER_SIDE[offense],
            yardline=next_yardline,
            reason="missed_field_goal",
            overtime_possession=self.state.quarter == "OT",
        )

    def _punt(self, offense: TeamSide) -> None:
        net_yards = int(round(_clamp(self.rng.gauss(41.0, 8.0), 24.0, 58.0)))
        landing = self.state.yardline + net_yards
        receiving_yardline = max(10, min(45, 100 - landing))
        self._consume_clock(self._play_seconds(offense, stopped_clock=False))
        self._event(
            "punt",
            offense=offense,
            net_yards=net_yards,
            receiving_yardline=receiving_yardline,
        )
        self._start_possession(
            _OTHER_SIDE[offense],
            yardline=receiving_yardline,
            reason="punt",
            overtime_possession=self.state.quarter == "OT",
        )

    def _fourth_down_decision(self, offense: TeamSide) -> str:
        score_gap = self.state.score[offense] - self.state.score[_OTHER_SIDE[offense]]
        yards_to_go = self.state.distance
        fg_distance = 117 - self.state.yardline
        if self._is_endgame() and score_gap < 0:
            if score_gap >= -3 and fg_distance <= self.config.field_goal_max_distance:
                return "field_goal"
            return "go"
        if self._is_endgame() and score_gap == 0 and self.state.quarter == "OT":
            if fg_distance <= self.config.field_goal_max_distance:
                return "field_goal"
            return "go"
        # This conventional short-yardage decision must precede the
        # field-goal-range branch; otherwise reachable attempts are masked
        # whenever the ball is already in field-goal territory.
        if (
            yards_to_go <= self.config.fourth_down_go_distance
            and self.state.yardline >= 45
        ):
            return "go"
        if fg_distance <= self.config.field_goal_max_distance and (
            self.state.yardline >= 55 or self._is_endgame()
        ):
            return "field_goal"
        return "punt"

    def _maybe_timeout_after_in_bounds_play(self, offense: TeamSide) -> None:
        if (
            self.state.quarter != 4
            or self.state.clock_seconds > self.config.timeout_window_seconds
        ):
            return
        defense = _OTHER_SIDE[offense]
        deficit = self.state.score[offense] - self.state.score[defense]
        if (
            deficit < 1
            or deficit > self.config.late_trailing_timeout_max_deficit
            or self.state.timeouts_for(defense) <= 0
        ):
            return
        self.state.use_timeout(defense)
        self._event("timeout", team=defense, reason="late_trailing_clock_stop")

    def _should_take_late_tied_non_fourth_field_goal(self, offense: TeamSide) -> bool:
        """Allow the reachable, regulation-ending FG state seen in train PBP."""

        return (
            self.state.quarter == 4
            and 0 < self.state.clock_seconds <= self.config.late_field_goal_window_seconds
            and self.state.down < 4
            and self.state.score[offense] == self.state.score[_OTHER_SIDE[offense]]
            and (117 - self.state.yardline) <= self.config.field_goal_max_distance
        )

    def _turnover(self, offense: TeamSide, *, kind: str) -> None:
        receiving_yardline = int(_clamp(float(100 - self.state.yardline), 5.0, 95.0))
        self._event(kind, offense=offense, receiving_yardline=receiving_yardline)
        self._start_possession(
            _OTHER_SIDE[offense],
            yardline=receiving_yardline,
            reason=kind,
            overtime_possession=self.state.quarter == "OT",
        )

    def _advance_down(self, yards: int) -> None:
        state = self.state
        state.yardline = int(_clamp(float(state.yardline + yards), 1.0, 99.0))
        if yards >= state.distance:
            state.down = 1
            state.distance = min(10, 100 - state.yardline)
        else:
            state.down += 1
            state.distance = max(1, state.distance - max(0, yards))

    def _resolve_scrimmage_play(self, offense: TeamSide) -> None:
        state = self.state
        clock_before = state.clock_seconds
        fourth_down_attempt = state.down == 4
        if self._should_take_late_tied_non_fourth_field_goal(offense):
            self.state.event_counts["late_tied_non_fourth_field_goal_attempt"] += 1
            self._event(
                "late_field_goal_decision",
                offense=offense,
                decision="field_goal",
                down=state.down,
            )
            self._attempt_field_goal(offense, source="late_tied_non_fourth")
            return
        if fourth_down_attempt:
            decision = self._fourth_down_decision(offense)
            self._event("fourth_down_decision", offense=offense, decision=decision)
            self.state.event_counts[f"fourth_down_{decision}"] += 1
            if decision == "field_goal":
                self._attempt_field_goal(offense)
                return
            if decision == "punt":
                self._punt(offense)
                return

        attack = self._attack_factor(offense)
        turnover_probability = _clamp(
            self.config.turnover_probability / attack, 0.012, 0.065
        )
        if self.rng.random() < turnover_probability:
            self._consume_clock(self._play_seconds(offense, stopped_clock=False))
            if state.down == 3:
                self.state.event_counts["third_down_attempt"] += 1
            self._turnover(offense, kind="turnover")
            return

        pass_probability = 0.52
        if self._is_endgame():
            pass_probability += 0.17 if self._is_trailing(offense) else -0.12
        is_pass = self.rng.random() < _clamp(pass_probability, 0.25, 0.80)
        incomplete = is_pass and self.rng.random() < _clamp(
            self.config.incompletion_probability / attack, 0.16, 0.48
        )
        if incomplete:
            self._consume_clock(self._play_seconds(offense, stopped_clock=True))
            self._event(
                "incomplete_pass",
                offense=offense,
                clock_before_seconds=round(clock_before, 3),
                clock_elapsed_seconds=round(clock_before - state.clock_seconds, 3),
            )
            if state.down == 3:
                self.state.event_counts["third_down_attempt"] += 1
            if fourth_down_attempt:
                self._turnover(offense, kind="turnover_on_downs")
                return
            state.down += 1
            self._validate_state()
            return

        yards = int(round(self.rng.gauss(self.config.base_yards * attack, self.config.yards_spread)))
        if self.rng.random() < self.config.explosive_play_probability * attack:
            yards += int(round(self.rng.uniform(12.0, 34.0)))
        yards = max(-12, yards)
        target_yardline = state.yardline + yards
        self._consume_clock(self._play_seconds(offense, stopped_clock=False))
        if target_yardline >= 100:
            self._event(
                "scrimmage_play",
                offense=offense,
                play_type="pass" if is_pass else "run",
                yards=max(0, 100 - state.yardline),
                touchdown=True,
                clock_before_seconds=round(clock_before, 3),
                clock_elapsed_seconds=round(clock_before - state.clock_seconds, 3),
            )
            if state.down == 3:
                self.state.event_counts["third_down_attempt"] += 1
                self.state.event_counts["third_down_conversion"] += 1
            self._score_touchdown(offense, source="scrimmage_play")
            return

        gained_first_down = yards >= state.distance
        if fourth_down_attempt and not gained_first_down:
            state.yardline = int(_clamp(float(state.yardline + yards), 1.0, 99.0))
            self._event(
                "turnover_on_downs",
                offense=offense,
                play_type="pass" if is_pass else "run",
                yards=yards,
                clock_before_seconds=round(clock_before, 3),
                clock_elapsed_seconds=round(clock_before - state.clock_seconds, 3),
            )
            self._start_possession(
                _OTHER_SIDE[offense],
                yardline=int(_clamp(float(100 - state.yardline), 5.0, 95.0)),
                reason="turnover_on_downs",
                overtime_possession=state.quarter == "OT",
            )
            return

        if state.down == 3:
            self.state.event_counts["third_down_attempt"] += 1
            if gained_first_down:
                self.state.event_counts["third_down_conversion"] += 1
        self._advance_down(yards)
        self._event(
            "scrimmage_play",
            offense=offense,
            play_type="pass" if is_pass else "run",
            yards=yards,
            touchdown=False,
            clock_before_seconds=round(clock_before, 3),
            clock_elapsed_seconds=round(clock_before - state.clock_seconds, 3),
        )
        self._maybe_timeout_after_in_bounds_play(offense)
        self._validate_state()

    def _advance_period_or_finish(self) -> None:
        state = self.state
        if state.quarter in {1, 2, 3}:
            prior = state.quarter
            state.quarter = int(prior) + 1
            state.clock_seconds = float(self.config.regulation_quarter_seconds)
            if state.quarter == 3:
                state.home_timeouts = self.config.timeouts_per_team
                state.away_timeouts = self.config.timeouts_per_team
            self._event("quarter_start", quarter=state.quarter)
            return
        if state.quarter == 4:
            if state.home_score != state.away_score:
                state.finished = True
                state.result_reason = "regulation_complete"
                self._event("game_end", reason=state.result_reason)
                return
            state.quarter = "OT"
            state.clock_seconds = float(self.config.overtime_seconds)
            state.home_timeouts = self.config.timeouts_per_team
            state.away_timeouts = self.config.timeouts_per_team
            receiving = "home" if self.rng.random() < 0.5 else "away"
            self._event("overtime_start", receiving_team=receiving)
            self._kickoff(receiving, reason="overtime_opening_kickoff")
            return
        state.finished = True
        state.result_reason = (
            "overtime_expired_tie"
            if state.home_score == state.away_score
            else "overtime_expired_with_lead"
        )
        self._event("game_end", reason=state.result_reason)

    def run(self) -> dict[str, Any]:
        self._event("game_start", opening_possession=self.state.possession)
        self._start_possession(
            self.state.possession,
            yardline=self.config.kickoff_touchback_yardline,
            reason="opening_kickoff",
        )
        while not self.state.finished and self.state.play_count < self.config.max_plays_per_game:
            if self.state.clock_seconds <= 0:
                self._advance_period_or_finish()
                continue
            self.state.play_count += 1
            self._resolve_scrimmage_play(self.state.possession)

        if not self.state.finished:
            self.state.finished = True
            self.state.result_reason = "max_play_guard"
            self._event("game_end", reason=self.state.result_reason)
        self._validate_state()
        return self._result()

    def run_overtime_probe(self) -> dict[str, Any]:
        """Exercise the same OT state path from a tied, regulation-complete game."""

        self.state = ClockPlayState(
            quarter="OT",
            clock_seconds=float(self.config.overtime_seconds),
            possession="home",
            home_timeouts=self.config.timeouts_per_team,
            away_timeouts=self.config.timeouts_per_team,
        )
        self._event("overtime_start", probe=True, receiving_team=self.state.possession)
        self._kickoff(self.state.possession, reason="overtime_opening_kickoff")
        while not self.state.finished and self.state.play_count < self.config.max_plays_per_game:
            if self.state.clock_seconds <= 0:
                self._advance_period_or_finish()
                continue
            self.state.play_count += 1
            self._resolve_scrimmage_play(self.state.possession)
        if not self.state.finished:
            self.state.finished = True
            self.state.result_reason = "max_play_guard"
            self._event("game_end", reason=self.state.result_reason)
        self._validate_state()
        return self._result()

    def _result(self) -> dict[str, Any]:
        state = self.state
        return {
            "model_version": self.config.model_version,
            "game_id": self.inputs.game_id,
            "seed": self.seed,
            "home_team": self.inputs.home_team,
            "away_team": self.inputs.away_team,
            "home_score": state.home_score,
            "away_score": state.away_score,
            "result_reason": state.result_reason,
            "play_count": state.play_count,
            "event_counts": dict(sorted(state.event_counts.items())),
            "transition_counts": dict(sorted(state.transition_counts.items())),
            "overtime_possessions": dict(state.overtime_possessions),
            "state_invariants": {
                "ok": not self.invariant_failures,
                "failures": list(self.invariant_failures),
                "final_state": self._snapshot(),
            },
            "events": self.events if self.collect_events else [],
        }


def derive_replicate_seed(root_seed: int, case_id: str, replicate_index: int) -> int:
    """Derive a stable independent seed without consuming game-model RNG."""

    text = f"{int(root_seed)}|{case_id}|{int(replicate_index)}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(text).digest()[:8], byteorder="big", signed=False)


def simulate_clock_play_game(
    inputs: ClockPlayGameInputs,
    *,
    seed: int,
    config: Optional[ClockPlayConfig] = None,
    collect_events: bool = False,
) -> dict[str, Any]:
    """Run one full regulation-plus-overtime game path."""

    return ClockPlaySimulator(
        inputs, seed=seed, config=config, collect_events=collect_events
    ).run()


def simulate_clock_play_overtime_probe(
    inputs: ClockPlayGameInputs,
    *,
    seed: int,
    config: Optional[ClockPlayConfig] = None,
    collect_events: bool = True,
) -> dict[str, Any]:
    """Run the baseline's overtime path from an explicitly tied start."""

    return ClockPlaySimulator(
        inputs, seed=seed, config=config, collect_events=collect_events
    ).run_overtime_probe()


def clock_play_config_dict(config: ClockPlayConfig) -> dict[str, Any]:
    """Serialize the effective config for a receipt without runtime objects."""

    return asdict(config)
