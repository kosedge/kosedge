#!/usr/bin/env python3
"""Build train-only pass and special-teams priors for the Clock-Play state loop."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.nfl_clock_play_simulator import (  # noqa: E402
    pass_state_key,
    special_teams_field_bucket,
)

TRAIN_SEASONS = frozenset(range(2013, 2024))
PASS_OUTCOMES = (
    "completion",
    "incompletion",
    "sack",
    "scramble",
    "interception",
    "fumble",
)
PUNT_OUTCOMES = (
    "touchback",
    "fair_catch",
    "dead_ball",
    "return",
    "return_touchdown",
    "block",
    "block_return_touchdown",
    "safety",
)
KICKOFF_OUTCOMES = ("touchback", "return", "return_touchdown", "safety")
OUTCOME_PARENT_PSEUDO_PLAYS = 60.0
YARD_PARENT_PSEUDO_PLAYS = 20.0


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


def _counter_weights(
    child: Counter[int], parent: Counter[int], *, fallback: int = 0
) -> dict[str, float]:
    weights: Counter[int] = Counter(child)
    parent_total = sum(parent.values())
    if parent_total:
        for value, count in parent.items():
            weights[value] += YARD_PARENT_PSEUDO_PLAYS * count / parent_total
    if not weights:
        weights[fallback] = 1.0
    return {str(value): float(count) for value, count in sorted(weights.items())}


@dataclass
class PassSamples:
    n: int = 0
    outcomes: Counter[str] = field(default_factory=Counter)
    yards: dict[str, Counter[int]] = field(
        default_factory=lambda: defaultdict(Counter)
    )
    return_yards: dict[str, Counter[int]] = field(
        default_factory=lambda: defaultdict(Counter)
    )
    return_touchdowns: Counter[str] = field(default_factory=Counter)

    def add(
        self,
        *,
        outcome: str,
        yards: int,
        return_yards: int,
        return_touchdown: bool,
    ) -> None:
        self.n += 1
        self.outcomes[outcome] += 1
        self.yards[outcome][yards] += 1
        if outcome in {"interception", "fumble"}:
            self.return_yards[outcome][return_yards] += 1
            if return_touchdown:
                self.return_touchdowns[outcome] += 1


def _estimate_pass(
    *, child: PassSamples, parent: PassSamples, global_samples: PassSamples, bucket: str
) -> dict[str, Any]:
    global_probs = {
        outcome: global_samples.outcomes[outcome] / global_samples.n
        for outcome in PASS_OUTCOMES
    }
    parent_probs = {
        outcome: (
            parent.outcomes[outcome] + OUTCOME_PARENT_PSEUDO_PLAYS * global_probs[outcome]
        )
        / (parent.n + OUTCOME_PARENT_PSEUDO_PLAYS)
        for outcome in PASS_OUTCOMES
    }
    raw = {
        outcome: (
            child.outcomes[outcome] + OUTCOME_PARENT_PSEUDO_PLAYS * parent_probs[outcome]
        )
        / (child.n + OUTCOME_PARENT_PSEUDO_PLAYS)
        for outcome in PASS_OUTCOMES
    }
    total = sum(raw.values())
    return {
        "bucket": bucket,
        "sample": {
            "called_passes": child.n,
            "outcomes": {outcome: child.outcomes[outcome] for outcome in PASS_OUTCOMES},
        },
        "outcome_probabilities": {
            outcome: raw[outcome] / total for outcome in PASS_OUTCOMES
        },
        "yard_value_weights": {
            outcome: _counter_weights(
                child.yards[outcome],
                parent.yards[outcome],
                fallback=-6 if outcome == "sack" else 0,
            )
            for outcome in PASS_OUTCOMES
        },
        "turnover_returns": {
            outcome: {
                "touchdown_rate": (
                    child.return_touchdowns[outcome] / child.outcomes[outcome]
                    if child.outcomes[outcome]
                    else (
                        parent.return_touchdowns[outcome] / parent.outcomes[outcome]
                        if parent.outcomes[outcome]
                        else (
                            global_samples.return_touchdowns[outcome]
                            / global_samples.outcomes[outcome]
                            if global_samples.outcomes[outcome]
                            else 0.0
                        )
                    )
                ),
                "return_yard_weights": _counter_weights(
                    child.return_yards[outcome],
                    parent.return_yards[outcome],
                ),
            }
            for outcome in ("interception", "fumble")
        },
    }


@dataclass
class SpecialSamples:
    n: int = 0
    outcomes: Counter[str] = field(default_factory=Counter)
    punt_yards: dict[str, Counter[int]] = field(
        default_factory=lambda: defaultdict(Counter)
    )
    return_yards: dict[str, Counter[int]] = field(
        default_factory=lambda: defaultdict(Counter)
    )

    def add(
        self, *, outcome: str, punt_yards: int = 0, return_yards: int = 0
    ) -> None:
        self.n += 1
        self.outcomes[outcome] += 1
        self.punt_yards[outcome][punt_yards] += 1
        self.return_yards[outcome][return_yards] += 1


def _estimate_special(
    *,
    child: SpecialSamples,
    parent: SpecialSamples,
    global_samples: SpecialSamples,
    outcomes: tuple[str, ...],
    bucket: str,
) -> dict[str, Any]:
    global_probs = {
        outcome: global_samples.outcomes[outcome] / global_samples.n
        for outcome in outcomes
    }
    parent_probs = {
        outcome: (
            parent.outcomes[outcome] + OUTCOME_PARENT_PSEUDO_PLAYS * global_probs[outcome]
        )
        / (parent.n + OUTCOME_PARENT_PSEUDO_PLAYS)
        for outcome in outcomes
    }
    raw = {
        outcome: (
            child.outcomes[outcome] + OUTCOME_PARENT_PSEUDO_PLAYS * parent_probs[outcome]
        )
        / (child.n + OUTCOME_PARENT_PSEUDO_PLAYS)
        for outcome in outcomes
    }
    total = sum(raw.values())
    return {
        "bucket": bucket,
        "sample": {"plays": child.n, "outcomes": dict(child.outcomes)},
        "outcome_probabilities": {
            outcome: raw[outcome] / total for outcome in outcomes
        },
        "punt_yard_weights": {
            outcome: _counter_weights(
                child.punt_yards[outcome], parent.punt_yards[outcome]
            )
            for outcome in outcomes
        },
        "return_yard_weights": {
            outcome: _counter_weights(
                child.return_yards[outcome], parent.return_yards[outcome]
            )
            for outcome in outcomes
        },
    }


@dataclass
class FieldGoalSamples:
    n: int = 0
    blocks: int = 0
    block_returns: SpecialSamples = field(default_factory=SpecialSamples)
    miss_returns: SpecialSamples = field(default_factory=SpecialSamples)

    def add(
        self,
        *,
        result: str,
        return_yards: int,
        return_touchdown: bool,
    ) -> None:
        self.n += 1
        target = self.block_returns if result == "block" else self.miss_returns
        if result == "block":
            self.blocks += 1
        target.add(
            outcome="return_touchdown" if return_touchdown else "return",
            return_yards=return_yards,
        )


def _estimate_field_goal(
    *, child: FieldGoalSamples, parent: FieldGoalSamples, global_samples: FieldGoalSamples, bucket: str
) -> dict[str, Any]:
    parent_block_rate = (
        parent.blocks / parent.n
        if parent.n
        else global_samples.blocks / global_samples.n
    )
    block_rate = (
        child.blocks + OUTCOME_PARENT_PSEUDO_PLAYS * parent_block_rate
    ) / (child.n + OUTCOME_PARENT_PSEUDO_PLAYS)

    def return_prior(
        child_returns: SpecialSamples, parent_returns: SpecialSamples
    ) -> dict[str, Any]:
        denominator = child_returns.n
        if denominator:
            td_rate = child_returns.outcomes["return_touchdown"] / denominator
        elif parent_returns.n:
            td_rate = (
                parent_returns.outcomes["return_touchdown"] / parent_returns.n
            )
        else:
            td_rate = 0.0
        return {
            "touchdown_rate": td_rate,
            "return_yard_weights": _counter_weights(
                child_returns.return_yards["return"],
                parent_returns.return_yards["return"],
            ),
        }

    return {
        "bucket": bucket,
        "sample": {"attempts": child.n, "blocks": child.blocks},
        "block_rate": block_rate,
        "block": return_prior(child.block_returns, parent.block_returns),
        "miss": return_prior(child.miss_returns, parent.miss_returns),
    }


def _pass_outcome(payload: Mapping[str, Any]) -> str:
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
    return "completion"


def _pass_parent_key(full_key: str) -> str:
    return "|".join(full_key.split("|")[:4])


def _punt_outcome(payload: Mapping[str, Any]) -> str:
    if _is_one(payload.get("safety")):
        return "safety"
    blocked = _is_one(payload.get("punt_blocked")) or _is_one(
        payload.get("blocked_punt")
    )
    return_touchdown = _is_one(payload.get("touchdown")) and (
        payload.get("td_team") == payload.get("defteam")
    )
    if blocked:
        return "block_return_touchdown" if return_touchdown else "block"
    if _is_one(payload.get("touchback")):
        return "touchback"
    if return_touchdown:
        return "return_touchdown"
    if _is_one(payload.get("fair_catch")):
        return "fair_catch"
    if _number(payload.get("return_yards")) is not None:
        return "return"
    return "dead_ball"


def _kickoff_outcome(payload: Mapping[str, Any]) -> str:
    if _is_one(payload.get("safety")):
        return "safety"
    if _is_one(payload.get("touchdown")) and payload.get("td_team") == payload.get(
        "defteam"
    ):
        return "return_touchdown"
    if _is_one(payload.get("touchback")):
        return "touchback"
    return "return"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pbp", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    pass_global = PassSamples()
    pass_parents: defaultdict[str, PassSamples] = defaultdict(PassSamples)
    pass_buckets: defaultdict[str, PassSamples] = defaultdict(PassSamples)
    punt_global = SpecialSamples()
    punt_buckets: defaultdict[str, SpecialSamples] = defaultdict(SpecialSamples)
    kickoff_global = SpecialSamples()
    fg_global = FieldGoalSamples()
    fg_buckets: defaultdict[str, FieldGoalSamples] = defaultdict(FieldGoalSamples)
    games: set[str] = set()
    rows_examined = 0

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
            rows_examined += 1
            game_id = str(payload.get("game_id") or "")
            if game_id:
                games.add(game_id)

            play_type = str(payload.get("play_type") or "")
            yardline_100 = _number(payload.get("yardline_100"))
            yardline = (
                max(1, min(99, int(round(100 - yardline_100))))
                if yardline_100 is not None
                else None
            )
            return_yards = int(round(_number(payload.get("return_yards")) or 0.0))

            is_called_pass = play_type == "pass" or _is_one(payload.get("qb_scramble"))
            down = _number(payload.get("down"))
            distance = _number(payload.get("ydstogo"))
            if (
                is_called_pass
                and yardline is not None
                and down is not None
                and distance is not None
            ):
                outcome = _pass_outcome(payload)
                yards = int(round(_number(payload.get("yards_gained")) or 0.0))
                if outcome == "incompletion":
                    yards = 0
                score_gap = int(
                    round(
                        (_number(payload.get("posteam_score")) or 0.0)
                        - (_number(payload.get("defteam_score")) or 0.0)
                    )
                )
                key = pass_state_key(
                    yardline=yardline,
                    down=int(down),
                    distance=max(1, int(round(distance))),
                    goal_to_go=_is_one(payload.get("goal_to_go")),
                    quarter=int(_number(payload.get("qtr")) or 1),
                    clock_seconds=_number(payload.get("quarter_seconds_remaining"))
                    or 0.0,
                    score_gap=score_gap,
                )
                return_td = _is_one(payload.get("touchdown")) and (
                    payload.get("td_team") == payload.get("defteam")
                )
                for samples in (
                    pass_global,
                    pass_parents[_pass_parent_key(key)],
                    pass_buckets[key],
                ):
                    samples.add(
                        outcome=outcome,
                        yards=yards,
                        return_yards=return_yards,
                        return_touchdown=return_td,
                    )

            if play_type == "punt" and yardline is not None:
                outcome = _punt_outcome(payload)
                punt_yards = int(round(_number(payload.get("punt_yards")) or 0.0))
                for samples in (
                    punt_global,
                    punt_buckets[special_teams_field_bucket(yardline)],
                ):
                    samples.add(
                        outcome=outcome,
                        punt_yards=punt_yards,
                        return_yards=return_yards,
                    )

            if play_type == "kickoff":
                kickoff_global.add(
                    outcome=_kickoff_outcome(payload),
                    return_yards=return_yards,
                )

            if play_type == "field_goal" and yardline is not None:
                result = str(payload.get("field_goal_result") or "").lower()
                blocked = result == "blocked" or _is_one(
                    payload.get("blocked_field_goal")
                )
                if blocked or result in {"missed", "no_good"}:
                    return_td = _is_one(payload.get("touchdown")) and (
                        payload.get("td_team") == payload.get("defteam")
                    )
                    for samples in (
                        fg_global,
                        fg_buckets[special_teams_field_bucket(yardline)],
                    ):
                        samples.add(
                            result="block" if blocked else "miss",
                            return_yards=return_yards,
                            return_touchdown=return_td,
                        )
                else:
                    for samples in (
                        fg_global,
                        fg_buckets[special_teams_field_bucket(yardline)],
                    ):
                        samples.n += 1

    if not pass_global.n or not punt_global.n or not kickoff_global.n or not fg_global.n:
        raise SystemExit("Historical PBP did not contain all required train-only event families")

    payload = {
        "artifact_id": "Clock-Play Coherent Pass and Special-Teams State Priors",
        "train_window": "2013-2023 regular season",
        "historical_source": args.pbp.as_posix(),
        "historical_games": len(games),
        "historical_rows_examined": rows_examined,
        "routing_contract": {
            "called_pass": "pass_state only",
            "designed_rush": "rush family only",
            "punt": "punt state only",
            "field_goal": "field-goal state only",
            "kickoff": "kickoff state only",
            "safety": "selected end-zone pass/rush/special transition only",
        },
        "shrinkage": {
            "outcome_parent_pseudo_plays": OUTCOME_PARENT_PSEUDO_PLAYS,
            "yard_parent_pseudo_plays": YARD_PARENT_PSEUDO_PLAYS,
            "pass_parent": "field-position × down × distance × goal-to-go",
            "special_teams_parent": "field-position bucket",
        },
        "priors": {
            "pass": {
                "default": _estimate_pass(
                    child=pass_global,
                    parent=pass_global,
                    global_samples=pass_global,
                    bucket="default",
                ),
                "buckets": {
                    key: _estimate_pass(
                        child=samples,
                        parent=pass_parents[_pass_parent_key(key)],
                        global_samples=pass_global,
                        bucket=key,
                    )
                    for key, samples in sorted(pass_buckets.items())
                },
            },
            "special_teams": {
                "punt": {
                    "touchback_yardline": 20,
                    "default": _estimate_special(
                        child=punt_global,
                        parent=punt_global,
                        global_samples=punt_global,
                        outcomes=PUNT_OUTCOMES,
                        bucket="default",
                    ),
                    "buckets": {
                        key: _estimate_special(
                            child=samples,
                            parent=punt_global,
                            global_samples=punt_global,
                            outcomes=PUNT_OUTCOMES,
                            bucket=key,
                        )
                        for key, samples in sorted(punt_buckets.items())
                    },
                },
                "kickoff": {
                    "touchback_yardline": 25,
                    "default": _estimate_special(
                        child=kickoff_global,
                        parent=kickoff_global,
                        global_samples=kickoff_global,
                        outcomes=KICKOFF_OUTCOMES,
                        bucket="default",
                    ),
                },
                "field_goal": {
                    "default": _estimate_field_goal(
                        child=fg_global,
                        parent=fg_global,
                        global_samples=fg_global,
                        bucket="default",
                    ),
                    "buckets": {
                        key: _estimate_field_goal(
                            child=samples,
                            parent=fg_global,
                            global_samples=fg_global,
                            bucket=key,
                        )
                        for key, samples in sorted(fg_buckets.items())
                    },
                },
            },
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
