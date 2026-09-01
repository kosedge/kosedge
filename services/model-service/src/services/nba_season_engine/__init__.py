"""NBA season engine package (Ch1 team prior shell + Ch2 roster×minutes)."""

from src.services.nba_season_engine.priors import (
    ENGINE_VERSION,
    MINUTE_GRID_SUM,
    PAPER_SIM_S_SET,
    PLAYER_YEAR_WEIGHTS,
    TEAM_CARRY_SHRINK,
    TEAM_REBASE_RESIDUAL_CAP,
)
from src.services.nba_season_engine.team_prior import (
    apply_team_carry_shrink,
    documentation as team_prior_documentation,
    get_team_prior,
    load_team_prior_pack,
)
from src.services.nba_season_engine.roster_minutes import (
    documentation as roster_minutes_documentation,
    get_rebased_team,
    get_team_minutes,
    load_minutes_grid,
    load_player_talent_pack,
    load_rebased_team_prior,
    load_transactions,
)

__all__ = [
    "ENGINE_VERSION",
    "TEAM_CARRY_SHRINK",
    "TEAM_REBASE_RESIDUAL_CAP",
    "PLAYER_YEAR_WEIGHTS",
    "MINUTE_GRID_SUM",
    "PAPER_SIM_S_SET",
    "apply_team_carry_shrink",
    "get_team_prior",
    "load_team_prior_pack",
    "team_prior_documentation",
    "get_rebased_team",
    "get_team_minutes",
    "load_minutes_grid",
    "load_player_talent_pack",
    "load_rebased_team_prior",
    "load_transactions",
    "roster_minutes_documentation",
]
