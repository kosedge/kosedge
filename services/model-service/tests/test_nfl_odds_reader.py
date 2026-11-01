"""Synthetic boundary tests for the local NFL odds reader + cutoff join."""

from __future__ import annotations

from datetime import datetime, timezone

from src.services.nfl_odds_reader import (
    AMBIGUOUS_IDENTITY,
    DUPLICATE_CONFLICT,
    INCOMPATIBLE_MARKET,
    MARKET_LINE_MISMATCH,
    MISSING_CUTOFF,
    MISSING_VALUE,
    POST_CUTOFF,
    UNRESOLVABLE_TIMESTAMP,
    classify_market,
    join_quotes_at_cutoff,
    line_for_side,
    normalize_quote_timestamp,
    resolve_team_identity,
    season_from_commence,
)


CUTOFF = "2020-09-10T20:00:00Z"
KICKOFF = "2020-09-10T20:20:00Z"

GAME = {
    "game_id": "2020_01_HOU_KC",
    "event_id": "evt-kc-hou",
    "season": 2020,
    "game_date": "2020-09-10",
    "home_team": "KC",
    "away_team": "HOU",
    "kickoff": KICKOFF,
    "forecast_cutoff": CUTOFF,
}


def _quote(**overrides):
    row = {
        "event_id": "evt-kc-hou",
        "season": 2020,
        "game_date": "2020-09-10",
        "home": "Kansas City Chiefs",
        "away": "Houston Texans",
        "book": "draftkings",
        "market": "spreads",
        "spread_home": -9.5,
        "price_home": -110,
        "price_away": -110,
        "captured_at": "2020-09-10T19:50:00Z",
        "snapshot_kind": "mid",
        "source": "synthetic",
        "provenance": "test",
    }
    row.update(overrides)
    return row


def test_home_favorite_spread_keeps_odds_api_sign_and_away_flip_is_explicit() -> None:
    assert line_for_side(-9.5, "home") == -9.5
    assert line_for_side(-9.5, "away") == 9.5
    result = join_quotes_at_cutoff([_quote(spread_home=-9.5)], [GAME], CUTOFF)
    assert len(result.eligible) == 1
    assert result.eligible[0].spread_home == -9.5
    assert line_for_side(result.eligible[0].spread_home, "away") == 9.5


def test_home_dog_spread_is_positive_and_does_not_silently_flip() -> None:
    result = join_quotes_at_cutoff([_quote(spread_home=3.5)], [GAME], CUTOFF)
    assert result.eligible[0].spread_home == 3.5
    assert line_for_side(result.eligible[0].spread_home, "home") == 3.5
    assert line_for_side(result.eligible[0].spread_home, "away") == -3.5


def test_alias_city_tokens_are_ambiguous_and_do_not_acquire() -> None:
    assert resolve_team_identity("Los Angeles").status == "ambiguous"
    assert resolve_team_identity("New York").status == "ambiguous"
    assert resolve_team_identity("NY").status == "ambiguous"
    assert resolve_team_identity("Los Angeles Rams").abbr == "LA"
    assert resolve_team_identity("LAR").abbr == "LA"
    assert resolve_team_identity("LAC").abbr == "LAC"
    assert resolve_team_identity("NYG").abbr == "NYG"
    assert resolve_team_identity("Washington Football Team").abbr == "WAS"

    quotes = [_quote(home="Los Angeles", away="Kansas City Chiefs")]
    games = [{**GAME, "event_id": "", "home_team": "LA", "away_team": "KC"}]
    result = join_quotes_at_cutoff(quotes, games, CUTOFF)
    assert result.eligible == []
    assert result.reason_tallies[AMBIGUOUS_IDENTITY] == 1


def test_post_cutoff_quote_is_rejected_and_later_close_is_not_substituted() -> None:
    quotes = [
        _quote(spread_home=-3.5, captured_at="2020-09-10T19:00:00Z", snapshot_kind="open"),
        _quote(spread_home=-7.5, captured_at="2020-09-10T20:00:00Z", snapshot_kind="mid"),
        _quote(spread_home=-9.5, captured_at="2020-09-10T20:15:00Z", snapshot_kind="close"),
    ]
    result = join_quotes_at_cutoff(quotes, [GAME], CUTOFF)
    assert [q.spread_home for q in result.eligible] == [-3.5, -7.5]
    assert result.reason_tallies[POST_CUTOFF] == 1
    latest = result.latest_per_book_market
    assert len(latest) == 1
    assert latest[0].spread_home == -7.5
    assert latest[0].captured_at.endswith("20:00:00Z")


def test_quote_exactly_at_cutoff_is_eligible() -> None:
    result = join_quotes_at_cutoff(
        [_quote(captured_at="2020-09-10T20:00:00+00:00")],
        [GAME],
        "2020-09-10T20:00:00Z",
    )
    assert len(result.eligible) == 1


def test_offset_timestamp_normalizes_to_utc_before_cutoff_compare() -> None:
    dt = normalize_quote_timestamp("2020-09-10T16:00:00-04:00")
    assert dt == datetime(2020, 9, 10, 20, 0, tzinfo=timezone.utc)
    result = join_quotes_at_cutoff(
        [_quote(captured_at="2020-09-10T16:00:00-04:00")],
        [GAME],
        "2020-09-10T20:00:00Z",
    )
    assert len(result.eligible) == 1
    assert result.eligible[0].captured_at == "2020-09-10T20:00:00Z"


def test_same_timestamp_on_different_games_is_not_a_conflict() -> None:
    other_game = {
        "game_id": "2020_01_NYJ_BUF",
        "event_id": "evt-buf-nyj",
        "season": 2020,
        "game_date": "2020-09-10",
        "home_team": "BUF",
        "away_team": "NYJ",
        "forecast_cutoff": CUTOFF,
    }
    quotes = [
        _quote(event_id="evt-kc-hou", home="KC", away="HOU", spread_home=-9.5),
        _quote(
            event_id="evt-buf-nyj",
            home="BUF",
            away="NYJ",
            spread_home=-2.5,
        ),
    ]
    result = join_quotes_at_cutoff(quotes, [GAME, other_game], CUTOFF)
    assert len(result.eligible) == 2
    assert DUPLICATE_CONFLICT not in result.reason_tallies


def test_duplicate_identical_quotes_keep_one() -> None:
    quotes = [_quote(), _quote()]
    result = join_quotes_at_cutoff(quotes, [GAME], CUTOFF)
    assert len(result.eligible) == 1
    assert result.identical_duplicate_n == 1
    assert DUPLICATE_CONFLICT not in result.reason_tallies


def test_duplicate_conflict_same_timestamp_different_line_is_excluded() -> None:
    quotes = [
        _quote(spread_home=-3.5, price_home=-110),
        _quote(spread_home=-4.0, price_home=-105),
    ]
    result = join_quotes_at_cutoff(quotes, [GAME], CUTOFF)
    assert result.eligible == []
    assert result.reason_tallies[DUPLICATE_CONFLICT] == 2


def test_missing_cutoff_and_missing_values_do_not_acquire() -> None:
    no_cutoff = join_quotes_at_cutoff([_quote()], [{**GAME, "forecast_cutoff": None}], None)
    assert no_cutoff.eligible == []
    assert no_cutoff.reason_tallies[MISSING_CUTOFF] == 1

    missing_book = join_quotes_at_cutoff([_quote(book="")], [GAME], CUTOFF)
    assert missing_book.reason_tallies[MISSING_VALUE] == 1

    bad_ts = join_quotes_at_cutoff([_quote(captured_at="not-a-time")], [GAME], CUTOFF)
    assert bad_ts.reason_tallies[UNRESOLVABLE_TIMESTAMP] == 1


def test_market_and_line_mismatch_rejected() -> None:
    assert classify_market("spreads") == "mainline"
    assert classify_market("player_pass_yds") == "prop"
    assert classify_market("spreads_h1") == "period"

    prop = join_quotes_at_cutoff([_quote(market="player_pass_yds", point=275.5)], [GAME], CUTOFF)
    assert prop.reason_tallies[INCOMPATIBLE_MARKET] == 1

    period = join_quotes_at_cutoff([_quote(market="spreads_h1", point=-3.5)], [GAME], CUTOFF)
    assert period.reason_tallies[INCOMPATIBLE_MARKET] == 1

    spread_no_line = join_quotes_at_cutoff(
        [_quote(spread_home=None, point=None, market="spreads")],
        [GAME],
        CUTOFF,
    )
    assert spread_no_line.reason_tallies[MARKET_LINE_MISMATCH] == 1

    moneyline_with_point = join_quotes_at_cutoff(
        [_quote(market="h2h", point=-3.5, price_home=-150, spread_home=None)],
        [GAME],
        CUTOFF,
    )
    assert moneyline_with_point.reason_tallies[MARKET_LINE_MISMATCH] == 1


def test_season_bound_uses_february_super_bowl_rule() -> None:
    assert season_from_commence("2024-02-11T23:30:00Z") == 2023
    assert season_from_commence("2024-09-05T00:20:00Z") == 2024
    late = join_quotes_at_cutoff(
        [_quote()],
        [{**GAME, "season": 2024}],
        CUTOFF,
    )
    assert late.eligible == []
    assert late.reason_tallies["season_out_of_bounds"] == 1
