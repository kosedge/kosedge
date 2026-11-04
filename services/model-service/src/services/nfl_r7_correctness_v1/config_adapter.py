"""Versioned opt-in math/config adapter. CERT=0.

Frozen source names (not features): 83 NFL_FRAMEWORK + 13 NFL_TOTALS.
Resolver, totals adjustment, and helpers consume explicit immutable values.
No ambient numeric env read or mutation. Does not edit pinned FW/SIM files.
"""

from __future__ import annotations

from contextvars import ContextVar
from types import MappingProxyType
from typing import Any, Mapping

ADAPTER_VERSION = "r7-config-adapter-v1"
APPLY_LINEAR_TOTALS_CALIBRATION = False

# (name, default, kind, branch) — branch is active | disabled | unavailable
# disabled = feature flag False in frozen source. unavailable = R7 profile does not apply.
_FW_CATALOG: tuple[tuple[str, Any, str, str], ...] = (
    ("NFL_FRAMEWORK_PRIOR_TOTAL_POINTS", 45.3, "float", "active"),
    ("NFL_FRAMEWORK_PRIOR_MARGIN_POINTS", 1.5, "float", "active"),
    ("NFL_FRAMEWORK_HOME_FIELD_POINTS", 1.05, "float", "active"),
    ("NFL_FRAMEWORK_BASE_SCORE_STDEV", 9.8, "float", "active"),
    ("NFL_FRAMEWORK_BASE_EFF_MARGIN_WEIGHT", 16.0, "float", "active"),
    ("NFL_FRAMEWORK_BASE_EFF_TOTAL_WEIGHT", 10.5, "float", "active"),
    ("NFL_FRAMEWORK_BASE_EFF_MAX_MARGIN_POINTS", 6.5, "float", "active"),
    ("NFL_FRAMEWORK_BASE_EFF_MAX_TOTAL_POINTS", 5.0, "float", "active"),
    ("NFL_FRAMEWORK_HFA_POINTS", 1.05, "float", "active"),
    ("NFL_FRAMEWORK_REST_MARGIN_PER_DAY", 0.18, "float", "active"),
    ("NFL_FRAMEWORK_REST_TOTAL_PER_DAY_ABS", 0.12, "float", "active"),
    ("NFL_FRAMEWORK_REST_MAX_MARGIN_POINTS", 2.0, "float", "active"),
    ("NFL_FRAMEWORK_REST_MAX_TOTAL_POINTS", 1.2, "float", "active"),
    ("NFL_FRAMEWORK_INJURY_MARGIN_WEIGHT", 2.75, "float", "active"),
    ("NFL_FRAMEWORK_INJURY_TOTAL_WEIGHT", 3.25, "float", "active"),
    ("NFL_FRAMEWORK_INJURY_MAX_MARGIN_POINTS", 2.6, "float", "active"),
    ("NFL_FRAMEWORK_INJURY_MAX_TOTAL_POINTS", 2.8, "float", "active"),
    ("NFL_FRAMEWORK_WEATHER_ENABLED", True, "bool", "active"),
    ("NFL_FRAMEWORK_WEATHER_WIND_WEIGHT_TOTAL", -0.07, "float", "active"),
    ("NFL_FRAMEWORK_WEATHER_PRECIP_WEIGHT_TOTAL", -0.12, "float", "active"),
    ("NFL_FRAMEWORK_WEATHER_EXTREME_TEMP_WEIGHT_TOTAL", -0.06, "float", "active"),
    ("NFL_FRAMEWORK_WEATHER_WIND_MARGIN_WEIGHT", -0.01, "float", "active"),
    ("NFL_FRAMEWORK_WEATHER_MAX_MARGIN_POINTS", 0.55, "float", "active"),
    ("NFL_FRAMEWORK_WEATHER_MAX_TOTAL_POINTS", 2.8, "float", "active"),
    ("NFL_FRAMEWORK_TRAVEL_ENABLED", True, "bool", "active"),
    ("NFL_FRAMEWORK_TRAVEL_MILES_WEIGHT_MARGIN", 0.0016, "float", "active"),
    ("NFL_FRAMEWORK_TRAVEL_TIMEZONE_WEIGHT_MARGIN", 0.28, "float", "active"),
    ("NFL_FRAMEWORK_TRAVEL_MILES_WEIGHT_TOTAL", -0.0014, "float", "active"),
    ("NFL_FRAMEWORK_TRAVEL_TIMEZONE_WEIGHT_TOTAL", -0.18, "float", "active"),
    ("NFL_FRAMEWORK_TRAVEL_MAX_MARGIN_POINTS", 1.75, "float", "active"),
    ("NFL_FRAMEWORK_TRAVEL_MAX_TOTAL_POINTS", 1.6, "float", "active"),
    ("NFL_FRAMEWORK_SHORT_REST_THRESHOLD_DAYS", 6.0, "float", "active"),
    ("NFL_FRAMEWORK_SHORT_REST_MARGIN_POINTS", 0.3, "float", "active"),
    ("NFL_FRAMEWORK_SITUATIONAL_MAX_MARGIN_POINTS", 0.8, "float", "active"),
    ("NFL_FRAMEWORK_REGRESSION_MARGIN_WEIGHT", 1.8, "float", "active"),
    ("NFL_FRAMEWORK_REGRESSION_TOTAL_WEIGHT", 1.2, "float", "active"),
    ("NFL_FRAMEWORK_REGRESSION_MAX_MARGIN_POINTS", 1.8, "float", "active"),
    ("NFL_FRAMEWORK_REGRESSION_MAX_TOTAL_POINTS", 1.2, "float", "active"),
    ("NFL_FRAMEWORK_REGRESSION_MIN_RELIABILITY", 0.35, "float", "active"),
    ("NFL_FRAMEWORK_REGRESSION_MAX_RELIABILITY", 0.85, "float", "active"),
    ("NFL_FRAMEWORK_KAV_ENABLED", True, "bool", "active"),
    ("NFL_FRAMEWORK_KAV_MARGIN_WEIGHT", 3.2, "float", "active"),
    ("NFL_FRAMEWORK_KAV_TOTAL_WEIGHT", 2.4, "float", "active"),
    ("NFL_FRAMEWORK_KAV_MAX_MARGIN_POINTS", 3.5, "float", "active"),
    ("NFL_FRAMEWORK_KAV_MAX_TOTAL_POINTS", 2.8, "float", "active"),
    ("NFL_FRAMEWORK_EXTERNAL_DVOA_ENABLED", False, "bool", "disabled"),
    ("NFL_FRAMEWORK_EXTERNAL_DVOA_MARGIN_WEIGHT", 0.0, "float", "disabled"),
    ("NFL_FRAMEWORK_EXTERNAL_DVOA_TOTAL_WEIGHT", 0.0, "float", "disabled"),
    ("NFL_FRAMEWORK_EXTERNAL_DVOA_MAX_MARGIN_POINTS", 0.0, "float", "disabled"),
    ("NFL_FRAMEWORK_EXTERNAL_DVOA_MAX_TOTAL_POINTS", 0.0, "float", "disabled"),
    ("NFL_FRAMEWORK_PERSONNEL_ENABLED", False, "bool", "disabled"),
    ("NFL_FRAMEWORK_PERSONNEL_MARGIN_WEIGHT", 0.85, "float", "disabled"),
    ("NFL_FRAMEWORK_PERSONNEL_TOTAL_WEIGHT", 0.45, "float", "disabled"),
    ("NFL_FRAMEWORK_PERSONNEL_ELASTICITY_MARGIN_WEIGHT", 0.15, "float", "disabled"),
    ("NFL_FRAMEWORK_PERSONNEL_MAX_MARGIN_POINTS", 1.6, "float", "disabled"),
    ("NFL_FRAMEWORK_PERSONNEL_MAX_TOTAL_POINTS", 1.1, "float", "disabled"),
    ("NFL_FRAMEWORK_COACH_AGGRESSION_ENABLED", False, "bool", "disabled"),
    ("NFL_FRAMEWORK_COACH_MARGIN_WEIGHT", 0.55, "float", "disabled"),
    ("NFL_FRAMEWORK_COACH_TOTAL_WEIGHT", 0.45, "float", "disabled"),
    ("NFL_FRAMEWORK_COACH_MAX_MARGIN_POINTS", 1.1, "float", "disabled"),
    ("NFL_FRAMEWORK_COACH_MAX_TOTAL_POINTS", 1.0, "float", "disabled"),
    ("NFL_FRAMEWORK_INFO_VELOCITY_ENABLED", False, "bool", "disabled"),
    ("NFL_FRAMEWORK_INFO_VELOCITY_MARGIN_WEIGHT", 0.90, "float", "disabled"),
    ("NFL_FRAMEWORK_INFO_VELOCITY_TOTAL_WEIGHT", 0.35, "float", "disabled"),
    ("NFL_FRAMEWORK_INFO_VELOCITY_MAX_MARGIN_POINTS", 1.2, "float", "disabled"),
    ("NFL_FRAMEWORK_INFO_VELOCITY_MAX_TOTAL_POINTS", 0.8, "float", "disabled"),
    ("NFL_FRAMEWORK_TRAVEL_WEATHER_ENABLED", True, "bool", "active"),
    ("NFL_FRAMEWORK_TW_MILES_WIND_WEIGHT_TOTAL", -0.000035, "float", "active"),
    ("NFL_FRAMEWORK_TW_TZ_PRECIP_WEIGHT_MARGIN", 0.04, "float", "active"),
    ("NFL_FRAMEWORK_TW_MAX_MARGIN_POINTS", 0.75, "float", "active"),
    ("NFL_FRAMEWORK_TW_MAX_TOTAL_POINTS", 1.4, "float", "active"),
    ("NFL_FRAMEWORK_ERROR_REGIME_ENABLED", True, "bool", "active"),
    ("NFL_FRAMEWORK_ERROR_REGIME_MAX_STDEV_WIDEN", 0.85, "float", "active"),
    ("NFL_FRAMEWORK_ERROR_REGIME_CONFIDENCE_PENALTY", 0.06, "float", "active"),
    ("NFL_FRAMEWORK_BASE_CONFIDENCE", 0.72, "float", "active"),
    ("NFL_FRAMEWORK_MISSING_FACTOR_PENALTY", 0.035, "float", "active"),
    ("NFL_FRAMEWORK_INJURY_STALENESS_THRESHOLD_HOURS", 42.0, "float", "active"),
    ("NFL_FRAMEWORK_INJURY_STALENESS_PENALTY", 0.08, "float", "active"),
    ("NFL_FRAMEWORK_VARIANCE_PENALTY_WEIGHT", 0.09, "float", "active"),
    ("NFL_FRAMEWORK_REGRESSION_PENALTY_WEIGHT", 0.07, "float", "active"),
    ("NFL_FRAMEWORK_MAX_UNCERTAINTY_PENALTY", 0.33, "float", "active"),
    ("NFL_FRAMEWORK_MAX_INJURY_FRESHNESS_HOURS", 72.0, "float", "active"),
    ("NFL_FRAMEWORK_MIN_FACTOR_COVERAGE", 0.55, "float", "active"),
)

_SIM_CATALOG: tuple[tuple[str, Any, str, str], ...] = (
    ("NFL_TOTALS_PASS_RATE_WEIGHT", 3.2, "float", "active"),
    ("NFL_TOTALS_EPA_INTERACTION_WEIGHT", 3.4, "float", "active"),
    ("NFL_TOTALS_SUCCESS_DELTA_WEIGHT", 7.4, "float", "active"),
    ("NFL_TOTALS_INJURY_WEIGHT", 6.0, "float", "active"),
    ("NFL_TOTALS_MAX_ADJUSTMENT_POINTS", 4.2, "float", "active"),
    ("NFL_TOTALS_INJURY_STDEV_WEIGHT", 1.35, "float", "active"),
    ("NFL_TOTALS_MAX_STDEV_ADJUSTMENT", 2.0, "float", "active"),
    ("NFL_TOTALS_CALIBRATION_MIN_TOTAL", 24.0, "float", "unavailable"),
    ("NFL_TOTALS_CALIBRATION_MAX_TOTAL", 66.0, "float", "unavailable"),
    ("NFL_TOTALS_CALIBRATION_SLOPE_DEFAULT", 1.0, "float", "unavailable"),
    ("NFL_TOTALS_CALIBRATION_INTERCEPT_DEFAULT", 0.0, "float", "unavailable"),
    ("NFL_TOTALS_CALIBRATION_MIN_SAMPLE", 80.0, "float", "unavailable"),
    ("NFL_TOTALS_CALIBRATION_INTERCEPT_ABS_MAX", 18.0, "float", "unavailable"),
)

_TOTALS_CTX: ContextVar[Mapping[str, float] | None] = ContextVar("r7_totals_settings", default=None)


def _row(name: str, default: Any, kind: str, branch: str) -> dict[str, Any]:
    return {
        "name": name,
        "value": bool(default) if kind == "bool" else float(default),
        "kind": kind,
        "branch": branch,
    }


def resolve_immutable_config() -> MappingProxyType:
    """Full resolved numerical defaults/flags. No getenv."""
    framework = [_row(*item) for item in _FW_CATALOG]
    simulator = [_row(*item) for item in _SIM_CATALOG]
    if len(framework) != 83:
        raise RuntimeError(f"expected 83 NFL_FRAMEWORK names, got {len(framework)}")
    if len(simulator) != 13:
        raise RuntimeError(f"expected 13 NFL_TOTALS names, got {len(simulator)}")
    fw_values = {row["name"]: row["value"] for row in framework}
    sim_values = {row["name"]: row["value"] for row in simulator}
    body = {
        "adapter_version": ADAPTER_VERSION,
        "apply_linear_totals_calibration": APPLY_LINEAR_TOTALS_CALIBRATION,
        "framework_name_count": 83,
        "simulator_name_count": 13,
        "framework": framework,
        "simulator": simulator,
        "framework_values": fw_values,
        "simulator_values": sim_values,
        "active_framework": [row["name"] for row in framework if row["branch"] == "active"],
        "disabled_framework": [row["name"] for row in framework if row["branch"] == "disabled"],
        "active_simulator": [row["name"] for row in simulator if row["branch"] == "active"],
        "unavailable_simulator": [row["name"] for row in simulator if row["branch"] == "unavailable"],
        "ambient_env_reread": False,
    }
    return MappingProxyType(body)


def totals_adjustment_settings(resolved: Mapping[str, Any] | None = None) -> dict[str, float]:
    """Active NFL_TOTALS values forwarded to _build_totals_adjustments."""
    catalog = resolved if resolved is not None else resolve_immutable_config()
    values = dict(catalog["simulator_values"])
    return {name: float(values[name]) for name in catalog["active_simulator"]}


def framework_config_overrides(resolved: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Explicit overrides for get_nfl_handicapping_config. No getenv."""
    catalog = resolved if resolved is not None else resolve_immutable_config()
    v = catalog["framework_values"]

    def f(name: str) -> float:
        return float(v[name])

    def b(name: str) -> bool:
        return bool(v[name])

    return {
        "priors": {
            "base_total_points": f("NFL_FRAMEWORK_PRIOR_TOTAL_POINTS"),
            "base_margin_points": f("NFL_FRAMEWORK_PRIOR_MARGIN_POINTS"),
            "home_field_points": f("NFL_FRAMEWORK_HOME_FIELD_POINTS"),
            "base_score_stdev": f("NFL_FRAMEWORK_BASE_SCORE_STDEV"),
        },
        "factors": {
            "base_efficiency": {
                "margin_weight": f("NFL_FRAMEWORK_BASE_EFF_MARGIN_WEIGHT"),
                "total_weight": f("NFL_FRAMEWORK_BASE_EFF_TOTAL_WEIGHT"),
                "max_margin_points": f("NFL_FRAMEWORK_BASE_EFF_MAX_MARGIN_POINTS"),
                "max_total_points": f("NFL_FRAMEWORK_BASE_EFF_MAX_TOTAL_POINTS"),
            },
            "home_field_advantage": {"margin_points": f("NFL_FRAMEWORK_HFA_POINTS")},
            "rest_travel": {
                "margin_per_day": f("NFL_FRAMEWORK_REST_MARGIN_PER_DAY"),
                "total_per_day_abs": f("NFL_FRAMEWORK_REST_TOTAL_PER_DAY_ABS"),
                "max_margin_points": f("NFL_FRAMEWORK_REST_MAX_MARGIN_POINTS"),
                "max_total_points": f("NFL_FRAMEWORK_REST_MAX_TOTAL_POINTS"),
            },
            "injuries_depth": {
                "margin_weight": f("NFL_FRAMEWORK_INJURY_MARGIN_WEIGHT"),
                "total_weight": f("NFL_FRAMEWORK_INJURY_TOTAL_WEIGHT"),
                "max_margin_points": f("NFL_FRAMEWORK_INJURY_MAX_MARGIN_POINTS"),
                "max_total_points": f("NFL_FRAMEWORK_INJURY_MAX_TOTAL_POINTS"),
            },
            "weather_environment": {
                "enabled": b("NFL_FRAMEWORK_WEATHER_ENABLED"),
                "wind_mph_weight_total": f("NFL_FRAMEWORK_WEATHER_WIND_WEIGHT_TOTAL"),
                "precip_mm_weight_total": f("NFL_FRAMEWORK_WEATHER_PRECIP_WEIGHT_TOTAL"),
                "extreme_temp_weight_total": f("NFL_FRAMEWORK_WEATHER_EXTREME_TEMP_WEIGHT_TOTAL"),
                "wind_margin_weight": f("NFL_FRAMEWORK_WEATHER_WIND_MARGIN_WEIGHT"),
                "max_margin_points": f("NFL_FRAMEWORK_WEATHER_MAX_MARGIN_POINTS"),
                "max_total_points": f("NFL_FRAMEWORK_WEATHER_MAX_TOTAL_POINTS"),
            },
            "travel_schedule": {
                "enabled": b("NFL_FRAMEWORK_TRAVEL_ENABLED"),
                "miles_weight_margin": f("NFL_FRAMEWORK_TRAVEL_MILES_WEIGHT_MARGIN"),
                "timezone_weight_margin": f("NFL_FRAMEWORK_TRAVEL_TIMEZONE_WEIGHT_MARGIN"),
                "miles_weight_total": f("NFL_FRAMEWORK_TRAVEL_MILES_WEIGHT_TOTAL"),
                "timezone_weight_total": f("NFL_FRAMEWORK_TRAVEL_TIMEZONE_WEIGHT_TOTAL"),
                "max_margin_points": f("NFL_FRAMEWORK_TRAVEL_MAX_MARGIN_POINTS"),
                "max_total_points": f("NFL_FRAMEWORK_TRAVEL_MAX_TOTAL_POINTS"),
            },
            "situational_flags": {
                "short_rest_threshold_days": f("NFL_FRAMEWORK_SHORT_REST_THRESHOLD_DAYS"),
                "short_rest_margin_points": f("NFL_FRAMEWORK_SHORT_REST_MARGIN_POINTS"),
                "max_margin_points": f("NFL_FRAMEWORK_SITUATIONAL_MAX_MARGIN_POINTS"),
            },
            "regression_luck": {
                "margin_weight": f("NFL_FRAMEWORK_REGRESSION_MARGIN_WEIGHT"),
                "total_weight": f("NFL_FRAMEWORK_REGRESSION_TOTAL_WEIGHT"),
                "max_margin_points": f("NFL_FRAMEWORK_REGRESSION_MAX_MARGIN_POINTS"),
                "max_total_points": f("NFL_FRAMEWORK_REGRESSION_MAX_TOTAL_POINTS"),
                "min_reliability": f("NFL_FRAMEWORK_REGRESSION_MIN_RELIABILITY"),
                "max_reliability": f("NFL_FRAMEWORK_REGRESSION_MAX_RELIABILITY"),
            },
            "kav_efficiency": {
                "enabled": b("NFL_FRAMEWORK_KAV_ENABLED"),
                "margin_weight": f("NFL_FRAMEWORK_KAV_MARGIN_WEIGHT"),
                "total_weight": f("NFL_FRAMEWORK_KAV_TOTAL_WEIGHT"),
                "max_margin_points": f("NFL_FRAMEWORK_KAV_MAX_MARGIN_POINTS"),
                "max_total_points": f("NFL_FRAMEWORK_KAV_MAX_TOTAL_POINTS"),
            },
            "external_dvoa": {
                "enabled": b("NFL_FRAMEWORK_EXTERNAL_DVOA_ENABLED"),
                "margin_weight": f("NFL_FRAMEWORK_EXTERNAL_DVOA_MARGIN_WEIGHT"),
                "total_weight": f("NFL_FRAMEWORK_EXTERNAL_DVOA_TOTAL_WEIGHT"),
                "max_margin_points": f("NFL_FRAMEWORK_EXTERNAL_DVOA_MAX_MARGIN_POINTS"),
                "max_total_points": f("NFL_FRAMEWORK_EXTERNAL_DVOA_MAX_TOTAL_POINTS"),
            },
            "personnel_efficiency": {
                "enabled": b("NFL_FRAMEWORK_PERSONNEL_ENABLED"),
                "margin_weight": f("NFL_FRAMEWORK_PERSONNEL_MARGIN_WEIGHT"),
                "total_weight": f("NFL_FRAMEWORK_PERSONNEL_TOTAL_WEIGHT"),
                "elasticity_margin_weight": f("NFL_FRAMEWORK_PERSONNEL_ELASTICITY_MARGIN_WEIGHT"),
                "max_margin_points": f("NFL_FRAMEWORK_PERSONNEL_MAX_MARGIN_POINTS"),
                "max_total_points": f("NFL_FRAMEWORK_PERSONNEL_MAX_TOTAL_POINTS"),
            },
            "coach_aggression": {
                "enabled": b("NFL_FRAMEWORK_COACH_AGGRESSION_ENABLED"),
                "margin_weight": f("NFL_FRAMEWORK_COACH_MARGIN_WEIGHT"),
                "total_weight": f("NFL_FRAMEWORK_COACH_TOTAL_WEIGHT"),
                "max_margin_points": f("NFL_FRAMEWORK_COACH_MAX_MARGIN_POINTS"),
                "max_total_points": f("NFL_FRAMEWORK_COACH_MAX_TOTAL_POINTS"),
            },
            "info_velocity": {
                "enabled": b("NFL_FRAMEWORK_INFO_VELOCITY_ENABLED"),
                "margin_weight": f("NFL_FRAMEWORK_INFO_VELOCITY_MARGIN_WEIGHT"),
                "total_weight": f("NFL_FRAMEWORK_INFO_VELOCITY_TOTAL_WEIGHT"),
                "max_margin_points": f("NFL_FRAMEWORK_INFO_VELOCITY_MAX_MARGIN_POINTS"),
                "max_total_points": f("NFL_FRAMEWORK_INFO_VELOCITY_MAX_TOTAL_POINTS"),
            },
            "travel_weather_interaction": {
                "enabled": b("NFL_FRAMEWORK_TRAVEL_WEATHER_ENABLED"),
                "miles_wind_weight_total": f("NFL_FRAMEWORK_TW_MILES_WIND_WEIGHT_TOTAL"),
                "tz_precip_weight_margin": f("NFL_FRAMEWORK_TW_TZ_PRECIP_WEIGHT_MARGIN"),
                "max_margin_points": f("NFL_FRAMEWORK_TW_MAX_MARGIN_POINTS"),
                "max_total_points": f("NFL_FRAMEWORK_TW_MAX_TOTAL_POINTS"),
            },
            "error_regime": {
                "enabled": b("NFL_FRAMEWORK_ERROR_REGIME_ENABLED"),
                "max_stdev_widen": f("NFL_FRAMEWORK_ERROR_REGIME_MAX_STDEV_WIDEN"),
                "confidence_penalty_weight": f("NFL_FRAMEWORK_ERROR_REGIME_CONFIDENCE_PENALTY"),
            },
        },
        "uncertainty": {
            "base_confidence": f("NFL_FRAMEWORK_BASE_CONFIDENCE"),
            "missing_factor_penalty": f("NFL_FRAMEWORK_MISSING_FACTOR_PENALTY"),
            "injury_staleness_threshold_hours": f("NFL_FRAMEWORK_INJURY_STALENESS_THRESHOLD_HOURS"),
            "injury_staleness_penalty": f("NFL_FRAMEWORK_INJURY_STALENESS_PENALTY"),
            "variance_penalty_weight": f("NFL_FRAMEWORK_VARIANCE_PENALTY_WEIGHT"),
            "regression_penalty_weight": f("NFL_FRAMEWORK_REGRESSION_PENALTY_WEIGHT"),
        },
        "guardrails": {
            "max_uncertainty_penalty": f("NFL_FRAMEWORK_MAX_UNCERTAINTY_PENALTY"),
            "max_injury_freshness_hours": f("NFL_FRAMEWORK_MAX_INJURY_FRESHNESS_HOURS"),
            "min_factor_coverage": f("NFL_FRAMEWORK_MIN_FACTOR_COVERAGE"),
        },
    }


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _feature_component(raw_value: float | None, *, low: float, high: float, weight: float) -> dict[str, float]:
    raw = float(raw_value) if raw_value is not None else 0.0
    bounded = _clamp(raw, low, high)
    return {"raw": raw, "bounded": bounded, "points": bounded * weight}


def build_totals_adjustments_explicit(inputs: Any, settings: Mapping[str, float]) -> dict[str, Any]:
    """Same math as nfl_simulator._build_totals_adjustments; explicit settings only."""
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
        return {"applied": False, "total_points": 0.0, "stdev_points": 0.0, "components": {}}

    def w(name: str) -> float:
        if name not in settings:
            raise KeyError(f"totals setting {name} not forwarded")
        return float(settings[name])

    pass_rate_total = (inputs.home_pass_rate_5g or 0.57) + (inputs.away_pass_rate_5g or 0.57)
    pass_rate_component = _feature_component(
        pass_rate_total - 1.14, low=-0.20, high=0.20, weight=w("NFL_TOTALS_PASS_RATE_WEIGHT")
    )
    epa_interaction_raw = (
        (inputs.home_off_epa_5g or 0.0)
        + (inputs.away_off_epa_5g or 0.0)
        + (inputs.home_def_epa_allowed_5g or 0.0)
        + (inputs.away_def_epa_allowed_5g or 0.0)
    )
    epa_interaction_component = _feature_component(
        epa_interaction_raw, low=-0.45, high=0.45, weight=w("NFL_TOTALS_EPA_INTERACTION_WEIGHT")
    )
    success_delta_raw = (
        ((inputs.home_success_offense_5g or 0.44) + (inputs.away_success_offense_5g or 0.44))
        - ((inputs.home_success_defense_allowed_5g or 0.44) + (inputs.away_success_defense_allowed_5g or 0.44))
    )
    success_delta_component = _feature_component(
        success_delta_raw, low=-0.12, high=0.12, weight=w("NFL_TOTALS_SUCCESS_DELTA_WEIGHT")
    )
    home_off_mult = _clamp(inputs.injury_nowcast_offense_multiplier_home or 1.0, 0.82, 1.08)
    away_off_mult = _clamp(inputs.injury_nowcast_offense_multiplier_away or 1.0, 0.82, 1.08)
    home_def_mult = _clamp(inputs.injury_nowcast_defense_multiplier_home or 1.0, 0.90, 1.18)
    away_def_mult = _clamp(inputs.injury_nowcast_defense_multiplier_away or 1.0, 0.90, 1.18)
    injury_conf = _clamp(
        ((inputs.injury_nowcast_confidence_home or 0.0) + (inputs.injury_nowcast_confidence_away or 0.0)) / 2.0,
        0.0,
        1.0,
    )
    offense_drag = ((1.0 - home_off_mult) + (1.0 - away_off_mult))
    defense_leak = ((home_def_mult - 1.0) + (away_def_mult - 1.0))
    injury_total_raw = (0.7 * defense_leak) - (1.25 * offense_drag)
    injury_component = _feature_component(
        injury_total_raw * injury_conf, low=-0.22, high=0.22, weight=w("NFL_TOTALS_INJURY_WEIGHT")
    )
    max_adj = w("NFL_TOTALS_MAX_ADJUSTMENT_POINTS")
    total_points = _clamp(
        pass_rate_component["points"]
        + epa_interaction_component["points"]
        + success_delta_component["points"]
        + injury_component["points"],
        -max_adj,
        max_adj,
    )
    injury_impact_strength = _clamp(
        ((inputs.injury_nowcast_impact_home or 0.0) + (inputs.injury_nowcast_impact_away or 0.0)) * injury_conf,
        0.0,
        1.0,
    )
    stdev_points = _clamp(
        injury_impact_strength * w("NFL_TOTALS_INJURY_STDEV_WEIGHT"),
        0.0,
        w("NFL_TOTALS_MAX_STDEV_ADJUSTMENT"),
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
        "settings_source": "r7-config-adapter-v1",
    }


def install_totals_adapter(sim: Any) -> None:
    """One-time wrap of isolated IF _build_totals_adjustments. ContextVar, concurrent-safe."""
    if getattr(sim, "_r7_totals_adapted", False):
        return
    original = sim._build_totals_adjustments

    def adapted(inputs: Any) -> dict[str, Any]:
        settings = _TOTALS_CTX.get()
        if settings is None:
            return original(inputs)
        return build_totals_adjustments_explicit(inputs, settings)

    sim._build_totals_adjustments = adapted
    sim._r7_totals_adapted = True


def push_totals_settings(settings: Mapping[str, float]):
    return _TOTALS_CTX.set(dict(settings))


def reset_totals_settings(token: Any) -> None:
    _TOTALS_CTX.reset(token)
