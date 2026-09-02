"""NHL season engine package (Ch1 team prior + Ch2 TOI/tandem)."""

from src.services.nhl_season_engine.priors import (
    ENGINE_VERSION,
    NHL_GOALIE_TANDEM_SHARE_SUM,
    NHL_TEAM_CARRY_SHRINK,
    NHL_TOI_GRID_SKATER_MINUTES,
    ODDS_SPORT_KEY,
    PAPER_SIM_S_SET,
    PLAYER_YEAR_WEIGHTS,
    PLAYER_YEAR_WEIGHTS_BY_SEASON_ID,
    PROP_PLAY_CAP_PER_SLATE,
    STARTER_GATE,
)
from src.services.nhl_season_engine.team_prior import (
    apply_nhl_team_carry_shrink,
    documentation as team_prior_documentation,
    get_team_prior,
    load_team_prior_pack,
)
from src.services.nhl_season_engine.toi_grid import (
    documentation as toi_grid_documentation,
    get_team_goalie_tandem,
    get_team_toi,
    load_goalie_tandem,
    load_toi_grid,
)

__all__ = [
    "ENGINE_VERSION",
    "NHL_TEAM_CARRY_SHRINK",
    "NHL_TOI_GRID_SKATER_MINUTES",
    "NHL_GOALIE_TANDEM_SHARE_SUM",
    "PAPER_SIM_S_SET",
    "PLAYER_YEAR_WEIGHTS",
    "PLAYER_YEAR_WEIGHTS_BY_SEASON_ID",
    "PROP_PLAY_CAP_PER_SLATE",
    "ODDS_SPORT_KEY",
    "STARTER_GATE",
    "apply_nhl_team_carry_shrink",
    "get_team_prior",
    "load_team_prior_pack",
    "team_prior_documentation",
    "load_toi_grid",
    "load_goalie_tandem",
    "get_team_toi",
    "get_team_goalie_tandem",
    "toi_grid_documentation",
]
