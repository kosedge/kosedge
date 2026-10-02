"""2022 close-recovery contract: leakage, orientation, conflicts, no scoring."""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.cfb_season_engine.priors import MATCHUP_RESPONSE
from src.services.cfb_season_engine.qb_feature_contract import QB_FEATURE_CONTRACT_VERSION
from src.services.cfb_warehouse.close_recovery_2022 import (
    TRAIN0_GATE,
    filter_2022_lake,
    join_2022_closes,
    locate_lake_sources,
    resolve_lake_snaps_for_game,
)
from src.services.cfb_warehouse.odds_lake import join_key, reduce_open_close


def _game(**overrides):
    row = {
        "game_id": "g1",
        "season": 2022,
        "week": 3,
        "game_date": "2022-09-17",
        "kickoff": "2022-09-17T16:00:00+00:00",
        "home_team_id": "ALA",
        "away_team_id": "UGA",
        "home_name": "Alabama Crimson Tide",
        "away_name": "Georgia Bulldogs",
        "fcs_home": False,
        "fcs_away": False,
        "home_score": 24,
        "away_score": 27,
    }
    row.update(overrides)
    return row


def test_coefficients_and_contract_untouched() -> None:
    assert MATCHUP_RESPONSE == 1.40
    assert QB_FEATURE_CONTRACT_VERSION == "cfb-qb-feature-v1"
    assert TRAIN0_GATE == 700


def test_close_is_last_legal_pre_kick_not_opener() -> None:
    snaps = [
        {
            "market": "spread",
            "book": "draftkings",
            "spread_home": -6.5,
            "captured_at": "2022-09-10T12:00:00+00:00",
        },
        {
            "market": "spread",
            "book": "draftkings",
            "spread_home": -7.5,
            "captured_at": "2022-09-16T18:00:00+00:00",
        },
        {
            "market": "spread",
            "book": "draftkings",
            "spread_home": -3.0,
            "captured_at": "2022-09-17T17:00:00+00:00",
        },
    ]
    reduced = reduce_open_close(
        snaps,
        kickoff="2022-09-17T16:00:00+00:00",
        game_date="2022-09-17",
    )
    assert reduced["open_spread_home"] == -6.5
    assert reduced["close_spread_home"] == -7.5
    assert reduced["source"] == "odds_api_lake"


def test_same_timestamp_kickoff_is_not_a_close() -> None:
    snaps = [
        {
            "market": "spread",
            "book": "draftkings",
            "spread_home": -3.5,
            "captured_at": "2022-09-17T16:00:00+00:00",
        }
    ]
    assert reduce_open_close(snaps, kickoff="2022-09-17T16:00:00+00:00", game_date="2022-09-17") == {}


def test_does_not_silently_pick_dual_date_skew() -> None:
    game = _game()
    by_key = {
        ("2022-09-16", "alabama crimson tide", "georgia bulldogs"): [
            {"market": "spread", "book": "draftkings", "spread_home": -3.0, "captured_at": "2022-09-16T12:00:00+00:00"}
        ],
        ("2022-09-18", "alabama crimson tide", "georgia bulldogs"): [
            {"market": "spread", "book": "draftkings", "spread_home": -10.0, "captured_at": "2022-09-16T12:00:00+00:00"}
        ],
    }
    attach = resolve_lake_snaps_for_game(game, by_key)
    assert attach["snaps"] == []
    assert "CONFLICT_DATE_SKEW" in attach["reasons"]


def test_refuses_silent_home_away_flip() -> None:
    game = _game()
    by_key = {
        join_key("2022-09-17", "Georgia Bulldogs", "Alabama Crimson Tide"): [
            {
                "market": "spread",
                "book": "draftkings",
                "spread_home": 7.5,
                "captured_at": "2022-09-17T12:00:00+00:00",
            }
        ]
    }
    attach = resolve_lake_snaps_for_game(game, by_key)
    assert attach["snaps"] == []
    assert "ORIENTATION_FLIP_CANDIDATE" in attach["reasons"]


def test_conflict_multi_game_excludes_both() -> None:
    games = [
        _game(game_id="a"),
        _game(game_id="b"),
    ]
    lake = [
        {
            "game_date": "2022-09-17",
            "home": "Alabama Crimson Tide",
            "away": "Georgia Bulldogs",
            "season": 2022,
            "market": "spread",
            "book": "draftkings",
            "spread_home": -7.5,
            "captured_at": "2022-09-17T12:00:00+00:00",
            "source": "the-odds-api-historical-enterprise",
        }
    ]
    audit = join_2022_closes(games, [], lake, layer_a_codes={"ALA", "UGA"})
    assert audit["duplicates"]["conflict_multi_game"] == 2
    assert audit["train0_n_lake"] == 0
    assert all("CONFLICT_MULTI_GAME" in r["reason_codes"] for r in audit["joined"])


def test_fcs_excluded_from_train0_separately() -> None:
    games = [
        _game(
            game_id="fcs",
            away_team_id="espn:999",
            away_name="Some FCS",
            fcs_away=True,
        )
    ]
    lake = [
        {
            "game_date": "2022-09-17",
            "home": "Alabama Crimson Tide",
            "away": "Some FCS",
            "season": 2022,
            "market": "spread",
            "book": "draftkings",
            "spread_home": -35.5,
            "total_points": 55.5,
            "captured_at": "2022-09-17T12:00:00+00:00",
            "source": "the-odds-api-historical-enterprise",
        }
    ]
    audit = join_2022_closes(games, [], lake, layer_a_codes={"ALA"})
    row = audit["joined"][0]
    assert row["valid_pregame_lake_close"] is True
    assert row["fbs_fbs"] is False
    assert row["train0_lake"] is False
    assert "FCS_AWAY" in row["reason_codes"]
    assert audit["fcs_exclusions"]["fcs_away"] == 1


def test_train0_counts_legitimate_fbs_close_actual() -> None:
    games = [_game(home_score=20, away_score=17)]
    sdv = [
        {
            "game_id": "g1",
            "close_spread_home": -6.0,
            "close_total": 49.0,
            "source": "sportsdataverse_espn_cfb_betting",
        }
    ]
    lake = [
        {
            "game_date": "2022-09-17",
            "home": "Alabama Crimson Tide",
            "away": "Georgia Bulldogs",
            "season": 2022,
            "market": "spread",
            "book": "draftkings",
            "spread_home": -7.5,
            "total_points": 52.5,
            "captured_at": "2022-09-17T12:00:00+00:00",
            "source": "the-odds-api-historical-enterprise",
        },
        {
            "game_date": "2022-09-17",
            "home": "Alabama Crimson Tide",
            "away": "Georgia Bulldogs",
            "season": 2022,
            "market": "total",
            "book": "draftkings",
            "total_points": 52.5,
            "captured_at": "2022-09-17T12:00:00+00:00",
            "source": "the-odds-api-historical-enterprise",
        },
    ]
    audit = join_2022_closes(games, sdv, lake, layer_a_codes={"ALA", "UGA"})
    row = audit["joined"][0]
    assert row["raw_lake_spread"] == -7.5
    assert row["raw_sdv_spread"] == -6.0
    assert row["close_spread_home"] == -7.5
    assert row["close_total"] == 52.5
    assert row["close_source"] == "odds_api_lake"
    assert row["train0_lake"] is True
    assert audit["funnel"]["raw_events"] == 1
    assert audit["funnel"]["valid_pregame_closes"] == 1
    assert audit["funnel"]["train0_close_actual_lake"] == 1
    assert audit["leakage"]["ok"] is True


def test_2025_snaps_are_stripped() -> None:
    snaps = [
        {"season": 2025, "game_date": "2025-09-06", "home": "A", "away": "B"},
        {"season": 2022, "game_date": "2022-09-17", "home": "A", "away": "B"},
    ]
    kept = filter_2022_lake(snaps)
    assert len(kept) == 1
    assert int(kept[0]["season"]) == 2022


def test_locate_does_not_claim_live_odds_api() -> None:
    loc = locate_lake_sources()
    live = [t for t in loc["tried"] if t["id"] == "odds_api_live_historical"][0]
    assert live["skipped"] is True
    assert live["present"] is False


def test_post_kick_does_not_enter_train0() -> None:
    games = [_game()]
    lake = [
        {
            "game_date": "2022-09-17",
            "home": "Alabama Crimson Tide",
            "away": "Georgia Bulldogs",
            "season": 2022,
            "market": "spread",
            "book": "draftkings",
            "spread_home": -1.5,
            "captured_at": "2022-09-17T20:00:00+00:00",
            "source": "the-odds-api-historical-enterprise",
        }
    ]
    audit = join_2022_closes(games, [], lake, layer_a_codes={"ALA", "UGA"})
    assert audit["joined"][0]["train0_lake"] is False
    assert "POST_KICK_ONLY" in audit["joined"][0]["reason_codes"]
    assert audit["funnel"]["valid_pregame_closes"] == 0
