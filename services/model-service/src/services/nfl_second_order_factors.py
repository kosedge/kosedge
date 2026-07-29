"""Pure helpers for narrow second-order factors (E/H/D).

Keep these leakage-safe and bounded. Heavy scraping / scheme-fit / SGP stay out.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _f(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def compute_travel_weather_interaction(
    *,
    travel_miles_away: Optional[float],
    travel_miles_home: Optional[float],
    travel_timezone_delta_away: Optional[float],
    travel_timezone_delta_home: Optional[float],
    weather_wind_mph: Optional[float],
    weather_precip_mm: Optional[float],
    weather_temp_f: Optional[float],
    weather_available: bool,
    travel_available: bool,
    miles_wind_weight_total: float = -0.000035,
    tz_precip_weight_margin: float = 0.04,
    max_margin_points: float = 0.75,
    max_total_points: float = 1.4,
) -> Dict[str, Any]:
    """Bounded travel × weather interaction (outdoor / circadian stress).

    Graceful skip when either feed is unavailable → zeros + available=False.
    Margin: home-friendly when away travel/tz stress coincides with bad weather.
    Total: depress totals when long travel meets wind/precip.
    """
    if not weather_available or not travel_available:
        return {
            "margin_points": 0.0,
            "total_points": 0.0,
            "available": False,
            "raw_signals": {"skipped": "weather_or_travel_unavailable"},
        }

    away_miles = max(0.0, _f(travel_miles_away))
    home_miles = max(0.0, _f(travel_miles_home))
    away_tz = abs(_f(travel_timezone_delta_away))
    home_tz = abs(_f(travel_timezone_delta_home))
    wind = max(0.0, _f(weather_wind_mph))
    precip = max(0.0, _f(weather_precip_mm))
    temp = _f(weather_temp_f, 60.0)
    extreme_temp = max(0.0, abs(temp - 60.0) - 25.0)

    # Travel "position": net away load relative to home (miles + timezone).
    away_load = (away_miles / 1000.0) + (0.55 * away_tz)
    home_load = (home_miles / 1000.0) + (0.55 * home_tz)
    load_diff = away_load - home_load
    weather_stress = (wind / 12.0) + (precip / 6.0) + (extreme_temp / 20.0)

    margin_raw = load_diff * weather_stress * tz_precip_weight_margin * 8.0
    # Extra home tilt when precip + away timezone delta.
    margin_raw += (away_tz - home_tz) * precip * tz_precip_weight_margin

    total_raw = (
        ((away_miles + home_miles) * wind * miles_wind_weight_total)
        + ((away_miles + home_miles) * precip * miles_wind_weight_total * 1.4)
    )

    return {
        "margin_points": round(_clamp(margin_raw, -max_margin_points, max_margin_points), 4),
        "total_points": round(_clamp(total_raw, -max_total_points, max_total_points), 4),
        "available": True,
        "raw_signals": {
            "away_load": round(away_load, 4),
            "home_load": round(home_load, 4),
            "weather_stress": round(weather_stress, 4),
            "wind_mph": round(wind, 3),
            "precip_mm": round(precip, 3),
        },
    }


def compute_error_regime_uncertainty(
    *,
    info_velocity_abs: float = 0.0,
    hours_since_injury_change: Optional[float] = None,
    weather_available: bool = True,
    factor_coverage: float = 1.0,
    injury_impact: float = 0.0,
    max_stdev_widen: float = 0.85,
    confidence_penalty_weight: float = 0.06,
) -> Dict[str, Any]:
    """Light error-regime detector: widen stdev / cut confidence; no point shift.

    High-velocity injury news, very fresh status changes, missing weather, or
    thin factor coverage push the regime score up.
    """
    regime = 0.0
    regime += _clamp(abs(info_velocity_abs) / 1.5, 0.0, 1.0) * 0.45
    if hours_since_injury_change is not None and hours_since_injury_change < 12.0:
        regime += 0.25 * (1.0 - (hours_since_injury_change / 12.0))
    if not weather_available:
        regime += 0.15
    regime += _clamp(1.0 - factor_coverage, 0.0, 1.0) * 0.20
    regime += _clamp(injury_impact, 0.0, 1.0) * 0.15
    regime = _clamp(regime, 0.0, 1.0)

    stdev_widen = round(regime * max_stdev_widen, 4)
    confidence_penalty = round(regime * confidence_penalty_weight, 4)
    return {
        "regime_score": round(regime, 4),
        "stdev_widen": stdev_widen,
        "confidence_penalty": confidence_penalty,
        "available": True,
        "margin_points": 0.0,
        "total_points": 0.0,
        "notes": "Uncertainty widening only; no unsupervised point shift.",
    }


def usage_elasticity_tilt(
    *,
    base_usage: float,
    elasticity_5g: Optional[float],
    max_tilt: float = 0.04,
) -> float:
    """Light player-usage tilt from team substitution elasticity (bounded)."""
    if elasticity_5g is None:
        return float(base_usage)
    tilt = _clamp(float(elasticity_5g) * 0.02, -max_tilt, max_tilt)
    return _clamp(float(base_usage) * (1.0 + tilt), 0.0, 1.0)
