"""Layer 1 — Team strength (offense / defense ratings).

Source of truth for how team O/D ratings are initialized and how they
evolve across a simulated season path.

REAL vs PLACEHOLDER
-------------------
- REAL: offense/defense indices loaded from ``_load_team_strength_priors``
  (EPA-based priors used by live ``simulate_nfl_game``), packaged prior-
  season EPA (``packaged_epa_prior``) when rolling tables are empty, or
  schedule-attached market projections when available.
- PLACEHOLDER: mean-reverting in-path strength updates after each simulated
  game. Evolution gains are calibrated (softened) so season win distributions
  stay in a realistic NFL band without mid-season explosion.
"""

from __future__ import annotations

import math
import random
from typing import Dict, Mapping, MutableMapping, Optional

from src.services.nfl_season_engine.calibration import (
    EXPECTED_POINTS_CLAMP,
    HOME_FIELD_POINTS,
    LEAGUE_TEAM_PPG,
    MATCHUP_RESPONSE,
    STRENGTH_CLAMP,
    STRENGTH_MEAN_REVERT,
    STRENGTH_NOISE,
    STRENGTH_UPDATE_RATE,
    WIN_PROB_MARGIN_SD,
    matchup_response_for_week,
    win_prob_margin_sd_for_week,
)
from src.services.nfl_season_engine.types import TeamStrengthState


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def initialize_strengths(
    teams: Mapping[str, Mapping[str, float]],
    *,
    default_source: str = "placeholder",
) -> Dict[str, TeamStrengthState]:
    """Build initial strength state for every team.

    ``teams`` values may include offense_index, defense_index, pace_factor,
    pass_rate_bias, source.
    """
    out: Dict[str, TeamStrengthState] = {}
    for team, payload in teams.items():
        out[str(team)] = TeamStrengthState(
            team=str(team),
            offense_index=float(payload.get("offense_index", 1.0)),
            defense_index=float(payload.get("defense_index", 1.0)),
            pace_factor=float(payload.get("pace_factor", 1.0)),
            pass_rate_bias=float(payload.get("pass_rate_bias", 0.0)),
            source=str(payload.get("source", default_source)),
            games_played=0,
        )
    return out


def copy_strength_book(
    strengths: Mapping[str, TeamStrengthState],
) -> Dict[str, TeamStrengthState]:
    return {team: state.copy() for team, state in strengths.items()}


def expected_team_points(
    offense: TeamStrengthState,
    opponent_defense: TeamStrengthState,
    *,
    home: bool,
    week: int = 0,
    matchup_response: Optional[float] = None,
) -> float:
    """Analytic expected points from O/D indices.

    Anchored near recent-NFL league-average team scoring
    (``LEAGUE_TEAM_PPG``). Home-field matches the live handicapping
    framework prior (~1.05 pts). Early weeks soften separation via
    ``matchup_response_for_week``.
    """
    raw = offense.offense_index / max(0.55, opponent_defense.defense_index)
    response = (
        float(matchup_response)
        if matchup_response is not None
        else (matchup_response_for_week(week) if week else MATCHUP_RESPONSE)
    )
    # Mild concave/convex response so elite/elite matchups do not explode
    # totals, while still allowing realistic season win separation.
    matchup = 1.0 + response * (raw - 1.0)
    base = LEAGUE_TEAM_PPG * matchup
    if home:
        base += HOME_FIELD_POINTS
    return _clamp(base, *EXPECTED_POINTS_CLAMP)


def win_prob_from_expected_scores(
    home_points: float,
    away_points: float,
    *,
    margin_sd: Optional[float] = None,
    week: int = 0,
) -> float:
    """Normal CDF win probability from expected scores."""
    sd = float(margin_sd) if margin_sd is not None else win_prob_margin_sd_for_week(week)
    if margin_sd is None and not week:
        sd = WIN_PROB_MARGIN_SD
    margin = home_points - away_points
    z = margin / max(8.0, sd)
    return _clamp(0.5 * (1.0 + math.erf(z / math.sqrt(2.0))), 0.02, 0.98)


def evolve_after_game(
    strengths: MutableMapping[str, TeamStrengthState],
    *,
    home_team: str,
    away_team: str,
    home_won: bool,
    home_score: float,
    away_score: float,
    rng: Optional[random.Random] = None,
) -> None:
    """Update O/D ratings in-place after one simulated game.

    Calibrated evolution: winners drift up slightly, losers drift down,
    with mean-reversion toward 1.0 and small Gaussian noise. Gains are
    softer than the foundation defaults so path coherence remains without
    win-total explosion.
    """
    rng = rng or random.Random()
    if home_team not in strengths or away_team not in strengths:
        # Missing clubs should not crash a path; skip evolution.
        return
    home = strengths[home_team]
    away = strengths[away_team]

    home_margin = float(home_score) - float(away_score)
    # Scale update by margin surprise vs a ~HFA home edge prior.
    surprise = _clamp((home_margin - HOME_FIELD_POINTS) / 14.0, -1.5, 1.5)

    def _step(state: TeamStrengthState, signed_surprise: float) -> None:
        noise_o = rng.gauss(0.0, STRENGTH_NOISE)
        noise_d = rng.gauss(0.0, STRENGTH_NOISE)
        state.offense_index = _clamp(
            state.offense_index
            + STRENGTH_UPDATE_RATE * signed_surprise
            + STRENGTH_MEAN_REVERT * (1.0 - state.offense_index)
            + noise_o,
            *STRENGTH_CLAMP,
        )
        state.defense_index = _clamp(
            state.defense_index
            + STRENGTH_UPDATE_RATE * signed_surprise * 0.80
            + STRENGTH_MEAN_REVERT * (1.0 - state.defense_index)
            + noise_d,
            *STRENGTH_CLAMP,
        )
        state.games_played += 1
        if (
            state.source in ("epa_prior", "packaged_epa_prior")
            or state.source.startswith("real")
            or state.source.startswith("epa_prior")
            or state.source.startswith("packaged_epa_prior")
        ):
            if "+path_evolved" not in state.source:
                state.source = f"{state.source}+path_evolved"
        elif "path_evolved" not in state.source:
            state.source = f"{state.source}+path_evolved"

    if home_won:
        _step(home, +abs(surprise) if surprise >= 0 else +0.12)
        _step(away, -abs(surprise) if surprise <= 0 else -0.12)
    else:
        _step(home, -abs(surprise) if surprise <= 0 else -0.12)
        _step(away, +abs(surprise) if surprise >= 0 else +0.12)
