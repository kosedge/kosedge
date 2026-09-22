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
