"""Pure-logic tests for Projections Hub actuals aggregation."""

from __future__ import annotations

from data_platform_nfl.projection_actuals import (
    accumulate_player_game,
    accumulate_team_result,
    build_bundle_from_rows,
    empty_bundle,
    finalize_player_rows,
    validate_bundle,
)


def test_empty_bundle_shape():
    b = empty_bundle(2026)
    ok, errors = validate_bundle(b)
    assert ok and not errors
    assert b["teams"] == {}
    assert b["players"] == {}
    assert b["source"] == "empty_preseason_scaffold"


def test_team_wins_losses_ties():
    teams: dict = {}
    accumulate_team_result(teams, home="PHI", away="DAL", home_score=24, away_score=20)
    accumulate_team_result(teams, home="PHI", away="NYG", home_score=17, away_score=17)
    assert teams["PHI"] == {"wins": 1, "losses": 0, "ties": 1}
    assert teams["DAL"] == {"wins": 0, "losses": 1, "ties": 0}
    assert teams["NYG"] == {"wins": 0, "losses": 0, "ties": 1}


def test_player_alias_keys_stay_in_sync():
    players: dict = {}
    accumulate_player_game(
        players,
        player_keys=["00-0036389"],
        metrics={"passing_yards": 250, "passing_tds": 2},
    )
    accumulate_player_game(
        players,
        player_keys=["uid-abc", "00-0036389", "PHI:00-0036389"],
        metrics={"passing_yards": 300, "passing_tds": 1, "rushing_yards": 20},
    )
    finalized = finalize_player_rows(players)
    assert finalized["uid-abc"]["passYards"] == 550.0
    assert finalized["00-0036389"]["passYards"] == 550.0
    assert finalized["PHI:00-0036389"]["rushYards"] == 20.0
    assert finalized["uid-abc"]["passTds"] == 3.0


def test_skips_zero_skill_rows():
    players: dict = {}
    accumulate_player_game(
        players,
        player_keys=["cb-1"],
        metrics={"passing_yards": 0, "def_tackles_solo": 8},
    )
    assert players == {}


def test_build_bundle_filters_postseason_and_pre():
    bundle = build_bundle_from_rows(
        season=2025,
        schedule_rows=[
            {"home_team": "PHI", "away_team": "DAL", "home_score": 24, "away_score": 20, "week": 1},
            {"home_team": "PHI", "away_team": "KC", "home_score": 30, "away_score": 27, "week": 19},
        ],
        player_rows=[
            {
                "player_id": "00-1",
                "player_uid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                "team": "PHI",
                "week": 1,
                "metrics": {
                    "season_type": "REG",
                    "passing_yards": 280,
                    "passing_tds": 2,
                    "rushing_yards": 10,
                },
            },
            {
                "player_id": "00-1",
                "player_uid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                "team": "PHI",
                "week": 1,
                "metrics": {"season_type": "PRE", "passing_yards": 999, "passing_tds": 9},
            },
            {
                "player_id": "00-1",
                "player_uid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                "team": "PHI",
                "week": 19,
                "metrics": {"season_type": "POST", "passing_yards": 400, "passing_tds": 3},
            },
        ],
    )
    assert bundle["teams"]["PHI"]["wins"] == 1
    assert "KC" not in bundle["teams"]  # postseason excluded
    uid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    assert bundle["players"][uid]["passYards"] == 280.0
    assert bundle["players"]["00-1"]["passTds"] == 2.0
    assert bundle["players"]["PHI:00-1"]["rushYards"] == 10.0
