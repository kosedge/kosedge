"""NBA season engine package (Chapter 1 shell — team prior only)."""

from src.services.nba_season_engine.priors import (
    ENGINE_VERSION,
    TEAM_CARRY_SHRINK,
    PAPER_SIM_S_SET,
)
from src.services.nba_season_engine.team_prior import (
    apply_team_carry_shrink,
    documentation,
    get_team_prior,
    load_team_prior_pack,
)

__all__ = [
    "ENGINE_VERSION",
    "TEAM_CARRY_SHRINK",
    "PAPER_SIM_S_SET",
    "apply_team_carry_shrink",
    "documentation",
    "get_team_prior",
    "load_team_prior_pack",
]
