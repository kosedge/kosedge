from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Dict, List, Optional


DEFAULT_MODEL_VERSION = "mlb-v1-pa-sim"
EXTRA_INNING_GHOST_RUNNER_FACTOR = 1.32
MAX_EXTRA_INNINGS = 9


@dataclass
class MlbGameInputs:
    game_id: str
    home_team: str
    away_team: str
    starter_home: Optional[str] = None
    starter_away: Optional[str] = None
    weather_temp_f: Optional[float] = None
    weather_wind_mph: Optional[float] = None
    weather_wind_dir_deg: Optional[float] = None
    weather_humidity_pct: Optional[float] = None
    park_factor_runs: Optional[float] = None
    umpire_home_plate: Optional[str] = None
    umpire_run_factor: float = 1.0
    lineup_confirmed: bool = False
    lineup_confidence_home: float = 0.85
    lineup_confidence_away: float = 0.85
    bullpen_fatigue_home: float = 0.50
    bullpen_fatigue_away: float = 0.50
    bullpen_availability_home: float = 0.65
    bullpen_availability_away: float = 0.65
    bullpen_high_lev_availability_home: float = 0.62
    bullpen_high_lev_availability_away: float = 0.62
    bullpen_ip_last3_home: float = 9.0
    bullpen_ip_last3_away: float = 9.0
    info_freshness_score_home: float = 1.0
    info_freshness_score_away: float = 1.0

    # V1 tuning knobs (to be replaced by learned model features)
    offense_home: float = 1.0
    offense_away: float = 1.0
    offense_split_home: float = 1.0
    offense_split_away: float = 1.0
    recent_form_index_home: float = 1.0
    recent_form_index_away: float = 1.0
    lineup_strength_index_home: float = 1.0
    lineup_strength_index_away: float = 1.0
    starter_quality_home: float = 1.0
    starter_quality_away: float = 1.0
    starter_k_factor_home: float = 1.0
    starter_k_factor_away: float = 1.0
    starter_bb_factor_home: float = 1.0
    starter_bb_factor_away: float = 1.0
    starter_gb_factor_home: float = 1.0
    starter_gb_factor_away: float = 1.0
    bullpen_quality_home: float = 1.0
    bullpen_quality_away: float = 1.0
    # Enterprise sharpening knobs (defaults keep prior behavior when unset).
    starter_firmness_home: float = 0.85
    starter_firmness_away: float = 0.85
    rest_days_home: float = 1.0
    rest_days_away: float = 1.0
    weather_reliability: float = 1.0
    uncertainty_total_mul: float = 1.0


def _clamp(v: float, lo: float, hi: float) -> float:
    return min(hi, max(lo, v))


def _poisson_knuth(rng: random.Random, lam: float) -> int:
    if lam <= 0:
        return 0
    # Knuth method is accurate enough for our run-level counts.
    l = math.exp(-lam)
    k = 0
    p = 1.0
    while p > l:
        k += 1
        p *= rng.random()
    return k - 1


def _fair_moneyline_from_prob(p_home: float) -> int:
    p = _clamp(p_home, 0.0001, 0.9999)
    if p >= 0.5:
        return int(round(-(100.0 * p / (1.0 - p))))
    return int(round((100.0 * (1.0 - p) / p)))


def _starter_shape_factor(k_factor: float, bb_factor: float, gb_factor: float) -> float:
    return _clamp(
        1.0 - (k_factor - 1.0) * 0.08 + (bb_factor - 1.0) * 0.08 - (gb_factor - 1.0) * 0.05,
        0.90,
        1.10,
    )


def _bounded_index(value: float) -> float:
    return _clamp(value, 0.78, 1.25)


def _effective_lineup_confidence(lineup_confidence: float, freshness_score: float) -> float:
    return _clamp(lineup_confidence * _clamp(freshness_score, 0.3, 1.0), 0.2, 1.0)


def _effective_offense_index(
    *,
    season_index: float,
    split_index: float,
    recent_index: float,
    lineup_index: float,
    effective_confidence: float,
    starter_facing: bool,
) -> float:
    season_component = _bounded_index(season_index)
    split_component = 1.0 + (_bounded_index(split_index) - 1.0) * (0.55 + 0.35 * effective_confidence)
    recent_component = 1.0 + (_bounded_index(recent_index) - 1.0) * (0.45 + 0.45 * effective_confidence)
    lineup_component = 1.0 + (_bounded_index(lineup_index) - 1.0) * (0.20 + 0.80 * effective_confidence)
    if starter_facing:
        weights = (0.42, 0.24, 0.14, 0.20)
    else:
        weights = (0.50, 0.16, 0.18, 0.16)
    return _clamp(
        season_component * weights[0]
        + split_component * weights[1]
        + recent_component * weights[2]
        + lineup_component * weights[3],
        0.76,
        1.28,
    )


def _quantile(values: List[int], q: float) -> float:
    if not values:
        return 0.0
    if q <= 0:
        return float(min(values))
    if q >= 1:
        return float(max(values))
    s = sorted(values)
    idx = int(round((len(s) - 1) * q))
    idx = max(0, min(len(s) - 1, idx))
    return float(s[idx])


def _beta_interval_from_wins(wins: int, losses: int, z: float = 1.645) -> Dict[str, float]:
    # Normal approximation on posterior mean with Beta(1,1) prior.
    a = wins + 1.0
    b = losses + 1.0
    mean = a / (a + b)
    var = (a * b) / (((a + b) ** 2) * (a + b + 1.0))
    sd = math.sqrt(max(var, 0.0))
    return {
        "low": _clamp(mean - z * sd, 0.0, 1.0),
        "high": _clamp(mean + z * sd, 0.0, 1.0),
    }


def _environment_run_multiplier(inputs: MlbGameInputs) -> float:
    park = inputs.park_factor_runs if inputs.park_factor_runs is not None else 1.0
    temp = inputs.weather_temp_f if inputs.weather_temp_f is not None else 68.0
    wind = inputs.weather_wind_mph if inputs.weather_wind_mph is not None else 6.0
    humidity = (
        inputs.weather_humidity_pct if inputs.weather_humidity_pct is not None else 50.0
    )
    wind_dir = inputs.weather_wind_dir_deg if inputs.weather_wind_dir_deg is not None else 180.0

    # Conservative V1 environmental transform. Tuned intentionally small to avoid overfitting.
    temp_mul = 1.0 + _clamp((temp - 68.0) * 0.0025, -0.08, 0.08)
    wind_mul = 1.0 + _clamp((wind - 6.0) * 0.003, -0.06, 0.06)
    hum_mul = 1.0 + _clamp((humidity - 50.0) * 0.0008, -0.03, 0.03)

    # Crude proxy: quartering/out-to-center winds (around 120-240 deg) slightly increase runs.
    dir_mul = 1.02 if 120.0 <= wind_dir <= 240.0 else 0.99
    ump_mul = _clamp(inputs.umpire_run_factor, 0.94, 1.06)
    raw = park * temp_mul * wind_mul * hum_mul * dir_mul * ump_mul
    # Dome / missing-weather: blend toward park-only so Open-Meteo noise cannot dominate.
    reliability = _clamp(float(getattr(inputs, "weather_reliability", 1.0) or 1.0), 0.0, 1.0)
    if reliability < 0.999:
        weather_portion = raw / max(park, 1e-6)
        blended = park * (weather_portion**reliability)
        return _clamp(blended, 0.70, 1.35)
    return _clamp(raw, 0.70, 1.35)


def _sample_walkoff_half_inning(rng: random.Random, lam: float, runs_needed: int) -> tuple[int, bool]:
    sampled_runs = _poisson_knuth(rng, lam)
    if sampled_runs < runs_needed:
        return sampled_runs, False
    # Allow a limited overrun to approximate multi-run walk-off hits without playing a full half inning.
    return min(sampled_runs, runs_needed + 1), True


def _simulate_full_game(rng: random.Random, rates: Dict[str, float]) -> Dict[str, int | bool]:
    home_runs = 0
    away_runs = 0

    first_five_home_lambda = max(0.05, rates["f5_home"] / 5.0)
    first_five_away_lambda = max(0.05, rates["f5_away"] / 5.0)
    late_home_total = max(0.20, rates["full_home"] - rates["f5_home"])
    late_away_total = max(0.20, rates["full_away"] - rates["f5_away"])
    late_home_lambda = max(0.05, late_home_total / 4.0)
    late_away_lambda = max(0.05, late_away_total / 4.0)

    for _inning in range(5):
        away_runs += _poisson_knuth(rng, first_five_away_lambda)
        home_runs += _poisson_knuth(rng, first_five_home_lambda)

    f5_home_runs = home_runs
    f5_away_runs = away_runs

    for _inning in range(6, 9):
        away_runs += _poisson_knuth(rng, late_away_lambda)
        home_runs += _poisson_knuth(rng, late_home_lambda)

    away_runs += _poisson_knuth(rng, late_away_lambda)
    home_walkoff = False
    if home_runs < away_runs:
        bottom_runs, home_walkoff = _sample_walkoff_half_inning(
            rng,
            late_home_lambda,
            away_runs - home_runs + 1,
        )
        home_runs += bottom_runs
    elif home_runs == away_runs:
        bottom_runs, home_walkoff = _sample_walkoff_half_inning(rng, late_home_lambda, 1)
        home_runs += bottom_runs

    extra_innings_played = 0
    extra_home_lambda = max(0.08, late_home_lambda * EXTRA_INNING_GHOST_RUNNER_FACTOR)
    extra_away_lambda = max(0.08, late_away_lambda * EXTRA_INNING_GHOST_RUNNER_FACTOR)
    while home_runs == away_runs and extra_innings_played < MAX_EXTRA_INNINGS:
        extra_innings_played += 1
        away_runs += _poisson_knuth(rng, extra_away_lambda)
        bottom_runs, home_walkoff = _sample_walkoff_half_inning(
            rng,
            extra_home_lambda,
            away_runs - home_runs + 1,
        )
        home_runs += bottom_runs

    if home_runs == away_runs:
        extra_innings_played += 1
        home_bias = rates["full_home"] / max(0.0001, rates["full_home"] + rates["full_away"])
        if rng.random() < home_bias:
            home_runs += 1
            home_walkoff = True
        else:
            away_runs += 1

    return {
        "home_runs": home_runs,
        "away_runs": away_runs,
        "f5_home_runs": f5_home_runs,
        "f5_away_runs": f5_away_runs,
        "extra_innings_played": extra_innings_played,
        "home_walkoff": home_walkoff,
    }


def _build_run_rates(inputs: MlbGameInputs) -> Dict[str, float]:
    env_mul = _environment_run_multiplier(inputs)
    base_full_game = 4.3  # baseline MLB team runs / game
    home_starter_shape = _starter_shape_factor(
        inputs.starter_k_factor_home,
        inputs.starter_bb_factor_home,
        inputs.starter_gb_factor_home,
    )
    away_starter_shape = _starter_shape_factor(
        inputs.starter_k_factor_away,
        inputs.starter_bb_factor_away,
        inputs.starter_gb_factor_away,
    )
    # Firmness shrinks extreme starter edges toward league average without mean-shifting ML.
    firm_home = _clamp(float(getattr(inputs, "starter_firmness_home", 0.85) or 0.85), 0.35, 1.0)
    firm_away = _clamp(float(getattr(inputs, "starter_firmness_away", 0.85) or 0.85), 0.35, 1.0)
    home_starter_effective = 1.0 + (inputs.starter_quality_home * home_starter_shape - 1.0) * (
        0.55 + 0.45 * firm_home
    )
    away_starter_effective = 1.0 + (inputs.starter_quality_away * away_starter_shape - 1.0) * (
        0.55 + 0.45 * firm_away
    )
    home_starter_run_factor = _clamp(home_starter_effective, 0.65, 1.35)
    away_starter_run_factor = _clamp(away_starter_effective, 0.65, 1.35)

    # Opponent run suppression from starter + bullpen quality.
    # Low firmness weights bullpen more (TBD SP ⇒ less starter-driven F5/FG split).
    home_starter_w = _clamp(0.55 + 0.20 * firm_home, 0.50, 0.75)
    away_starter_w = _clamp(0.55 + 0.20 * firm_away, 0.50, 0.75)
    home_allowed_factor = _clamp(
        home_starter_w * home_starter_run_factor
        + (1.0 - home_starter_w) * inputs.bullpen_quality_home,
        0.70,
        1.35,
    )
    away_allowed_factor = _clamp(
        away_starter_w * away_starter_run_factor
        + (1.0 - away_starter_w) * inputs.bullpen_quality_away,
        0.70,
        1.35,
    )

    # Bullpen fatigue: higher fatigue increases opponent scoring in full-game markets.
    home_bullpen_stress = _clamp((inputs.bullpen_fatigue_home - 0.5) * 0.35, -0.12, 0.20)
    away_bullpen_stress = _clamp((inputs.bullpen_fatigue_away - 0.5) * 0.35, -0.12, 0.20)
    home_avail = _clamp(inputs.bullpen_availability_home, 0.05, 1.0)
    away_avail = _clamp(inputs.bullpen_availability_away, 0.05, 1.0)
    home_high_lev_avail = _clamp(inputs.bullpen_high_lev_availability_home, 0.05, 1.0)
    away_high_lev_avail = _clamp(inputs.bullpen_high_lev_availability_away, 0.05, 1.0)
    home_avail_penalty = _clamp((0.70 - home_avail) * 0.30, -0.08, 0.20)
    away_avail_penalty = _clamp((0.70 - away_avail) * 0.30, -0.08, 0.20)
    home_high_lev_penalty = _clamp((0.66 - home_high_lev_avail) * 0.22, -0.05, 0.16)
    away_high_lev_penalty = _clamp((0.66 - away_high_lev_avail) * 0.22, -0.05, 0.16)
    home_allowed_factor = _clamp(
        home_allowed_factor
        * (1.0 + home_bullpen_stress + home_avail_penalty + home_high_lev_penalty),
        0.65,
        1.45,
    )
    away_allowed_factor = _clamp(
        away_allowed_factor
        * (1.0 + away_bullpen_stress + away_avail_penalty + away_high_lev_penalty),
        0.65,
        1.45,
    )

    # Season offense is the anchor. Split, recent form, and live lineup strength are layered on top.
    eff_conf_home = _effective_lineup_confidence(
        inputs.lineup_confidence_home,
        inputs.info_freshness_score_home,
    )
    eff_conf_away = _effective_lineup_confidence(
        inputs.lineup_confidence_away,
        inputs.info_freshness_score_away,
    )
    offense_home_full = _effective_offense_index(
        season_index=inputs.offense_home,
        split_index=inputs.offense_split_home,
        recent_index=inputs.recent_form_index_home,
        lineup_index=inputs.lineup_strength_index_home,
        effective_confidence=eff_conf_home,
        starter_facing=False,
    )
    offense_away_full = _effective_offense_index(
        season_index=inputs.offense_away,
        split_index=inputs.offense_split_away,
        recent_index=inputs.recent_form_index_away,
        lineup_index=inputs.lineup_strength_index_away,
        effective_confidence=eff_conf_away,
        starter_facing=False,
    )
    offense_home_f5 = _effective_offense_index(
        season_index=inputs.offense_home,
        split_index=inputs.offense_split_home,
        recent_index=inputs.recent_form_index_home,
        lineup_index=inputs.lineup_strength_index_home,
        effective_confidence=eff_conf_home,
        starter_facing=True,
    )
    offense_away_f5 = _effective_offense_index(
        season_index=inputs.offense_away,
        split_index=inputs.offense_split_away,
        recent_index=inputs.recent_form_index_away,
        lineup_index=inputs.lineup_strength_index_away,
        effective_confidence=eff_conf_away,
        starter_facing=True,
    )

    uncertainty_mul = _clamp(float(getattr(inputs, "uncertainty_total_mul", 1.0) or 1.0), 1.0, 1.04)
    full_home = _clamp(
        base_full_game * offense_home_full * away_allowed_factor * env_mul * uncertainty_mul,
        2.0,
        8.8,
    )
    full_away = _clamp(
        base_full_game * offense_away_full * home_allowed_factor * env_mul * uncertainty_mul,
        2.0,
        8.8,
    )

    # F5 is starter-dominant; weight starter quality more heavily.
    f5_home = _clamp(
        (base_full_game * 5.0 / 9.0)
        * offense_home_f5
        * _clamp(away_starter_run_factor, 0.70, 1.35)
        * env_mul
        * uncertainty_mul,
        0.8,
        5.2,
    )
    f5_away = _clamp(
        (base_full_game * 5.0 / 9.0)
        * offense_away_f5
        * _clamp(home_starter_run_factor, 0.70, 1.35)
        * env_mul
        * uncertainty_mul,
        0.8,
        5.2,
    )
    return {
        "full_home": full_home,
        "full_away": full_away,
        "f5_home": f5_home,
        "f5_away": f5_away,
        "offense_home_full": offense_home_full,
        "offense_away_full": offense_away_full,
        "offense_home_f5": offense_home_f5,
        "offense_away_f5": offense_away_f5,
    }


def simulate_mlb_game(
    inputs: MlbGameInputs,
    *,
    simulations: int = 4000,
    seed: Optional[int] = None,
    model_version: str = DEFAULT_MODEL_VERSION,
) -> Dict[str, object]:
    rng = random.Random(seed)
    rates = _build_run_rates(inputs)

    f5_home_wins = 0
    fg_home_wins = 0
    f5_totals: List[int] = []
    fg_totals: List[int] = []
    f5_margins: List[int] = []
    fg_margins: List[int] = []
    fg_home_cover_run_line = 0
    f5_home_cover_run_line = 0
    push_f5 = 0
    extra_innings_games = 0
    extra_innings_total = 0
    home_walkoff_wins = 0
    # Canonical MLB run line used for cover pricing (±1.5).
    run_line_abs = 1.5

    for _ in range(simulations):
        result = _simulate_full_game(rng, rates)
        f5_home = int(result["f5_home_runs"])
        f5_away = int(result["f5_away_runs"])
        fg_home = int(result["home_runs"])
        fg_away = int(result["away_runs"])
        f5_margin = f5_home - f5_away
        fg_margin = fg_home - fg_away

        if f5_home > f5_away:
            f5_home_wins += 1
        elif f5_home == f5_away:
            push_f5 += 1
        if fg_home > fg_away:
            fg_home_wins += 1
        if bool(result["home_walkoff"]):
            home_walkoff_wins += 1
        if int(result["extra_innings_played"]) > 0:
            extra_innings_games += 1
            extra_innings_total += int(result["extra_innings_played"])

        f5_totals.append(f5_home + f5_away)
        fg_totals.append(fg_home + fg_away)
        f5_margins.append(f5_margin)
        fg_margins.append(fg_margin)
        # Home covers -1.5 when margin > 1.5; covers +1.5 when margin > -1.5.
        # Fair cover prob is reported for the home side of the canonical favorite line.
        if fg_margin > run_line_abs:
            fg_home_cover_run_line += 1
        if f5_margin > run_line_abs:
            f5_home_cover_run_line += 1

    # Exclude pushes from moneyline probability denominator.
    f5_ml_denom = max(1, simulations - push_f5)
    fg_ml_denom = max(1, simulations)
    f5_home_prob = f5_home_wins / f5_ml_denom
    fg_home_prob = fg_home_wins / fg_ml_denom
    f5_ci = _beta_interval_from_wins(f5_home_wins, max(0, f5_ml_denom - f5_home_wins))
    fg_ci = _beta_interval_from_wins(fg_home_wins, max(0, fg_ml_denom - fg_home_wins))
    f5_mean = sum(f5_totals) / simulations
    fg_mean = sum(fg_totals) / simulations
    f5_margin_mean = sum(f5_margins) / simulations
    fg_margin_mean = sum(fg_margins) / simulations
    # Negative spread_home = home favored (matches odds_snapshots convention).
    fair_fg_spread_home = -round(fg_margin_mean * 2.0) / 2.0
    fair_f5_spread_home = -round(f5_margin_mean * 2.0) / 2.0
    if abs(fair_fg_spread_home) < 0.5:
        fair_fg_spread_home = -1.5 if fg_margin_mean >= 0 else 1.5
    if abs(fair_f5_spread_home) < 0.5:
        fair_f5_spread_home = -1.5 if f5_margin_mean >= 0 else 1.5
    fg_cover_prob = fg_home_cover_run_line / simulations
    f5_cover_prob = f5_home_cover_run_line / simulations
    f5_p10 = _quantile(f5_totals, 0.10)
    f5_p50 = _quantile(f5_totals, 0.50)
    f5_p90 = _quantile(f5_totals, 0.90)
    fg_p10 = _quantile(fg_totals, 0.10)
    fg_p50 = _quantile(fg_totals, 0.50)
    fg_p90 = _quantile(fg_totals, 0.90)

    drivers: List[Dict[str, object]] = []
    env_from_neutral = _environment_run_multiplier(inputs) - 1.0
    if abs(env_from_neutral) >= 0.015:
        drivers.append(
            {
                "name": "environment",
                "direction": "over" if env_from_neutral > 0 else "under",
                "impact_pct": round(env_from_neutral * 100.0, 2),
            }
        )
    lineup_delta = ((inputs.lineup_confidence_home + inputs.lineup_confidence_away) / 2.0) - 0.85
    if abs(lineup_delta) >= 0.03:
        drivers.append(
            {
                "name": "lineup_confidence",
                "direction": "over" if lineup_delta > 0 else "under",
                "impact_pct": round(lineup_delta * 20.0, 2),
            }
        )
    fatigue_delta = ((inputs.bullpen_fatigue_home + inputs.bullpen_fatigue_away) / 2.0) - 0.50
    if abs(fatigue_delta) >= 0.04:
        drivers.append(
            {
                "name": "bullpen_fatigue",
                "direction": "over" if fatigue_delta > 0 else "under",
                "impact_pct": round(fatigue_delta * 28.0, 2),
            }
        )
    avail_delta = 0.65 - ((inputs.bullpen_availability_home + inputs.bullpen_availability_away) / 2.0)
    if abs(avail_delta) >= 0.04:
        drivers.append(
            {
                "name": "bullpen_availability",
                "direction": "over" if avail_delta > 0 else "under",
                "impact_pct": round(avail_delta * 24.0, 2),
            }
        )
    split_delta = ((inputs.offense_split_home - 1.0) + (inputs.offense_split_away - 1.0)) / 2.0
    if abs(split_delta) >= 0.02:
        drivers.append(
            {
                "name": "starter_handedness_split",
                "direction": "over" if split_delta > 0 else "under",
                "impact_pct": round(split_delta * 100.0, 2),
            }
        )
    lineup_strength_delta = (
        (inputs.lineup_strength_index_home - 1.0) + (inputs.lineup_strength_index_away - 1.0)
    ) / 2.0
    if abs(lineup_strength_delta) >= 0.02:
        drivers.append(
            {
                "name": "lineup_strength",
                "direction": "over" if lineup_strength_delta > 0 else "under",
                "impact_pct": round(lineup_strength_delta * 100.0, 2),
            }
        )
    recent_form_delta = (
        (inputs.recent_form_index_home - 1.0) + (inputs.recent_form_index_away - 1.0)
    ) / 2.0
    if abs(recent_form_delta) >= 0.02:
        drivers.append(
            {
                "name": "recent_form",
                "direction": "over" if recent_form_delta > 0 else "under",
                "impact_pct": round(recent_form_delta * 100.0, 2),
            }
        )

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
            "weather_wind_dir_deg": inputs.weather_wind_dir_deg,
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
            "bullpen_ip_last3_home": inputs.bullpen_ip_last3_home,
            "bullpen_ip_last3_away": inputs.bullpen_ip_last3_away,
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
        "run_rates": rates,
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
            "drivers": drivers[:4],
        },
    }
