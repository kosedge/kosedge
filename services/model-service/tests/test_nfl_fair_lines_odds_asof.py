"""Fair-lines odds_as_of must never be datetime.now() / request clock."""

from __future__ import annotations

from src.routes.nfl import _event_odds_last_update, _max_odds_api_last_update


def test_max_odds_api_last_update_picks_latest_book_stamp() -> None:
    events = [
        {
            "bookmakers": [
                {
                    "key": "draftkings",
                    "last_update": "2026-09-02T16:00:00Z",
                    "markets": [
                        {"key": "spreads", "last_update": "2026-09-02T16:05:00Z"}
                    ],
                },
                {
                    "key": "fanduel",
                    "last_update": "2026-09-02T17:00:00Z",
                    "markets": [{"key": "spreads"}],
                },
            ]
        }
    ]
    assert _max_odds_api_last_update(events) == "2026-09-02T17:00:00Z"
    assert _event_odds_last_update(events[0]) == "2026-09-02T17:00:00Z"


def test_max_odds_api_last_update_blank_when_no_last_update() -> None:
    events = [
        {
            "bookmakers": [
                {
                    "key": "draftkings",
                    "markets": [{"key": "spreads", "outcomes": []}],
                }
            ]
        }
    ]
    assert _max_odds_api_last_update(events) is None
    assert _max_odds_api_last_update([]) is None
    assert _max_odds_api_last_update(None) is None
