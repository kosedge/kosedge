from __future__ import annotations

from src.services.nfl_clock_play_simulator import (
    ClockPlayConfig,
    ClockPlayGameInputs,
    ClockPlaySimulator,
    ClockPlayState,
    pre_entry_pass_rz_state_key,
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


def _rz_pass_transition_config(*, outcome: str, yards: int = 1) -> ClockPlayConfig:
    probabilities = {
        "touchdown": 0.0,
        "turnover": 0.0,
        "incomplete": 0.0,
        "loss": 0.0,
        "zero": 0.0,
        "one_two": 0.0,
        "short_gain": 0.0,
        "first_down": 0.0,
    }
    probabilities[outcome] = 1.0
    yard_weights = {
        name: {"0": 1.0} if name == "incomplete" else {str(yards): 1.0}
        for name in probabilities
    }
    return ClockPlayConfig(
        red_zone_rush_transition_enabled=True,
        red_zone_pass_transition_enabled=True,
        red_zone_pass_transition_priors={
            "default": {
                "bucket": "unit_test",
                "outcome_probabilities": probabilities,
                "yard_value_weights": yard_weights,
            }
        },
        red_zone_rush_transition_priors={
            "default": {
                "bucket": "unit_test",
                "outcome_probabilities": {
                    "touchdown": 0.0,
                    "turnover": 0.0,
                    "loss": 0.0,
                    "zero": 0.0,
                    "one_two": 0.0,
                    "short_gain": 0.0,
                    "first_down": 1.0,
                },
                "yard_value_weights": {
                    "first_down": {str(yards): 1.0},
                },
            }
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


def _pre_entry_pass_rz_config(
    *,
    route: str = "run",
    outcome: str = "first_down",
    yards: int = 3,
) -> ClockPlayConfig:
    routes = {"pass": 0.0, "run": 0.0}
    routes[route] = 1.0
    outcomes = {
        "touchdown": 0.0,
        "turnover": 0.0,
        "incomplete": 0.0,
        "loss": 0.0,
        "zero": 0.0,
        "one_two": 0.0,
        "short_gain": 0.0,
        "first_down": 0.0,
    }
    outcomes[outcome] = 1.0
    return ClockPlayConfig(
        pre_entry_pass_rz_enabled=True,
        pre_entry_pass_rz_priors={
            "default": {
                "bucket": "unit_test",
                "route_probabilities": routes,
                "outcome_probabilities": {
                    "pass": outcomes,
                    "run": outcomes,
                },
                "yard_value_weights": {
                    selected_route: {
                        selected_outcome: {str(yards): 1.0}
                        for selected_outcome in outcomes
                    }
                    for selected_route in routes
                },
            }
        },
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


def test_rz_endgame_trail3_precedence_overrides_go_prior() -> None:
    config = ClockPlayConfig(
        red_zone_fourth_decision_enabled=True,
        red_zone_endgame_trailing_fg_precedence_enabled=True,
        q4_trail3_fg_range_action_probabilities={"field_goal": 1.0, "go": 0.0},
        red_zone_fourth_decision_priors={
            "default": {
                "bucket": "unit_test",
                "action_probabilities": {
                    "field_goal": 0.0,
                    "go": 1.0,
                    "punt": 0.0,
                },
            }
        },
    )
    simulator = ClockPlaySimulator(_inputs(), seed=1, config=config, collect_events=True)
    simulator.state = ClockPlayState(
        quarter=4,
        clock_seconds=120.0,
        possession="home",
        yardline=85,
        down=4,
        distance=5,
        home_score=17,
        away_score=20,
    )
    assert simulator._fourth_down_decision("home") == "field_goal"


def test_rz_q4_full_quarter_trail3_precedence_outside_endgame() -> None:
    config = ClockPlayConfig(
        red_zone_fourth_decision_enabled=True,
        red_zone_q4_trail3_fg_precedence_full_quarter_enabled=True,
        q4_trail3_fg_range_action_probabilities={"field_goal": 1.0, "go": 0.0},
        red_zone_fourth_decision_priors={
            "default": {
                "bucket": "unit_test",
                "action_probabilities": {
                    "field_goal": 0.0,
                    "go": 1.0,
                    "punt": 0.0,
                },
            }
        },
    )
    simulator = ClockPlaySimulator(_inputs(), seed=1, config=config)
    simulator.state = ClockPlayState(
        quarter=4,
        clock_seconds=600.0,
        possession="home",
        yardline=85,
        down=4,
        distance=5,
        home_score=17,
        away_score=20,
    )
    assert simulator._fourth_down_decision("home") == "field_goal"


def test_rz_q4_trail3_precedence_samples_train_go_branch() -> None:
    config = ClockPlayConfig(
        red_zone_fourth_decision_enabled=True,
        red_zone_q4_trail3_fg_precedence_full_quarter_enabled=True,
        q4_trail3_fg_range_action_probabilities={"field_goal": 0.0, "go": 1.0},
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
    simulator = ClockPlaySimulator(_inputs(), seed=1, config=config)
    simulator.state = ClockPlayState(
        quarter=4,
        clock_seconds=600.0,
        possession="home",
        yardline=85,
        down=4,
        distance=5,
        home_score=17,
        away_score=20,
    )
    assert simulator._fourth_down_decision("home") == "go"


def test_rz_q4_trail3_precedence_skips_outside_red_zone() -> None:
    config = ClockPlayConfig(
        red_zone_fourth_decision_enabled=True,
        red_zone_q4_trail3_fg_precedence_full_quarter_enabled=True,
        q4_trail3_fg_range_action_probabilities={"field_goal": 1.0, "go": 0.0},
        red_zone_fourth_decision_priors={
            "default": {
                "bucket": "unit_test",
                "action_probabilities": {
                    "field_goal": 0.0,
                    "go": 1.0,
                    "punt": 0.0,
                },
            }
        },
    )
    simulator = ClockPlaySimulator(_inputs(), seed=1, config=config)
    simulator.state = ClockPlayState(
        quarter=4,
        clock_seconds=600.0,
        possession="home",
        yardline=65,
        down=4,
        distance=5,
        home_score=17,
        away_score=20,
    )
    assert simulator._fourth_down_decision("home") == "field_goal"


def test_rz_endgame_trail3_precedence_disabled_uses_rz_prior() -> None:
    config = ClockPlayConfig(
        red_zone_fourth_decision_enabled=True,
        red_zone_endgame_trailing_fg_precedence_enabled=False,
        red_zone_fourth_decision_priors={
            "default": {
                "bucket": "unit_test",
                "action_probabilities": {
                    "field_goal": 0.0,
                    "go": 1.0,
                    "punt": 0.0,
                },
            }
        },
    )
    simulator = ClockPlaySimulator(_inputs(), seed=1, config=config)
    simulator.state = ClockPlayState(
        quarter=4,
        clock_seconds=120.0,
        possession="home",
        yardline=85,
        down=4,
        distance=5,
        home_score=17,
        away_score=20,
    )
    assert simulator._fourth_down_decision("home") == "go"


def test_non_fourth_red_zone_generic_pass_uses_train_incompletion_prior() -> None:
    config = ClockPlayConfig(
        red_zone_rush_transition_enabled=True,
        red_zone_generic_pass_incompletion_enabled=True,
        red_zone_generic_pass_incompletion_priors={
            "default": {
                "bucket": "unit_test",
                "incomplete_probability": 1.0,
            }
        },
        red_zone_rush_transition_priors={
            "default": {
                "bucket": "unit_test",
                "outcome_probabilities": {"first_down": 1.0},
                "yard_value_weights": {"first_down": {"5": 1.0}},
            }
        },
    )
    for seed in range(1, 200):
        simulator = ClockPlaySimulator(
            _inputs(),
            seed=seed,
            config=config,
            collect_events=True,
        )
        simulator.state = ClockPlayState(
            quarter=1,
            clock_seconds=600.0,
            possession="home",
            yardline=88,
            down=2,
            distance=7,
        )
        simulator._resolve_scrimmage_play("home")
        if simulator.state.event_counts["incomplete_pass"]:
            break
    else:  # pragma: no cover
        raise AssertionError("No deterministic RZ generic pass route found")

    assert simulator.state.event_counts["incomplete_pass"] == 1
    assert simulator.state.down == 3


def test_non_fourth_red_zone_pass_uses_pass_transition_when_enabled() -> None:
    simulator = ClockPlaySimulator(
        _inputs(),
        seed=7,
        config=_rz_pass_transition_config(outcome="incomplete"),
        collect_events=True,
    )
    simulator.state = ClockPlayState(
        quarter=1,
        clock_seconds=600.0,
        possession="home",
        yardline=85,
        down=2,
        distance=6,
    )
    simulator._resolve_scrimmage_play("home")

    assert simulator.state.event_counts["red_zone_pass_transition"] == 1
    assert simulator.state.event_counts["red_zone_rush_transition"] == 0
    assert simulator.state.down == 3


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


def test_pre_entry_pass_rz_key_requires_the_owned_handoff_state() -> None:
    assert (
        pre_entry_pass_rz_state_key(
            pre_entry_yardline=70,
            yardline=82,
            down=2,
            distance=6,
            goal_to_go=False,
        )
        == "70-74|20-16|2|6+|non_gtg"
    )


def test_pass_crossing_routes_exactly_once_to_joint_rz_continuation() -> None:
    priors = _pre_entry_pass_rz_config().pre_entry_pass_rz_priors
    rush = _rz_rush_transition_config(
        outcome="touchdown"
    ).red_zone_rush_transition_priors
    config = ClockPlayConfig(
        base_yards=10.0,
        yards_spread=0.0,
        turnover_probability=0.0,
        incompletion_probability=0.0,
        explosive_play_probability=0.0,
        pre_entry_pass_rz_enabled=True,
        pre_entry_pass_rz_priors=priors,
        red_zone_rush_transition_enabled=True,
        red_zone_rush_transition_priors=rush,
    )
    for seed in range(1, 100):
        simulator = ClockPlaySimulator(
            _inputs(), seed=seed, config=config, collect_events=True
        )
        simulator.state = ClockPlayState(
            quarter=1,
            clock_seconds=600.0,
            possession="home",
            yardline=79,
            down=1,
            distance=1,
        )
        simulator._resolve_scrimmage_play("home")
        if simulator.state.event_counts["pre_entry_pass_rz_handoff"]:
            simulator._resolve_scrimmage_play("home")
            break
    else:  # pragma: no cover - protects the train-supported handoff receipt
        raise AssertionError("No deterministic eligible pre-entry pass crossing found")

    assert simulator.state.event_counts["pre_entry_pass_rz_handoff"] == 1
    assert simulator.state.event_counts["pre_entry_pass_rz_continuation"] == 1
    assert simulator.state.event_counts["pre_entry_pass_rz_route_run"] == 1
    assert simulator.state.event_counts["red_zone_rush_transition"] == 0
    assert simulator.invariant_failures == []


def test_fourth_down_never_consumes_pending_pre_entry_pass_rz_handoff() -> None:
    simulator = ClockPlaySimulator(
        _inputs(),
        seed=1,
        config=_pre_entry_pass_rz_config(),
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
    simulator._pending_pre_entry_pass_rz_state = pre_entry_pass_rz_state_key(
        pre_entry_yardline=79,
        yardline=85,
        down=4,
        distance=2,
        goal_to_go=False,
    )
    simulator._resolve_scrimmage_play("home")

    assert simulator.state.event_counts["pre_entry_pass_rz_continuation"] == 0
    assert simulator._pending_pre_entry_pass_rz_state is None


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
