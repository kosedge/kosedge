"""Layer 1 — Team strength (offense / defense ratings).

Source of truth for how team O/D ratings are initialized and how they
evolve across a simulated season path.

REAL vs PLACEHOLDER
-------------------
- REAL: offense/defense indices loaded from ``_load_team_strength_priors``
  (EPA-based priors used by live ``simulate_nfl_game``), or from schedule-
  attached market projections when available.
- PLACEHOLDER: mean-reverting in-path strength updates after each simulated
  game. Calibration is intentionally thin — structure + coherence first.
"""

from __future__ import annotations

import math
import random
from typing import Dict, Mapping, MutableMapping, Optional

from src.services.nfl_season_engine.types import TeamStrengthState

# Thin evolution knobs (documented placeholders — not backtested).
STRENGTH_UPDATE_RATE = 0.04
STRENGTH_MEAN_REVERT = 0.015
STRENGTH_NOISE = 0.012
STRENGTH_CLAMP = (0.70, 1.35)


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
) -> float:
    """Thin analytic expected points from O/D indices.

    Anchored near a ~22.5 league-average team total. Home-field is a small
    additive bump — same spirit as ``nfl_handicapping_framework``, not a
    re-implementation of the full decomposition.
    """
    matchup = offense.offense_index / max(0.55, opponent_defense.defense_index)
    base = 22.5 * matchup
    if home:
        base += 1.35
    return _clamp(base, 10.0, 40.0)


def win_prob_from_expected_scores(
    home_points: float,
    away_points: float,
    *,
    margin_sd: float = 13.5,
) -> float:
    """Normal CDF win probability from expected scores (thin analytic)."""
    margin = home_points - away_points
    z = margin / max(8.0, margin_sd)
    # erf-based normal CDF
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

    PLACEHOLDER evolution: winners drift up slightly, losers drift down,
    with mean-reversion toward 1.0 and small Gaussian noise. This keeps
    season paths coherent (hot/cold streaks) without claiming calibrated
    Bayesian updating.
    """
    rng = rng or random.Random()
    home = strengths[home_team]
    away = strengths[away_team]

    home_margin = float(home_score) - float(away_score)
    # Scale update by margin surprise vs a ~3-point home edge prior.
    surprise = _clamp((home_margin - 2.5) / 14.0, -1.5, 1.5)

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
            + STRENGTH_UPDATE_RATE * signed_surprise * 0.85
            + STRENGTH_MEAN_REVERT * (1.0 - state.defense_index)
            + noise_d,
            *STRENGTH_CLAMP,
        )
        state.games_played += 1
        if state.source == "epa_prior" or state.source.startswith("real"):
            state.source = f"{state.source}+path_evolved"
        elif "path_evolved" not in state.source:
            state.source = f"{state.source}+path_evolved"

    if home_won:
        _step(home, +abs(surprise) if surprise >= 0 else +0.15)
        _step(away, -abs(surprise) if surprise <= 0 else -0.15)
    else:
        _step(home, -abs(surprise) if surprise <= 0 else -0.15)
        _step(away, +abs(surprise) if surprise >= 0 else +0.15)
