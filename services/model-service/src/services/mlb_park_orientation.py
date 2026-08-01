"""Park CF bearings + park-relative wind for totals-only weather.

ML path keeps absolute wind-dir mul (S0). Totals can optionally apply a
park-relative out-to-CF adjustment without touching win probs / spreads.
"""

from __future__ import annotations

import math
import os
from typing import Dict, Optional

# Approximate center-field bearing from home plate (degrees, meteorological:
# 0=N, 90=E). Sourced from published stadium orientation references; ±5–10° OK
# for a bounded totals mul.
PARK_CF_BEARING_DEG: Dict[str, float] = {
    "ARI": 45.0,
    "ATL": 30.0,
    "BAL": 30.0,
    "BOS": 45.0,
    "CHC": 30.0,
    "CIN": 60.0,
    "CLE": 0.0,
    "COL": 0.0,
    "CWS": 130.0,
    "DET": 150.0,
    "HOU": 25.0,
    "KC": 15.0,
    "LAA": 45.0,
    "LAD": 20.0,
    "MIA": 45.0,
    "MIL": 135.0,
    "MIN": 0.0,
    "NYM": 15.0,
    "NYY": 60.0,
    "OAK": 35.0,
    "PHI": 15.0,
    "PIT": 115.0,
    "SD": 0.0,
    "SEA": 45.0,
    "SF": 90.0,
    "STL": 60.0,
    "TB": 45.0,
    "TEX": 35.0,
    "TOR": 0.0,
    "WSH": 30.0,
}

# Domes / retractable where outdoor wind should not move totals.
_INDOOR_OR_RETRACTABLE = frozenset({"ARI", "HOU", "MIA", "MIL", "SEA", "TB", "TEX", "TOR"})


def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or str(raw).strip() == "":
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


# Default OFF — ship only after densify totals MAE/CLV green + ML flat.
TOTALS_PARK_REL_WIND_ENABLED = _env_flag("MLB_TOTALS_PARK_REL_WIND_ENABLED", False)


def apply_totals_park_rel_wind_flag(enabled: Optional[bool] = None) -> bool:
    global TOTALS_PARK_REL_WIND_ENABLED
    if enabled is not None:
        TOTALS_PARK_REL_WIND_ENABLED = bool(enabled)
    return bool(TOTALS_PARK_REL_WIND_ENABLED)


def get_totals_park_rel_wind_enabled() -> bool:
    return bool(TOTALS_PARK_REL_WIND_ENABLED)


def reset_totals_park_rel_wind_from_env() -> bool:
    return apply_totals_park_rel_wind_flag(_env_flag("MLB_TOTALS_PARK_REL_WIND_ENABLED", False))


def cf_bearing_for_team(home_abbr: Optional[str]) -> Optional[float]:
    if not home_abbr:
        return None
    key = str(home_abbr).strip().upper()
    if key == "AZ":
        key = "ARI"
    if key in {"CHW"}:
        key = "CWS"
    return PARK_CF_BEARING_DEG.get(key)


def wind_to_deg(wind_from_deg: float) -> float:
    """Open-Meteo wind_direction_10m is meteorological 'from'; convert to 'to'."""
    return (float(wind_from_deg) + 180.0) % 360.0


def relative_to_cf_deg(*, wind_from_deg: float, cf_bearing_deg: float) -> float:
    """Angle of wind-to relative to CF bearing in [0, 180] (0 = out to CF)."""
    wind_to = wind_to_deg(wind_from_deg)
    delta = abs(((wind_to - float(cf_bearing_deg) + 180.0) % 360.0) - 180.0)
    return float(delta)


def park_relative_wind_totals_mul(
    *,
    home_abbr: Optional[str],
    wind_from_deg: Optional[float],
    wind_mph: Optional[float],
    weather_reliability: float = 1.0,
) -> float:
    """Bounded totals-only mul. 1.0 when disabled / missing / indoor."""
    if not TOTALS_PARK_REL_WIND_ENABLED:
        return 1.0
    abbr = (home_abbr or "").strip().upper()
    if abbr == "AZ":
        abbr = "ARI"
    if abbr in {"CHW"}:
        abbr = "CWS"
    if abbr in _INDOOR_OR_RETRACTABLE:
        return 1.0
    if wind_from_deg is None or wind_mph is None:
        return 1.0
    cf = cf_bearing_for_team(abbr)
    if cf is None:
        return 1.0
    rel = relative_to_cf_deg(wind_from_deg=float(wind_from_deg), cf_bearing_deg=cf)
    # Out-to-CF (rel≈0) boosts; in-from-CF (rel≈180) suppresses.
    # Cosine: +1 out, −1 in. Scale by excess wind above 6 mph.
    cos_align = math.cos(math.radians(rel))
    wind_excess = max(0.0, float(wind_mph) - 6.0)
    raw = 1.0 + 0.004 * wind_excess * cos_align
    reliability = max(0.0, min(1.0, float(weather_reliability or 1.0)))
    blended = 1.0 + (raw - 1.0) * reliability
    return max(0.97, min(1.04, blended))
