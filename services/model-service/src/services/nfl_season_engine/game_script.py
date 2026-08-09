"""Layer 2 — Game script / play-calling (pace, total, win prob, script).

Consumes Layer 1 team strengths and emits a ``GameScript`` for one game
inside one replicate. Optionally draws a realized score outcome used by
the season path for win/loss and strength evolution.

v1.6 play-calling
-----------------
Score differential + a representative remaining-clock snapshot map to:

- Fine script detail: large_lead / small_lead / neutral / small_deficit /
  large_deficit (coarse lead/trail/neutral preserved for Layer 3/4)
- Time bucket: early / mid / late
- Intensity in [0, 1] (margin size × late-game pressure)
- Explicit play mix: pass_rate, run_rate, early_down_pass_rate, hurry_up

v1.8 coaching tendencies
------------------------
Team coaching profiles (``coaching_tendencies``) apply modest overlays:
baseline pass bias, script-aggression scaling, early-down bias, and
two-minute / hurry-up aggression. Usage still reacts only through the
existing script → usage matrix.

This is still a **game-level** analytic (not drive-by-drive). The clock
snapshot is a deterministic-given-seed representative phase for usage /
play-mix — not a full temporal sim.
"""

from __future__ import annotations

import random
from typing import Dict, Mapping, Optional, Tuple

from src.services.nfl_season_engine.calibration import (
    LEAGUE_BASE_PASS_RATE,
    LEAGUE_BASE_PLAYS,
    PACE_PLAYS_CLAMP,
    early_season_uncertainty,
    score_noise_sd_for_week,
)
from src.services.nfl_season_engine.coaching_tendencies import (
    CoachingProfile,
    baseline_pass_rate,
    profile_for_team,
)
from src.services.nfl_season_engine.team_strength import (
    expected_team_points,
    win_prob_from_expected_scores,
)
from src.services.nfl_season_engine.types import (
    GameScript,
    ScheduledGame,
    ScriptDetail,
    ScriptState,
    TeamStrengthState,
    TimeBucket,
)

# Margin thresholds (points) for fine script detail.
_LARGE_MARGIN = 14.0
_SMALL_MARGIN = 4.0
# Full game clock proxy (minutes).
_GAME_MINUTES = 60.0


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def coarse_script(detail: ScriptDetail) -> ScriptState:
    """Map fine detail → coarse lead/trail/neutral."""
    if detail in ("large_lead", "small_lead"):
        return "lead"
    if detail in ("large_deficit", "small_deficit"):
        return "trail"
    return "neutral"


def time_bucket_from_minutes(minutes_remaining: float) -> TimeBucket:
    """Bucket remaining clock into early / mid / late."""
    m = _clamp(float(minutes_remaining), 0.0, _GAME_MINUTES)
    if m > 40.0:
        return "early"
    if m > 20.0:
        return "mid"
    return "late"


def script_detail_from_margin(own_score: float, opp_score: float) -> ScriptDetail:
    """Classify fine script from score differential."""
    margin = float(own_score) - float(opp_score)
    if margin >= _LARGE_MARGIN:
        return "large_lead"
    if margin >= _SMALL_MARGIN:
        return "small_lead"
    if margin <= -_LARGE_MARGIN:
        return "large_deficit"
    if margin <= -_SMALL_MARGIN:
        return "small_deficit"
    return "neutral"


def script_intensity(
    *,
    own_score: float,
    opp_score: float,
    minutes_remaining: float,
) -> float:
    """Intensity in [0, 1]: larger |margin| and later clock → higher.

    Neutral margins stay near 0; a 21-point late deficit/lead approaches 1.
    """
    margin = abs(float(own_score) - float(opp_score))
    # Soft floor so small leads still register once time compresses.
    margin_term = _clamp(margin / 21.0, 0.0, 1.0)
    late_term = _clamp(1.0 - (float(minutes_remaining) / _GAME_MINUTES), 0.0, 1.0)
    # Weight late clock more — early large leads are milder play-call tilts.
    raw = 0.45 * margin_term + 0.55 * margin_term * (0.35 + 0.65 * late_term)
    if margin < _SMALL_MARGIN:
        raw *= 0.35
    return round(_clamp(raw, 0.0, 1.0), 4)


def sample_minutes_remaining(
    rng: random.Random,
    *,
    abs_margin: float,
) -> float:
    """Draw a representative remaining-clock snapshot (deterministic given rng).

    Larger realized margins bias toward late-game phases (protecting lead /
    chasing), where play-calling shifts are most observable. Close games
    spread across mid/late.
    """
    u = rng.random()
    if abs_margin >= _LARGE_MARGIN:
        # Mostly late: ~4–22 minutes.
        return _clamp(4.0 + u * 18.0, 0.5, _GAME_MINUTES)
    if abs_margin >= _SMALL_MARGIN:
        # Mid–late: ~12–38 minutes.
        return _clamp(12.0 + u * 26.0, 0.5, _GAME_MINUTES)
    # Competitive: broader mid/early-mid mix.
    return _clamp(18.0 + u * 36.0, 0.5, _GAME_MINUTES)


def _late_factor(time_bucket: TimeBucket) -> float:
    return {"early": 0.40, "mid": 0.75, "late": 1.0}[time_bucket]


def play_mix_from_script(
    *,
    base_pass_rate: float,
    detail: ScriptDetail,
    intensity: float,
    time_bucket: TimeBucket,
    coaching: Optional[CoachingProfile] = None,
    team: Optional[str] = None,
) -> Dict[str, float]:
    """Translate script detail + clock into pass/run/early-down/hurry-up.

    Returns keys: pass_rate, run_rate, early_down_pass_rate, hurry_up.
    When ``coaching`` / ``team`` is provided, applies modest v1.8 tendency
    overlays (script aggression, early-down bias, two-minute aggression).
    ``base_pass_rate`` should already include coaching ``pass_rate_bias``
    when callers use ``baseline_pass_rate``.
    """
    profile = coaching or (profile_for_team(team) if team else None)
    aggression = float(profile.script_aggression) if profile is not None else 1.0
    early_bias = float(profile.early_down_pass_bias) if profile is not None else 0.0
    two_min = float(profile.two_minute_aggression) if profile is not None else 1.0

    lf = _late_factor(time_bucket)
    inten = _clamp(float(intensity), 0.0, 1.0)
    # Base deltas at full late intensity; scaled by lf × inten × aggression.
    detail_delta = {
        "large_lead": -0.11,
        "small_lead": -0.055,
        "neutral": 0.0,
        "small_deficit": 0.065,
        "large_deficit": 0.12,
    }[detail]
    unscaled_pass_delta = detail_delta * (
        0.35 + 0.65 * lf * max(inten, 0.25 if detail != "neutral" else 0.0)
    )
    pass_delta = unscaled_pass_delta * aggression
    # Mild win-probability-independent noise is intentionally omitted (seeded
    # elsewhere via score realization). Keep play-mix deterministic given inputs.
    pass_rate = _clamp(base_pass_rate + pass_delta, 0.32, 0.82)
    # Early downs move in the same direction but less extremely (2nd/3rd long
    # still pass; clock-kill early downs drive the lead-late run tilt).
    early_down_pass = _clamp(
        base_pass_rate + pass_delta * 0.78 + early_bias, 0.30, 0.80
    )
    hurry = 0.0
    if detail in ("small_deficit", "large_deficit") and time_bucket == "late":
        hurry = _clamp(
            0.25 + 0.65 * inten * (1.15 if detail == "large_deficit" else 1.0),
            0.0,
            1.0,
        )
    elif detail == "large_deficit" and time_bucket == "mid":
        hurry = _clamp(0.10 + 0.25 * inten, 0.0, 0.55)
    hurry = _clamp(hurry * two_min, 0.0, 1.0)
    # Leading late → almost no hurry-up; slight pace-down is implicit via run rate.
    if detail in ("small_lead", "large_lead") and time_bucket == "late":
        hurry = 0.0
    return {
        "pass_rate": round(pass_rate, 4),
        "run_rate": round(1.0 - pass_rate, 4),
        "early_down_pass_rate": round(early_down_pass, 4),
        "hurry_up": round(hurry, 4),
        # Inspectable (ignored by consumers that only read the four mix keys).
        "unscaled_pass_delta": round(unscaled_pass_delta, 4),
        "script_aggression": round(aggression, 4),
    }


def play_mix_for_side(script: GameScript, side: str) -> Dict[str, float]:
    """Inspectable play-mix dict for diagnostics / ops dumps."""
    if side == "home":
        return {
            "script_state": script.home_script,
            "script_detail": script.home_script_detail,
            "script_intensity": script.home_script_intensity,
            "time_bucket": script.time_bucket,
            "minutes_remaining": script.minutes_remaining,
            "pass_rate": script.home_pass_rate,
            "run_rate": script.home_run_rate,
            "early_down_pass_rate": script.home_early_down_pass_rate,
            "hurry_up": script.home_hurry_up,
        }
    return {
        "script_state": script.away_script,
        "script_detail": script.away_script_detail,
        "script_intensity": script.away_script_intensity,
        "time_bucket": script.time_bucket,
        "minutes_remaining": script.minutes_remaining,
        "pass_rate": script.away_pass_rate,
        "run_rate": script.away_run_rate,
        "early_down_pass_rate": script.away_early_down_pass_rate,
        "hurry_up": script.away_hurry_up,
    }


def _strength_or_default(
    strengths: Mapping[str, TeamStrengthState], team: str
) -> TeamStrengthState:
    """Return team strength or a league-average placeholder (no KeyError)."""
    state = strengths.get(team)
    if state is not None:
        return state
    return TeamStrengthState(team=team, source="missing_team_default")


def build_game_script(
    game: ScheduledGame,
    strengths: Mapping[str, TeamStrengthState],
    *,
    rng: Optional[random.Random] = None,
    realized: bool = True,
    force_home_score: Optional[float] = None,
    force_away_score: Optional[float] = None,
    force_minutes_remaining: Optional[float] = None,
    force_home_detail: Optional[ScriptDetail] = None,
    force_away_detail: Optional[ScriptDetail] = None,
) -> Tuple[GameScript, Dict[str, float]]:
    """Build Layer 2 script (+ optional realized scores for path sims).

    Force hooks (tests / ops comparisons) are optional and keep the default
    path unchanged when omitted. Returns
    ``(script, {"home_score", "away_score", "home_won"})``.
    """
    rng = rng or random.Random()
    home = _strength_or_default(strengths, game.home_team)
    away = _strength_or_default(strengths, game.away_team)
    week = int(getattr(game, "week", 0) or 0)
    score_sd = score_noise_sd_for_week(week)

    home_exp = expected_team_points(home, away, home=True, week=week)
    away_exp = expected_team_points(away, home, home=False, week=week)
    home_wp = win_prob_from_expected_scores(home_exp, away_exp, week=week)
    expected_total = home_exp + away_exp

    # v1.16: per-team offensive play expectation (own pace + offense), plus a
    # shared game-pace average for diagnostics. Shared pace alone collapsed
    # every QB1 into the same attempt band.
    def _team_pace(state: TeamStrengthState) -> float:
        return _clamp(
            LEAGUE_BASE_PLAYS
            * float(state.pace_factor)
            * (1.0 + 0.14 * (float(state.offense_index) - 1.0)),
            *PACE_PLAYS_CLAMP,
        )

    home_pace = _team_pace(home)
    away_pace = _team_pace(away)
    pace = _clamp(0.5 * (home_pace + away_pace), *PACE_PLAYS_CLAMP)

    home_coach = profile_for_team(game.home_team)
    away_coach = profile_for_team(game.away_team)
    home_base_pass = baseline_pass_rate(
        league_base=LEAGUE_BASE_PASS_RATE,
        strength_pass_bias=home.pass_rate_bias,
        coaching=home_coach,
    )
    away_base_pass = baseline_pass_rate(
        league_base=LEAGUE_BASE_PASS_RATE,
        strength_pass_bias=away.pass_rate_bias,
        coaching=away_coach,
    )

    if force_home_score is not None and force_away_score is not None:
        home_score = max(0.0, float(force_home_score))
        away_score = max(0.0, float(force_away_score))
    elif realized:
        home_score = max(0.0, rng.gauss(home_exp, score_sd))
        away_score = max(0.0, rng.gauss(away_exp, score_sd))
        # Avoid degenerate 0-0 ties dominating; nudge slightly if both tiny.
        if home_score < 1.0 and away_score < 1.0:
            home_score, away_score = 3.0, 0.0
    else:
        home_score = home_exp
        away_score = away_exp

    abs_margin = abs(home_score - away_score)
    if force_minutes_remaining is not None:
        minutes = _clamp(float(force_minutes_remaining), 0.5, _GAME_MINUTES)
    else:
        minutes = sample_minutes_remaining(rng, abs_margin=abs_margin)
    bucket = time_bucket_from_minutes(minutes)

    home_detail: ScriptDetail = force_home_detail or script_detail_from_margin(
        home_score, away_score
    )
    away_detail: ScriptDetail = force_away_detail or script_detail_from_margin(
        away_score, home_score
    )
    # If detail is forced without scores that match, intensity still uses scores.
    home_inten = script_intensity(
        own_score=home_score, opp_score=away_score, minutes_remaining=minutes
    )
    away_inten = script_intensity(
        own_score=away_score, opp_score=home_score, minutes_remaining=minutes
    )
    # Forced details should still get meaningful intensity for usage tests.
    if force_home_detail is not None and force_home_detail != "neutral":
        home_inten = max(home_inten, 0.55 if bucket != "late" else 0.85)
    if force_away_detail is not None and force_away_detail != "neutral":
        away_inten = max(away_inten, 0.55 if bucket != "late" else 0.85)

    home_mix = play_mix_from_script(
        base_pass_rate=home_base_pass,
        detail=home_detail,
        intensity=home_inten,
        time_bucket=bucket,
        coaching=home_coach,
    )
    away_mix = play_mix_from_script(
        base_pass_rate=away_base_pass,
        detail=away_detail,
        intensity=away_inten,
        time_bucket=bucket,
        coaching=away_coach,
    )

    # Mild hurry-up pace bump: trailing late teams nudge their own plays more.
    home_hurry = 1.0 + 0.05 * float(home_mix["hurry_up"])
    away_hurry = 1.0 + 0.05 * float(away_mix["hurry_up"])
    home_pace = _clamp(home_pace * home_hurry, *PACE_PLAYS_CLAMP)
    away_pace = _clamp(away_pace * away_hurry, *PACE_PLAYS_CLAMP)
    pace = _clamp(0.5 * (home_pace + away_pace), *PACE_PLAYS_CLAMP)

    script = GameScript(
        game_id=game.game_id,
        home_team=game.home_team,
        away_team=game.away_team,
        home_win_prob=round(home_wp, 4),
        expected_total=round(expected_total, 2),
        expected_home_score=round(home_exp, 2),
        expected_away_score=round(away_exp, 2),
        pace_plays=round(pace, 2),
        home_pass_rate=home_mix["pass_rate"],
        away_pass_rate=away_mix["pass_rate"],
        home_script=coarse_script(home_detail),
        away_script=coarse_script(away_detail),
        home_implied_total=round(home_score if realized or force_home_score is not None else home_exp, 2),
        away_implied_total=round(away_score if realized or force_away_score is not None else away_exp, 2),
        source="team_strength_analytic_cal_v3_coherence",
        minutes_remaining=round(minutes, 2),
        time_bucket=bucket,
        home_script_detail=home_detail,
        away_script_detail=away_detail,
        home_script_intensity=home_inten,
        away_script_intensity=away_inten,
        home_early_down_pass_rate=home_mix["early_down_pass_rate"],
        away_early_down_pass_rate=away_mix["early_down_pass_rate"],
        home_hurry_up=home_mix["hurry_up"],
        away_hurry_up=away_mix["hurry_up"],
        home_run_rate=home_mix["run_rate"],
        away_run_rate=away_mix["run_rate"],
        home_pace_plays=round(home_pace, 2),
        away_pace_plays=round(away_pace, 2),
        week=week,
        early_season_uncertainty=early_season_uncertainty(week),
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
        "expected_home_score_mean": round(
            sum(s.expected_home_score for s in scripts) / n, 2
        ),
        "expected_away_score_mean": round(
            sum(s.expected_away_score for s in scripts) / n, 2
        ),
        "pace_plays_mean": round(sum(s.pace_plays for s in scripts) / n, 2),
        "home_pass_rate_mean": round(sum(s.home_pass_rate for s in scripts) / n, 4),
        "away_pass_rate_mean": round(sum(s.away_pass_rate for s in scripts) / n, 4),
        "home_lead_rate": round(sum(1 for s in scripts if s.home_script == "lead") / n, 4),
        "home_trail_rate": round(sum(1 for s in scripts if s.home_script == "trail") / n, 4),
        # v1.6 additive play-mix / detail summaries
        "home_early_down_pass_rate_mean": round(
            sum(s.home_early_down_pass_rate for s in scripts) / n, 4
        ),
        "away_early_down_pass_rate_mean": round(
            sum(s.away_early_down_pass_rate for s in scripts) / n, 4
        ),
        "home_hurry_up_mean": round(sum(s.home_hurry_up for s in scripts) / n, 4),
        "away_hurry_up_mean": round(sum(s.away_hurry_up for s in scripts) / n, 4),
        "home_script_intensity_mean": round(
            sum(s.home_script_intensity for s in scripts) / n, 4
        ),
        "away_script_intensity_mean": round(
            sum(s.away_script_intensity for s in scripts) / n, 4
        ),
        "minutes_remaining_mean": round(sum(s.minutes_remaining for s in scripts) / n, 2),
        "time_bucket_late_rate": round(
            sum(1 for s in scripts if s.time_bucket == "late") / n, 4
        ),
        "home_large_lead_rate": round(
            sum(1 for s in scripts if s.home_script_detail == "large_lead") / n, 4
        ),
        "home_large_deficit_rate": round(
            sum(1 for s in scripts if s.home_script_detail == "large_deficit") / n, 4
        ),
    }
