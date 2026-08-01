"""Bounded PA-sim input sharpening for subscription-grade MLB pricing.

Pure helpers only — no I/O. Every multiplier is clamped so holdout walks
cannot be broken by a single noisy feature (missing SP, short rest, etc.).
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Dict, Optional

from .mlb_simulator import MlbGameInputs

# Indoor / roof-closed parks: weather should not dominate run environment.
_DOME_OR_RETRACTABLE = {
    "ARI",
    "HOU",
    "MIA",
    "MIL",
    "TB",
    "TEX",
    "TOR",
}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def starter_firmness(
    *,
    starter_name: Optional[str],
    starter_source: Optional[str] = None,
    lineup_confirmed: bool = False,
) -> float:
    """0.35–1.0 confidence that the named starter will actually take the ball."""
    if not starter_name or not str(starter_name).strip():
        return 0.40
    source = (starter_source or "").lower()
    if source in {"mlb-stats-api", "static-prior"}:
        base = 0.88
    elif source in {"heuristic-fallback", "neutral"}:
        base = 0.62
    else:
        base = 0.72
    if lineup_confirmed:
        base += 0.08
    return _clamp(base, 0.35, 1.0)


def apply_missing_pitcher_shrink(
    starter_quality: float,
    *,
    firmness: float,
    max_shrink: float = 0.12,
) -> float:
    """Pull starter quality toward league-average when firmness is low."""
    shrink = _clamp((1.0 - firmness) * max_shrink, 0.0, max_shrink)
    return _clamp(1.0 + (float(starter_quality) - 1.0) * (1.0 - shrink), 0.70, 1.35)


def rest_day_multipliers(rest_days: Optional[float]) -> Dict[str, float]:
    """Bounded offense / bullpen stress from calendar rest (MLB-native scale)."""
    days = 1.0 if rest_days is None else float(rest_days)
    # 0 = same-day / doubleheader; 1 = normal; >=3 = series off / travel rest.
    if days <= 0.0:
        offense_mul = 0.985
        bullpen_stress = 0.06
    elif days < 1.0:
        offense_mul = 0.992
        bullpen_stress = 0.03
    elif days >= 3.0:
        offense_mul = 1.012
        bullpen_stress = -0.04
    else:
        offense_mul = 1.0
        bullpen_stress = 0.0
    return {
        "offense_mul": _clamp(offense_mul, 0.97, 1.03),
        "bullpen_stress": _clamp(bullpen_stress, -0.06, 0.08),
        "rest_days": days,
    }


def bullpen_quality_from_state(
    *,
    fatigue: float,
    availability: float,
    high_lev_availability: float,
) -> float:
    """Map fatigue/availability into a bounded bullpen quality index (~1.0)."""
    fatigue_term = (0.50 - float(fatigue)) * 0.14
    avail_term = (float(availability) - 0.65) * 0.12
    high_lev_term = (float(high_lev_availability) - 0.62) * 0.08
    return _clamp(1.0 + fatigue_term + avail_term + high_lev_term, 0.82, 1.18)


def platoon_split_weight(*, firmness_opponent_starter: float, split_index: float) -> float:
    """How hard to lean on handedness split vs season offense (0–1 scale helper)."""
    split_signal = abs(float(split_index) - 1.0)
    return _clamp(0.35 + 0.45 * float(firmness_opponent_starter) + 0.40 * split_signal, 0.25, 0.95)


def platoon_split_for_hand(
    *,
    season_index: float,
    split_vs_l: Optional[float],
    split_vs_r: Optional[float],
    opponent_hand: str,
    fallback_split: Optional[float] = None,
) -> float:
    """Pick the matchup split for the opposing starter's hand (bounded)."""
    hand = (opponent_hand or "U").upper()
    if hand == "L" and split_vs_l is not None:
        return _clamp(float(split_vs_l), 0.78, 1.25)
    if hand == "R" and split_vs_r is not None:
        return _clamp(float(split_vs_r), 0.78, 1.25)
    if fallback_split is not None:
        return _clamp(float(fallback_split), 0.78, 1.25)
    return _clamp(float(season_index), 0.78, 1.25)


def weather_reliability_mul(
    *,
    home_abbr: Optional[str],
    weather_temp_f: Optional[float],
    weather_wind_mph: Optional[float] = None,
) -> float:
    """Damp environmental weather when park is a dome / roof likely closed.

    Outdoor parks with temp-only (no wind) get partial credit — wind is the
    dominant totals lever, so missing wind should not fully trust the env mul.
    """
    abbr = (home_abbr or "").upper()
    if abbr in _DOME_OR_RETRACTABLE:
        return 0.35
    if weather_temp_f is None:
        return 0.55
    if weather_wind_mph is None:
        return 0.72
    return 1.0


def apply_environment_weather_dampen(
    env_mul: float,
    *,
    park_factor: float,
    weather_reliability: float,
) -> float:
    """Blend full env multiplier toward park-only when weather is unreliable."""
    park = float(park_factor) if park_factor else 1.0
    w = _clamp(float(weather_reliability), 0.0, 1.0)
    blended = park * ((env_mul / max(park, 1e-6)) ** w) if park > 0 else env_mul
    return _clamp(blended, 0.70, 1.35)


def compute_sp_change_shock(
    *,
    prior_starter: Optional[str],
    new_starter: Optional[str],
    prior_quality: float = 1.0,
    new_quality: float = 1.0,
    max_abs_allowed_shock: float = 0.07,
) -> Dict[str, float]:
    """Bounded opponent-allowed shock when the probable/confirmed SP changes."""
    prior_key = " ".join((prior_starter or "").lower().split())
    new_key = " ".join((new_starter or "").lower().split())
    if not prior_key and not new_key:
        return {"allowed_mul": 1.0, "changed": 0.0, "quality_delta": 0.0}
    if prior_key == new_key:
        return {"allowed_mul": 1.0, "changed": 0.0, "quality_delta": 0.0}
    # starter_quality is a run-allowed factor: lower = better pitcher = fewer runs.
    quality_delta = float(new_quality) - float(prior_quality)
    # Named → missing: treat as uncertainty toward more runs allowed.
    if prior_key and not new_key:
        quality_delta = max(quality_delta, 0.06)
    if (not prior_key) and new_key:
        quality_delta = min(quality_delta, -0.03)
    shock = _clamp(quality_delta * 0.55, -max_abs_allowed_shock, max_abs_allowed_shock)
    return {
        "allowed_mul": 1.0 + shock,
        "changed": 1.0,
        "quality_delta": quality_delta,
    }


def sharpen_game_inputs(
    inputs: MlbGameInputs,
    *,
    starter_source_home: Optional[str] = None,
    starter_source_away: Optional[str] = None,
    home_abbr: Optional[str] = None,
    rest_days_home: Optional[float] = None,
    rest_days_away: Optional[float] = None,
) -> tuple[MlbGameInputs, Dict[str, Any]]:
    """Apply enterprise PA-sim sharpening; return (inputs, diagnostics)."""
    firm_home = starter_firmness(
        starter_name=inputs.starter_home,
        starter_source=starter_source_home,
        lineup_confirmed=inputs.lineup_confirmed,
    )
    firm_away = starter_firmness(
        starter_name=inputs.starter_away,
        starter_source=starter_source_away,
        lineup_confirmed=inputs.lineup_confirmed,
    )
    q_home = apply_missing_pitcher_shrink(inputs.starter_quality_home, firmness=firm_home)
    q_away = apply_missing_pitcher_shrink(inputs.starter_quality_away, firmness=firm_away)

    rest_home = rest_day_multipliers(
        rest_days_home if rest_days_home is not None else inputs.rest_days_home
    )
    rest_away = rest_day_multipliers(
        rest_days_away if rest_days_away is not None else inputs.rest_days_away
    )

    # Do not bake fatigue/availability into bullpen_quality here — the PA / pitch
    # simulators already apply those levers. Double-counting compressed late-game
    # edges and muddied moneyline sharpness. Keep only rest-day bullpen stress.
    bp_home = _clamp(
        float(inputs.bullpen_quality_home) * (1.0 - rest_home["bullpen_stress"] * 0.5),
        0.80,
        1.20,
    )
    bp_away = _clamp(
        float(inputs.bullpen_quality_away) * (1.0 - rest_away["bullpen_stress"] * 0.5),
        0.80,
        1.20,
    )

    # Platoon lean: amplify split index modestly when opponent SP is firm.
    split_w_home = platoon_split_weight(
        firmness_opponent_starter=firm_away,
        split_index=inputs.offense_split_home,
    )
    split_w_away = platoon_split_weight(
        firmness_opponent_starter=firm_home,
        split_index=inputs.offense_split_away,
    )
    split_home = _clamp(
        1.0 + (float(inputs.offense_split_home) - 1.0) * (0.70 + 0.30 * split_w_home),
        0.78,
        1.25,
    )
    split_away = _clamp(
        1.0 + (float(inputs.offense_split_away) - 1.0) * (0.70 + 0.30 * split_w_away),
        0.78,
        1.25,
    )

    offense_home = _clamp(float(inputs.offense_home) * rest_home["offense_mul"], 0.78, 1.25)
    offense_away = _clamp(float(inputs.offense_away) * rest_away["offense_mul"], 0.78, 1.25)

    # Low firmness → slight total inflation (uncertainty), not a directional ML hack.
    uncertainty_total_mul = _clamp(
        1.0 + (1.0 - 0.5 * (firm_home + firm_away)) * 0.025,
        1.0,
        1.03,
    )

    updated = replace(
        inputs,
        starter_quality_home=q_home,
        starter_quality_away=q_away,
        starter_firmness_home=firm_home,
        starter_firmness_away=firm_away,
        offense_home=offense_home,
        offense_away=offense_away,
        offense_split_home=split_home,
        offense_split_away=split_away,
        bullpen_quality_home=bp_home,
        bullpen_quality_away=bp_away,
        rest_days_home=float(rest_home["rest_days"]),
        rest_days_away=float(rest_away["rest_days"]),
        weather_reliability=weather_reliability_mul(
            home_abbr=home_abbr,
            weather_temp_f=inputs.weather_temp_f,
            weather_wind_mph=inputs.weather_wind_mph,
        ),
        uncertainty_total_mul=uncertainty_total_mul,
    )
    diag = {
        "pa_feature_sharpen": {
            "starter_firmness_home": firm_home,
            "starter_firmness_away": firm_away,
            "rest_days_home": rest_home["rest_days"],
            "rest_days_away": rest_away["rest_days"],
            "bullpen_quality_home": bp_home,
            "bullpen_quality_away": bp_away,
            "uncertainty_total_mul": uncertainty_total_mul,
            "weather_reliability": updated.weather_reliability,
            "platoon_weight_home": split_w_home,
            "platoon_weight_away": split_w_away,
        }
    }
    return updated, diag
