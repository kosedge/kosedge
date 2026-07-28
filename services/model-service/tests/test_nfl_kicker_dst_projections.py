from __future__ import annotations

from src.services.nfl_kicker_dst_projections import (
    FG_BUCKET_POINTS,
    GAMES_PER_REGULAR_SEASON,
    allocate_attempts_to_buckets,
    compute_dst_season_fantasy_points,
    compute_kicker_season_fantasy_points,
    expected_points_allowed_fantasy_points_per_game,
    fantasy_points_from_field_goals,
    normal_cdf,
    project_kicker_fg_makes_by_bucket,
    project_pat_makes,
    project_team_fg_attempt_volume,
    project_team_points_allowed_mean,
    shrink_defense_stat_per_game,
    shrink_rate_empirical_bayes,
)


# ---------------------------------------------------------------------------
# FG-distance-bucket scoring
# ---------------------------------------------------------------------------


def test_fg_bucket_points_match_yahoo_default_convention() -> None:
    assert FG_BUCKET_POINTS["0_19"] == 3.0
    assert FG_BUCKET_POINTS["20_29"] == 3.0
    assert FG_BUCKET_POINTS["30_39"] == 3.0
    assert FG_BUCKET_POINTS["40_49"] == 4.0
    assert FG_BUCKET_POINTS["50_59"] == 5.0
    assert FG_BUCKET_POINTS["60_plus"] == 5.0


def test_fantasy_points_from_field_goals_sums_bucket_points() -> None:
    makes = {"0_19": 2.0, "20_29": 3.0, "30_39": 4.0, "40_49": 5.0, "50_59": 1.0, "60_plus": 0.0}
    # (2+3+4)*3 + 5*4 + 1*5 = 27 + 20 + 5 = 52
    assert fantasy_points_from_field_goals(makes) == 52.0


def test_compute_kicker_season_fantasy_points_adds_pat() -> None:
    makes = {"0_19": 10.0, "20_29": 0.0, "30_39": 0.0, "40_49": 0.0, "50_59": 0.0, "60_plus": 0.0}
    # 10 FGs * 3 pts + 20 PATs * 1 pt = 30 + 20 = 50
    assert compute_kicker_season_fantasy_points(fg_makes_by_bucket=makes, pat_makes=20.0) == 50.0


def test_shrink_rate_empirical_bayes_returns_league_rate_at_zero_attempts() -> None:
    # A rookie/thin-sample kicker with zero real career attempts in a bucket
    # is projected at exactly the league-average rate -- no special-casing.
    assert shrink_rate_empirical_bayes(sample_makes=0.0, sample_attempts=0.0, league_rate=0.62, prior_attempts=10.0) == 0.62


def test_shrink_rate_empirical_bayes_converges_to_real_rate_with_large_sample() -> None:
    # 200 real attempts should dominate a 10-attempt prior and land very
    # close to the real observed 90% make rate, not the 50% league average.
    shrunk = shrink_rate_empirical_bayes(sample_makes=180.0, sample_attempts=200.0, league_rate=0.50, prior_attempts=10.0)
    assert 0.87 < shrunk < 0.90


def test_shrink_rate_empirical_bayes_blends_thin_sample_toward_league_average() -> None:
    # A kicker who is 1-for-1 on 50+ yard attempts (a real but tiny sample)
    # should NOT be projected at 100% -- shrinkage should pull it most of
    # the way back toward the league-average long-FG rate.
    shrunk = shrink_rate_empirical_bayes(sample_makes=1.0, sample_attempts=1.0, league_rate=0.65, prior_attempts=10.0)
    assert 0.65 < shrunk < 0.80


def test_project_kicker_fg_makes_by_bucket_uses_shrunk_kicker_accuracy() -> None:
    team_attempts = {"0_19": 10.0, "20_29": 10.0, "30_39": 10.0, "40_49": 10.0, "50_59": 5.0, "60_plus": 1.0}
    # An elite, well-established kicker (large real career sample, high
    # accuracy in every bucket) should out-project a rookie with no history
    # (who gets projected at the league-average rate) in every bucket.
    elite_makes = project_kicker_fg_makes_by_bucket(
        team_attempts_by_bucket=team_attempts,
        kicker_career_makes_by_bucket={"0_19": 95.0, "20_29": 90.0, "30_39": 85.0, "40_49": 80.0, "50_59": 40.0, "60_plus": 4.0},
        kicker_career_attempts_by_bucket={"0_19": 100.0, "20_29": 100.0, "30_39": 100.0, "40_49": 100.0, "50_59": 50.0, "60_plus": 5.0},
        league_make_rate_by_bucket={"0_19": 0.98, "20_29": 0.95, "30_39": 0.88, "40_49": 0.80, "50_59": 0.65, "60_plus": 0.50},
    )
    rookie_makes = project_kicker_fg_makes_by_bucket(
        team_attempts_by_bucket=team_attempts,
        kicker_career_makes_by_bucket={},
        kicker_career_attempts_by_bucket={},
        league_make_rate_by_bucket={"0_19": 0.98, "20_29": 0.95, "30_39": 0.88, "40_49": 0.80, "50_59": 0.65, "60_plus": 0.50},
    )
    for bucket in ("40_49", "50_59", "60_plus"):
        assert elite_makes[bucket] >= rookie_makes[bucket]
    # Rookie should land at exactly the league rate x team attempts.
    assert rookie_makes["50_59"] == 5.0 * 0.65


def test_project_team_fg_attempt_volume_increases_for_red_zone_inefficient_team() -> None:
    baseline = project_team_fg_attempt_volume(
        team_fg_attempts_per_game_history=2.0,
        team_red_zone_td_rate=0.20,
        league_avg_red_zone_td_rate=0.20,
        games=16.0,
    )
    stalling_team = project_team_fg_attempt_volume(
        team_fg_attempts_per_game_history=2.0,
        team_red_zone_td_rate=0.10,  # scores TDs in the red zone half as often as league average
        league_avg_red_zone_td_rate=0.20,
        games=16.0,
    )
    efficient_team = project_team_fg_attempt_volume(
        team_fg_attempts_per_game_history=2.0,
        team_red_zone_td_rate=0.35,  # well above league average red-zone efficiency
        league_avg_red_zone_td_rate=0.20,
        games=16.0,
    )
    assert stalling_team > baseline > efficient_team


def test_allocate_attempts_to_buckets_preserves_total_and_favors_team_history() -> None:
    league_shares = {b: 1.0 / 6 for b in ("0_19", "20_29", "30_39", "40_49", "50_59", "60_plus")}
    result = allocate_attempts_to_buckets(
        total_attempts=60.0,
        team_bucket_makes={},
        team_bucket_attempts={"0_19": 50.0, "20_29": 50.0, "30_39": 50.0, "40_49": 0.0, "50_59": 0.0, "60_plus": 0.0},
        league_bucket_shares=league_shares,
    )
    assert abs(sum(result.values()) - 60.0) < 1e-6
    # A team with real history entirely in short buckets should get most of
    # its allocated attempts in short buckets, not the flat league split.
    assert result["0_19"] > result["50_59"]


def test_project_pat_makes_scales_with_team_offensive_tds() -> None:
    makes = project_pat_makes(team_offensive_tds_season=50.0, two_point_attempt_rate=0.02, league_pat_make_rate=0.94)
    # 50 TDs * (1 - 0.02) attempt rate * 0.94 make rate
    assert abs(makes - (50.0 * 0.98 * 0.94)) < 1e-6


# ---------------------------------------------------------------------------
# DST points-allowed tiering
# ---------------------------------------------------------------------------


def test_normal_cdf_matches_known_values_at_the_mean() -> None:
    assert abs(normal_cdf(20.0, mean=20.0, std=5.0) - 0.5) < 1e-9


def test_normal_cdf_degenerates_to_step_function_at_zero_std() -> None:
    assert normal_cdf(19.9, mean=20.0, std=0.0) == 0.0
    assert normal_cdf(20.0, mean=20.0, std=0.0) == 1.0
    assert normal_cdf(20.1, mean=20.0, std=0.0) == 1.0


def test_expected_points_allowed_fantasy_points_matches_tier_at_zero_variance() -> None:
    # With std -> 0, this should converge to exactly tiering the mean: 14-20
    # points allowed = 1 fantasy point.
    points = expected_points_allowed_fantasy_points_per_game(mean_points_allowed=17.0, std_points_allowed=0.01)
    assert abs(points - 1.0) < 0.05


def test_expected_points_allowed_fantasy_points_is_lower_for_worse_defense() -> None:
    elite_defense = expected_points_allowed_fantasy_points_per_game(mean_points_allowed=14.0, std_points_allowed=9.0)
    bad_defense = expected_points_allowed_fantasy_points_per_game(mean_points_allowed=28.0, std_points_allowed=9.0)
    assert elite_defense > bad_defense


def test_expected_points_allowed_fantasy_points_penalizes_variance_at_a_concave_tier_boundary() -> None:
    # Real distributional effect: two defenses with the SAME mean (21) score
    # differently once real game-to-game variance is modeled, because the
    # points-allowed tier payoff is concave (nonlinear) -- tiering the mean
    # alone would wrongly treat these as identical.
    steady_defense = expected_points_allowed_fantasy_points_per_game(mean_points_allowed=21.0, std_points_allowed=2.0)
    volatile_defense = expected_points_allowed_fantasy_points_per_game(mean_points_allowed=21.0, std_points_allowed=14.0)
    assert steady_defense != volatile_defense


def test_shrink_defense_stat_per_game_returns_league_average_with_no_history() -> None:
    assert shrink_defense_stat_per_game(stat_name="defensive_tds", team_total=0.0, team_games=0.0, league_avg_per_game=0.10) == 0.10


def test_shrink_defense_stat_per_game_shrinks_defensive_tds_harder_than_sacks() -> None:
    # Same real sample (10 games, double the league-average rate observed)
    # should shrink LESS for sacks (higher real predictability, lower prior
    # strength) than for defensive TDs (famously fluky, higher prior
    # strength) -- i.e. sacks should sit further from league average.
    sacks_shrunk = shrink_defense_stat_per_game(stat_name="sacks", team_total=2.0 * 2.5 * 10, team_games=10.0, league_avg_per_game=2.5)
    tds_shrunk = shrink_defense_stat_per_game(stat_name="defensive_tds", team_total=2.0 * 0.10 * 10, team_games=10.0, league_avg_per_game=0.10)
    sacks_gap_ratio = (sacks_shrunk - 2.5) / (2.0 * 2.5 - 2.5)
    tds_gap_ratio = (tds_shrunk - 0.10) / (2.0 * 0.10 - 0.10)
    assert sacks_gap_ratio > tds_gap_ratio


def test_project_team_points_allowed_mean_adjusts_for_defensive_epa() -> None:
    strong_defense = project_team_points_allowed_mean(
        team_points_allowed_per_game_history=22.0,
        team_epa_per_play_defense_allowed=-0.10,  # allows less EPA/play than league average
        league_avg_epa_per_play_defense_allowed=0.0,
    )
    weak_defense = project_team_points_allowed_mean(
        team_points_allowed_per_game_history=22.0,
        team_epa_per_play_defense_allowed=0.10,
        league_avg_epa_per_play_defense_allowed=0.0,
    )
    assert strong_defense < 22.0 < weak_defense


def test_compute_dst_season_fantasy_points_returns_component_breakdown_and_total() -> None:
    breakdown = compute_dst_season_fantasy_points(
        points_allowed_mean_per_game=18.0,
        points_allowed_std_per_game=9.0,
        sacks_per_game=2.5,
        interceptions_per_game=0.8,
        fumble_recoveries_per_game=0.5,
        defensive_tds_per_game=0.10,
        safeties_per_game=0.03,
        games=17.0,
    )
    assert set(breakdown.keys()) == {
        "points_allowed_component",
        "sacks_component",
        "interceptions_component",
        "fumble_recoveries_component",
        "touchdowns_component",
        "safeties_component",
        "total_points",
    }
    component_sum = sum(v for k, v in breakdown.items() if k != "total_points")
    assert abs(component_sum - breakdown["total_points"]) < 1e-3
    # A real, plausible full-season DST point total (see task sanity-check
    # convention: good DSTs land roughly 100-140 points in standard scoring).
    assert 60.0 < breakdown["total_points"] < 200.0


def test_compute_dst_season_fantasy_points_rewards_better_defense() -> None:
    elite = compute_dst_season_fantasy_points(
        points_allowed_mean_per_game=14.0,
        points_allowed_std_per_game=8.0,
        sacks_per_game=3.2,
        interceptions_per_game=1.1,
        fumble_recoveries_per_game=0.6,
        defensive_tds_per_game=0.12,
        safeties_per_game=0.03,
        games=GAMES_PER_REGULAR_SEASON,
    )
    poor = compute_dst_season_fantasy_points(
        points_allowed_mean_per_game=28.0,
        points_allowed_std_per_game=8.0,
        sacks_per_game=1.5,
        interceptions_per_game=0.4,
        fumble_recoveries_per_game=0.3,
        defensive_tds_per_game=0.05,
        safeties_per_game=0.01,
        games=GAMES_PER_REGULAR_SEASON,
    )
    assert elite["total_points"] > poor["total_points"]
