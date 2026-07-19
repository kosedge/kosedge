from __future__ import annotations

from src.services.nfl_award_projections import (
    MVP_POSITION_PRIOR_WEIGHT,
    MVP_STAT_WEIGHT,
    MVP_TEAM_WEIGHT,
    OPOY_STAT_WEIGHT,
    OPOY_TEAM_WEIGHT,
    compute_stat_composite,
    compute_team_success_score,
    meets_award_volume_threshold,
    min_max_normalize,
    rank_award_candidates,
    score_mvp_candidate,
    score_opoy_candidate,
    select_primary_starter_per_team_position,
)


def test_min_max_normalize_bounds_and_midpoint() -> None:
    values = [4.0, 8.0, 12.0]
    assert min_max_normalize(4.0, values) == 0.0
    assert min_max_normalize(12.0, values) == 1.0
    assert min_max_normalize(8.0, values) == 0.5


def test_min_max_normalize_handles_degenerate_range_without_dividing_by_zero() -> None:
    assert min_max_normalize(7.0, [7.0, 7.0, 7.0]) == 0.5
    assert min_max_normalize(7.0, []) == 0.5


def test_min_max_normalize_clamps_out_of_range_values() -> None:
    assert min_max_normalize(-5.0, [0.0, 10.0]) == 0.0
    assert min_max_normalize(50.0, [0.0, 10.0]) == 1.0


def test_compute_team_success_score_rewards_wins_and_division_title_prob() -> None:
    peer_wins = [6.0, 9.0, 12.0]
    best = compute_team_success_score(expected_wins=12.0, division_title_prob=0.8, peer_expected_wins=peer_wins)
    worst = compute_team_success_score(expected_wins=6.0, division_title_prob=0.05, peer_expected_wins=peer_wins)
    assert best > worst
    assert 0.0 <= best <= 1.0
    assert 0.0 <= worst <= 1.0


def test_compute_stat_composite_is_scaled_within_position_peer_group() -> None:
    # A QB's raw yardage scale dwarfs a TE's, but both should land near 1.0
    # if each is the best IN THEIR OWN peer group.
    qb_composite = compute_stat_composite(
        total_yards=4800.0, total_tds=38.0, peer_total_yards=[3000.0, 4000.0, 4800.0], peer_total_tds=[20.0, 30.0, 38.0]
    )
    te_composite = compute_stat_composite(
        total_yards=1100.0, total_tds=10.0, peer_total_yards=[600.0, 900.0, 1100.0], peer_total_tds=[4.0, 7.0, 10.0]
    )
    assert qb_composite == 1.0
    assert te_composite == 1.0


def test_score_mvp_candidate_gives_qb_a_real_boost_over_identical_non_qb_profile() -> None:
    qb_score = score_mvp_candidate(position="QB", team_success_score=0.8, stat_composite=0.8)
    wr_score = score_mvp_candidate(position="WR", team_success_score=0.8, stat_composite=0.8)
    assert qb_score > wr_score
    assert round(qb_score - wr_score, 4) == MVP_POSITION_PRIOR_WEIGHT


def test_score_mvp_candidate_lets_an_exceptional_non_qb_season_still_beat_a_mediocre_qb() -> None:
    dominant_rb = score_mvp_candidate(position="RB", team_success_score=0.95, stat_composite=1.0)
    weak_qb_on_bad_team = score_mvp_candidate(position="QB", team_success_score=0.1, stat_composite=0.2)
    assert dominant_rb > weak_qb_on_bad_team


def test_score_mvp_weights_sum_to_one() -> None:
    assert round(MVP_TEAM_WEIGHT + MVP_STAT_WEIGHT + MVP_POSITION_PRIOR_WEIGHT, 6) == 1.0


def test_score_opoy_candidate_has_no_position_prior_and_weights_stats_over_team() -> None:
    qb_score = score_opoy_candidate(team_success_score=0.5, stat_composite=0.9)
    wr_score = score_opoy_candidate(team_success_score=0.5, stat_composite=0.9)
    assert qb_score == wr_score  # OPOY formula itself is position-blind
    assert OPOY_STAT_WEIGHT > OPOY_TEAM_WEIGHT


def test_meets_award_volume_threshold_gates_out_low_volume_backups() -> None:
    assert meets_award_volume_threshold(
        position="QB", pass_yards_total=3000.0, rush_yards_total=100.0, receiving_yards_total=0.0
    )
    assert not meets_award_volume_threshold(
        position="QB", pass_yards_total=400.0, rush_yards_total=20.0, receiving_yards_total=0.0
    )
    assert meets_award_volume_threshold(
        position="RB", pass_yards_total=0.0, rush_yards_total=900.0, receiving_yards_total=200.0
    )
    assert not meets_award_volume_threshold(
        position="RB", pass_yards_total=0.0, rush_yards_total=50.0, receiving_yards_total=30.0
    )


def test_meets_award_volume_threshold_rejects_unsupported_positions() -> None:
    assert not meets_award_volume_threshold(
        position="LB", pass_yards_total=0.0, rush_yards_total=0.0, receiving_yards_total=0.0
    )


def test_rank_award_candidates_orders_by_score_key_descending_with_deterministic_ties() -> None:
    candidates = [
        {"player_key": "b", "mvp_score": 0.9},
        {"player_key": "a", "mvp_score": 0.95},
        {"player_key": "c", "mvp_score": 0.9},
    ]
    ranked = rank_award_candidates(candidates, score_key="mvp_score")
    assert [c["player_key"] for c in ranked] == ["a", "b", "c"]
    assert [c["rank_overall"] for c in ranked] == [1, 2, 3]


def test_rank_award_candidates_does_not_mutate_input() -> None:
    candidates = [{"player_key": "a", "mvp_score": 0.5}]
    rank_award_candidates(candidates, score_key="mvp_score")
    assert "rank_overall" not in candidates[0]


def test_select_primary_starter_keeps_only_the_highest_volume_player_per_team_position() -> None:
    # Regression guard for a real observed artifact: a backup QB projected
    # with near-starter passing volume must never be able to out-compete
    # their own team's actual starter for an award nomination.
    candidates = [
        {"player_key": "LA:starter", "team": "LA", "position": "QB", "pass_yards_total": 3062.0},
        {"player_key": "LA:backup", "team": "LA", "position": "QB", "pass_yards_total": 2792.0},
        {"player_key": "BUF:starter", "team": "BUF", "position": "QB", "pass_yards_total": 2864.0},
    ]
    survivors = select_primary_starter_per_team_position(candidates, volume_key="pass_yards_total")
    survivor_keys = {c["player_key"] for c in survivors}
    assert survivor_keys == {"LA:starter", "BUF:starter"}
    assert "LA:backup" not in survivor_keys


def test_select_primary_starter_treats_each_team_position_pair_independently() -> None:
    candidates = [
        {"player_key": "LA:qb1", "team": "LA", "position": "QB", "vol": 3000.0},
        {"player_key": "LA:rb1", "team": "LA", "position": "RB", "vol": 900.0},
        {"player_key": "BUF:qb1", "team": "BUF", "position": "QB", "vol": 2800.0},
    ]
    survivors = select_primary_starter_per_team_position(candidates, volume_key="vol")
    assert {c["player_key"] for c in survivors} == {"LA:qb1", "LA:rb1", "BUF:qb1"}
