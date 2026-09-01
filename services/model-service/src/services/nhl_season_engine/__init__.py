"""NHL season engine package (Ch1 team prior shell; raw fetcher snapshots)."""

from src.services.nhl_season_engine.priors import (
    ENGINE_VERSION,
    NHL_TEAM_CARRY_SHRINK,
    ODDS_SPORT_KEY,
    PAPER_SIM_S_SET,
    PLAYER_YEAR_WEIGHTS,
    PROP_PLAY_CAP_PER_SLATE,
    STARTER_GATE,
)
from src.services.nhl_season_engine.team_prior import (
    apply_nhl_team_carry_shrink,
    documentation as team_prior_documentation,
    get_team_prior,
    load_team_prior_pack,
)

__all__ = [
    "ENGINE_VERSION",
    "NHL_TEAM_CARRY_SHRINK",
    "PAPER_SIM_S_SET",
    "PLAYER_YEAR_WEIGHTS",
    "PROP_PLAY_CAP_PER_SLATE",
    "ODDS_SPORT_KEY",
    "STARTER_GATE",
    "apply_nhl_team_carry_shrink",
    "get_team_prior",
    "load_team_prior_pack",
    "team_prior_documentation",
]
