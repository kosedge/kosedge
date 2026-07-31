from __future__ import annotations

import math
import os
import random
from dataclasses import dataclass
from typing import Any, Dict, Optional

from src.services.nfl_handicapping_framework import (
    compute_nfl_projection_decomposition,
    get_nfl_handicapping_config,
)

DEFAULT_NFL_MODEL_VERSION = "nfl-v1.5-matchup-sim"

# When a live market line is available for a game, shrink the model's raw
# margin/total toward it by these weights. This exists because the model's
# team-strength signal is derived from rolling EPA snapshots that can be thin
# or stale (e.g. static preseason placeholders before real 2026 games are
# played), which let a handful of matchups drift several points away from
# consensus with no anchor pulling them back. A moderate blend (well short of
# 1.0) keeps the model free to disagree with the market where it has genuine
# signal, while preventing the largest, least-defensible misses.
#
# Defaults are empirically tuned (not guessed): scripts/nfl/historical_market_backtest.py
# swept blend weights against 3,562 real games (2013-2025) using nflverse's
# free closing spread_line/total_line, minimizing MAE vs actual outcomes.
# 0.30 won for both spread and total (see data/ops/nfl-market-blend-backtest-*.json).
# Interestingly the raw model already edges out the market alone on this sample
# (spread MAE 9.62 vs 9.92, total MAE 10.28 vs 10.51) -- blending still helps
# because it averages out each side's idiosyncratic misses.
NFL_MARKET_BLEND_SPREAD_WEIGHT = float(os.getenv("NFL_MARKET_BLEND_SPREAD_WEIGHT", "0.30"))
NFL_MARKET_BLEND_TOTAL_WEIGHT = float(os.getenv("NFL_MARKET_BLEND_TOTAL_WEIGHT", "0.30"))
# Extra market weight in weeks 1–4 while in-season sample is thin / hydrated.
# Base 0.30 + boost → week-1 ~0.55. Env: NFL_EARLY_SEASON_MARKET_BLEND_BOOST_W1 etc.
_EARLY_SEASON_MARKET_BLEND_BOOST = {
    1: float(os.getenv("NFL_EARLY_SEASON_MARKET_BLEND_BOOST_W1", "0.25")),
    2: float(os.getenv("NFL_EARLY_SEASON_MARKET_BLEND_BOOST_W2", "0.20")),
    3: float(os.getenv("NFL_EARLY_SEASON_MARKET_BLEND_BOOST_W3", "0.15")),
    4: float(os.getenv("NFL_EARLY_SEASON_MARKET_BLEND_BOOST_W4", "0.10")),
}


def _market_blend_weight_for_week(base_weight: float, season_week: Optional[int]) -> float:
    weight = _clamp(float(base_weight), 0.0, 1.0)
    if season_week is None:
        return weight
    try:
        week = int(season_week)
    except (TypeError, ValueError):
        return weight
    boost = float(_EARLY_SEASON_MARKET_BLEND_BOOST.get(week, 0.0) or 0.0)
    return _clamp(weight + max(0.0, boost), 0.0, 0.85)


def _early_season_side_disagreement_boost(
    *,
    season_week: Optional[int],
    pre_blend_margin: float,
    market_spread_home: float,
    min_abs_delta: float = 1.5,
) -> float:
    """Extra market weight when early-season model and market disagree on side.

    Thin / hydrated weeks can still produce a home-favorite raw margin while
    the market has the home club as a dog (or vice versa). Pull harder toward
    consensus without requiring a team-specific special case.
    """
    if season_week is None:
        return 0.0
    try:
        week = int(season_week)
    except (TypeError, ValueError):
        return 0.0
    if week < 1 or week > 4:
        return 0.0
    market_margin = -float(market_spread_home)
    opposite = (pre_blend_margin > 0 and market_margin < 0) or (
        pre_blend_margin < 0 and market_margin > 0
    )
    if not opposite:
        return 0.0
    if abs(float(pre_blend_margin) - float(market_margin)) < float(min_abs_delta):
        return 0.0
    # Week-1 gets the strongest disagreement pull; decays through week 4.
    return float({1: 0.30, 2: 0.22, 3: 0.15, 4: 0.08}.get(week, 0.0))


@dataclass
class NflGameInputs:
    game_id: str
    home_team: str
    away_team: str
    offense_index_home: float = 1.0
    offense_index_away: float = 1.0
    defense_index_home: float = 1.0
    defense_index_away: float = 1.0
    rest_days_home: float = 7.0
    rest_days_away: float = 7.0
    matchup_season: Optional[int] = None
    matchup_week: Optional[int] = None
    matchup_game_id: Optional[str] = None
    matchup_home_team: Optional[str] = None
    matchup_away_team: Optional[str] = None
    home_off_epa_5g: Optional[float] = None
    away_off_epa_5g: Optional[float] = None
    home_def_epa_allowed_5g: Optional[float] = None
    away_def_epa_allowed_5g: Optional[float] = None
    home_pass_rate_5g: Optional[float] = None
    away_pass_rate_5g: Optional[float] = None
    home_success_offense_5g: Optional[float] = None
    away_success_offense_5g: Optional[float] = None
    home_success_defense_allowed_5g: Optional[float] = None
    away_success_defense_allowed_5g: Optional[float] = None
    matchup_diff_off_epa_5g: Optional[float] = None
    matchup_diff_def_epa_allowed_5g: Optional[float] = None
    matchup_diff_pressure_generated_5g: Optional[float] = None
    matchup_diff_pressure_allowed_5g: Optional[float] = None
    matchup_diff_red_zone_td_rate_5g: Optional[float] = None
    matchup_diff_success_rate_5g: Optional[float] = None
    feature_pack_version: Optional[str] = None
    injury_nowcast_confidence_home: Optional[float] = None
    injury_nowcast_confidence_away: Optional[float] = None
    injury_nowcast_freshness_home_hours: Optional[float] = None
    injury_nowcast_freshness_away_hours: Optional[float] = None
    injury_nowcast_impact_home: Optional[float] = None
    injury_nowcast_impact_away: Optional[float] = None
    injury_nowcast_offense_multiplier_home: Optional[float] = None
    injury_nowcast_offense_multiplier_away: Optional[float] = None
    injury_nowcast_defense_multiplier_home: Optional[float] = None
    injury_nowcast_defense_multiplier_away: Optional[float] = None
    injury_nowcast_source: Optional[str] = None
    injury_nowcast_home_drivers: Optional[list[dict[str, Any]]] = None
    injury_nowcast_away_drivers: Optional[list[dict[str, Any]]] = None
    weather_available: Optional[bool] = None
    weather_wind_mph: Optional[float] = None
    weather_precip_mm: Optional[float] = None
    weather_temp_f: Optional[float] = None
    weather_source: Optional[str] = None
    travel_available: Optional[bool] = None
    travel_miles_home: Optional[float] = None
    travel_miles_away: Optional[float] = None
    travel_timezone_delta_home: Optional[float] = None
    travel_timezone_delta_away: Optional[float] = None
    # Situational tendency PROE (pass_rate − xpass); mild totals/spread tilt.
    tendency_proe_home: Optional[float] = None
    tendency_proe_away: Optional[float] = None
    tendency_total_signal: Optional[float] = None
    tendency_spread_signal: Optional[float] = None
    # Owned KAV (lagged opponent-adjusted efficiency). Never same-week.
    home_kav_offense_5g: Optional[float] = None
    away_kav_offense_5g: Optional[float] = None
    home_kav_defense_5g: Optional[float] = None
    away_kav_defense_5g: Optional[float] = None
    home_kav_net_5g: Optional[float] = None
    away_kav_net_5g: Optional[float] = None
    kav_as_of_week: Optional[int] = None
    # Second-order edge (week-lagged personnel / coach aggression).
    home_personnel_edge_5g: Optional[float] = None
    away_personnel_edge_5g: Optional[float] = None
    home_sub_elasticity_5g: Optional[float] = None
    away_sub_elasticity_5g: Optional[float] = None
    home_coach_aggression_5g: Optional[float] = None
    away_coach_aggression_5g: Optional[float] = None
    home_coach_pace_5g: Optional[float] = None
    away_coach_pace_5g: Optional[float] = None
    second_order_as_of_week: Optional[int] = None
    # Injury/practice information velocity (E).
    info_velocity_home: Optional[float] = None
    info_velocity_away: Optional[float] = None
    hours_since_change_home: Optional[float] = None
    hours_since_change_away: Optional[float] = None


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _fair_moneyline_from_prob(prob: float) -> int:
    p = _clamp(prob, 0.001, 0.999)
    if p >= 0.5:
        return int(round(-(100.0 * p) / (1.0 - p)))
    return int(round((100.0 * (1.0 - p)) / p))


def _quantile(sorted_vals: list[float], q: float) -> float:
    if not sorted_vals:
        return 0.0
    q = _clamp(q, 0.0, 1.0)
    idx = int(round((len(sorted_vals) - 1) * q))
    return float(sorted_vals[idx])


def _feature_component(
    raw_value: Optional[float],
    *,
    low: float,
    high: float,
    weight: float,
) -> Dict[str, float]:
    raw = float(raw_value) if raw_value is not None else 0.0
    bounded = _clamp(raw, low, high)
    return {"raw": raw, "bounded": bounded, "points": bounded * weight}


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return float(default)
    try:
        return float(raw)
    except ValueError:
        return float(default)


def _build_matchup_adjustments(inputs: NflGameInputs) -> Dict[str, Any]:
    matchup_present = any(
        value is not None
        for value in (
            inputs.matchup_diff_off_epa_5g,
            inputs.matchup_diff_def_epa_allowed_5g,
            inputs.matchup_diff_pressure_generated_5g,
            inputs.matchup_diff_pressure_allowed_5g,
            inputs.matchup_diff_red_zone_td_rate_5g,
            inputs.matchup_diff_success_rate_5g,
            inputs.home_off_epa_5g,
            inputs.away_off_epa_5g,
            inputs.home_pass_rate_5g,
            inputs.away_pass_rate_5g,
        )
    )
    if not matchup_present:
        return {
            "applied": False,
            "home_points": 0.0,
            "away_points": 0.0,
            "spread_signal": 0.0,
            "total_signal": 0.0,
            "components": {},
            "pack_reference": None,
        }

    components = {
        "diff_off_epa_5g": _feature_component(
            inputs.matchup_diff_off_epa_5g,
            low=-0.30,
            high=0.30,
            weight=5.4,
        ),
        "diff_def_epa_allowed_5g": _feature_component(
            inputs.matchup_diff_def_epa_allowed_5g,
            low=-0.30,
            high=0.30,
            weight=5.0,
        ),
        "diff_pressure_generated_5g": _feature_component(
            inputs.matchup_diff_pressure_generated_5g,
            low=-0.10,
            high=0.10,
            weight=7.0,
        ),
        "diff_pressure_allowed_5g": _feature_component(
            inputs.matchup_diff_pressure_allowed_5g,
            low=-0.10,
            high=0.10,
            weight=6.2,
        ),
        "diff_red_zone_td_rate_5g": _feature_component(
            inputs.matchup_diff_red_zone_td_rate_5g,
            low=-0.20,
            high=0.20,
            weight=4.8,
        ),
        "diff_success_rate_5g": _feature_component(
            inputs.matchup_diff_success_rate_5g,
            low=-0.15,
            high=0.15,
            weight=4.5,
        ),
    }
    spread_signal = _clamp(sum(c["points"] for c in components.values()), -4.25, 4.25)

    home_off_component = _feature_component(inputs.home_off_epa_5g, low=-0.30, high=0.30, weight=2.4)
    away_off_component = _feature_component(inputs.away_off_epa_5g, low=-0.30, high=0.30, weight=2.4)
    pass_rate_total = (inputs.home_pass_rate_5g or 0.0) + (inputs.away_pass_rate_5g or 0.0)
    pass_rate_signal = _feature_component(pass_rate_total - 1.14, low=-0.20, high=0.20, weight=4.0)
    total_signal = _clamp(
        home_off_component["points"] + away_off_component["points"] + pass_rate_signal["points"],
        -2.8,
        2.8,
    )

    # Mild PROE tendency tilt (does not override EPA pack).
    tendency_spread = _clamp(float(inputs.tendency_spread_signal or 0.0), -0.6, 0.6)
    tendency_total = _clamp(float(inputs.tendency_total_signal or 0.0), -1.2, 1.2)
    if inputs.tendency_spread_signal is None and (
        inputs.tendency_proe_home is not None or inputs.tendency_proe_away is not None
    ):
        from src.services.nfl_tendency_pricing import tendency_game_signals

        signals = tendency_game_signals(
            float(inputs.tendency_proe_home or 0.0),
            float(inputs.tendency_proe_away or 0.0),
        )
        tendency_spread = float(signals["spread_signal"])
        tendency_total = float(signals["total_signal"])
    spread_signal = _clamp(spread_signal + tendency_spread, -4.25, 4.25)
    total_signal = _clamp(total_signal + tendency_total, -2.8, 2.8)

    home_points = _clamp((0.72 * spread_signal) + (0.57 * total_signal), -3.6, 3.6)
    away_points = _clamp((-0.58 * spread_signal) + (0.43 * total_signal), -3.0, 3.0)
    return {
        "applied": True,
        "home_points": home_points,
        "away_points": away_points,
        "spread_signal": spread_signal,
        "total_signal": total_signal,
        "components": {
            **components,
            "home_off_epa_5g": home_off_component,
            "away_off_epa_5g": away_off_component,
            "combined_pass_rate_5g": pass_rate_signal,
            "tendency_proe_spread": {
                "raw": tendency_spread,
                "bounded": tendency_spread,
                "points": tendency_spread,
            },
            "tendency_proe_total": {
                "raw": tendency_total,
                "bounded": tendency_total,
                "points": tendency_total,
            },
        },
        "pack_reference": {
            "version": inputs.feature_pack_version,
            "season": inputs.matchup_season,
            "week": inputs.matchup_week,
            "game_id": inputs.matchup_game_id,
            "home_team": inputs.matchup_home_team,
            "away_team": inputs.matchup_away_team,
        },
    }


def _build_totals_adjustments(inputs: NflGameInputs) -> Dict[str, Any]:
    component_values = (
        inputs.home_pass_rate_5g,
        inputs.away_pass_rate_5g,
        inputs.home_off_epa_5g,
        inputs.away_off_epa_5g,
        inputs.home_def_epa_allowed_5g,
        inputs.away_def_epa_allowed_5g,
        inputs.home_success_offense_5g,
        inputs.away_success_offense_5g,
        inputs.home_success_defense_allowed_5g,
        inputs.away_success_defense_allowed_5g,
        inputs.injury_nowcast_impact_home,
        inputs.injury_nowcast_impact_away,
        inputs.injury_nowcast_confidence_home,
        inputs.injury_nowcast_confidence_away,
        inputs.injury_nowcast_offense_multiplier_home,
        inputs.injury_nowcast_offense_multiplier_away,
        inputs.injury_nowcast_defense_multiplier_home,
        inputs.injury_nowcast_defense_multiplier_away,
    )
    if not any(value is not None for value in component_values):
        return {
            "applied": False,
            "total_points": 0.0,
            "stdev_points": 0.0,
            "components": {},
        }

    pass_rate_total = (inputs.home_pass_rate_5g or 0.57) + (inputs.away_pass_rate_5g or 0.57)
    pass_rate_component = _feature_component(
        pass_rate_total - 1.14,
        low=-0.20,
        high=0.20,
        weight=_env_float("NFL_TOTALS_PASS_RATE_WEIGHT", 3.2),
    )

    epa_interaction_raw = (
        (inputs.home_off_epa_5g or 0.0)
        + (inputs.away_off_epa_5g or 0.0)
        + (inputs.home_def_epa_allowed_5g or 0.0)
        + (inputs.away_def_epa_allowed_5g or 0.0)
    )
    epa_interaction_component = _feature_component(
        epa_interaction_raw,
        low=-0.45,
        high=0.45,
        weight=_env_float("NFL_TOTALS_EPA_INTERACTION_WEIGHT", 3.4),
    )

    success_delta_raw = (
        ((inputs.home_success_offense_5g or 0.44) + (inputs.away_success_offense_5g or 0.44))
        - ((inputs.home_success_defense_allowed_5g or 0.44) + (inputs.away_success_defense_allowed_5g or 0.44))
    )
    success_delta_component = _feature_component(
        success_delta_raw,
        low=-0.12,
        high=0.12,
        weight=_env_float("NFL_TOTALS_SUCCESS_DELTA_WEIGHT", 7.4),
    )

    home_off_mult = _clamp(inputs.injury_nowcast_offense_multiplier_home or 1.0, 0.82, 1.08)
    away_off_mult = _clamp(inputs.injury_nowcast_offense_multiplier_away or 1.0, 0.82, 1.08)
    home_def_mult = _clamp(inputs.injury_nowcast_defense_multiplier_home or 1.0, 0.90, 1.18)
    away_def_mult = _clamp(inputs.injury_nowcast_defense_multiplier_away or 1.0, 0.90, 1.18)
    injury_conf = _clamp(
        (
            (inputs.injury_nowcast_confidence_home or 0.0)
            + (inputs.injury_nowcast_confidence_away or 0.0)
        )
        / 2.0,
        0.0,
        1.0,
    )
    offense_drag = ((1.0 - home_off_mult) + (1.0 - away_off_mult))
    defense_leak = ((home_def_mult - 1.0) + (away_def_mult - 1.0))
    injury_total_raw = (0.7 * defense_leak) - (1.25 * offense_drag)
    injury_component = _feature_component(
        injury_total_raw * injury_conf,
        low=-0.22,
        high=0.22,
        weight=_env_float("NFL_TOTALS_INJURY_WEIGHT", 6.0),
    )

    total_points = _clamp(
        pass_rate_component["points"]
        + epa_interaction_component["points"]
        + success_delta_component["points"]
        + injury_component["points"],
        -_env_float("NFL_TOTALS_MAX_ADJUSTMENT_POINTS", 4.2),
        _env_float("NFL_TOTALS_MAX_ADJUSTMENT_POINTS", 4.2),
    )

    injury_impact_strength = _clamp(
        ((inputs.injury_nowcast_impact_home or 0.0) + (inputs.injury_nowcast_impact_away or 0.0)) * injury_conf,
        0.0,
        1.0,
    )
    stdev_points = _clamp(
        injury_impact_strength * _env_float("NFL_TOTALS_INJURY_STDEV_WEIGHT", 1.35),
        0.0,
        _env_float("NFL_TOTALS_MAX_STDEV_ADJUSTMENT", 2.0),
    )
    return {
        "applied": True,
        "total_points": total_points,
        "stdev_points": stdev_points,
        "components": {
            "combined_pass_rate_5g": pass_rate_component,
            "offense_defense_epa_interaction_5g": epa_interaction_component,
            "combined_success_rate_delta_5g": success_delta_component,
            "injury_total_signal": injury_component,
            "injury_confidence": injury_conf,
        },
    }


def _apply_totals_linear_calibration(
    base_total: float,
    *,
    calibration: Optional[Dict[str, Any]],
    apply: bool = True,
) -> Dict[str, Any]:
    floor = _env_float("NFL_TOTALS_CALIBRATION_MIN_TOTAL", 24.0)
    ceiling = _env_float("NFL_TOTALS_CALIBRATION_MAX_TOTAL", 66.0)
    default_slope = _clamp(_env_float("NFL_TOTALS_CALIBRATION_SLOPE_DEFAULT", 1.0), 0.75, 1.25)
    default_intercept = _env_float("NFL_TOTALS_CALIBRATION_INTERCEPT_DEFAULT", 0.0)
    min_sample = max(5, int(_env_float("NFL_TOTALS_CALIBRATION_MIN_SAMPLE", 80.0)))
    intercept_abs_max = abs(_env_float("NFL_TOTALS_CALIBRATION_INTERCEPT_ABS_MAX", 18.0))

    source = "defaults"
    slope = default_slope
    intercept = default_intercept
    sample_size = 0
    if isinstance(calibration, dict):
        maybe_slope = calibration.get("slope")
        maybe_intercept = calibration.get("intercept")
        sample_size = int(calibration.get("sample_size") or 0)
        eligible = bool(calibration.get("eligible", True))
        if (
            apply
            and eligible
            and isinstance(maybe_slope, (float, int))
            and isinstance(maybe_intercept, (float, int))
            and sample_size >= min_sample
        ):
            slope = _clamp(float(maybe_slope), 0.75, 1.25)
            intercept = _clamp(float(maybe_intercept), -intercept_abs_max, intercept_abs_max)
            source = str(calibration.get("source") or "historical-fit")
        elif not apply:
            source = "deferred"

    if not apply:
        calibrated_total = float(base_total)
    else:
        calibrated_total = _clamp((slope * float(base_total)) + intercept, floor, ceiling)
    return {
        "base_total": round(float(base_total), 4),
        "calibrated_total": round(calibrated_total, 4),
        "delta": round(calibrated_total - float(base_total), 4),
        "slope": round(slope, 6),
        "intercept": round(intercept, 6),
        "source": source,
        "sample_size": int(sample_size),
        "applied": bool(apply and source not in {"defaults", "deferred"}),
    }


def simulate_nfl_game(
    inputs: NflGameInputs,
    *,
    simulations: int = 4000,
    seed: Optional[int] = None,
    model_version: str = DEFAULT_NFL_MODEL_VERSION,
    totals_calibration: Optional[Dict[str, Any]] = None,
    apply_linear_totals_calibration: bool = True,
    config_overrides: Optional[Dict[str, Any]] = None,
    market_spread_home: Optional[float] = None,
    market_total: Optional[float] = None,
) -> Dict[str, Any]:
    rng = random.Random(seed)
    sims = max(300, int(simulations))
    framework_config = get_nfl_handicapping_config(config_overrides=config_overrides)

    matchup_adjustments = _build_matchup_adjustments(inputs)
    totals_adjustments = _build_totals_adjustments(inputs)
    decomposition = compute_nfl_projection_decomposition(
        offense_index_home=inputs.offense_index_home,
        offense_index_away=inputs.offense_index_away,
        defense_index_home=inputs.defense_index_home,
        defense_index_away=inputs.defense_index_away,
        rest_days_home=inputs.rest_days_home,
        rest_days_away=inputs.rest_days_away,
        matchup_adjustments=matchup_adjustments,
        totals_adjustments=totals_adjustments,
        injury_nowcast_impact_home=inputs.injury_nowcast_impact_home,
        injury_nowcast_impact_away=inputs.injury_nowcast_impact_away,
        injury_nowcast_freshness_home_hours=inputs.injury_nowcast_freshness_home_hours,
        injury_nowcast_freshness_away_hours=inputs.injury_nowcast_freshness_away_hours,
        injury_nowcast_confidence_home=inputs.injury_nowcast_confidence_home,
        injury_nowcast_confidence_away=inputs.injury_nowcast_confidence_away,
        injury_nowcast_offense_multiplier_home=inputs.injury_nowcast_offense_multiplier_home,
        injury_nowcast_offense_multiplier_away=inputs.injury_nowcast_offense_multiplier_away,
        injury_nowcast_defense_multiplier_home=inputs.injury_nowcast_defense_multiplier_home,
        injury_nowcast_defense_multiplier_away=inputs.injury_nowcast_defense_multiplier_away,
        weather_wind_mph=inputs.weather_wind_mph,
        weather_precip_mm=inputs.weather_precip_mm,
        weather_temp_f=inputs.weather_temp_f,
        weather_available=inputs.weather_available,
        travel_miles_home=inputs.travel_miles_home,
        travel_miles_away=inputs.travel_miles_away,
        travel_timezone_delta_home=inputs.travel_timezone_delta_home,
        travel_timezone_delta_away=inputs.travel_timezone_delta_away,
        travel_available=inputs.travel_available,
        home_kav_net_5g=inputs.home_kav_net_5g,
        away_kav_net_5g=inputs.away_kav_net_5g,
        home_kav_offense_5g=inputs.home_kav_offense_5g,
        away_kav_offense_5g=inputs.away_kav_offense_5g,
        home_kav_defense_5g=inputs.home_kav_defense_5g,
        away_kav_defense_5g=inputs.away_kav_defense_5g,
        kav_as_of_week=inputs.kav_as_of_week,
        home_personnel_edge_5g=inputs.home_personnel_edge_5g,
        away_personnel_edge_5g=inputs.away_personnel_edge_5g,
        home_sub_elasticity_5g=inputs.home_sub_elasticity_5g,
        away_sub_elasticity_5g=inputs.away_sub_elasticity_5g,
        home_coach_aggression_5g=inputs.home_coach_aggression_5g,
        away_coach_aggression_5g=inputs.away_coach_aggression_5g,
        home_coach_pace_5g=inputs.home_coach_pace_5g,
        away_coach_pace_5g=inputs.away_coach_pace_5g,
        second_order_as_of_week=inputs.second_order_as_of_week,
        info_velocity_home=inputs.info_velocity_home,
        info_velocity_away=inputs.info_velocity_away,
        hours_since_change_home=inputs.hours_since_change_home,
        hours_since_change_away=inputs.hours_since_change_away,
        config_overrides=config_overrides,
    )

    mean_home = max(7.5, float(decomposition["expected_home_points"]))
    mean_away = max(7.0, float(decomposition["expected_away_points"]))
    error_stdev_widen = float(decomposition.get("error_regime_stdev_widen") or 0.0)
    stdev = _clamp(
        float(framework_config["priors"]["base_score_stdev"])
        + float(totals_adjustments["stdev_points"])
        + error_stdev_widen,
        7.6,
        12.2,
    )

    totals: list[float] = []
    margins: list[float] = []

    for _ in range(sims):
        home_score = max(0.0, rng.gauss(mean_home, stdev))
        away_score = max(0.0, rng.gauss(mean_away, stdev))
        totals.append(home_score + away_score)
        margins.append(home_score - away_score)

    market_blend: Dict[str, Any] = {"spread_applied": False, "total_applied": False}
    season_week = inputs.matchup_week
    if market_spread_home is not None and margins:
        weight = _market_blend_weight_for_week(NFL_MARKET_BLEND_SPREAD_WEIGHT, season_week)
        pre_blend_margin = sum(margins) / len(margins)
        disagreement_boost = _early_season_side_disagreement_boost(
            season_week=season_week,
            pre_blend_margin=float(pre_blend_margin),
            market_spread_home=float(market_spread_home),
        )
        if disagreement_boost > 0:
            weight = _clamp(weight + disagreement_boost, 0.0, 0.85)
        market_margin = -float(market_spread_home)
        post_blend_margin = ((1.0 - weight) * pre_blend_margin) + (weight * market_margin)
        shift = post_blend_margin - pre_blend_margin
        margins = [m + shift for m in margins]
        market_blend.update(
            spread_applied=True,
            spread_weight=round(weight, 3),
            base_spread_weight=round(_clamp(NFL_MARKET_BLEND_SPREAD_WEIGHT, 0.0, 1.0), 3),
            side_disagreement_boost=round(float(disagreement_boost), 3),
            season_week=season_week,
            market_spread_home=round(float(market_spread_home), 3),
            pre_blend_margin_mean=round(pre_blend_margin, 3),
            post_blend_margin_mean=round(post_blend_margin, 3),
            spread_shift=round(shift, 3),
        )

    if market_total is not None and totals:
        weight = _market_blend_weight_for_week(NFL_MARKET_BLEND_TOTAL_WEIGHT, season_week)
        pre_blend_total = sum(totals) / len(totals)
        post_blend_total = ((1.0 - weight) * pre_blend_total) + (weight * float(market_total))
        shift = post_blend_total - pre_blend_total
        totals = [t + shift for t in totals]
        market_blend.update(
            total_applied=True,
            total_weight=round(weight, 3),
            base_total_weight=round(_clamp(NFL_MARKET_BLEND_TOTAL_WEIGHT, 0.0, 1.0), 3),
            season_week=season_week,
            market_total=round(float(market_total), 3),
            pre_blend_total_mean=round(pre_blend_total, 3),
            post_blend_total_mean=round(post_blend_total, 3),
            total_shift=round(shift, 3),
        )

    home_wins = sum(1 for m in margins if m > 0)
    totals.sort()
    margins.sort()
    home_prob = home_wins / sims
    away_prob = 1.0 - home_prob
    spread_home = -sum(margins) / len(margins) if margins else 0.0
    base_total_mean = sum(totals) / len(totals) if totals else 0.0
    totals_calibration_out = _apply_totals_linear_calibration(
        base_total_mean,
        calibration=totals_calibration,
        apply=bool(apply_linear_totals_calibration),
    )
    total_mean = float(totals_calibration_out["calibrated_total"])
    quantile_shift = float(totals_calibration_out["delta"])

    markets = {
        "home_win_prob": round(home_prob, 4),
        "away_win_prob": round(away_prob, 4),
        "total_mean": round(total_mean, 2),
        "spread_home": round(spread_home, 2),
        "fair_home_ml": _fair_moneyline_from_prob(home_prob),
        "fair_away_ml": _fair_moneyline_from_prob(away_prob),
        "total_p10": round(_quantile(totals, 0.10) + quantile_shift, 2),
        "total_p50": round(_quantile(totals, 0.50) + quantile_shift, 2),
        "total_p90": round(_quantile(totals, 0.90) + quantile_shift, 2),
    }
    diagnostics = {
        "mean_home_points": round(mean_home, 3),
        "mean_away_points": round(mean_away, 3),
        "drivers": [
            {"name": "predicted_margin", "value": decomposition["predicted_margin"]},
            {"name": "predicted_total", "value": decomposition["predicted_total"]},
            {"name": "factor_coverage", "value": decomposition["factor_coverage"]},
            {"name": "confidence_score", "value": decomposition["confidence_score"]},
        ],
        "matchup_feature_adjustments": {
            "applied": bool(matchup_adjustments["applied"]),
            "home_points": round(float(matchup_adjustments["home_points"]), 4),
            "away_points": round(float(matchup_adjustments["away_points"]), 4),
            "spread_signal": round(float(matchup_adjustments["spread_signal"]), 4),
            "total_signal": round(float(matchup_adjustments["total_signal"]), 4),
            "pack_reference": matchup_adjustments["pack_reference"],
            "components": matchup_adjustments["components"],
        },
        "totals_adjustments": {
            "applied": bool(totals_adjustments["applied"]),
            "total_points": round(float(totals_adjustments["total_points"]), 4),
            "stdev_points": round(float(totals_adjustments["stdev_points"]), 4),
            "components": totals_adjustments["components"],
        },
        "totals_calibration": totals_calibration_out,
        "market_blend": market_blend,
        "framework": {
            "framework_version": decomposition["framework_version"],
            "predicted_margin": decomposition["predicted_margin"],
            "predicted_total": decomposition["predicted_total"],
            "factor_coverage": decomposition["factor_coverage"],
            "confidence_score": decomposition["confidence_score"],
            "uncertainty_penalties": decomposition["uncertainty_penalties"],
            "factor_contributions": decomposition["factor_contributions"],
            "guardrails": decomposition["guardrails"],
        },
        "injury_nowcast": {
            "source": inputs.injury_nowcast_source,
            "home_confidence": inputs.injury_nowcast_confidence_home,
            "away_confidence": inputs.injury_nowcast_confidence_away,
            "home_freshness_hours": inputs.injury_nowcast_freshness_home_hours,
            "away_freshness_hours": inputs.injury_nowcast_freshness_away_hours,
            "home_impact": inputs.injury_nowcast_impact_home,
            "away_impact": inputs.injury_nowcast_impact_away,
            "home_offense_multiplier": inputs.injury_nowcast_offense_multiplier_home,
            "away_offense_multiplier": inputs.injury_nowcast_offense_multiplier_away,
            "home_defense_multiplier": inputs.injury_nowcast_defense_multiplier_home,
            "away_defense_multiplier": inputs.injury_nowcast_defense_multiplier_away,
            "home_top_drivers": inputs.injury_nowcast_home_drivers or [],
            "away_top_drivers": inputs.injury_nowcast_away_drivers or [],
        },
        "environment": {
            "weather": {
                "available": inputs.weather_available,
                "source": inputs.weather_source,
                "wind_mph": inputs.weather_wind_mph,
                "precip_mm": inputs.weather_precip_mm,
                "temp_f": inputs.weather_temp_f,
            },
            "travel": {
                "available": inputs.travel_available,
                "travel_miles_home": inputs.travel_miles_home,
                "travel_miles_away": inputs.travel_miles_away,
                "timezone_delta_home": inputs.travel_timezone_delta_home,
                "timezone_delta_away": inputs.travel_timezone_delta_away,
            },
        },
    }
    return {
        "game_id": inputs.game_id,
        "model_version": model_version,
        "simulation_count": sims,
        "inputs": {
            "home_team": inputs.home_team,
            "away_team": inputs.away_team,
            "offense_index_home": inputs.offense_index_home,
            "offense_index_away": inputs.offense_index_away,
            "defense_index_home": inputs.defense_index_home,
            "defense_index_away": inputs.defense_index_away,
            "rest_days_home": inputs.rest_days_home,
            "rest_days_away": inputs.rest_days_away,
            "matchup_season": inputs.matchup_season,
            "matchup_week": inputs.matchup_week,
            "matchup_game_id": inputs.matchup_game_id,
            "matchup_home_team": inputs.matchup_home_team,
            "matchup_away_team": inputs.matchup_away_team,
            "home_off_epa_5g": inputs.home_off_epa_5g,
            "away_off_epa_5g": inputs.away_off_epa_5g,
            "home_def_epa_allowed_5g": inputs.home_def_epa_allowed_5g,
            "away_def_epa_allowed_5g": inputs.away_def_epa_allowed_5g,
            "home_pass_rate_5g": inputs.home_pass_rate_5g,
            "away_pass_rate_5g": inputs.away_pass_rate_5g,
            "home_success_offense_5g": inputs.home_success_offense_5g,
            "away_success_offense_5g": inputs.away_success_offense_5g,
            "home_success_defense_allowed_5g": inputs.home_success_defense_allowed_5g,
            "away_success_defense_allowed_5g": inputs.away_success_defense_allowed_5g,
            "matchup_diff_off_epa_5g": inputs.matchup_diff_off_epa_5g,
            "matchup_diff_def_epa_allowed_5g": inputs.matchup_diff_def_epa_allowed_5g,
            "matchup_diff_pressure_generated_5g": inputs.matchup_diff_pressure_generated_5g,
            "matchup_diff_pressure_allowed_5g": inputs.matchup_diff_pressure_allowed_5g,
            "matchup_diff_red_zone_td_rate_5g": inputs.matchup_diff_red_zone_td_rate_5g,
            "matchup_diff_success_rate_5g": inputs.matchup_diff_success_rate_5g,
            "home_kav_offense_5g": inputs.home_kav_offense_5g,
            "away_kav_offense_5g": inputs.away_kav_offense_5g,
            "home_kav_defense_5g": inputs.home_kav_defense_5g,
            "away_kav_defense_5g": inputs.away_kav_defense_5g,
            "home_kav_net_5g": inputs.home_kav_net_5g,
            "away_kav_net_5g": inputs.away_kav_net_5g,
            "kav_as_of_week": inputs.kav_as_of_week,
            "feature_pack_version": inputs.feature_pack_version,
            "injury_nowcast_confidence_home": inputs.injury_nowcast_confidence_home,
            "injury_nowcast_confidence_away": inputs.injury_nowcast_confidence_away,
            "injury_nowcast_freshness_home_hours": inputs.injury_nowcast_freshness_home_hours,
            "injury_nowcast_freshness_away_hours": inputs.injury_nowcast_freshness_away_hours,
            "injury_nowcast_impact_home": inputs.injury_nowcast_impact_home,
            "injury_nowcast_impact_away": inputs.injury_nowcast_impact_away,
            "injury_nowcast_offense_multiplier_home": inputs.injury_nowcast_offense_multiplier_home,
            "injury_nowcast_offense_multiplier_away": inputs.injury_nowcast_offense_multiplier_away,
            "injury_nowcast_defense_multiplier_home": inputs.injury_nowcast_defense_multiplier_home,
            "injury_nowcast_defense_multiplier_away": inputs.injury_nowcast_defense_multiplier_away,
            "injury_nowcast_source": inputs.injury_nowcast_source,
            "weather_available": inputs.weather_available,
            "weather_wind_mph": inputs.weather_wind_mph,
            "weather_precip_mm": inputs.weather_precip_mm,
            "weather_temp_f": inputs.weather_temp_f,
            "weather_source": inputs.weather_source,
            "travel_available": inputs.travel_available,
            "travel_miles_home": inputs.travel_miles_home,
            "travel_miles_away": inputs.travel_miles_away,
            "travel_timezone_delta_home": inputs.travel_timezone_delta_home,
            "travel_timezone_delta_away": inputs.travel_timezone_delta_away,
        },
        "markets": markets,
        "diagnostics": diagnostics,
        "decomposition": decomposition,
    }
