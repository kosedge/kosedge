"""Shared, pure helpers for turning summed real usage into a per-team-week
expected rate -- used by both `preseason_hydration.py` (returning veterans)
and `rookie_baselines.py` (historical rookie-tier baselines), which is why
this lives in its own module: `preseason_hydration` already imports FROM
`rookie_baselines`, so putting this here (rather than in either of those
two) avoids a circular import while letting both share one tested
implementation of the same real fix.
"""

from __future__ import annotations

DEFAULT_TEAM_SEASON_GAMES = 17
"""Fallback team-season length (real games played) used only when a season
has no real `nflverse` team-situational rows at all (should not happen in
practice once a season has been played, but keeps callers total rather than
crashing on a fully-empty table)."""


def compute_hydration_games_denominator(games_active: float, team_season_games: float) -> float:
    """Pure: the real denominator for turning a player's summed real-season
    usage into an expected per-team-week rate.

    `games_active` = the number of weeks this SPECIFIC player recorded real
    usage (`games_played > 0`) -- a fair "rate when they play" for a
    full-time starter, but a badly inflated denominator-substitute for a
    part-time/backup player whose few played games are disproportionately
    likely to be injury-driven emergency action that looks like starter-level
    volume by construction (see `preseason_hydration.hydrate_preseason_player_usage`
    and `rookie_baselines.compute_rookie_usage_baselines` for the two
    production bugs this fixed: backup QBs projected at near-starter season
    volume, and UDFA/late-round rookie QB baselines built almost entirely
    from injury-driven emergency starts).

    `team_season_games` = the player's real team's total games played that
    season -- the correct denominator, since it counts every team-week
    including the ones the player didn't suit up (or wasn't active) for at
    all.

    Returns `max(games_active, team_season_games)`, i.e. this can only pull
    an inflated rate DOWN toward reality (a part-time player's team-season
    length exceeds their own active-week count) -- it can never push a
    legitimate every-week starter's rate up, since their own active-week
    count is already ~= their team's season length.
    """
    return max(float(games_active), float(team_season_games))
