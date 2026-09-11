"""DFS game-environment join.

Reuses Edge Board period/event identity rules: full-game pregame totals and
spreads only. F5 / live / missing period / wrong event fail closed.
Never infer period from line magnitude.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional

from src.services.nfl_dfs_identity import canonical_team_code

GAME_ENV_VERSION = "nfl-dfs-game-env-v1"
FULL_GAME_PREGAME_PERIODS = {
    "fg",
    "fg_pregame",
    "full",
    "full_game",
    "full-game",
    "regulation",
    "game",
}
LIVE_PERIODS = {"fg_live", "live"}
FIRST_FIVE_PERIODS = {"1st5", "f5"}
FEATURED_FG_MARKETS = {"totals", "h2h", "spreads"}


@dataclass(frozen=True)
class DfsGameMarketQuote:
    event: Optional[str]
    sport: str
    market: str
    period: Optional[str]
    side: Optional[str]
    line: Optional[float]
    book: Optional[str]
    timestamp: Optional[str]
    home_team: Optional[str]
    away_team: Optional[str]
    season: Optional[int]
    week: Optional[int]
    commence_time: Optional[str]


@dataclass(frozen=True)
class DfsGameEnv:
    available: bool
    reason: str
    total: Optional[float] = None
    spread: Optional[float] = None
    implied_team_total: Optional[float] = None
    book: Optional[str] = None
    period: Optional[str] = None
    as_of: Optional[str] = None

    def as_public(self) -> Dict[str, Any]:
        payload = asdict(self)
        if not self.available:
            payload["total"] = None
            payload["spread"] = None
            payload["implied_team_total"] = None
        return payload


def _period_token(raw: Optional[str]) -> Optional[str]:
    if raw is None:
        return None
    token = str(raw).strip().lower()
    return token or None


def certify_game_market_quote(
    quote: DfsGameMarketQuote,
    *,
    season: int,
    week: int,
    team: str,
    opponent: str,
    sport: str = "nfl",
) -> DfsGameEnv:
    """Fail closed unless this is a certified FG pregame quote for this game."""
    if _period_token(quote.sport) not in {None, "nfl"} and _period_token(quote.sport) != _period_token(sport):
        return DfsGameEnv(False, "sport_mismatch")
    if quote.season is not None and int(quote.season) != int(season):
        return DfsGameEnv(False, "season_mismatch")
    if quote.week is not None and int(quote.week) != int(week):
        return DfsGameEnv(False, "week_mismatch")

    period = _period_token(quote.period)
    if period is None:
        return DfsGameEnv(False, "missing_period_identity")
    if period in LIVE_PERIODS:
        return DfsGameEnv(False, "in_play")
    if period in FIRST_FIVE_PERIODS:
        return DfsGameEnv(False, "period_not_fg")
    if period not in FULL_GAME_PREGAME_PERIODS:
        return DfsGameEnv(False, "period_not_fg")

    market = _period_token(quote.market)
    if market not in FEATURED_FG_MARKETS:
        return DfsGameEnv(False, "market_not_featured_fg")

    team_c = canonical_team_code(team)
    opp_c = canonical_team_code(opponent)
    home = canonical_team_code(quote.home_team)
    away = canonical_team_code(quote.away_team)
    if not team_c or not opp_c or not home or not away:
        return DfsGameEnv(False, "missing_event_teams")
    participants = {home, away}
    if team_c not in participants or opp_c not in participants:
        return DfsGameEnv(False, "event_mismatch")
    if {team_c, opp_c} != participants:
        return DfsGameEnv(False, "event_mismatch")

    return DfsGameEnv(
        available=True,
        reason="ok",
        total=quote.line if market == "totals" else None,
        spread=quote.line if market == "spreads" else None,
        book=quote.book,
        period=period,
        as_of=quote.timestamp,
    )


def implied_team_total(*, game_total: Optional[float], team_spread: Optional[float]) -> Optional[float]:
    """Implied team scoring from certified FG total + that team's spread.

    Spread is from the team's perspective (negative = favorite).
    """
    if game_total is None or team_spread is None:
        return None
    if game_total != game_total or team_spread != team_spread:
        return None
    if game_total <= 0:
        return None
    return round((float(game_total) / 2.0) - (float(team_spread) / 2.0), 3)


def join_game_environment(
    *,
    season: int,
    week: int,
    team: str,
    opponent: str,
    total_quote: Optional[DfsGameMarketQuote],
    spread_quote: Optional[DfsGameMarketQuote],
) -> DfsGameEnv:
    total_env = (
        certify_game_market_quote(total_quote, season=season, week=week, team=team, opponent=opponent)
        if total_quote
        else DfsGameEnv(False, "missing_total_quote")
    )
    spread_env = (
        certify_game_market_quote(spread_quote, season=season, week=week, team=team, opponent=opponent)
        if spread_quote
        else DfsGameEnv(False, "missing_spread_quote")
    )
    total = total_env.total if total_env.available else None
    spread = spread_env.spread if spread_env.available else None
    if total is None and spread is None:
        reason = total_env.reason if not total_env.available else spread_env.reason
        return DfsGameEnv(False, reason)
    implied = implied_team_total(game_total=total, team_spread=spread)
    return DfsGameEnv(
        available=True,
        reason="ok",
        total=total,
        spread=spread,
        implied_team_total=implied,
        book=total_env.book or spread_env.book,
        period="fg",
        as_of=total_env.as_of or spread_env.as_of,
    )
