"""Layer 2 — Game script (pace, total, win prob, lead/trail/neutral).

Consumes Layer 1 team strengths and emits a ``GameScript`` for one game
inside one replicate. Optionally draws a realized score outcome used by
the season path for win/loss and strength evolution.
"""

from __future__ import annotations

import random
from typing import Dict, Mapping, Optional, Tuple

from src.services.nfl_season_engine.calibration import (
    LEAGUE_BASE_PASS_RATE,
    LEAGUE_BASE_PLAYS,
    PACE_PLAYS_CLAMP,
    SCORE_NOISE_SD,
)
from src.services.nfl_season_engine.team_strength import (
    expected_team_points,
    win_prob_from_expected_scores,
)
from src.services.nfl_season_engine.types import (
    GameScript,
    ScheduledGame,
    ScriptState,
    TeamStrengthState,
)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _script_from_margin(own_score: float, opp_score: float) -> ScriptState:
    margin = own_score - opp_score
    if margin >= 4.0:
        return "lead"
    if margin <= -4.0:
        return "trail"
    return "neutral"


def build_game_script(
    game: ScheduledGame,
    strengths: Mapping[str, TeamStrengthState],
    *,
    rng: Optional[random.Random] = None,
    realized: bool = True,
) -> Tuple[GameScript, Dict[str, float]]:
    """Build Layer 2 script (+ optional realized scores for path sims).

    Returns ``(script, {"home_score", "away_score", "home_won"})``.
    """
    rng = rng or random.Random()
    home = strengths[game.home_team]
    away = strengths[game.away_team]

    home_exp = expected_team_points(home, away, home=True)
    away_exp = expected_team_points(away, home, home=False)
    home_wp = win_prob_from_expected_scores(home_exp, away_exp)
    expected_total = home_exp + away_exp

    # pace_plays = per-team offensive snap/play expectation for this game.
    pace = LEAGUE_BASE_PLAYS * 0.5 * (home.pace_factor + away.pace_factor)
    pace = _clamp(pace, *PACE_PLAYS_CLAMP)

    home_pass = _clamp(LEAGUE_BASE_PASS_RATE + home.pass_rate_bias, 0.38, 0.72)
    away_pass = _clamp(LEAGUE_BASE_PASS_RATE + away.pass_rate_bias, 0.38, 0.72)

    if realized:
        home_score = max(0.0, rng.gauss(home_exp, SCORE_NOISE_SD))
        away_score = max(0.0, rng.gauss(away_exp, SCORE_NOISE_SD))
        # Avoid degenerate 0-0 ties dominating; nudge slightly if both tiny.
        if home_score < 1.0 and away_score < 1.0:
            home_score, away_score = 3.0, 0.0
    else:
        home_score = home_exp
        away_score = away_exp

    home_script = _script_from_margin(home_score, away_score)
    away_script = _script_from_margin(away_score, home_score)

    # Script feeds back into pass rate for usage layer.
    home_pass = _clamp(home_pass + {"lead": -0.045, "trail": 0.055, "neutral": 0.0}[home_script], 0.35, 0.78)
    away_pass = _clamp(away_pass + {"lead": -0.045, "trail": 0.055, "neutral": 0.0}[away_script], 0.35, 0.78)

    script = GameScript(
        game_id=game.game_id,
        home_team=game.home_team,
        away_team=game.away_team,
        home_win_prob=round(home_wp, 4),
        expected_total=round(expected_total, 2),
        expected_home_score=round(home_exp, 2),
        expected_away_score=round(away_exp, 2),
        pace_plays=round(pace, 2),
        home_pass_rate=round(home_pass, 4),
        away_pass_rate=round(away_pass, 4),
        home_script=home_script,
        away_script=away_script,
        home_implied_total=round(home_score if realized else home_exp, 2),
        away_implied_total=round(away_score if realized else away_exp, 2),
        source="team_strength_analytic_cal_v1",
    )
    outcome = {
        "home_score": float(home_score),
        "away_score": float(away_score),
        "home_won": 1.0 if home_score >= away_score else 0.0,
    }
    return script, outcome


def summarize_script_distribution(
    scripts: list[GameScript],
) -> Dict[str, float]:
    if not scripts:
        return {}
    n = len(scripts)
    return {
        "home_win_prob_mean": round(sum(s.home_win_prob for s in scripts) / n, 4),
        "expected_total_mean": round(sum(s.expected_total for s in scripts) / n, 2),
        "pace_plays_mean": round(sum(s.pace_plays for s in scripts) / n, 2),
        "home_pass_rate_mean": round(sum(s.home_pass_rate for s in scripts) / n, 4),
        "away_pass_rate_mean": round(sum(s.away_pass_rate for s in scripts) / n, 4),
        "home_lead_rate": round(sum(1 for s in scripts if s.home_script == "lead") / n, 4),
        "home_trail_rate": round(sum(1 for s in scripts if s.home_script == "trail") / n, 4),
    }
