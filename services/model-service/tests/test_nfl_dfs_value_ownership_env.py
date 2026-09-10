from __future__ import annotations

from src.services.nfl_dfs_game_env import DfsGameMarketQuote, certify_game_market_quote, implied_team_total
from src.services.nfl_dfs_ownership import leverage_from_upside_and_own, unavailable_ownership
from src.services.nfl_dfs_value import points_per_1k, salary_relative_positional_value


def test_points_per_1k_is_transparent() -> None:
    assert points_per_1k(21.0, 7000) == 3.0
    assert points_per_1k(21.0, None) is None
    assert points_per_1k(21.0, 0) is None


def test_salary_relative_value_uses_same_slate_peers() -> None:
    valued = salary_relative_positional_value(
        projection=22.0,
        salary=7000,
        peer_salaries_and_projections=[(7000, 22.0), (6900, 18.0), (6800, 17.0)],
    )
    assert valued.points_per_1k == 3.1429
    assert valued.salary_rel_delta is not None
    assert valued.salary_rel_delta > 0
    assert valued.band_size >= 2


def test_ownership_stays_unavailable() -> None:
    own = unavailable_ownership(
        site="DK", season=2026, week=1, slate_id="151307", player_uid="uid-1"
    )
    public = own.as_public()
    assert public["status"] == "unavailable"
    assert public["projected_own"] is None
    assert public["leverage"] is None
    assert leverage_from_upside_and_own(upside_probability=0.3, expected_ownership=0.12) is None


def test_f5_quote_does_not_join_game_env() -> None:
    quote = DfsGameMarketQuote(
        event="buf-hou",
        sport="nfl",
        market="totals_1st_5_innings",
        period="1st5",
        side="over",
        line=3.5,
        book="draftkings",
        timestamp="2026-09-10T16:00:00Z",
        home_team="HOU",
        away_team="BUF",
        season=2026,
        week=1,
        commence_time="2026-09-13T17:00:00Z",
    )
    env = certify_game_market_quote(quote, season=2026, week=1, team="BUF", opponent="HOU")
    assert env.available is False
    assert env.reason == "period_not_fg"
    assert env.total is None


def test_wrong_event_market_fail_closed() -> None:
    quote = DfsGameMarketQuote(
        event="kc-lac",
        sport="nfl",
        market="totals",
        period="fg",
        side="over",
        line=47.5,
        book="fanduel",
        timestamp="2026-09-10T16:00:00Z",
        home_team="LAC",
        away_team="KC",
        season=2026,
        week=1,
        commence_time="2026-09-13T17:00:00Z",
    )
    env = certify_game_market_quote(quote, season=2026, week=1, team="BUF", opponent="HOU")
    assert env.available is False
    assert env.reason == "event_mismatch"


def test_missing_period_fail_closed() -> None:
    quote = DfsGameMarketQuote(
        event="buf-hou",
        sport="nfl",
        market="totals",
        period=None,
        side="over",
        line=44.5,
        book="draftkings",
        timestamp="2026-09-10T16:00:00Z",
        home_team="HOU",
        away_team="BUF",
        season=2026,
        week=1,
        commence_time="2026-09-13T17:00:00Z",
    )
    env = certify_game_market_quote(quote, season=2026, week=1, team="BUF", opponent="HOU")
    assert env.reason == "missing_period_identity"


def test_implied_team_total_from_certified_lines() -> None:
    assert implied_team_total(game_total=44.0, team_spread=-3.0) == 23.5
