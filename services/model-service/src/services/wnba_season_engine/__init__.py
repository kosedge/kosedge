"""WNBA season engine package (Ch1–Ch2 + Ch5 PlayerProjection)."""

from src.services.wnba_season_engine.priors import (
    ENGINE_VERSION,
    MINUTE_GRID_SUM,
    ODDS_SPORT_KEY,
    PAPER_SIM_S_SET,
    PLAYER_YEAR_WEIGHTS,
    PPG_BAND,
    PROP_PLAY_CAP_PER_SLATE,
    WNBA_TEAM_CARRY_SHRINK,
    WNBA_TEAM_REBASE_RESIDUAL_CAP,
    YTD_SEASON,
)
from src.services.wnba_season_engine.team_prior import (
    apply_wnba_team_carry_shrink,
    documentation as team_prior_documentation,
    get_team_prior,
    load_team_prior_pack,
)
from src.services.wnba_season_engine.roster_minutes import (
    documentation as roster_minutes_documentation,
    get_rebased_team,
    get_team_minutes,
    load_minutes_grid,
    load_player_talent_pack,
    load_rebased_team_prior,
)
from src.services.wnba_season_engine.player_projection import (
    VECTOR_KEYS,
    documentation as player_projection_documentation,
    get_player_projection,
    get_team_projections,
    load_player_projection_pack,
    team_pts_identity,
)

__all__ = [
    "ENGINE_VERSION",
    "WNBA_TEAM_CARRY_SHRINK",
    "WNBA_TEAM_REBASE_RESIDUAL_CAP",
    "YTD_SEASON",
    "PAPER_SIM_S_SET",
    "PLAYER_YEAR_WEIGHTS",
    "MINUTE_GRID_SUM",
    "PPG_BAND",
    "PROP_PLAY_CAP_PER_SLATE",
    "ODDS_SPORT_KEY",
    "VECTOR_KEYS",
    "apply_wnba_team_carry_shrink",
    "get_team_prior",
    "load_team_prior_pack",
    "team_prior_documentation",
    "get_rebased_team",
    "get_team_minutes",
    "load_minutes_grid",
    "load_player_talent_pack",
    "load_rebased_team_prior",
    "roster_minutes_documentation",
    "get_player_projection",
    "get_team_projections",
    "load_player_projection_pack",
    "team_pts_identity",
    "player_projection_documentation",
]
