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


def _red_zone_config(*, outcome: str, yards: float = 3.0) -> ClockPlayConfig:
    probabilities = {
        "touchdown": 0.0,
        "first_down": 0.0,
        "continue": 0.0,
        "turnover": 0.0,
        "turnover_on_downs": 0.0,
    }
    probabilities[outcome] = 1.0
    yards_by_outcome = {
        name: {"mean": yards, "stddev": 0.0}
        for name in probabilities
    }
    return ClockPlayConfig(
        red_zone_transition_enabled=True,
        red_zone_transition_priors={
            "default": {
                "bucket": "unit_test",
                "outcome_probabilities": probabilities,
                "yards_by_outcome": yards_by_outcome,
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


def test_red_zone_transition_first_down_preserves_possession() -> None:
    simulator = ClockPlaySimulator(
        _inputs(),
        seed=4,
        config=_red_zone_config(outcome="first_down", yards=4.0),
        collect_events=True,
    )
    simulator.state = ClockPlayState(
        quarter=2,
        clock_seconds=300.0,
        possession="home",
        yardline=85,
        down=2,
        distance=3,
    )
    simulator._resolve_scrimmage_play("home")

    assert simulator.state.possession == "home"
    assert simulator.state.yardline >= 88
    assert simulator.state.down == 1
    assert simulator.state.event_counts["red_zone_transition"] == 1
    assert simulator.invariant_failures == []


def test_red_zone_transition_turnover_on_downs_flips_at_actual_spot() -> None:
    simulator = ClockPlaySimulator(
        _inputs(),
        seed=4,
        config=_red_zone_config(outcome="turnover_on_downs", yards=-1.0),
        collect_events=True,
    )
    simulator.state = ClockPlayState(
        quarter=2,
        clock_seconds=300.0,
        possession="home",
        yardline=85,
        down=4,
        distance=2,
    )
    simulator._resolve_scrimmage_play("home")

    assert simulator.state.possession == "away"
    assert simulator.state.yardline == 16
    assert simulator.state.event_counts["turnover_on_downs"] == 1
    assert simulator.invariant_failures == []


def test_red_zone_transition_does_not_run_outside_red_zone() -> None:
    simulator = ClockPlaySimulator(
        _inputs(),
        seed=4,
        config=_red_zone_config(outcome="touchdown"),
        collect_events=True,
    )
    simulator.state = ClockPlayState(
        quarter=2,
        clock_seconds=300.0,
        possession="home",
        yardline=79,
        down=1,
        distance=10,
    )
    simulator._resolve_scrimmage_play("home")

    assert simulator.state.event_counts["red_zone_transition"] == 0


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
