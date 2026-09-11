from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.services.odds_expansion import (
    LAKE_FIELDS,
    BookQuote,
    catalog_coverage,
    classify_polling_tier,
    event_has_verified_mainline,
    filter_ingestible_events,
    lake_row_from_wide_snapshot,
    multi_book_consensus,
    should_ingest_event,
    should_refresh_on_cadence,
    snapshot_kind_from_history,
)


NOW = datetime(2026, 9, 11, 18, 0, tzinfo=timezone.utc)

FAR_FUTURE = {
    "id": "evt_bowl",
    "sport_key": "americanfootball_ncaaf",
    "commence_time": "2027-01-01T00:00:00Z",
    "home_team": "Alabama Crimson Tide",
    "away_team": "Ohio State Buckeyes",
    "bookmakers": [
        {
            "key": "draftkings",
            "last_update": "2026-09-11T12:00:00Z",
            "markets": [
                {
                    "key": "spreads",
                    "outcomes": [
                        {"name": "Alabama Crimson Tide", "point": -3.5, "price": -110},
                        {"name": "Ohio State Buckeyes", "point": 3.5, "price": -110},
                    ],
                }
            ],
        }
    ],
}

NO_BOOKS = {
    "id": "evt_nobooks",
    "commence_time": "2026-12-01T18:00:00Z",
    "home_team": "A",
    "away_team": "B",
    "bookmakers": [],
}


def test_verified_mainline_required() -> None:
    assert event_has_verified_mainline(FAR_FUTURE) is True
    assert event_has_verified_mainline(NO_BOOKS) is False
    assert should_ingest_event(NO_BOOKS, now=NOW) is False


def test_no_current_week_filter_on_far_future() -> None:
    assert should_ingest_event(FAR_FUTURE, now=NOW) is True
    kept = filter_ingestible_events([FAR_FUTURE, NO_BOOKS], now=NOW)
    assert [e["id"] for e in kept] == ["evt_bowl"]


def test_catalog_coverage_does_not_week_filter() -> None:
    catalog = [
        FAR_FUTURE,
        {"id": "evt_later", "commence_time": "2026-12-15T18:00:00Z"},
    ]
    cov = catalog_coverage(catalog, [FAR_FUTURE], now=NOW)
    assert cov["week_filter"] is None
    assert cov["horizon"] == "all_available"
    assert cov["far_future_ingested"] == 1
    assert cov["catalog_missing_odds"] == 1


def test_polling_tiers_and_hooks() -> None:
    assert classify_polling_tier(NOW + timedelta(hours=2), now=NOW) == "final_hours"
    assert (
        classify_polling_tier(
            datetime(2026, 9, 12, 3, 30, tzinfo=timezone.utc), now=NOW
        )
        == "game_day"
    )
    assert classify_polling_tier(NOW + timedelta(days=3), now=NOW) == "d1_7"
    assert classify_polling_tier(NOW + timedelta(days=20), now=NOW) == "far_future"

    assert should_refresh_on_cadence("far_future", "hourly") is False
    assert should_refresh_on_cadence("far_future", "overnight") is True
    assert should_refresh_on_cadence("game_day", "hourly") is True
    assert should_refresh_on_cadence("far_future", "hourly", meaningful_movement=True) is False
    assert should_refresh_on_cadence("d1_7", "hourly", meaningful_movement=True) is True


def test_consensus_isolates_stale_and_rogue() -> None:
    fresh = NOW - timedelta(minutes=5)
    stale = NOW - timedelta(hours=20)
    quotes = [
        BookQuote("draftkings", -3.0, -110, fresh, "spread"),
        BookQuote("fanduel", -3.0, -108, fresh, "spread"),
        BookQuote("betmgm", -3.5, -110, fresh, "spread"),
        BookQuote("roguebook", -21.0, -110, fresh, "spread"),
        BookQuote("oldbook", -3.0, -110, stale, "spread"),
    ]
    result = multi_book_consensus(quotes, now=NOW)
    assert result.book_count >= 3
    assert "roguebook" in result.isolated_books
    assert "oldbook" in result.stale_books
    assert result.consensus_line is not None
    assert abs(result.consensus_line - -3.0) <= 0.5
    assert result.best_book != "oldbook"


def test_lake_fields_and_snapshot_kinds() -> None:
    first = NOW - timedelta(days=10)
    last = NOW
    assert snapshot_kind_from_history(
        captured_at=first, first_captured_at=first, last_captured_at=last
    ) == "OPEN"
    assert snapshot_kind_from_history(
        captured_at=last, first_captured_at=first, last_captured_at=last
    ) == "CURRENT"
    assert snapshot_kind_from_history(
        captured_at=last,
        first_captured_at=first,
        last_captured_at=last,
        is_last_pre_kickoff=True,
    ) == "CLOSE"
    rows = lake_row_from_wide_snapshot(
        sport="nfl",
        league="nfl",
        season=2026,
        canonical_game_id="g1",
        provider_event_id="evt_1",
        book="draftkings",
        market_type="spread",
        retrieved_at=NOW,
        market_as_of=NOW,
        event_start=NOW + timedelta(days=20),
        source="the-odds-api",
        spread_home=-3.0,
        spread_away=3.0,
        price_home=-110,
        price_away=-110,
    )
    assert len(rows) == 2
    assert all(name in rows[0] for name in LAKE_FIELDS)
    assert {r["side"] for r in rows} == {"home", "away"}
