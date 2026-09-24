from __future__ import annotations

from src.services.nfl_clock_play_simulator import (
    ClockPlayConfig,
    ClockPlayGameInputs,
    ClockPlaySimulator,
    ClockPlayState,
    simulate_clock_play_game,
    simulate_clock_play_overtime_probe,
)


def _inputs() -> ClockPlayGameInputs:
    return ClockPlayGameInputs(
        game_id="synthetic-clock-play",
        home_team="SYN_HOME",
        away_team="SYN_AWAY",
    )


def _continuation_config(
    *,
    conversion_rate: float,
    td_given_conversion: float,
    converted_yards: float = 4.0,
    failure_yards: float = 0.0,
) -> ClockPlayConfig:
    return ClockPlayConfig(
        fourth_down_continuation_enabled=True,
        fourth_down_continuation_priors={
            "default": {
                "bucket": "unit_test",
                "conversion_rate": conversion_rate,
                "td_given_conversion": td_given_conversion,
                "converted_non_td_yards": {
                    "mean": converted_yards,
                    "stddev": 0.0,
                },
                "failure_yards": {
                    "mean": failure_yards,
                    "stddev": 0.0,
                },
            }
        },
    )


def _clock_flow_config() -> ClockPlayConfig:
    return ClockPlayConfig(
        clock_flow_enabled=True,
        clock_flow_priors={
            "default": {"mean_seconds": 30.0, "stddev_seconds": 0.0},
            "kinds": {
                "pass": {"mean_seconds": 27.0, "stddev_seconds": 0.0},
                "incomplete_pass": {"mean_seconds": 24.0, "stddev_seconds": 0.0},
            },
        },
    )


def _rz_rush_transition_config(*, outcome: str, yards: int = 1) -> ClockPlayConfig:
    probabilities = {
        "touchdown": 0.0,
        "turnover": 0.0,
        "loss": 0.0,
        "zero": 0.0,
        "one_two": 0.0,
        "short_gain": 0.0,
        "first_down": 0.0,
    }
    probabilities[outcome] = 1.0
    return ClockPlayConfig(
        red_zone_rush_transition_enabled=True,
        red_zone_rush_transition_priors={
            "default": {
                "bucket": "unit_test",
                "outcome_probabilities": probabilities,
                "yard_value_weights": {
                    name: {str(yards): 1.0} for name in probabilities
                },
            }
        },
    )


def _exclusive_rz_rush_config() -> ClockPlayConfig:
    continuation = _continuation_config(
        conversion_rate=1.0,
        td_given_conversion=1.0,
    ).fourth_down_continuation_priors
    rush = _rz_rush_transition_config(outcome="first_down").red_zone_rush_transition_priors
    return ClockPlayConfig(
        fourth_down_continuation_enabled=True,
        fourth_down_continuation_priors=continuation,
        red_zone_rush_transition_enabled=True,
        red_zone_rush_transition_priors=rush,
    )


def _rz_fourth_decision_config() -> ClockPlayConfig:
    return ClockPlayConfig(
        red_zone_fourth_decision_enabled=True,
        red_zone_fourth_decision_priors={
            "default": {
                "bucket": "unit_test",
                "action_probabilities": {
                    "field_goal": 1.0,
                    "go": 0.0,
                    "punt": 0.0,
                },
            }
        },
    )


def _fourth_down_decision_config(*, action: str) -> ClockPlayConfig:
    return ClockPlayConfig(
        fourth_down_decision_enabled=True,
        fourth_down_decision_priors={
            "default": {
                "action_probabilities": {
                    name: 1.0 if name == action else 0.0
                    for name in ("field_goal", "go", "punt")
                }
            }
        },
    )


def _coherent_state_config(
    *,
    pass_outcome: str = "completion",
    pass_yards: int = 4,
    punt_outcome: str = "fair_catch",
    kickoff_outcome: str = "touchback",
    field_goal_block_rate: float = 0.0,
) -> ClockPlayConfig:
    pass_outcomes = (
        "completion",
        "incompletion",
        "sack",
        "scramble",
        "interception",
        "fumble",
    )
    punt_outcomes = (
        "touchback",
        "fair_catch",
        "dead_ball",
        "return",
        "return_touchdown",
        "block",
        "block_return_touchdown",
        "safety",
    )
    kickoff_outcomes = ("touchback", "return", "return_touchdown", "safety")
    return ClockPlayConfig(
        pass_state_enabled=True,
        pass_state_priors={
            "default": {
                "outcome_probabilities": {
                    outcome: 1.0 if outcome == pass_outcome else 0.0
                    for outcome in pass_outcomes
                },
                "yard_value_weights": {
                    outcome: {str(pass_yards): 1.0} for outcome in pass_outcomes
                },
                "turnover_returns": {
                    outcome: {
                        "touchdown_rate": 0.0,
                        "return_yard_weights": {"7": 1.0},
                    }
                    for outcome in ("interception", "fumble")
                },
            }
        },
        special_teams_state_enabled=True,
        special_teams_state_priors={
            "punt": {
                "default": {
                    "outcome_probabilities": {
                        outcome: 1.0 if outcome == punt_outcome else 0.0
                        for outcome in punt_outcomes
                    },
                    "punt_yard_weights": {
                        outcome: {"40": 1.0} for outcome in punt_outcomes
                    },
                    "return_yard_weights": {
                        outcome: {"7": 1.0} for outcome in punt_outcomes
                    },
                }
            },
            "kickoff": {
                "default": {
                    "outcome_probabilities": {
                        outcome: 1.0 if outcome == kickoff_outcome else 0.0
                        for outcome in kickoff_outcomes
                    },
                    "return_yard_weights": {
                        outcome: {"7": 1.0} for outcome in kickoff_outcomes
                    },
                }
            },
            "field_goal": {
                "default": {
                    "block_rate": field_goal_block_rate,
                    "block": {
                        "touchdown_rate": 0.0,
                        "return_yard_weights": {"7": 1.0},
                    },
                    "miss": {
                        "touchdown_rate": 0.0,
                        "return_yard_weights": {"7": 1.0},
                    },
                }
            },
        },
    )


def _designed_rush_state_config(
    *,
    outcome: str,
    yards: int = 4,
    fumble_return_yards: int = 7,
) -> ClockPlayConfig:
    outcomes = (
        "touchdown",
        "fumble",
        "first_down",
        "loss",
        "zero",
        "short_gain",
    )
    return ClockPlayConfig(
        designed_rush_state_enabled=True,
        designed_rush_state_priors={
            "default": {
                "outcome_probabilities": {
                    name: 1.0 if name == outcome else 0.0 for name in outcomes
                },
                "yard_value_weights": {
                    name: {str(yards): 1.0} for name in outcomes
                },
                "turnover_returns": {
                    "fumble": {
                        "touchdown_rate": 0.0,
                        "return_yard_weights": {str(fumble_return_yards): 1.0},
                    }
                },
            }
        },
    )


def _called_play_state_config(*, family: str) -> ClockPlayConfig:
    return ClockPlayConfig(
        called_play_state_enabled=True,
        called_play_state_priors={
            "default": {
                "call_probabilities": {
                    name: 1.0 if name == family else 0.0
                    for name in ("pass", "rush")
                }
            }
        },
    )


def _coherent_rush_config(
    *,
    rush_outcome: str,
    rz_outcome: str = "first_down",
) -> ClockPlayConfig:
    pass_config = _coherent_state_config()
    rush_config = _designed_rush_state_config(outcome=rush_outcome)
    rz_config = _rz_rush_transition_config(outcome=rz_outcome)
    return ClockPlayConfig(
        pass_state_enabled=True,
        pass_state_priors=pass_config.pass_state_priors,
        special_teams_state_enabled=True,
        special_teams_state_priors=pass_config.special_teams_state_priors,
        designed_rush_state_enabled=True,
        designed_rush_state_priors=rush_config.designed_rush_state_priors,
        red_zone_rush_transition_enabled=True,
        red_zone_rush_transition_priors=rz_config.red_zone_rush_transition_priors,
    )


def test_seeded_full_game_replays_exactly() -> None:
    first = simulate_clock_play_game(_inputs(), seed=101, collect_events=True)
    replay = simulate_clock_play_game(_inputs(), seed=101, collect_events=True)

    assert first == replay
    assert first["play_count"] > 0
    assert first["state_invariants"]["ok"] is True


def test_touchdown_transitions_through_try_then_kickoff() -> None:
    simulator = ClockPlaySimulator(_inputs(), seed=7, collect_events=True)
    simulator._score_touchdown("home", source="unit_test")

    event_types = [event["event_type"] for event in simulator.events]
    touchdown_index = event_types.index("touchdown")
    try_index = next(
        index
        for index, event_type in enumerate(event_types)
        if index > touchdown_index and event_type in {"pat_try", "two_point_try"}
    )
    kickoff_index = event_types.index("kickoff", try_index)

    assert touchdown_index < try_index < kickoff_index
    assert simulator.state.finished is False
    assert simulator.state.transition_counts["touchdown_to_try"] == 1
    assert simulator.state.transition_counts["try_to_kickoff"] == 1


def test_made_field_goal_transitions_to_kickoff_without_terminal_lock() -> None:
    for seed in range(1, 50):
        simulator = ClockPlaySimulator(_inputs(), seed=seed, collect_events=True)
        simulator.state = ClockPlayState(
            quarter=2,
            clock_seconds=180.0,
            possession="home",
            yardline=80,
            down=4,
            distance=4,
        )
        simulator._attempt_field_goal("home")
        if simulator.state.event_counts["field_goal_made"]:
            event_types = [event["event_type"] for event in simulator.events]
            field_goal_index = event_types.index("field_goal_made")
            assert event_types[field_goal_index + 1] == "kickoff"
            assert simulator.state.finished is False
            assert simulator.state.transition_counts["field_goal_to_kickoff"] == 1
            break
    else:  # pragma: no cover - protects against an accidental zero make rate
        raise AssertionError("No made field goal found in deterministic seed range")


def test_fourth_down_failure_changes_possession_without_invalid_down() -> None:
    simulator = ClockPlaySimulator(_inputs(), seed=3, collect_events=True)
    simulator.state = ClockPlayState(
        quarter=1,
        clock_seconds=600.0,
        possession="home",
        yardline=45,
        down=4,
        distance=40,
    )
    simulator._resolve_scrimmage_play("home")

    assert simulator.state.possession == "away"
    assert simulator.state.down == 1
    assert simulator.state.distance >= 1
    assert simulator.invariant_failures == []


def test_endgame_timeout_stops_clock_for_trailing_defense() -> None:
    simulator = ClockPlaySimulator(_inputs(), seed=4, collect_events=True)
    simulator.state = ClockPlayState(
        quarter=4,
        clock_seconds=100.0,
        possession="home",
        yardline=50,
        down=2,
        distance=7,
        home_score=17,
        away_score=13,
        away_timeouts=2,
    )
    simulator._maybe_timeout_after_in_bounds_play("home")

    assert simulator.state.away_timeouts == 1
    assert simulator.state.event_counts["timeout"] == 1


def test_late_timeout_preserves_timeout_when_deficit_is_multiple_possessions() -> None:
    simulator = ClockPlaySimulator(_inputs(), seed=4, collect_events=True)
    simulator.state = ClockPlayState(
        quarter=4,
        clock_seconds=80.0,
        possession="home",
        yardline=50,
        down=2,
        distance=7,
        home_score=24,
        away_score=0,
        away_timeouts=2,
    )
    simulator._maybe_timeout_after_in_bounds_play("home")

    assert simulator.state.away_timeouts == 2
    assert simulator.state.event_counts["timeout"] == 0


def test_conventional_short_fourth_down_is_not_masked_by_field_goal_range() -> None:
    simulator = ClockPlaySimulator(_inputs(), seed=4)
    simulator.state = ClockPlayState(
        quarter=2,
        clock_seconds=300.0,
        possession="home",
        yardline=65,
        down=4,
        distance=2,
    )

    assert simulator._fourth_down_decision("home") == "go"


def test_non_red_zone_fourth_down_uses_train_decision_prior() -> None:
    simulator = ClockPlaySimulator(
        _inputs(),
        seed=4,
        config=_fourth_down_decision_config(action="punt"),
    )
    simulator.state = ClockPlayState(
        quarter=2,
        clock_seconds=300.0,
        possession="home",
        yardline=65,
        down=4,
        distance=2,
    )

    assert simulator._fourth_down_decision("home") == "punt"


def test_clock_flow_uses_train_prior_by_play_kind() -> None:
    simulator = ClockPlaySimulator(_inputs(), seed=4, config=_clock_flow_config())

    assert simulator._play_seconds("home", stopped_clock=False, kind="pass") == 27.0
    assert (
        simulator._play_seconds("home", stopped_clock=True, kind="incomplete_pass")
        == 24.0
    )
    assert simulator._play_seconds("home", stopped_clock=False, kind="punt") == 30.0


def test_clock_flow_runtime_scale_changes_elapsed_time_only() -> None:
    config = _clock_flow_config()
    scaled = ClockPlayConfig(
        clock_flow_enabled=True,
        clock_flow_runtime_scale=0.5,
        clock_flow_priors=config.clock_flow_priors,
    )
    simulator = ClockPlaySimulator(_inputs(), seed=4, config=scaled)

    assert simulator._play_seconds("home", stopped_clock=False, kind="pass") == 13.5


def test_non_fourth_red_zone_rush_uses_rush_transition_only() -> None:
    for seed in range(1, 100):
        simulator = ClockPlaySimulator(
            _inputs(),
            seed=seed,
            config=_rz_rush_transition_config(outcome="first_down", yards=4),
            collect_events=True,
        )
        simulator.state = ClockPlayState(
            quarter=1,
            clock_seconds=600.0,
            possession="home",
            yardline=85,
            down=1,
            distance=3,
        )
        simulator._resolve_scrimmage_play("home")
        if simulator.state.event_counts["red_zone_rush_transition"]:
            break
    else:  # pragma: no cover - protects the route selection receipt
        raise AssertionError("No deterministic red-zone rush route found")

    assert simulator.state.event_counts["red_zone_rush_transition"] == 1
    assert simulator.state.event_counts["fourth_down_decision"] == 0
    assert simulator.state.down == 1


def test_fourth_down_go_bypasses_rush_transition() -> None:
    simulator = ClockPlaySimulator(
        _inputs(),
        seed=1,
        config=_exclusive_rz_rush_config(),
        collect_events=True,
    )
    simulator.state = ClockPlayState(
        quarter=1,
        clock_seconds=600.0,
        possession="home",
        yardline=99,
        down=4,
        distance=1,
    )
    simulator._resolve_scrimmage_play("home")

    assert simulator.state.event_counts["fourth_down_go"] == 1
    assert simulator.state.event_counts["red_zone_rush_transition"] == 0


def test_red_zone_fourth_decision_uses_train_action_prior() -> None:
    simulator = ClockPlaySimulator(
        _inputs(),
        seed=1,
        config=_rz_fourth_decision_config(),
        collect_events=True,
    )
    simulator.state = ClockPlayState(
        quarter=1,
        clock_seconds=600.0,
        possession="home",
        yardline=85,
        down=4,
        distance=2,
    )
    simulator._resolve_scrimmage_play("home")

    assert simulator.state.event_counts["fourth_down_field_goal"] == 1
    assert simulator.state.event_counts["red_zone_rush_transition"] == 0


def test_non_fourth_red_zone_pass_bypasses_rush_transition() -> None:
    for seed in range(1, 100):
        simulator = ClockPlaySimulator(
            _inputs(),
            seed=seed,
            config=_rz_rush_transition_config(outcome="touchdown"),
            collect_events=True,
        )
        simulator.state = ClockPlayState(
            quarter=1,
            clock_seconds=600.0,
            possession="home",
            yardline=85,
            down=1,
            distance=10,
        )
        simulator._resolve_scrimmage_play("home")
        scrimmage = next(
            (
                event
                for event in simulator.events
                if event["event_type"] == "scrimmage_play"
            ),
            None,
        )
        if scrimmage is not None and scrimmage.get("play_type") == "pass":
            break
    else:  # pragma: no cover - protects the route selection receipt
        raise AssertionError("No deterministic red-zone pass route found")

    assert simulator.state.event_counts["red_zone_rush_transition"] == 0
    assert simulator.state.event_counts["fourth_down_decision"] == 0


def test_outside_red_zone_rush_bypasses_rush_transition() -> None:
    simulator = ClockPlaySimulator(
        _inputs(),
        seed=1,
        config=_rz_rush_transition_config(outcome="touchdown"),
        collect_events=True,
    )
    simulator.state = ClockPlayState(
        quarter=1,
        clock_seconds=600.0,
        possession="home",
        yardline=40,
        down=1,
        distance=10,
    )
    simulator._resolve_scrimmage_play("home")

    assert simulator.state.event_counts["red_zone_rush_transition"] == 0


def test_fourth_down_continuation_conversion_resets_first_down() -> None:
    simulator = ClockPlaySimulator(
        _inputs(),
        seed=4,
        config=_continuation_config(
            conversion_rate=1.0,
            td_given_conversion=0.0,
            converted_yards=4.0,
        ),
        collect_events=True,
    )
    simulator.state = ClockPlayState(
        quarter=2,
        clock_seconds=300.0,
        possession="home",
        yardline=70,
        down=4,
        distance=2,
    )
    simulator._resolve_scrimmage_play("home")

    assert simulator.state.possession == "home"
    assert simulator.state.yardline >= 72
    assert simulator.state.down == 1
    assert simulator.state.event_counts["fourth_down_conversion"] == 1
    assert simulator.state.event_counts["touchdown"] == 0
    assert simulator.invariant_failures == []


def test_fourth_down_continuation_failure_uses_short_of_line_field_position() -> None:
    simulator = ClockPlaySimulator(
        _inputs(),
        seed=4,
        config=_continuation_config(
            conversion_rate=0.0,
            td_given_conversion=0.0,
            failure_yards=-1.0,
        ),
        collect_events=True,
    )
    simulator.state = ClockPlayState(
        quarter=2,
        clock_seconds=300.0,
        possession="home",
        yardline=60,
        down=4,
        distance=2,
    )
    simulator._resolve_scrimmage_play("home")

    assert simulator.state.possession == "away"
    assert simulator.state.yardline == 41
    assert simulator.state.down == 1
    assert simulator.state.event_counts["turnover_on_downs"] == 1
    assert simulator.invariant_failures == []


def test_goal_line_fourth_down_conversion_is_a_touchdown() -> None:
    simulator = ClockPlaySimulator(
        _inputs(),
        seed=4,
        config=_continuation_config(
            conversion_rate=1.0,
            td_given_conversion=0.0,
        ),
        collect_events=True,
    )
    simulator.state = ClockPlayState(
        quarter=1,
        clock_seconds=40.0,
        possession="home",
        yardline=99,
        down=4,
        distance=1,
    )
    simulator._resolve_scrimmage_play("home")

    assert simulator.state.event_counts["fourth_down_conversion"] == 1
    assert simulator.state.event_counts["fourth_down_continuation_touchdown"] == 1
    assert simulator.state.event_counts["touchdown"] == 1
    assert simulator.state.transition_counts["touchdown_to_try"] == 1
    assert simulator.invariant_failures == []


def test_tied_non_fourth_late_field_goal_state_is_reachable() -> None:
    for seed in range(1, 50):
        simulator = ClockPlaySimulator(_inputs(), seed=seed, collect_events=True)
        simulator.state = ClockPlayState(
            quarter=4,
            clock_seconds=8.0,
            possession="home",
            yardline=80,
            down=2,
            distance=5,
            home_score=17,
            away_score=17,
        )
        simulator._resolve_scrimmage_play("home")

        assert simulator.state.event_counts["late_tied_non_fourth_field_goal_attempt"] == 1
        assert simulator.events[0]["event_type"] == "late_field_goal_decision"
        if simulator.state.event_counts["late_tied_non_fourth_field_goal_made"]:
            break
    else:  # pragma: no cover - protects against an accidental zero make rate
        raise AssertionError("No made late non-fourth field goal found in deterministic seed range")


def test_overtime_probe_exercises_overtime_state_path() -> None:
    result = simulate_clock_play_overtime_probe(_inputs(), seed=55, collect_events=True)

    assert result["event_counts"]["overtime_start"] == 1
    assert result["event_counts"]["possession_start"] >= 1
    assert result["state_invariants"]["ok"] is True
    assert result["result_reason"].startswith("overtime_") or result["result_reason"] == "max_play_guard"


def test_scrimmage_play_decrements_clock() -> None:
    simulator = ClockPlaySimulator(_inputs(), seed=22, config=ClockPlayConfig(), collect_events=True)
    simulator.state = ClockPlayState(
        quarter=1,
        clock_seconds=400.0,
        possession="home",
        yardline=25,
        down=1,
        distance=10,
    )
    simulator._resolve_scrimmage_play("home")

    assert simulator.state.clock_seconds < 400.0


def test_pass_state_routes_each_primary_outcome_exclusively() -> None:
    for outcome in (
        "completion",
        "incompletion",
        "sack",
        "scramble",
        "interception",
        "fumble",
    ):
        simulator = ClockPlaySimulator(
            _inputs(),
            seed=19,
            config=_coherent_state_config(pass_outcome=outcome),
            collect_events=True,
        )
        simulator.state = ClockPlayState(
            quarter=1,
            clock_seconds=600.0,
            possession="home",
            yardline=50,
            down=1,
            distance=10,
        )

        simulator._resolve_pass_attempt("home")

        assert simulator.state.event_counts["route_pass"] == 1
        assert simulator.state.event_counts[f"pass_outcome_{outcome}"] == 1
        assert simulator.state.event_counts["pass_attempt"] == 1
        assert simulator.state.event_counts["route_rush"] == 0
        assert simulator.state.event_counts["route_red_zone_rush"] == 0
        assert simulator.state.event_counts["turnover"] == 0


def test_called_play_state_selects_one_pass_or_rush_family_before_outcome() -> None:
    pass_config = _coherent_state_config(pass_outcome="completion")
    rush_config = _designed_rush_state_config(outcome="short_gain", yards=3)
    for family, expected_route in (("pass", "pass"), ("rush", "designed_rush")):
        selector = _called_play_state_config(family=family)
        simulator = ClockPlaySimulator(
            _inputs(),
            seed=19,
            config=ClockPlayConfig(
                pass_state_enabled=True,
                pass_state_priors=pass_config.pass_state_priors,
                called_play_state_enabled=True,
                called_play_state_priors=selector.called_play_state_priors,
                designed_rush_state_enabled=True,
                designed_rush_state_priors=rush_config.designed_rush_state_priors,
            ),
            collect_events=True,
        )
        simulator.state = ClockPlayState(
            quarter=1,
            clock_seconds=600.0,
            possession="home",
            yardline=50,
            down=1,
            distance=10,
        )

        simulator._resolve_scrimmage_play("home")

        assert simulator.state.event_counts["play_call"] == 1
        assert simulator.state.event_counts[f"play_call_{family}"] == 1
        assert simulator.state.event_counts[f"route_{expected_route}"] == 1
        assert simulator.state.event_counts["route_pass"] + simulator.state.event_counts[
            "route_designed_rush"
        ] == 1


def test_designed_rush_state_routes_each_primary_outcome_exclusively() -> None:
    for outcome in (
        "touchdown",
        "fumble",
        "first_down",
        "loss",
        "zero",
        "short_gain",
    ):
        simulator = ClockPlaySimulator(
            _inputs(),
            seed=19,
            config=_designed_rush_state_config(outcome=outcome),
            collect_events=True,
        )
        simulator.state = ClockPlayState(
            quarter=1,
            clock_seconds=600.0,
            possession="home",
            yardline=50,
            down=1,
            distance=10,
        )

        simulator._resolve_designed_rush("home")

        assert simulator.state.event_counts["route_designed_rush"] == 1
        assert simulator.state.event_counts["designed_rush_attempt"] == 1
        assert simulator.state.event_counts[f"designed_rush_outcome_{outcome}"] == 1
        assert simulator.state.event_counts["route_rush"] == 0
        assert simulator.state.event_counts["route_pass"] == 0
        assert simulator.state.event_counts["route_red_zone_rush"] == 0


def test_designed_rush_fumble_owns_direct_return_transition() -> None:
    simulator = ClockPlaySimulator(
        _inputs(),
        seed=20,
        config=_designed_rush_state_config(outcome="fumble", yards=2),
        collect_events=True,
    )
    simulator.state = ClockPlayState(
        quarter=1,
        clock_seconds=600.0,
        possession="home",
        yardline=50,
        down=2,
        distance=8,
    )

    simulator._resolve_designed_rush("home")

    assert simulator.state.event_counts["route_designed_rush"] == 1
    assert simulator.state.event_counts["fumble"] == 1
    assert simulator.state.event_counts["turnover"] == 0
    assert simulator.state.possession == "away"
    assert simulator.state.yardline == 55


def test_red_zone_rush_transition_precedes_designed_rush_state() -> None:
    for seed in range(1, 100):
        simulator = ClockPlaySimulator(
            _inputs(),
            seed=seed,
            config=_coherent_rush_config(rush_outcome="touchdown"),
            collect_events=True,
        )
        simulator.state = ClockPlayState(
            quarter=1,
            clock_seconds=600.0,
            possession="home",
            yardline=85,
            down=1,
            distance=3,
        )
        simulator._resolve_scrimmage_play("home")
        if simulator.state.event_counts["route_red_zone_rush"]:
            break
    else:  # pragma: no cover - protects the routing priority
        raise AssertionError("No deterministic red-zone rush route found")

    assert simulator.state.event_counts["route_red_zone_rush"] == 1
    assert simulator.state.event_counts["route_designed_rush"] == 0
    assert simulator.state.event_counts["route_pass"] == 0


def test_fourth_down_continuation_precedes_designed_rush_state() -> None:
    continuation = _continuation_config(
        conversion_rate=1.0,
        td_given_conversion=0.0,
        converted_yards=4.0,
    )
    rush = _designed_rush_state_config(outcome="touchdown")
    simulator = ClockPlaySimulator(
        _inputs(),
        seed=21,
        config=ClockPlayConfig(
            fourth_down_continuation_enabled=True,
            fourth_down_continuation_priors=continuation.fourth_down_continuation_priors,
            designed_rush_state_enabled=True,
            designed_rush_state_priors=rush.designed_rush_state_priors,
        ),
        collect_events=True,
    )
    simulator.state = ClockPlayState(
        quarter=2,
        clock_seconds=300.0,
        possession="home",
        yardline=70,
        down=4,
        distance=2,
    )

    simulator._resolve_scrimmage_play("home")

    assert simulator.state.event_counts["route_fourth_down_go"] == 1
    assert simulator.state.event_counts["route_designed_rush"] == 0


def test_sack_in_end_zone_is_a_state_derived_safety() -> None:
    simulator = ClockPlaySimulator(
        _inputs(),
        seed=20,
        config=_coherent_state_config(pass_outcome="sack", pass_yards=-6),
        collect_events=True,
    )
    simulator.state = ClockPlayState(
        quarter=1,
        clock_seconds=600.0,
        possession="home",
        yardline=5,
        down=2,
        distance=8,
    )

    simulator._resolve_pass_attempt("home")

    assert simulator.state.away_score == 2
    assert simulator.state.event_counts["safety"] == 1
    assert simulator.state.event_counts["route_pass"] == 1
    assert simulator.state.event_counts["route_kickoff"] == 1


def test_special_teams_punt_block_has_one_punt_owner_and_changes_possession() -> None:
    simulator = ClockPlaySimulator(
        _inputs(),
        seed=21,
        config=_coherent_state_config(punt_outcome="block"),
        collect_events=True,
    )
    simulator.state = ClockPlayState(
        quarter=2,
        clock_seconds=500.0,
        possession="home",
        yardline=40,
        down=4,
        distance=8,
    )

    simulator._punt("home")

    assert simulator.state.event_counts["route_punt"] == 1
    assert simulator.state.event_counts["blocked_punt"] == 1
    assert simulator.state.possession == "away"
    assert simulator.state.event_counts["route_pass"] == 0


def test_dead_ball_punt_starts_receiving_possession_at_landing_spot() -> None:
    simulator = ClockPlaySimulator(
        _inputs(),
        seed=22,
        config=_coherent_state_config(punt_outcome="dead_ball"),
        collect_events=True,
    )
    simulator.state = ClockPlayState(
        quarter=2,
        clock_seconds=500.0,
        possession="home",
        yardline=40,
        down=4,
        distance=8,
    )

    simulator._punt("home")

    assert simulator.state.possession == "away"
    assert simulator.state.yardline == 20
    assert simulator.state.event_counts["punt_dead_ball"] == 1


def test_punt_return_touchdown_transitions_to_try_and_kickoff() -> None:
    simulator = ClockPlaySimulator(
        _inputs(),
        seed=23,
        config=_coherent_state_config(punt_outcome="return_touchdown"),
        collect_events=True,
    )
    simulator.state = ClockPlayState(
        quarter=2,
        clock_seconds=500.0,
        possession="home",
        yardline=40,
        down=4,
        distance=8,
    )

    simulator._punt("home")

    assert simulator.state.event_counts["return_touchdown"] == 1
    assert simulator.state.event_counts["non_offensive_touchdown"] == 1
    assert simulator.state.transition_counts["touchdown_to_try"] == 1
    assert simulator.state.event_counts["route_punt"] == 1
    assert simulator.state.event_counts["route_kickoff"] == 1


def test_kickoff_return_and_return_touchdown_are_direct_special_transitions() -> None:
    returned = ClockPlaySimulator(
        _inputs(),
        seed=23,
        config=_coherent_state_config(kickoff_outcome="return"),
        collect_events=True,
    )
    returned._kickoff("away", reason="unit_test")

    assert returned.state.possession == "away"
    assert returned.state.yardline == 32
    assert returned.state.event_counts["route_kickoff"] == 1

    touchdown_config = _coherent_state_config(kickoff_outcome="return_touchdown")
    touchdown_config.special_teams_state_priors["kickoff"]["default"][
        "outcome_probabilities"
    ] = {
        "return": 0.0,
        "return_touchdown": 0.5,
        "safety": 0.0,
        "touchback": 0.5,
    }
    touchdown = ClockPlaySimulator(
        _inputs(),
        seed=24,
        config=touchdown_config,
        collect_events=True,
    )
    touchdown.rng.random = iter((0.25, 0.9, 0.5, 0.75)).__next__  # type: ignore[method-assign]
    touchdown._kickoff("away", reason="unit_test")

    assert touchdown.state.event_counts["return_touchdown"] == 1
    assert touchdown.state.event_counts["non_offensive_touchdown"] == 1
    assert touchdown.state.transition_counts["touchdown_to_try"] == 1
    assert touchdown.state.event_counts["route_kickoff"] == 2
