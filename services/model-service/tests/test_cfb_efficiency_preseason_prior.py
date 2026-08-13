"""Phase A leakage + garbage-time; Phase B prior season boundary."""

from __future__ import annotations

import math
import os

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.cfb_warehouse.efficiency_adj import (
    aggregate_team_games,
    assert_no_future_weeks,
    filter_plays_before_week,
    week_snapshots,
)
from src.services.cfb_warehouse.garbage import garbage_weight
from src.services.cfb_warehouse.preseason_prior import (
    assert_prior_season_boundary,
    combine_prior,
    program_component,
    season_weight,
)


def _play(**kwargs):
    base = {
        "season": 2024,
        "week": 1,
        "game_id": "g1",
        "pos_team": "Georgia Bulldogs",
        "def_pos_team": "Clemson Tigers",
        "EPA": 0.2,
        "EPA_success": True,
        "statYardage": 8,
        "pass": True,
        "rush": False,
        "scrimmage_play": True,
        "stuffed_run": False,
        "rz_play": False,
        "pos_score_diff": 0,
        "start.TimeSecsRem": 1200,
        "under_2": False,
        "half": 1,
    }
    base.update(kwargs)
    return base


def test_competitive_play_full_weight() -> None:
    assert garbage_weight(pos_score_diff=3, time_secs_rem=200, under_two=False, half=2) == 1.0


def test_deep_garbage_second_half_downweights() -> None:
    w = garbage_weight(pos_score_diff=28, time_secs_rem=120, under_two=True, half=2)
    assert w < 0.2
    assert w >= 0.10


def test_first_half_blowout_still_mostly_counts() -> None:
    w = garbage_weight(pos_score_diff=28, time_secs_rem=400, under_two=False, half=1)
    assert w >= 0.80


def test_week_w_features_exclude_week_ge_w_plays() -> None:
    plays = [
        _play(week=1, EPA=0.4, game_id="w1"),
        _play(week=2, EPA=9.9, game_id="w2", pos_team="Georgia Bulldogs"),
        _play(week=3, EPA=-9.9, game_id="w3"),
    ]
    kept = filter_plays_before_week(plays, season=2024, week=2)
    assert {p["week"] for p in kept} == {1}
    assert all(p["EPA"] != 9.9 for p in kept)

    games = aggregate_team_games(plays)
    snaps = week_snapshots(games, season=2024, weeks=[1, 2, 3])
    w2 = [r for r in snaps if r["as_of_week"] == 2 and r["team_id"] == "UGA"]
    assert w2 and w2[0]["max_week_included"] == 1
    assert w2[0]["feature_week"] == 1
    assert_no_future_weeks(w2, season=2024, week=2)
    w1 = [r for r in snaps if r["as_of_week"] == 1 and r["team_id"] == "UGA"]
    assert w1[0]["cold_start"] is True
    assert w1[0]["max_week_included"] == 0


def test_future_week_row_raises() -> None:
    with pytest.raises(ValueError, match="leakage"):
        assert_no_future_weeks(
            [{"team_id": "UGA", "max_week_included": 4}],
            season=2024,
            week=4,
        )


def test_fcs_plays_are_kept_and_flagged() -> None:
    plays = [
        _play(pos_team="Georgia Bulldogs", def_pos_team="Montana Grizzlies", week=1),
    ]
    games = aggregate_team_games(plays)
    assert len(games) == 1
    assert games[0]["fcs_opponent"] is True
    assert games[0]["team_id"] == "UGA"
    snaps = week_snapshots(games, season=2024, weeks=[2])
    assert all(not str(r["team_id"]).startswith("fcs:") for r in snaps)
    uga = [r for r in snaps if r["team_id"] == "UGA"]
    assert uga and uga[0]["fcs_games"] == 1


def test_prior_rejects_same_year_results() -> None:
    with pytest.raises(ValueError, match="leakage"):
        assert_prior_season_boundary(
            [{"season": 2026, "team_id": "UGA", "off_epa_adj": 0.4}],
            prior_year=2026,
        )
    assert season_weight(2026, 2026) == 0.0
    assert season_weight(2025, 2026) > season_weight(2016, 2026)


def test_program_prior_ignores_future_season() -> None:
    finals = [
        {"season": 2024, "team_id": "UGA", "off_epa_adj": 0.20, "def_epa_adj": -0.10},
        {"season": 2026, "team_id": "UGA", "off_epa_adj": 9.0, "def_epa_adj": -9.0},
    ]
    legal = [r for r in finals if r["season"] < 2026]
    prog = program_component(legal, "UGA", prior_year=2026)
    assert 2026 not in prog["seasons"]
    assert prog["net_epa"] == pytest.approx(0.30, abs=0.01)


def test_high_churn_qb_has_wider_sigma_than_incumbent_powerhouse() -> None:
    program = {"points": 8.0, "sigma": 2.5, "net_epa": 0.28, "seasons": [2024, 2025]}
    uga = combine_prior(
        team_id="UGA",
        prior_year=2026,
        program=program,
        roster_strength=78,
        returning_production=70,
        portal_out=20,
        qb_class="incumbent",
        new_hc=False,
        as_of="2026-08-12",
    )
    rebuild = combine_prior(
        team_id="BALL",
        prior_year=2026,
        program={"points": -6.0, "sigma": 5.0, "net_epa": -0.2, "seasons": [2024]},
        roster_strength=38,
        returning_production=28,
        portal_out=70,
        qb_class="true_freshman",
        new_hc=True,
        as_of="2026-08-12",
    )
    assert uga["mean_points"] > rebuild["mean_points"]
    assert rebuild["sigma_points"] > uga["sigma_points"]


def test_nan_epa_does_not_poison_adjustment() -> None:
    plays = [
        _play(week=1, EPA=0.30, game_id="g1"),
        _play(week=1, EPA=float("nan"), game_id="g2", pos_team="Clemson Tigers"),
        _play(week=1, EPA=0.10, game_id="g3", pos_team=None, def_pos_team="Georgia Bulldogs"),
    ]
    games = aggregate_team_games(plays)
    assert games
    assert all(math.isfinite(g["off_epa_raw"]) for g in games)
    snaps = week_snapshots(games, season=2024, weeks=[2])
    uga = [r for r in snaps if r["team_id"] == "UGA"]
    assert uga and math.isfinite(uga[0]["off_epa_adj"])


def test_project_game_reads_prior_without_changing_spread() -> None:
    from src.services.cfb_season_engine import (
        build_packaged_universe,
        project_game_preview,
        project_game_to_dict,
    )

    universe = build_packaged_universe(2026)
    proj = project_game_preview(
        universe, home_team="UGA", away_team="BALL", week=1, neutral_site=True
    )
    payload = project_game_to_dict(proj)
    assert payload["spread_home"] == proj.spread_home
    assert payload["home_win_prob"] == proj.home_win_prob
    assert payload["research_prior"]["used_in_spread"] is False
    assert payload["research_prior"]["season"] == 2026
