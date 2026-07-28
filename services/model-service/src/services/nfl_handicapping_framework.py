from __future__ import annotations

import os
from copy import deepcopy
from typing import Any, Dict, Iterable, List, Optional

NFL_HANDICAPPING_FRAMEWORK_VERSION = "nfl-handicap-core-v3"


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return float(default)
    try:
        return float(raw)
    except ValueError:
        return float(default)


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _to_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return bool(default)
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _safe_component_points(components: Dict[str, Any], key: str) -> float:
    item = components.get(key)
    if not isinstance(item, dict):
        return 0.0
    return _to_float(item.get("points"), 0.0) or 0.0


def _merge_config(base: Dict[str, Any], overrides: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    merged = deepcopy(base)
    if not isinstance(overrides, dict):
        return merged

    def _merge(dst: Dict[str, Any], src: Dict[str, Any]) -> None:
        for key, value in src.items():
            if isinstance(value, dict) and isinstance(dst.get(key), dict):
                _merge(dst[key], value)
            else:
                dst[key] = value

    _merge(merged, overrides)
    return merged


def get_nfl_handicapping_config(config_overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    min_quality_default = _env_float("NFL_EDGE_MIN_QUALITY_SCORE", 58.0)
    min_confidence_default = _env_float("NFL_EDGE_MIN_CONFIDENCE_SCORE", 0.53)
    min_edge_default = _env_float("NFL_EDGE_MIN_ML_EDGE_PROB", 0.01)
    base = {
        "framework_version": NFL_HANDICAPPING_FRAMEWORK_VERSION,
        "priors": {
            # 2023-2025 league game totals average ~45.3 (see calibration audit).
            # Prior 43.5 systematically under-projected O/U and flooded Under edges.
            "base_total_points": _env_float("NFL_FRAMEWORK_PRIOR_TOTAL_POINTS", 45.3),
            "base_margin_points": _env_float("NFL_FRAMEWORK_PRIOR_MARGIN_POINTS", 1.5),
            # 2023–2025 adaptive re-sim: model home spreads ~0.7pts stronger than
            # market and slight negative home ATS margin — trim HFA toward 1.0.
            "home_field_points": _env_float("NFL_FRAMEWORK_HOME_FIELD_POINTS", 1.05),
            # Single-team score stdev ~9.8-10.3 in recent seasons; 9.2 was slightly tight.
            "base_score_stdev": _env_float("NFL_FRAMEWORK_BASE_SCORE_STDEV", 9.8),
        },
        "factors": {
            "base_efficiency": {
                "margin_weight": _env_float("NFL_FRAMEWORK_BASE_EFF_MARGIN_WEIGHT", 16.0),
                "total_weight": _env_float("NFL_FRAMEWORK_BASE_EFF_TOTAL_WEIGHT", 10.5),
                "max_margin_points": _env_float("NFL_FRAMEWORK_BASE_EFF_MAX_MARGIN_POINTS", 6.5),
                "max_total_points": _env_float("NFL_FRAMEWORK_BASE_EFF_MAX_TOTAL_POINTS", 5.0),
            },
            "home_field_advantage": {
                # Keep in sync with priors.home_field_points (trimmed after 2023–25 ATS audit).
                "margin_points": _env_float("NFL_FRAMEWORK_HFA_POINTS", 1.05),
            },
            "rest_travel": {
                "margin_per_day": _env_float("NFL_FRAMEWORK_REST_MARGIN_PER_DAY", 0.18),
                "total_per_day_abs": _env_float("NFL_FRAMEWORK_REST_TOTAL_PER_DAY_ABS", 0.12),
                "max_margin_points": _env_float("NFL_FRAMEWORK_REST_MAX_MARGIN_POINTS", 2.0),
                "max_total_points": _env_float("NFL_FRAMEWORK_REST_MAX_TOTAL_POINTS", 1.2),
            },
            "injuries_depth": {
                "margin_weight": _env_float("NFL_FRAMEWORK_INJURY_MARGIN_WEIGHT", 2.75),
                "total_weight": _env_float("NFL_FRAMEWORK_INJURY_TOTAL_WEIGHT", 3.25),
                "max_margin_points": _env_float("NFL_FRAMEWORK_INJURY_MAX_MARGIN_POINTS", 2.6),
                "max_total_points": _env_float("NFL_FRAMEWORK_INJURY_MAX_TOTAL_POINTS", 2.8),
            },
            "weather_environment": {
                "enabled": _to_bool(os.getenv("NFL_FRAMEWORK_WEATHER_ENABLED"), True),
                "wind_mph_weight_total": _env_float("NFL_FRAMEWORK_WEATHER_WIND_WEIGHT_TOTAL", -0.07),
                "precip_mm_weight_total": _env_float("NFL_FRAMEWORK_WEATHER_PRECIP_WEIGHT_TOTAL", -0.12),
                "extreme_temp_weight_total": _env_float("NFL_FRAMEWORK_WEATHER_EXTREME_TEMP_WEIGHT_TOTAL", -0.06),
                "wind_margin_weight": _env_float("NFL_FRAMEWORK_WEATHER_WIND_MARGIN_WEIGHT", -0.01),
                "max_margin_points": _env_float("NFL_FRAMEWORK_WEATHER_MAX_MARGIN_POINTS", 0.55),
                "max_total_points": _env_float("NFL_FRAMEWORK_WEATHER_MAX_TOTAL_POINTS", 2.8),
            },
            "travel_schedule": {
                "enabled": _to_bool(os.getenv("NFL_FRAMEWORK_TRAVEL_ENABLED"), True),
                "miles_weight_margin": _env_float("NFL_FRAMEWORK_TRAVEL_MILES_WEIGHT_MARGIN", 0.0016),
                "timezone_weight_margin": _env_float("NFL_FRAMEWORK_TRAVEL_TIMEZONE_WEIGHT_MARGIN", 0.28),
                "miles_weight_total": _env_float("NFL_FRAMEWORK_TRAVEL_MILES_WEIGHT_TOTAL", -0.0014),
                "timezone_weight_total": _env_float("NFL_FRAMEWORK_TRAVEL_TIMEZONE_WEIGHT_TOTAL", -0.18),
                "max_margin_points": _env_float("NFL_FRAMEWORK_TRAVEL_MAX_MARGIN_POINTS", 1.75),
                "max_total_points": _env_float("NFL_FRAMEWORK_TRAVEL_MAX_TOTAL_POINTS", 1.6),
            },
            "situational_flags": {
                "short_rest_threshold_days": _env_float("NFL_FRAMEWORK_SHORT_REST_THRESHOLD_DAYS", 6.0),
                "short_rest_margin_points": _env_float("NFL_FRAMEWORK_SHORT_REST_MARGIN_POINTS", 0.3),
                "max_margin_points": _env_float("NFL_FRAMEWORK_SITUATIONAL_MAX_MARGIN_POINTS", 0.8),
            },
            "regression_luck": {
                "margin_weight": _env_float("NFL_FRAMEWORK_REGRESSION_MARGIN_WEIGHT", 1.8),
                "total_weight": _env_float("NFL_FRAMEWORK_REGRESSION_TOTAL_WEIGHT", 1.2),
                "max_margin_points": _env_float("NFL_FRAMEWORK_REGRESSION_MAX_MARGIN_POINTS", 1.8),
                "max_total_points": _env_float("NFL_FRAMEWORK_REGRESSION_MAX_TOTAL_POINTS", 1.2),
                "min_reliability": _clamp(_env_float("NFL_FRAMEWORK_REGRESSION_MIN_RELIABILITY", 0.35), 0.1, 1.0),
                "max_reliability": _clamp(_env_float("NFL_FRAMEWORK_REGRESSION_MAX_RELIABILITY", 0.85), 0.2, 1.0),
            },
            # Owned opponent-adjusted efficiency (KAV). Ground-truth for the model.
            "kav_efficiency": {
                "enabled": _to_bool(os.getenv("NFL_FRAMEWORK_KAV_ENABLED"), True),
                "margin_weight": _env_float("NFL_FRAMEWORK_KAV_MARGIN_WEIGHT", 3.2),
                "total_weight": _env_float("NFL_FRAMEWORK_KAV_TOTAL_WEIGHT", 2.4),
                "max_margin_points": _env_float("NFL_FRAMEWORK_KAV_MAX_MARGIN_POINTS", 3.5),
                "max_total_points": _env_float("NFL_FRAMEWORK_KAV_MAX_TOTAL_POINTS", 2.8),
            },
            # Optional public DVOA second opinion — never used for training; placeholder only.
            "external_dvoa": {
                "enabled": _to_bool(os.getenv("NFL_FRAMEWORK_EXTERNAL_DVOA_ENABLED"), False),
                "margin_weight": _env_float("NFL_FRAMEWORK_EXTERNAL_DVOA_MARGIN_WEIGHT", 0.0),
                "total_weight": _env_float("NFL_FRAMEWORK_EXTERNAL_DVOA_TOTAL_WEIGHT", 0.0),
                "max_margin_points": _env_float("NFL_FRAMEWORK_EXTERNAL_DVOA_MAX_MARGIN_POINTS", 0.0),
                "max_total_points": _env_float("NFL_FRAMEWORK_EXTERNAL_DVOA_MAX_TOTAL_POINTS", 0.0),
            },
        },
        "uncertainty": {
            "base_confidence": _clamp(_env_float("NFL_FRAMEWORK_BASE_CONFIDENCE", 0.72), 0.05, 0.99),
            "missing_factor_penalty": _clamp(_env_float("NFL_FRAMEWORK_MISSING_FACTOR_PENALTY", 0.035), 0.0, 0.25),
            "injury_staleness_threshold_hours": _env_float("NFL_FRAMEWORK_INJURY_STALENESS_THRESHOLD_HOURS", 42.0),
            "injury_staleness_penalty": _clamp(_env_float("NFL_FRAMEWORK_INJURY_STALENESS_PENALTY", 0.08), 0.0, 0.3),
            "variance_penalty_weight": _clamp(_env_float("NFL_FRAMEWORK_VARIANCE_PENALTY_WEIGHT", 0.09), 0.0, 0.4),
            "regression_penalty_weight": _clamp(_env_float("NFL_FRAMEWORK_REGRESSION_PENALTY_WEIGHT", 0.07), 0.0, 0.3),
        },
        "guardrails": {
            "min_quality_score": min_quality_default,
            "min_confidence_score": min_confidence_default,
            "min_ml_edge_prob": min_edge_default,
            "max_uncertainty_penalty": _env_float("NFL_FRAMEWORK_MAX_UNCERTAINTY_PENALTY", 0.33),
            "max_injury_freshness_hours": _env_float("NFL_FRAMEWORK_MAX_INJURY_FRESHNESS_HOURS", 72.0),
            "min_factor_coverage": _clamp(_env_float("NFL_FRAMEWORK_MIN_FACTOR_COVERAGE", 0.55), 0.0, 1.0),
        },
    }
    return _merge_config(base, config_overrides)


def compute_nfl_projection_decomposition(
    *,
    offense_index_home: float,
    offense_index_away: float,
    defense_index_home: float,
    defense_index_away: float,
    rest_days_home: float,
    rest_days_away: float,
    matchup_adjustments: Dict[str, Any],
    totals_adjustments: Dict[str, Any],
    injury_nowcast_impact_home: Optional[float],
    injury_nowcast_impact_away: Optional[float],
    injury_nowcast_freshness_home_hours: Optional[float],
    injury_nowcast_freshness_away_hours: Optional[float],
    injury_nowcast_confidence_home: Optional[float],
    injury_nowcast_confidence_away: Optional[float],
    injury_nowcast_offense_multiplier_home: Optional[float],
    injury_nowcast_offense_multiplier_away: Optional[float],
    injury_nowcast_defense_multiplier_home: Optional[float],
    injury_nowcast_defense_multiplier_away: Optional[float],
    weather_wind_mph: Optional[float] = None,
    weather_precip_mm: Optional[float] = None,
    weather_temp_f: Optional[float] = None,
    weather_available: Optional[bool] = None,
    travel_miles_home: Optional[float] = None,
    travel_miles_away: Optional[float] = None,
    travel_timezone_delta_home: Optional[float] = None,
    travel_timezone_delta_away: Optional[float] = None,
    travel_available: Optional[bool] = None,
    home_kav_net_5g: Optional[float] = None,
    away_kav_net_5g: Optional[float] = None,
    home_kav_offense_5g: Optional[float] = None,
    away_kav_offense_5g: Optional[float] = None,
    home_kav_defense_5g: Optional[float] = None,
    away_kav_defense_5g: Optional[float] = None,
    kav_as_of_week: Optional[int] = None,
    external_dvoa_home: Optional[float] = None,
    external_dvoa_away: Optional[float] = None,
    config_overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    cfg = get_nfl_handicapping_config(config_overrides=config_overrides)
    factors_cfg = cfg["factors"]
    priors = cfg["priors"]

    matchup_components = matchup_adjustments.get("components") if isinstance(matchup_adjustments, dict) else {}
    matchup_components = matchup_components if isinstance(matchup_components, dict) else {}
    totals_components = totals_adjustments.get("components") if isinstance(totals_adjustments, dict) else {}
    totals_components = totals_components if isinstance(totals_components, dict) else {}

    off_def_home = _clamp((offense_index_home / max(0.75, defense_index_away)) - 1.0, -0.25, 0.25)
    off_def_away = _clamp((offense_index_away / max(0.75, defense_index_home)) - 1.0, -0.25, 0.25)
    spread_signal = _to_float(matchup_adjustments.get("spread_signal"), 0.0) or 0.0
    total_signal = _to_float(matchup_adjustments.get("total_signal"), 0.0) or 0.0

    base_margin_points = _clamp(
        (off_def_home - off_def_away) * factors_cfg["base_efficiency"]["margin_weight"] + (0.35 * spread_signal),
        -factors_cfg["base_efficiency"]["max_margin_points"],
        factors_cfg["base_efficiency"]["max_margin_points"],
    )
    base_total_points = _clamp(
        (off_def_home + off_def_away) * factors_cfg["base_efficiency"]["total_weight"]
        + (0.28 * total_signal)
        + _safe_component_points(totals_components, "combined_pass_rate_5g")
        + _safe_component_points(totals_components, "offense_defense_epa_interaction_5g"),
        -factors_cfg["base_efficiency"]["max_total_points"],
        factors_cfg["base_efficiency"]["max_total_points"],
    )

    rest_delta = float(rest_days_home) - float(rest_days_away)
    rest_margin_points = _clamp(
        rest_delta * factors_cfg["rest_travel"]["margin_per_day"],
        -factors_cfg["rest_travel"]["max_margin_points"],
        factors_cfg["rest_travel"]["max_margin_points"],
    )
    rest_total_points = _clamp(
        -abs(rest_delta) * factors_cfg["rest_travel"]["total_per_day_abs"],
        -factors_cfg["rest_travel"]["max_total_points"],
        factors_cfg["rest_travel"]["max_total_points"],
    )

    injury_conf = _clamp(
        ((_to_float(injury_nowcast_confidence_home, 0.0) or 0.0) + (_to_float(injury_nowcast_confidence_away, 0.0) or 0.0))
        / 2.0,
        0.0,
        1.0,
    )
    offense_mult_home = _clamp(_to_float(injury_nowcast_offense_multiplier_home, 1.0) or 1.0, 0.82, 1.12)
    offense_mult_away = _clamp(_to_float(injury_nowcast_offense_multiplier_away, 1.0) or 1.0, 0.82, 1.12)
    defense_mult_home = _clamp(_to_float(injury_nowcast_defense_multiplier_home, 1.0) or 1.0, 0.9, 1.2)
    defense_mult_away = _clamp(_to_float(injury_nowcast_defense_multiplier_away, 1.0) or 1.0, 0.9, 1.2)
    injury_margin_signal = (
        (_to_float(injury_nowcast_impact_away, 0.0) or 0.0)
        - (_to_float(injury_nowcast_impact_home, 0.0) or 0.0)
        + (offense_mult_home - offense_mult_away)
        + ((defense_mult_away - 1.0) - (defense_mult_home - 1.0))
    )
    injury_margin_points = _clamp(
        injury_margin_signal * injury_conf * factors_cfg["injuries_depth"]["margin_weight"],
        -factors_cfg["injuries_depth"]["max_margin_points"],
        factors_cfg["injuries_depth"]["max_margin_points"],
    )
    injury_total_points = _clamp(
        _safe_component_points(totals_components, "injury_total_signal")
        + (
            (_to_float(injury_nowcast_impact_home, 0.0) or 0.0)
            + (_to_float(injury_nowcast_impact_away, 0.0) or 0.0)
        )
        * injury_conf
        * factors_cfg["injuries_depth"]["total_weight"],
        -factors_cfg["injuries_depth"]["max_total_points"],
        factors_cfg["injuries_depth"]["max_total_points"],
    )

    short_rest_threshold = factors_cfg["situational_flags"]["short_rest_threshold_days"]
    home_short = 1.0 if rest_days_home < short_rest_threshold else 0.0
    away_short = 1.0 if rest_days_away < short_rest_threshold else 0.0
    situational_margin_points = _clamp(
        (away_short - home_short) * factors_cfg["situational_flags"]["short_rest_margin_points"],
        -factors_cfg["situational_flags"]["max_margin_points"],
        factors_cfg["situational_flags"]["max_margin_points"],
    )

    red_zone_points = _safe_component_points(matchup_components, "diff_red_zone_td_rate_5g")
    success_delta_points = _safe_component_points(totals_components, "combined_success_rate_delta_5g")
    regression_margin_points = _clamp(
        -red_zone_points * factors_cfg["regression_luck"]["margin_weight"],
        -factors_cfg["regression_luck"]["max_margin_points"],
        factors_cfg["regression_luck"]["max_margin_points"],
    )
    regression_total_points = _clamp(
        -success_delta_points * factors_cfg["regression_luck"]["total_weight"],
        -factors_cfg["regression_luck"]["max_total_points"],
        factors_cfg["regression_luck"]["max_total_points"],
    )
    spread_strength = _clamp(abs(_to_float(matchup_adjustments.get("spread_signal"), 0.0) or 0.0) / 4.25, 0.0, 1.0)
    epa_strength = _clamp(abs(_safe_component_points(matchup_components, "diff_off_epa_5g")) / 1.6, 0.0, 1.0)
    pressure_strength = _clamp(
        (
            abs(_safe_component_points(matchup_components, "diff_pressure_generated_5g"))
            + abs(_safe_component_points(matchup_components, "diff_pressure_allowed_5g"))
        )
        / 1.4,
        0.0,
        1.0,
    )
    regression_cfg = factors_cfg["regression_luck"]
    regression_reliability = _clamp(
        (0.45 * spread_strength) + (0.35 * epa_strength) + (0.20 * pressure_strength),
        float(regression_cfg.get("min_reliability", 0.35)),
        float(regression_cfg.get("max_reliability", 0.85)),
    )
    regression_margin_points = _clamp(
        regression_margin_points * regression_reliability,
        -factors_cfg["regression_luck"]["max_margin_points"],
        factors_cfg["regression_luck"]["max_margin_points"],
    )
    regression_total_points = _clamp(
        regression_total_points * regression_reliability,
        -factors_cfg["regression_luck"]["max_total_points"],
        factors_cfg["regression_luck"]["max_total_points"],
    )

    weather_cfg = factors_cfg["weather_environment"]
    weather_data_available = bool(weather_available) and bool(weather_cfg.get("enabled"))
    wind_mph = max(0.0, _to_float(weather_wind_mph, 0.0) or 0.0)
    precip_mm = max(0.0, _to_float(weather_precip_mm, 0.0) or 0.0)
    temp_f = _to_float(weather_temp_f)
    extreme_temp = 0.0 if temp_f is None else max(0.0, abs(float(temp_f) - 60.0) - 15.0)
    weather_margin_points = _clamp(
        wind_mph * float(weather_cfg.get("wind_margin_weight", 0.0)),
        -float(weather_cfg.get("max_margin_points", 0.0)),
        float(weather_cfg.get("max_margin_points", 0.0)),
    )
    weather_total_points = _clamp(
        (wind_mph * float(weather_cfg.get("wind_mph_weight_total", 0.0)))
        + (precip_mm * float(weather_cfg.get("precip_mm_weight_total", 0.0)))
        + (extreme_temp * float(weather_cfg.get("extreme_temp_weight_total", 0.0))),
        -float(weather_cfg.get("max_total_points", 0.0)),
        float(weather_cfg.get("max_total_points", 0.0)),
    )
    if not weather_data_available:
        weather_margin_points = 0.0
        weather_total_points = 0.0

    travel_cfg = factors_cfg["travel_schedule"]
    travel_data_available = bool(travel_available) and bool(travel_cfg.get("enabled"))
    away_travel_miles = max(0.0, _to_float(travel_miles_away, 0.0) or 0.0)
    home_travel_miles = max(0.0, _to_float(travel_miles_home, 0.0) or 0.0)
    away_tz = abs(_to_float(travel_timezone_delta_away, 0.0) or 0.0)
    home_tz = abs(_to_float(travel_timezone_delta_home, 0.0) or 0.0)
    travel_margin_points = _clamp(
        ((away_travel_miles - home_travel_miles) * float(travel_cfg.get("miles_weight_margin", 0.0)))
        + ((away_tz - home_tz) * float(travel_cfg.get("timezone_weight_margin", 0.0))),
        -float(travel_cfg.get("max_margin_points", 0.0)),
        float(travel_cfg.get("max_margin_points", 0.0)),
    )
    travel_total_points = _clamp(
        ((away_travel_miles + home_travel_miles) * float(travel_cfg.get("miles_weight_total", 0.0)))
        + ((away_tz + home_tz) * float(travel_cfg.get("timezone_weight_total", 0.0))),
        -float(travel_cfg.get("max_total_points", 0.0)),
        float(travel_cfg.get("max_total_points", 0.0)),
    )
    if not travel_data_available:
        travel_margin_points = 0.0
        travel_total_points = 0.0

    contributions = {
        "base_efficiency": {
            "margin_points": round(base_margin_points, 4),
            "total_points": round(base_total_points, 4),
            "available": True,
            "notes": "Blends offense/defense priors with EPA proxy components.",
            "raw_signals": {
                "off_def_home": round(off_def_home, 5),
                "off_def_away": round(off_def_away, 5),
                "spread_signal": round(spread_signal, 5),
                "total_signal": round(total_signal, 5),
            },
        },
        "home_field_advantage": {
            "margin_points": round(factors_cfg["home_field_advantage"]["margin_points"], 4),
            "total_points": 0.0,
            "available": True,
            "notes": "Static home-field prior in point space.",
            "raw_signals": {},
        },
        "rest_travel": {
            "margin_points": round(rest_margin_points, 4),
            "total_points": round(rest_total_points, 4),
            "available": True,
            "notes": "Rest differential proxy. Travel feed is not yet connected.",
            "raw_signals": {"rest_days_home": rest_days_home, "rest_days_away": rest_days_away, "rest_delta": round(rest_delta, 4)},
        },
        "injuries_depth": {
            "margin_points": round(injury_margin_points, 4),
            "total_points": round(injury_total_points, 4),
            "available": bool(
                injury_nowcast_impact_home is not None
                or injury_nowcast_impact_away is not None
                or injury_nowcast_offense_multiplier_home is not None
                or injury_nowcast_offense_multiplier_away is not None
            ),
            "notes": "Uses injury nowcast multipliers and confidence-aware scaling.",
            "raw_signals": {
                "injury_confidence": round(injury_conf, 4),
                "home_impact": _to_float(injury_nowcast_impact_home),
                "away_impact": _to_float(injury_nowcast_impact_away),
            },
        },
        "weather_environment": {
            "margin_points": round(weather_margin_points, 4),
            "total_points": round(weather_total_points, 4),
            "available": weather_data_available,
            "notes": "Weather impact from wind/precip/extreme temperature context.",
            "raw_signals": {
                "wind_mph": round(wind_mph, 3),
                "precip_mm": round(precip_mm, 3),
                "temp_f": temp_f,
                "extreme_temp_delta": round(extreme_temp, 3),
            },
        },
        "travel_schedule": {
            "margin_points": round(travel_margin_points, 4),
            "total_points": round(travel_total_points, 4),
            "available": travel_data_available,
            "notes": "Travel intensity from away/home mileage and timezone transitions.",
            "raw_signals": {
                "travel_miles_home": round(home_travel_miles, 3),
                "travel_miles_away": round(away_travel_miles, 3),
                "timezone_delta_home": round(home_tz, 3),
                "timezone_delta_away": round(away_tz, 3),
            },
        },
        "situational_flags": {
            "margin_points": round(situational_margin_points, 4),
            "total_points": 0.0,
            "available": True,
            "notes": "Short-rest situational flag only; travel intensity is pending.",
            "raw_signals": {"home_short_rest": bool(home_short), "away_short_rest": bool(away_short)},
        },
        "regression_luck": {
            "margin_points": round(regression_margin_points, 4),
            "total_points": round(regression_total_points, 4),
            "available": bool(red_zone_points or success_delta_points),
            "notes": "Regresses volatile red-zone and success-rate outliers.",
            "raw_signals": {
                "red_zone_component_points": round(red_zone_points, 4),
                "success_delta_component_points": round(success_delta_points, 4),
                "reliability": round(regression_reliability, 4),
            },
        },
        "kav_efficiency": {
            "margin_points": 0.0,
            "total_points": 0.0,
            "available": False,
            "notes": "Owned KAV (opponent-adjusted EPA). Strict week-1 lag.",
            "raw_signals": {},
        },
        "external_dvoa": {
            "margin_points": 0.0,
            "total_points": 0.0,
            "available": False,
            "notes": "Optional public DVOA second opinion; disabled for training.",
            "raw_signals": {},
        },
    }

    kav_cfg = factors_cfg["kav_efficiency"]
    kav_enabled = bool(kav_cfg.get("enabled"))
    kav_home_net = _to_float(home_kav_net_5g)
    kav_away_net = _to_float(away_kav_net_5g)
    if kav_enabled and kav_home_net is not None and kav_away_net is not None:
        kav_diff = kav_home_net - kav_away_net
        kav_margin = _clamp(
            kav_diff * float(kav_cfg["margin_weight"]),
            -float(kav_cfg["max_margin_points"]),
            float(kav_cfg["max_margin_points"]),
        )
        home_off_k = _to_float(home_kav_offense_5g, 0.0) or 0.0
        away_off_k = _to_float(away_kav_offense_5g, 0.0) or 0.0
        home_def_k = _to_float(home_kav_defense_5g, 0.0) or 0.0
        away_def_k = _to_float(away_kav_defense_5g, 0.0) or 0.0
        kav_total_signal = home_off_k + away_off_k + home_def_k + away_def_k
        kav_total = _clamp(
            kav_total_signal * float(kav_cfg["total_weight"]) * 0.5,
            -float(kav_cfg["max_total_points"]),
            float(kav_cfg["max_total_points"]),
        )
        contributions["kav_efficiency"] = {
            "margin_points": round(kav_margin, 4),
            "total_points": round(kav_total, 4),
            "available": True,
            "notes": "Owned KAV (opponent-adjusted EPA). Strict week-1 lag.",
            "raw_signals": {
                "home_kav_net_5g": round(kav_home_net, 6),
                "away_kav_net_5g": round(kav_away_net, 6),
                "diff_kav_net_5g": round(kav_diff, 6),
                "kav_as_of_week": kav_as_of_week,
            },
        }

    ext_cfg = factors_cfg["external_dvoa"]
    ext_home = _to_float(external_dvoa_home)
    ext_away = _to_float(external_dvoa_away)
    if bool(ext_cfg.get("enabled")) and ext_home is not None and ext_away is not None:
        ext_diff = ext_home - ext_away
        ext_margin = _clamp(
            ext_diff * float(ext_cfg["margin_weight"]),
            -float(ext_cfg["max_margin_points"]),
            float(ext_cfg["max_margin_points"]),
        )
        contributions["external_dvoa"] = {
            "margin_points": round(ext_margin, 4),
            "total_points": 0.0,
            "available": True,
            "notes": "Optional public DVOA second opinion (not used in training).",
            "raw_signals": {
                "external_dvoa_home": round(ext_home, 6),
                "external_dvoa_away": round(ext_away, 6),
            },
        }

    predicted_margin = float(
        contributions["base_efficiency"]["margin_points"]
        + contributions["home_field_advantage"]["margin_points"]
        + contributions["rest_travel"]["margin_points"]
        + contributions["injuries_depth"]["margin_points"]
        + contributions["weather_environment"]["margin_points"]
        + contributions["travel_schedule"]["margin_points"]
        + contributions["situational_flags"]["margin_points"]
        + contributions["regression_luck"]["margin_points"]
        + contributions["kav_efficiency"]["margin_points"]
        + contributions["external_dvoa"]["margin_points"]
    )
    predicted_total = float(
        priors["base_total_points"]
        + contributions["base_efficiency"]["total_points"]
        + contributions["rest_travel"]["total_points"]
        + contributions["injuries_depth"]["total_points"]
        + contributions["weather_environment"]["total_points"]
        + contributions["travel_schedule"]["total_points"]
        + contributions["regression_luck"]["total_points"]
        + contributions["kav_efficiency"]["total_points"]
        + contributions["external_dvoa"]["total_points"]
    )
    predicted_total = _clamp(predicted_total, 30.0, 66.0)

    expected_home = max(7.5, (predicted_total + predicted_margin) / 2.0)
    expected_away = max(7.0, (predicted_total - predicted_margin) / 2.0)
    reconstructed_total = expected_home + expected_away

    available_count = sum(1 for item in contributions.values() if bool(item.get("available")))
    factor_coverage = available_count / max(1, len(contributions))
    uncertainty_cfg = cfg["uncertainty"]
    missing_count = len(contributions) - available_count
    freshness_hours = max(
        _to_float(injury_nowcast_freshness_home_hours, 0.0) or 0.0,
        _to_float(injury_nowcast_freshness_away_hours, 0.0) or 0.0,
    )
    penalties = {
        "missing_data": round(missing_count * uncertainty_cfg["missing_factor_penalty"], 4),
        "injury_staleness": round(
            uncertainty_cfg["injury_staleness_penalty"] if freshness_hours > uncertainty_cfg["injury_staleness_threshold_hours"] else 0.0,
            4,
        ),
        "variance": round(
            _clamp((_to_float(totals_adjustments.get("stdev_points"), 0.0) or 0.0) / 2.0, 0.0, 1.0)
            * uncertainty_cfg["variance_penalty_weight"],
            4,
        ),
        "regression": round(
            _clamp(abs(regression_margin_points) / max(0.01, factors_cfg["regression_luck"]["max_margin_points"]), 0.0, 1.0)
            * uncertainty_cfg["regression_penalty_weight"],
            4,
        ),
    }
    total_penalty = round(sum(penalties.values()), 4)
    confidence_score = _clamp(uncertainty_cfg["base_confidence"] - total_penalty, 0.05, 0.99)

    return {
        "framework_version": cfg["framework_version"],
        "predicted_margin": round(predicted_margin, 4),
        "predicted_total": round(reconstructed_total, 4),
        "expected_home_points": round(expected_home, 4),
        "expected_away_points": round(expected_away, 4),
        "factor_contributions": contributions,
        "factor_coverage": round(factor_coverage, 4),
        "confidence_score": round(confidence_score, 4),
        "uncertainty_penalties": {
            **penalties,
            "total_penalty": total_penalty,
            "freshness_hours": round(freshness_hours, 3),
        },
        "guardrails": cfg["guardrails"],
    }


def evaluate_nfl_edge_guardrails(
    *,
    edge_prob: float,
    quality_score: float,
    confidence_score: float,
    uncertainty_penalty: float,
    factor_coverage: float,
    injury_freshness_hours: Optional[float],
    min_quality_score: Optional[float] = None,
    min_confidence_score: Optional[float] = None,
    min_ml_edge_prob: Optional[float] = None,
    max_uncertainty_penalty: Optional[float] = None,
    min_factor_coverage: Optional[float] = None,
    config_overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    cfg = get_nfl_handicapping_config(config_overrides=config_overrides)
    guardrails = cfg["guardrails"]
    resolved_min_quality = float(min_quality_score) if min_quality_score is not None else float(guardrails["min_quality_score"])
    resolved_min_confidence = (
        float(min_confidence_score) if min_confidence_score is not None else float(guardrails["min_confidence_score"])
    )
    resolved_min_edge = float(min_ml_edge_prob) if min_ml_edge_prob is not None else float(guardrails["min_ml_edge_prob"])
    resolved_max_uncertainty_penalty = (
        float(max_uncertainty_penalty)
        if max_uncertainty_penalty is not None
        else float(guardrails["max_uncertainty_penalty"])
    )
    resolved_min_factor_coverage = (
        float(min_factor_coverage)
        if min_factor_coverage is not None
        else float(guardrails["min_factor_coverage"])
    )
    reason_codes: List[str] = []

    if quality_score < resolved_min_quality:
        reason_codes.append("quality_score_below_threshold")
    if confidence_score < resolved_min_confidence:
        reason_codes.append("confidence_score_below_threshold")
    if abs(edge_prob) < resolved_min_edge:
        reason_codes.append("edge_prob_below_threshold")
    if uncertainty_penalty > resolved_max_uncertainty_penalty:
        reason_codes.append("uncertainty_penalty_exceeded")
    if factor_coverage < resolved_min_factor_coverage:
        reason_codes.append("factor_coverage_below_minimum")
    freshness = _to_float(injury_freshness_hours)
    if freshness is not None and freshness > float(guardrails["max_injury_freshness_hours"]):
        reason_codes.append("injury_freshness_stale")

    return {
        "eligible": len(reason_codes) == 0,
        "reason_codes": reason_codes,
        "applied_thresholds": {
            "min_quality_score": resolved_min_quality,
            "min_confidence_score": resolved_min_confidence,
            "min_ml_edge_prob": resolved_min_edge,
            "max_uncertainty_penalty": resolved_max_uncertainty_penalty,
            "min_factor_coverage": resolved_min_factor_coverage,
            "max_injury_freshness_hours": float(guardrails["max_injury_freshness_hours"]),
        },
    }


def summarize_nfl_factor_attribution_from_points(points: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    framework_versions: set[str] = set()
    factor_accumulator: Dict[str, Dict[str, float]] = {}
    rows_with_framework = 0
    for point in points:
        projection = point.get("projection")
        if not isinstance(projection, dict):
            continue
        decomposition = projection.get("decomposition")
        if not isinstance(decomposition, dict):
            continue
        rows_with_framework += 1
        version = decomposition.get("framework_version")
        if isinstance(version, str) and version:
            framework_versions.add(version)
        factors = decomposition.get("factor_contributions")
        if not isinstance(factors, dict):
            continue
        for factor_name, payload in factors.items():
            if not isinstance(payload, dict):
                continue
            bucket = factor_accumulator.setdefault(
                str(factor_name),
                {
                    "rows": 0.0,
                    "available_rows": 0.0,
                    "sum_abs_margin_points": 0.0,
                    "sum_abs_total_points": 0.0,
                },
            )
            bucket["rows"] += 1.0
            if bool(payload.get("available")):
                bucket["available_rows"] += 1.0
            bucket["sum_abs_margin_points"] += abs(_to_float(payload.get("margin_points"), 0.0) or 0.0)
            bucket["sum_abs_total_points"] += abs(_to_float(payload.get("total_points"), 0.0) or 0.0)

    factors_summary: Dict[str, Any] = {}
    for factor_name, bucket in factor_accumulator.items():
        rows = int(bucket["rows"])
        if rows <= 0:
            continue
        factors_summary[factor_name] = {
            "coverage_rate": round(bucket["available_rows"] / rows, 4),
            "avg_abs_margin_points": round(bucket["sum_abs_margin_points"] / rows, 4),
            "avg_abs_total_points": round(bucket["sum_abs_total_points"] / rows, 4),
            "rows": rows,
        }

    return {
        "framework_versions": sorted(framework_versions),
        "rows_with_framework": rows_with_framework,
        "factor_count": len(factors_summary),
        "factors": factors_summary,
    }
