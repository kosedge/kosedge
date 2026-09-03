"""DK/FD stake close is the PLAY label; best-of-books is shop-only."""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.routes.nfl import (
    NFL_DEFAULT_ODDS_BOOKMAKERS,
    NFL_ODDS_API_CARRIED_BOOKMAKERS,
    NFL_ODDS_REGIONS,
    _extract_book_market_prices,
    _resolve_nfl_odds_bookmakers_for_request,
)
from src.services.nfl_market_close import stake_close_spread


def test_stake_close_prefers_draftkings_then_fanduel() -> None:
    value, book = stake_close_spread(draftkings=-6.5, fanduel=-3.0, consensus=-4.0, best=-2.5)
    assert value == -6.5
    assert book == "draftkings"
    value, book = stake_close_spread(fanduel=-3.0, consensus=-4.0, best=-2.5)
    assert value == -3.0
    assert book == "fanduel"
    value, book = stake_close_spread(consensus=-4.0, best=-2.5)
    assert value == -4.0
    assert book == "consensus"


def test_extract_play_compare_uses_dk_not_shop_best() -> None:
    event = {
        "home_team": "Kansas City Chiefs",
        "away_team": "Buffalo Bills",
        "bookmakers": [
            {
                "key": "draftkings",
                "markets": [
                    {
                        "key": "spreads",
                        "outcomes": [
                            {"name": "Kansas City Chiefs", "point": -6.5, "price": -110},
                            {"name": "Buffalo Bills", "point": 6.5, "price": -110},
                        ],
                    }
                ],
            },
            {
                "key": "fanatics",
                "markets": [
                    {
                        "key": "spreads",
                        "outcomes": [
                            {"name": "Kansas City Chiefs", "point": -8.0, "price": -105},
                            {"name": "Buffalo Bills", "point": 8.0, "price": -115},
                        ],
                    }
                ],
            },
        ],
    }
    out = _extract_book_market_prices(event)
    assert out["dk_spread_home"] == -6.5
    assert out["stake_spread_home"] == -6.5
    assert out["stake_spread_book"] == "draftkings"
    assert out["best_spread_home"] == -8.0


def test_extract_consensus_is_mode_not_average() -> None:
    event = {
        "home_team": "Seattle Seahawks",
        "away_team": "New England Patriots",
        "bookmakers": [
            {
                "key": "draftkings",
                "markets": [
                    {
                        "key": "spreads",
                        "outcomes": [
                            {"name": "Seattle Seahawks", "point": -3.5, "price": -110},
                            {"name": "New England Patriots", "point": 3.5, "price": -110},
                        ],
                    },
                    {
                        "key": "totals",
                        "outcomes": [
                            {"name": "Over", "point": 44.5, "price": -110},
                            {"name": "Under", "point": 44.5, "price": -110},
                        ],
                    },
                ],
            },
            {
                "key": "fanduel",
                "markets": [
                    {
                        "key": "spreads",
                        "outcomes": [
                            {"name": "Seattle Seahawks", "point": -4.0, "price": -110},
                            {"name": "New England Patriots", "point": 4.0, "price": -110},
                        ],
                    },
                    {
                        "key": "totals",
                        "outcomes": [
                            {"name": "Over", "point": 44.5, "price": -110},
                            {"name": "Under", "point": 44.5, "price": -110},
                        ],
                    },
                ],
            },
            {
                "key": "betmgm",
                "markets": [
                    {
                        "key": "spreads",
                        "outcomes": [
                            {"name": "Seattle Seahawks", "point": -3.5, "price": -110},
                            {"name": "New England Patriots", "point": 3.5, "price": -110},
                        ],
                    },
                ],
            },
        ],
    }
    out = _extract_book_market_prices(event)
    assert out["market_spread_home"] == -3.5  # not AVG −3.67
    assert out["market_total"] == 44.5
    assert out["best_spread_home"] == -3.5 or out["best_spread_home"] == -4.0


def test_extract_best_ignores_not_carried_books_and_prefers_fresher_tie() -> None:
    """circa is designated but not on Odds API — must not win Best Line."""
    event = {
        "home_team": "Seattle Seahawks",
        "away_team": "New England Patriots",
        "bookmakers": [
            {
                "key": "draftkings",
                "last_update": "2026-09-02T16:00:00Z",
                "markets": [
                    {
                        "key": "spreads",
                        "outcomes": [
                            {"name": "Seattle Seahawks", "point": -3.5, "price": -110},
                            {"name": "New England Patriots", "point": 3.5, "price": -110},
                        ],
                    }
                ],
            },
            {
                "key": "fanduel",
                "last_update": "2026-09-02T17:00:00Z",
                "markets": [
                    {
                        "key": "spreads",
                        "outcomes": [
                            {"name": "Seattle Seahawks", "point": -3.5, "price": -110},
                            {"name": "New England Patriots", "point": 3.5, "price": -110},
                        ],
                    }
                ],
            },
            {
                "key": "circa",
                "last_update": "2026-09-02T18:00:00Z",
                "markets": [
                    {
                        "key": "spreads",
                        "outcomes": [
                            {"name": "Seattle Seahawks", "point": -7.0, "price": -105},
                            {"name": "New England Patriots", "point": 7.0, "price": -115},
                        ],
                    }
                ],
            },
        ],
    }
    out = _extract_book_market_prices(event)
    assert out["best_spread_home"] == -3.5
    assert out["best_spread_book"] == "fanduel"


def test_nfl_odds_request_carried_nine_excludes_not_carried() -> None:
    """Request path pulls nine carried keys; bet365/circa/betr stay UI-only."""
    request_books = _resolve_nfl_odds_bookmakers_for_request(None).split(",")
    carried = [b.strip() for b in NFL_ODDS_API_CARRIED_BOOKMAKERS.split(",") if b.strip()]
    designated = [b.strip() for b in NFL_DEFAULT_ODDS_BOOKMAKERS.split(",") if b.strip()]
    assert len(designated) == 12
    assert len(carried) == 9
    assert request_books == carried
    assert "bovada" in request_books
    assert "williamhill_us" in request_books
    assert "betonlineag" in request_books
    assert "bet365" not in request_books
    assert "circa" not in request_books
    assert "betr" not in request_books
    assert NFL_ODDS_REGIONS == "us,us2"
    assert "theScore" not in NFL_DEFAULT_ODDS_BOOKMAKERS
    assert "thescore" not in NFL_DEFAULT_ODDS_BOOKMAKERS.lower()
    assert "espnbet" not in NFL_DEFAULT_ODDS_BOOKMAKERS

