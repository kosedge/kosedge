from __future__ import annotations

import random
from typing import Dict, List, Optional

from .mlb_simulator import (
    AWAY_FIELD_OFFENSE_MUL,
    HOME_FIELD_OFFENSE_MUL,
    MATCHUP_MUL_ENABLED,
    MlbGameInputs,
    _effective_lineup_confidence,
    _effective_offense_index,
    _offense_pitcher_matchup_mul,
)

PITCH_SIM_MODEL_VERSION = "mlb-v2-pitch-sim"


def _clamp(v: float, lo: float, hi: float) -> float:
    return min(hi, max(lo, v))


def _fair_moneyline_from_prob(p_home: float) -> int:
    p = _clamp(p_home, 0.0001, 0.9999)
    if p >= 0.5:
        return int(round(-(100.0 * p / (1.0 - p))))
    return int(round((100.0 * (1.0 - p) / p)))


def _quantile(values: List[int], q: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    idx = int(round((len(s) - 1) * q))
    idx = max(0, min(len(s) - 1, idx))
    return float(s[idx])


def _beta_interval_from_wins(wins: int, losses: int, z: float = 1.645) -> Dict[str, float]:
    a = wins + 1.0
    b = losses + 1.0
    mean = a / (a + b)
    var = (a * b) / (((a + b) ** 2) * (a + b + 1.0))
    sd = max(var, 0.0) ** 0.5
    return {"low": _clamp(mean - z * sd, 0.0, 1.0), "high": _clamp(mean + z * sd, 0.0, 1.0)}


def _run_environment(inputs: MlbGameInputs) -> float:
    park = inputs.park_factor_runs if inputs.park_factor_runs is not None else 1.0
    temp = inputs.weather_temp_f if inputs.weather_temp_f is not None else 68.0
    wind = inputs.weather_wind_mph if inputs.weather_wind_mph is not None else 6.0
    temp_mul = 1.0 + _clamp((temp - 68.0) * 0.0025, -0.08, 0.08)
    wind_mul = 1.0 + _clamp((wind - 6.0) * 0.0030, -0.06, 0.06)
    ump = _clamp(inputs.umpire_run_factor, 0.94, 1.06)
    return _clamp(park * temp_mul * wind_mul * ump, 0.72, 1.38)


def _next_pa_outcome(
    rng: random.Random,
    *,
    offense_mul: float,
    defense_mul: float,
    env_mul: float,
    pitcher_k_factor: float,
    pitcher_bb_factor: float,
    pitcher_gb_factor: float,
) -> Dict[str, object]:
    # Pitch-loop skeleton: each PA resolved by balls/strikes or ball in play.
    balls = 0
    strikes = 0
    pitch_count = 0
    while True:
        pitch_count += 1
        strike_prob = _clamp(
            0.49
            * defense_mul
            * (pitcher_k_factor ** 0.55)
            / max(0.75, offense_mul)
            / max(0.85, pitcher_bb_factor ** 0.20),
            0.38,
            0.66,
        )
        ball_in_play_prob = _clamp(
            0.165
            * offense_mul
            / max(0.84, pitcher_k_factor ** 0.35),
            0.11,
            0.24,
        )
        u = rng.random()
        if u < strike_prob:
            strikes += 1
            if strikes >= 3:
                return {"result": "k", "pitch_count": pitch_count}
            continue
        if u < strike_prob + ball_in_play_prob:
            break
        balls += 1
        if balls >= 4:
            return {"result": "bb", "pitch_count": pitch_count}

    # Ball in play outcome.
    hit_prob = _clamp(
        0.29
        * offense_mul
        * env_mul
        * (1.0 - (pitcher_gb_factor - 1.0) * 0.05)
        * (1.0 + (pitcher_bb_factor - 1.0) * 0.03)
        / max(0.78, defense_mul),
        0.16,
        0.44,
    )
    if rng.random() > hit_prob:
        return {"result": "out", "pitch_count": pitch_count}

    # Hit type split.
    hr_prob = _clamp(
        0.105 * env_mul * offense_mul / max(0.84, pitcher_gb_factor ** 0.40),
        0.04,
        0.22,
    )
    dbl_prob = _clamp(0.205 * env_mul / max(0.90, pitcher_gb_factor ** 0.12), 0.11, 0.30)
    trp_prob = 0.02
    hv = rng.random()
    if hv < hr_prob:
        return {"result": "hr", "pitch_count": pitch_count}
    if hv < hr_prob + dbl_prob:
        return {"result": "2b", "pitch_count": pitch_count}
    if hv < hr_prob + dbl_prob + trp_prob:
        return {"result": "3b", "pitch_count": pitch_count}
    return {"result": "1b", "pitch_count": pitch_count}


def _advance_runners(
    outcome: str,
    *,
    on1: bool,
    on2: bool,
    on3: bool,
) -> Dict[str, object]:
    runs = 0
    if outcome in {"k", "out"}:
        return {"runs": 0, "on1": on1, "on2": on2, "on3": on3, "outs_added": 1}
    if outcome == "bb":
        if on1 and on2 and on3:
            runs += 1
        return {
            "runs": runs,
            "on1": True,
            "on2": on1 or on2,
            "on3": on3 or (on1 and on2),
            "outs_added": 0,
        }
    if outcome == "1b":
        runs += int(on3)
        return {
            "runs": runs,
            "on1": True,
            "on2": on1,
            "on3": on2,
            "outs_added": 0,
        }
    if outcome == "2b":
        runs += int(on3) + int(on2)
        return {
            "runs": runs,
            "on1": False,
            "on2": True,
            "on3": on1,
            "outs_added": 0,
        }
    if outcome == "3b":
        runs += int(on1) + int(on2) + int(on3)
        return {"runs": runs, "on1": False, "on2": False, "on3": True, "outs_added": 0}
    if outcome == "hr":
        runs += 1 + int(on1) + int(on2) + int(on3)
        return {"runs": runs, "on1": False, "on2": False, "on3": False, "outs_added": 0}
    return {"runs": 0, "on1": on1, "on2": on2, "on3": on3, "outs_added": 1}


def _simulate_half_inning(
    rng: random.Random,
    *,
    offense_mul: float,
    defense_mul: float,
    env_mul: float,
    pitcher_k_factor: float,
    pitcher_bb_factor: float,
    pitcher_gb_factor: float,
    start_on_second: bool = False,
    walkoff_target_runs: Optional[int] = None,
) -> Dict[str, int]:
    outs = 0
    runs = 0
    pitches = 0
    on1 = False
    on2 = start_on_second
    on3 = False
    while outs < 3:
        pa = _next_pa_outcome(
            rng,
            offense_mul=offense_mul,
            defense_mul=defense_mul,
            env_mul=env_mul,
            pitcher_k_factor=pitcher_k_factor,
            pitcher_bb_factor=pitcher_bb_factor,
            pitcher_gb_factor=pitcher_gb_factor,
        )
        outcome = str(pa["result"])
        pitches += int(pa["pitch_count"])
        adv = _advance_runners(outcome, on1=on1, on2=on2, on3=on3)
        runs += int(adv["runs"])
        if walkoff_target_runs is not None and runs >= walkoff_target_runs:
            return {"runs": runs, "pitches": pitches}
        on1 = bool(adv["on1"])
        on2 = bool(adv["on2"])
        on3 = bool(adv["on3"])
        outs += int(adv["outs_added"])
    return {"runs": runs, "pitches": pitches}


def simulate_mlb_game_pitch_by_pitch(
    inputs: MlbGameInputs,
    *,
    simulations: int = 4000,
    seed: Optional[int] = None,
    model_version: str = PITCH_SIM_MODEL_VERSION,
) -> Dict[str, object]:
    rng = random.Random(seed)
    env = _run_environment(inputs)
    eff_conf_home = _effective_lineup_confidence(
        inputs.lineup_confidence_home,
        inputs.info_freshness_score_home,
    )
    eff_conf_away = _effective_lineup_confidence(
        inputs.lineup_confidence_away,
        inputs.info_freshness_score_away,
    )
    firm_home = _clamp(float(getattr(inputs, "starter_firmness_home", 0.85) or 0.85), 0.35, 1.0)
    firm_away = _clamp(float(getattr(inputs, "starter_firmness_away", 0.85) or 0.85), 0.35, 1.0)
    if MATCHUP_MUL_ENABLED:
        matchup_home = _offense_pitcher_matchup_mul(
            offense_split=inputs.offense_split_home,
            recent_form=inputs.recent_form_index_home,
            opp_k_factor=inputs.starter_k_factor_away,
            opp_bb_factor=inputs.starter_bb_factor_away,
            opp_gb_factor=inputs.starter_gb_factor_away,
            opp_firmness=firm_away,
        )
        matchup_away = _offense_pitcher_matchup_mul(
            offense_split=inputs.offense_split_away,
            recent_form=inputs.recent_form_index_away,
            opp_k_factor=inputs.starter_k_factor_home,
            opp_bb_factor=inputs.starter_bb_factor_home,
            opp_gb_factor=inputs.starter_gb_factor_home,
            opp_firmness=firm_home,
        )
    else:
        matchup_home = 1.0
        matchup_away = 1.0
    offense_home_early = (
        _effective_offense_index(
            season_index=inputs.offense_home,
            split_index=inputs.offense_split_home,
            recent_index=inputs.recent_form_index_home,
            lineup_index=inputs.lineup_strength_index_home,
            effective_confidence=eff_conf_home,
            starter_facing=True,
        )
        * HOME_FIELD_OFFENSE_MUL
        * _clamp(1.0 + (matchup_home - 1.0) * 1.25, 0.96, 1.04)
    )
    offense_away_early = (
        _effective_offense_index(
            season_index=inputs.offense_away,
            split_index=inputs.offense_split_away,
            recent_index=inputs.recent_form_index_away,
            lineup_index=inputs.lineup_strength_index_away,
            effective_confidence=eff_conf_away,
            starter_facing=True,
        )
        * AWAY_FIELD_OFFENSE_MUL
        * _clamp(1.0 + (matchup_away - 1.0) * 1.25, 0.96, 1.04)
    )
    offense_home_late = (
        _effective_offense_index(
            season_index=inputs.offense_home,
            split_index=inputs.offense_split_home,
            recent_index=inputs.recent_form_index_home,
            lineup_index=inputs.lineup_strength_index_home,
            effective_confidence=eff_conf_home,
            starter_facing=False,
        )
        * HOME_FIELD_OFFENSE_MUL
        * matchup_home
    )
    offense_away_late = (
        _effective_offense_index(
            season_index=inputs.offense_away,
            split_index=inputs.offense_split_away,
            recent_index=inputs.recent_form_index_away,
            lineup_index=inputs.lineup_strength_index_away,
            effective_confidence=eff_conf_away,
            starter_facing=False,
        )
        * AWAY_FIELD_OFFENSE_MUL
        * matchup_away
    )

    defense_home_st = _clamp(1.0 / max(0.01, inputs.starter_quality_home), 0.75, 1.30)
    defense_away_st = _clamp(1.0 / max(0.01, inputs.starter_quality_away), 0.75, 1.30)
    home_avail_penalty = _clamp((0.70 - _clamp(inputs.bullpen_availability_home, 0.05, 1.0)) * 0.30, -0.08, 0.20)
    away_avail_penalty = _clamp((0.70 - _clamp(inputs.bullpen_availability_away, 0.05, 1.0)) * 0.30, -0.08, 0.20)
    home_high_lev_penalty = _clamp(
        (0.66 - _clamp(inputs.bullpen_high_lev_availability_home, 0.05, 1.0)) * 0.22,
        -0.05,
        0.16,
    )
    away_high_lev_penalty = _clamp(
        (0.66 - _clamp(inputs.bullpen_high_lev_availability_away, 0.05, 1.0)) * 0.22,
        -0.05,
        0.16,
    )
    defense_home_bp = _clamp(
        (1.0 / max(0.01, inputs.bullpen_quality_home))
        * (
            1.0
            - (inputs.bullpen_fatigue_home - 0.5) * 0.35
            - home_avail_penalty
            - home_high_lev_penalty
        ),
        0.70,
        1.45,
    )
    defense_away_bp = _clamp(
        (1.0 / max(0.01, inputs.bullpen_quality_away))
        * (
            1.0
            - (inputs.bullpen_fatigue_away - 0.5) * 0.35
            - away_avail_penalty
            - away_high_lev_penalty
        ),
        0.70,
        1.45,
    )

    f5_home_wins = 0
    fg_home_wins = 0
    push_f5 = 0
    push_fg = 0
    f5_totals: List[int] = []
    fg_totals: List[int] = []
    f5_margins: List[int] = []
    fg_margins: List[int] = []
    fg_home_cover_run_line = 0
    f5_home_cover_run_line = 0
    pitch_totals: List[int] = []
    extra_innings_games = 0
    extra_innings_total = 0
    home_walkoff_wins = 0
    run_line_abs = 1.5

    for _ in range(simulations):
        home_runs = 0
        away_runs = 0
        f5_home = 0
        f5_away = 0
        game_pitches = 0
        home_walkoff = False
        extra_innings_played = 0

        for inning in range(1, 9):
            away_half = _simulate_half_inning(
                rng,
                offense_mul=offense_away_early if inning <= 5 else offense_away_late,
                defense_mul=defense_home_st if inning <= 5 else defense_home_bp,
                env_mul=env,
                pitcher_k_factor=inputs.starter_k_factor_home if inning <= 5 else 1.0,
                pitcher_bb_factor=inputs.starter_bb_factor_home if inning <= 5 else 1.0,
                pitcher_gb_factor=inputs.starter_gb_factor_home if inning <= 5 else 1.0,
            )
            away_runs += away_half["runs"]
            game_pitches += away_half["pitches"]

            home_half = _simulate_half_inning(
                rng,
                offense_mul=offense_home_early if inning <= 5 else offense_home_late,
                defense_mul=defense_away_st if inning <= 5 else defense_away_bp,
                env_mul=env,
                pitcher_k_factor=inputs.starter_k_factor_away if inning <= 5 else 1.0,
                pitcher_bb_factor=inputs.starter_bb_factor_away if inning <= 5 else 1.0,
                pitcher_gb_factor=inputs.starter_gb_factor_away if inning <= 5 else 1.0,
            )
            home_runs += home_half["runs"]
            game_pitches += home_half["pitches"]

            if inning == 5:
                f5_home, f5_away = home_runs, away_runs

        away_ninth = _simulate_half_inning(
            rng,
            offense_mul=offense_away_late,
            defense_mul=defense_home_bp,
            env_mul=env,
            pitcher_k_factor=1.0,
            pitcher_bb_factor=1.0,
            pitcher_gb_factor=1.0,
        )
        away_runs += away_ninth["runs"]
        game_pitches += away_ninth["pitches"]

        if home_runs <= away_runs:
            home_ninth = _simulate_half_inning(
                rng,
                offense_mul=offense_home_late,
                defense_mul=defense_away_bp,
                env_mul=env,
                pitcher_k_factor=1.0,
                pitcher_bb_factor=1.0,
                pitcher_gb_factor=1.0,
                walkoff_target_runs=away_runs - home_runs + 1,
            )
            home_runs += home_ninth["runs"]
            game_pitches += home_ninth["pitches"]
            if home_runs > away_runs:
                home_walkoff = True

        while home_runs == away_runs and extra_innings_played < 9:
            extra_innings_played += 1
            away_extra = _simulate_half_inning(
                rng,
                offense_mul=offense_away_late,
                defense_mul=defense_home_bp,
                env_mul=env,
                pitcher_k_factor=1.0,
                pitcher_bb_factor=1.0,
                pitcher_gb_factor=1.0,
                start_on_second=True,
            )
            away_runs += away_extra["runs"]
            game_pitches += away_extra["pitches"]

            home_extra = _simulate_half_inning(
                rng,
                offense_mul=offense_home_late,
                defense_mul=defense_away_bp,
                env_mul=env,
                pitcher_k_factor=1.0,
                pitcher_bb_factor=1.0,
                pitcher_gb_factor=1.0,
                start_on_second=True,
                walkoff_target_runs=away_runs - home_runs + 1,
            )
            home_runs += home_extra["runs"]
            game_pitches += home_extra["pitches"]
            if home_runs > away_runs:
                home_walkoff = True
                break

        if home_runs == away_runs:
            extra_innings_played += 1
            if rng.random() < (offense_home_late / max(0.0001, offense_home_late + offense_away_late)):
                home_runs += 1
                home_walkoff = True
            else:
                away_runs += 1

        f5_margin = f5_home - f5_away
        fg_margin = home_runs - away_runs
        if f5_home > f5_away:
            f5_home_wins += 1
        elif f5_home == f5_away:
            push_f5 += 1
        if home_runs > away_runs:
            fg_home_wins += 1
        if extra_innings_played > 0:
            extra_innings_games += 1
            extra_innings_total += extra_innings_played
        if home_walkoff:
            home_walkoff_wins += 1

        f5_totals.append(f5_home + f5_away)
        fg_totals.append(home_runs + away_runs)
        f5_margins.append(f5_margin)
        fg_margins.append(fg_margin)
        if fg_margin > run_line_abs:
            fg_home_cover_run_line += 1
        if f5_margin > run_line_abs:
            f5_home_cover_run_line += 1
        pitch_totals.append(game_pitches)

    f5_denom = max(1, simulations - push_f5)
    fg_denom = max(1, simulations)
    f5_home_prob = f5_home_wins / f5_denom
    fg_home_prob = fg_home_wins / fg_denom
    f5_ci = _beta_interval_from_wins(f5_home_wins, max(0, f5_denom - f5_home_wins))
    fg_ci = _beta_interval_from_wins(fg_home_wins, max(0, fg_denom - fg_home_wins))
    f5_mean = sum(f5_totals) / simulations
    fg_mean = sum(fg_totals) / simulations
    f5_margin_mean = sum(f5_margins) / simulations
    fg_margin_mean = sum(fg_margins) / simulations
    fair_fg_spread_home = -round(fg_margin_mean * 2.0) / 2.0
    fair_f5_spread_home = -round(f5_margin_mean * 2.0) / 2.0
    if abs(fair_fg_spread_home) < 0.5:
        fair_fg_spread_home = -1.5 if fg_margin_mean >= 0 else 1.5
    if abs(fair_f5_spread_home) < 0.5:
        fair_f5_spread_home = -1.5 if f5_margin_mean >= 0 else 1.5
    fg_cover_prob = fg_home_cover_run_line / simulations
    f5_cover_prob = f5_home_cover_run_line / simulations
    pitch_mean = sum(pitch_totals) / simulations
    f5_p10 = _quantile(f5_totals, 0.10)
    f5_p50 = _quantile(f5_totals, 0.50)
    f5_p90 = _quantile(f5_totals, 0.90)
    fg_p10 = _quantile(fg_totals, 0.10)
    fg_p50 = _quantile(fg_totals, 0.50)
    fg_p90 = _quantile(fg_totals, 0.90)

    return {
        "game_id": inputs.game_id,
        "model_version": model_version,
        "simulation_count": simulations,
        "inputs": {
            "home_team": inputs.home_team,
            "away_team": inputs.away_team,
            "starter_home": inputs.starter_home,
            "starter_away": inputs.starter_away,
            "umpire_home_plate": inputs.umpire_home_plate,
            "umpire_run_factor": inputs.umpire_run_factor,
            "lineup_confirmed": inputs.lineup_confirmed,
            "weather_temp_f": inputs.weather_temp_f,
            "weather_wind_mph": inputs.weather_wind_mph,
            "weather_humidity_pct": inputs.weather_humidity_pct,
            "park_factor_runs": inputs.park_factor_runs,
            "lineup_confidence_home": inputs.lineup_confidence_home,
            "lineup_confidence_away": inputs.lineup_confidence_away,
            "bullpen_fatigue_home": inputs.bullpen_fatigue_home,
            "bullpen_fatigue_away": inputs.bullpen_fatigue_away,
            "bullpen_availability_home": inputs.bullpen_availability_home,
            "bullpen_availability_away": inputs.bullpen_availability_away,
            "bullpen_high_lev_availability_home": inputs.bullpen_high_lev_availability_home,
            "bullpen_high_lev_availability_away": inputs.bullpen_high_lev_availability_away,
            "info_freshness_score_home": inputs.info_freshness_score_home,
            "info_freshness_score_away": inputs.info_freshness_score_away,
            "offense_home": inputs.offense_home,
            "offense_away": inputs.offense_away,
            "offense_split_home": inputs.offense_split_home,
            "offense_split_away": inputs.offense_split_away,
            "recent_form_index_home": inputs.recent_form_index_home,
            "recent_form_index_away": inputs.recent_form_index_away,
            "lineup_strength_index_home": inputs.lineup_strength_index_home,
            "lineup_strength_index_away": inputs.lineup_strength_index_away,
            "starter_k_factor_home": inputs.starter_k_factor_home,
            "starter_k_factor_away": inputs.starter_k_factor_away,
            "starter_bb_factor_home": inputs.starter_bb_factor_home,
            "starter_bb_factor_away": inputs.starter_bb_factor_away,
            "starter_gb_factor_home": inputs.starter_gb_factor_home,
            "starter_gb_factor_away": inputs.starter_gb_factor_away,
        },
        "run_rates": {
            "env_multiplier": env,
            "home_offense_early": offense_home_early,
            "away_offense_early": offense_away_early,
            "home_offense_late": offense_home_late,
            "away_offense_late": offense_away_late,
            "home_starter_defense": defense_home_st,
            "away_starter_defense": defense_away_st,
            "home_bullpen_defense": defense_home_bp,
            "away_bullpen_defense": defense_away_bp,
        },
        "markets": {
            "f5_home_win_prob": f5_home_prob,
            "fg_home_win_prob": fg_home_prob,
            "f5_home_win_prob_ci_low": f5_ci["low"],
            "f5_home_win_prob_ci_high": f5_ci["high"],
            "fg_home_win_prob_ci_low": fg_ci["low"],
            "fg_home_win_prob_ci_high": fg_ci["high"],
            "f5_total_mean": f5_mean,
            "fg_total_mean": fg_mean,
            "f5_total_p10": f5_p10,
            "f5_total_p50": f5_p50,
            "f5_total_p90": f5_p90,
            "fg_total_p10": fg_p10,
            "fg_total_p50": fg_p50,
            "fg_total_p90": fg_p90,
            "fair_f5_home_ml": _fair_moneyline_from_prob(f5_home_prob),
            "fair_fg_home_ml": _fair_moneyline_from_prob(fg_home_prob),
            "fair_f5_total": round(f5_mean * 2.0) / 2.0,
            "fair_fg_total": round(fg_mean * 2.0) / 2.0,
            "fair_f5_spread_home": fair_f5_spread_home,
            "fair_fg_spread_home": fair_fg_spread_home,
            "f5_margin_mean": round(f5_margin_mean, 4),
            "fg_margin_mean": round(fg_margin_mean, 4),
            "f5_home_cover_prob_run_line": round(f5_cover_prob, 6),
            "fg_home_cover_prob_run_line": round(fg_cover_prob, 6),
            "run_line_point": -run_line_abs,
        },
        "diagnostics": {
            "f5_push_rate": push_f5 / simulations,
            "fg_push_rate": 0.0,
            "extra_innings_rate": extra_innings_games / simulations,
            "avg_extra_innings": round(extra_innings_total / max(1, extra_innings_games), 3)
            if extra_innings_games > 0
            else 0.0,
            "home_walkoff_rate": home_walkoff_wins / simulations,
            "avg_total_pitches": round(pitch_mean, 2),
            "simulator_type": "pitch_by_pitch",
        },
    }

