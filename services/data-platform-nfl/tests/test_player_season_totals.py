from __future__ import annotations

from data_platform_nfl.player_season_totals import (
    FALLBACK_EXPECTED_GAMES_GIVEN_APPEARANCE,
    aggregate_weekly_projection_rows,
    apply_qb_starter_volume_lock,
    designate_qb_starter_shares,
    evaluate_season_pass_leader_quality,
)


def _week(pass_yards=0.0, rush_yards=0.0, rec_yards=0.0, receptions=0.0, pass_tds=0.0, rush_tds=0.0, rec_tds=0.0, anytime_td_prob=0.0):
    return {
        "pass_yards_mean": pass_yards,
        "rush_yards_mean": rush_yards,
        "receiving_yards_mean": rec_yards,
        "receptions_mean": receptions,
        "pass_tds_mean": pass_tds,
        "rush_tds_mean": rush_tds,
        "rec_tds_mean": rec_tds,
        "anytime_td_prob": anytime_td_prob,
    }


def test_games_projected_counts_real_weeks_only_not_a_flat_constant() -> None:
    # A player with only 3 real weekly rows (e.g. mid-season, or partial
    # slate) must NOT be silently forced to 18 -- the old frozen-file bug.
    weekly_rows = [_week(), _week(), _week()]
    totals = aggregate_weekly_projection_rows(weekly_rows)
    assert totals["games_projected"] == 3

    totals_full_season = aggregate_weekly_projection_rows([_week()] * 17)
    assert totals_full_season["games_projected"] == 17


def test_yardage_and_td_totals_sum_weekly_means() -> None:
    weekly_rows = [
        _week(pass_yards=250.0, rush_tds=1.0, anytime_td_prob=0.1),
        _week(pass_yards=300.0, rush_tds=0.0, anytime_td_prob=0.05),
        _week(pass_yards=200.0, rush_tds=2.0, anytime_td_prob=0.2),
    ]
    totals = aggregate_weekly_projection_rows(weekly_rows)
    assert totals["pass_yards_total"] == 750.0
    assert totals["rush_tds_total"] == 3.0


def test_anytime_td_prob_uses_at_least_one_game_formula_not_raw_sum() -> None:
    # Three weeks each with a 50% single-game TD probability should NOT sum
    # to 1.5 (an invalid probability) -- it should be the probability of
    # scoring in at least one of the three games: 1 - 0.5^3 = 0.875.
    weekly_rows = [_week(anytime_td_prob=0.5), _week(anytime_td_prob=0.5), _week(anytime_td_prob=0.5)]
    totals = aggregate_weekly_projection_rows(weekly_rows)
    assert totals["anytime_td_prob"] == round(1 - 0.5 ** 3, 4)
    assert 0.0 <= totals["anytime_td_prob"] <= 1.0


def test_anytime_td_prob_is_bounded_even_for_a_high_volume_bell_cow() -> None:
    # A player projected near-certain to score most weeks should still land
    # at a bounded probability, never exceeding 1.0 the way a raw sum would.
    weekly_rows = [_week(anytime_td_prob=0.85) for _ in range(17)]
    totals = aggregate_weekly_projection_rows(weekly_rows)
    assert totals["anytime_td_prob"] <= 1.0
    assert totals["anytime_td_prob"] > 0.99  # virtually certain across 17 games


def test_empty_weekly_rows_yields_zeroed_totals_with_zero_games() -> None:
    totals = aggregate_weekly_projection_rows([])
    assert totals["games_projected"] == 0
    assert totals["pass_yards_total"] == 0.0
    assert totals["anytime_td_prob"] == 0.0


def test_fallback_expected_playoff_games_matches_bracket_derivation() -> None:
    # 6 wildcard + 4 divisional + 2 conference-championship + 1 Super Bowl =
    # 13 games = 26 team-game appearances, spread over the 14 playoff teams.
    assert FALLBACK_EXPECTED_GAMES_GIVEN_APPEARANCE == 26.0 / 14.0
    assert 1.8 < FALLBACK_EXPECTED_GAMES_GIVEN_APPEARANCE < 1.9


def test_designate_qb_starter_shares_prefers_depth_one_with_prior() -> None:
    # CIN-shaped room: Burrow depth=1 with solid prior; Flacco depth=2 with
    # near-equal injury-year attempts must NOT stay co-primary.
    shares = designate_qb_starter_shares(
        player_ids=["burrow", "flacco"],
        depth_orders={"burrow": 1.0, "flacco": 2.0},
        prior_attempts={"burrow": 278.0, "flacco": 264.0},
    )
    assert shares["burrow"] > shares["flacco"]
    assert shares["burrow"] >= 0.90


def test_apply_qb_starter_volume_lock_clears_dual_full_volume_room() -> None:
    rows = [
        {
            "team": "CIN",
            "position": "QB",
            "player_id": "burrow",
            "player_name": "J.Burrow",
            "player_key": "burrow",
            "pass_yards_total": 2290.0,
            "pass_tds_total": 15.0,
            "rush_yards_total": 200.0,
            "rush_tds_total": 2.0,
            "receiving_yards_total": 0.0,
            "receptions_total": 0.0,
            "rec_tds_total": 0.0,
            "games_projected": 17,
            "anytime_td_prob": 0.5,
        },
        {
            "team": "CIN",
            "position": "QB",
            "player_id": "flacco",
            "player_name": "J.Flacco",
            "player_key": "flacco",
            "pass_yards_total": 3845.0,
            "pass_tds_total": 25.0,
            "rush_yards_total": 40.0,
            "rush_tds_total": 0.0,
            "receiving_yards_total": 0.0,
            "receptions_total": 0.0,
            "rec_tds_total": 0.0,
            "games_projected": 17,
            "anytime_td_prob": 0.4,
        },
        {
            "team": "CIN",
            "position": "WR",
            "player_id": "chase",
            "player_name": "J.Chase",
            "player_key": "chase",
            "pass_yards_total": 0.0,
            "pass_tds_total": 0.0,
            "rush_yards_total": 0.0,
            "rush_tds_total": 0.0,
            "receiving_yards_total": 1400.0,
            "receptions_total": 100.0,
            "rec_tds_total": 10.0,
            "games_projected": 17,
            "anytime_td_prob": 0.9,
        },
    ]
    locked, audit = apply_qb_starter_volume_lock(
        rows,
        depth_by_team={"CIN": {"burrow": 1.0, "flacco": 2.0}},
        prior_attempts_by_team={"CIN": {"burrow": 278.0, "flacco": 264.0}},
    )
    by_id = {r["player_id"]: r for r in locked if r["position"] == "QB"}
    assert by_id["burrow"]["pass_yards_total"] >= 3800.0
    assert by_id["flacco"]["pass_yards_total"] < 400.0
    assert audit["teams_locked"] == 1
    quality = evaluate_season_pass_leader_quality(locked)
    assert quality["dual_full_volume_qb_rooms_count"] == 0
    assert quality["publish_ready"] is True
