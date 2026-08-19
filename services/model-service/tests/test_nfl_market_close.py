"""DK/FD stake close is the PLAY label; best-of-books is shop-only."""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.routes.nfl import _extract_book_market_prices
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
