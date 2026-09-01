"""WNBA season engine package (Ch1 team prior shell)."""

from src.services.wnba_season_engine.priors import (
    ENGINE_VERSION,
    MINUTE_GRID_SUM,
    ODDS_SPORT_KEY,
    PAPER_SIM_S_SET,
    PLAYER_YEAR_WEIGHTS,
    PROP_PLAY_CAP_PER_SLATE,
    WNBA_TEAM_CARRY_SHRINK,
    YTD_SEASON,
)
from src.services.wnba_season_engine.team_prior import (
    apply_wnba_team_carry_shrink,
    documentation as team_prior_documentation,
    get_team_prior,
    load_team_prior_pack,
)

__all__ = [
    "ENGINE_VERSION",
    "WNBA_TEAM_CARRY_SHRINK",
    "YTD_SEASON",
    "PAPER_SIM_S_SET",
    "PLAYER_YEAR_WEIGHTS",
    "MINUTE_GRID_SUM",
    "PROP_PLAY_CAP_PER_SLATE",
    "ODDS_SPORT_KEY",
    "apply_wnba_team_carry_shrink",
    "get_team_prior",
    "load_team_prior_pack",
    "team_prior_documentation",
]
