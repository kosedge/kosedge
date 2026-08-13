"""Odds-lake open/close reduction + name join (no Postgres required)."""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.cfb_warehouse.odds_lake import (
    join_key,
    overlay_closing_lines,
    reduce_open_close,
)
from src.services.cfb_warehouse.pbp import PBP_CORE_COLUMNS


def test_post_kickoff_snapshot_is_not_the_close() -> None:
    snaps = [
        {
            "market": "spread",
            "book": "draftkings",
            "spread_home": -13.5,
            "captured_at": "2024-08-23T17:53:45+00:00",
        },
        {
            "market": "spread",
            "book": "draftkings",
            "spread_home": -10.5,
            "captured_at": "2024-08-31T15:50:00+00:00",
        },
        {
            "market": "spread",
            "book": "draftkings",
            "spread_home": -3.0,
            "captured_at": "2024-08-31T17:00:00+00:00",  # after kickoff
        },
    ]
    reduced = reduce_open_close(
        snaps,
        kickoff="2024-08-31T16:00:00+00:00",
        game_date="2024-08-31",
    )
    assert reduced["open_spread_home"] == -13.5
    assert reduced["close_spread_home"] == -10.5
    assert reduced["source"] == "odds_api_lake"


def test_same_timestamp_kickoff_is_not_available() -> None:
    snaps = [
        {
            "market": "spread",
            "book": "fanduel",
            "spread_home": -7.0,
            "captured_at": "2024-09-07T16:00:00+00:00",
        }
    ]
    reduced = reduce_open_close(
        snaps,
        kickoff="2024-09-07T16:00:00+00:00",
        game_date="2024-09-07",
    )
    assert reduced == {}


def test_name_join_georgia_clemson_does_not_drop_unmatched_year() -> None:
    games = [
        {
            "game_id": "401628323",
            "season": 2024,
            "week": 1,
            "game_date": "2024-08-31",
            "kickoff": "2024-08-31T16:00:00+00:00",
            "home_team_id": "UGA",
            "away_team_id": "CLEM",
            "home_name": "Georgia Bulldogs",
            "away_name": "Clemson Tigers",
        },
        {
            "game_id": "no-odds-2020",
            "season": 2020,
            "week": 1,
            "game_date": "2020-09-05",
            "kickoff": "2020-09-05T16:00:00+00:00",
            "home_team_id": "UAB",
            "away_team_id": "espn:1",
            "home_name": "UAB Blazers",
            "away_name": "Some FCS",
        },
    ]
    sdv_closes = [
        {
            "game_id": "401628323",
            "season": 2024,
            "close_spread_home": -10.5,
            "close_total": 49.5,
            "source": "sportsdataverse_espn_cfb_betting",
            "line_fidelity": "close_ish_resolved",
        },
        {
            "game_id": "no-odds-2020",
            "season": 2020,
            "close_spread_home": -21.0,
            "source": "sportsdataverse_espn_cfb_betting",
            "line_fidelity": "close_ish_resolved",
        },
    ]
    lake = [
        {
            "game_date": "2024-08-31",
            "home": "Georgia Bulldogs",
            "away": "Clemson Tigers",
            "market": "spread",
            "book": "draftkings",
            "spread_home": -13.5,
            "captured_at": "2024-08-23T17:53:45+00:00",
        },
        {
            "game_date": "2024-08-31",
            "home": "Georgia Bulldogs",
            "away": "Clemson Tigers",
            "market": "spread",
            "book": "draftkings",
            "spread_home": -11.0,
            "captured_at": "2024-08-31T15:00:00+00:00",
        },
    ]
    merged, stats = overlay_closing_lines(games, sdv_closes, lake)
    by_id = {r["game_id"]: r for r in merged}
    assert by_id["401628323"]["open_spread_home"] == -13.5
    assert by_id["401628323"]["close_spread_home"] == -11.0
    assert by_id["401628323"]["source"] == "odds_api_lake"
    # Unmatched 2020 game kept with SDV fill — no silent year drop.
    assert by_id["no-odds-2020"]["close_spread_home"] == -21.0
    assert by_id["no-odds-2020"]["source"] == "sportsdataverse_espn_cfb_betting"
    assert stats["matched"] == 1
    assert stats["unmatched"] == 1
    assert join_key("2024-08-31", "Georgia Bulldogs", "Clemson Tigers") == (
        "2024-08-31",
        "georgia bulldogs",
        "clemson tigers",
    )


def test_pbp_core_keeps_epa_success_state() -> None:
    joined = " ".join(PBP_CORE_COLUMNS)
    for token in ("EPA", "EPA_success", "rz_play", "stuffed_run", "game_id", "down"):
        assert token in joined
