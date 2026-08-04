"""Modest CFB priors + early-season uncertainty (approximate, labeled).

College football 2026 reality drives these knobs:
- Extreme roster turnover (portal + NIL + draft + freshmen)
- Weak YoY team identity → historical team ratings alone are NOT enough
- QB situation is a first-class lever
- Early-season uncertainty is *wider* than NFL W1–W4

v0.2 deepens roster_strength + qb_situation_index as the primary drivers
of team projection. Calibration remains intentionally thin.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping

# Bump when priors / architecture change in a material way.
ENGINE_VERSION = "cfb-season-engine-v0.2-roster-qb"
CALIBRATION_TAG = "cfb-season-engine-priors-v0.2-roster-qb"

# ---------------------------------------------------------------------------
# League environment (FBS-ish)
# Approximate recent FBS averages — not a calibrated scoring model.
# ---------------------------------------------------------------------------
LEAGUE_TEAM_PPG = 27.5
HOME_FIELD_POINTS = 2.5  # CFB HFA typically larger / more variable than NFL
NEUTRAL_SITE_HFA = 0.0
SCORE_NOISE_SD = 12.5
WIN_PROB_MARGIN_SD = 16.5
LEAGUE_BASE_PLAYS = 70.0
LEAGUE_BASE_PASS_RATE = 0.55
EXPECTED_POINTS_CLAMP = (7.0, 55.0)
PACE_PLAYS_CLAMP = (55.0, 90.0)
MATCHUP_RESPONSE = 1.05

# Path evolution (placeholder — not backtested).
STRENGTH_UPDATE_RATE = 0.035
STRENGTH_MEAN_REVERT = 0.012
STRENGTH_NOISE = 0.018
STRENGTH_CLAMP = (0.55, 1.55)

# ---------------------------------------------------------------------------
# Layer 1 — roster strength components (transparent weights)
# ---------------------------------------------------------------------------
ROSTER_SNAP_WEIGHT = 0.65
ROSTER_START_WEIGHT = 0.35
ROSTER_PORTAL_OUT_WEIGHT = 0.70
ROSTER_PORTAL_NET_OFFSET = 35.0

ROSTER_STRENGTH_RETURNING = 0.32
ROSTER_STRENGTH_PORTAL_NET = 0.26
ROSTER_STRENGTH_RECRUITING = 0.26
ROSTER_STRENGTH_EXPERIENCE = 0.16

# ---------------------------------------------------------------------------
# Layer 2 — QB situation (first-class lever)
# ---------------------------------------------------------------------------
QB_CLASS_UNCERTAINTY: Dict[str, float] = {
    "incumbent": 0.18,
    "portal": 0.42,
    "open_competition": 0.55,
    "true_freshman": 0.62,
    "unknown": 0.50,
}

# Class → offense multiplier. Intentionally sharp so true_freshman vs
# incumbent is visible in project-game / season-sim, not a 1% nudge.
QB_CLASS_OFFENSE_MULT: Dict[str, float] = {
    "incumbent": 1.10,
    "portal": 0.96,
    "open_competition": 0.88,
    "true_freshman": 0.80,
    "unknown": 0.93,
}

QB_CAST_OL_WEIGHT = 0.55
QB_CAST_WEAPONS_WEIGHT = 0.45
QB_CAST_INDEX_SCALE = 0.14  # ±14% index from cast extremes

# ---------------------------------------------------------------------------
# Layer 4 — composition: roster_strength + qb_situation dominate
# Historical team strength is deliberately *not* a dominant term.
# ---------------------------------------------------------------------------
WEIGHT_ROSTER_STRENGTH = 0.40
WEIGHT_QB_SITUATION = 0.36
WEIGHT_SKILL_GROUP = 0.14
WEIGHT_OL_GROUP = 0.10

# Legacy aliases retained for status docs / older call sites.
WEIGHT_RETURNING_PROD = ROSTER_STRENGTH_RETURNING
WEIGHT_PORTAL_NET = ROSTER_STRENGTH_PORTAL_NET
WEIGHT_RECRUITING = ROSTER_STRENGTH_RECRUITING
WEIGHT_EXPERIENCE = ROSTER_STRENGTH_EXPERIENCE
WEIGHT_QB = WEIGHT_QB_SITUATION

WEIGHT_DEF_ROSTER_STRENGTH = 0.28
WEIGHT_DEF_FRONT_SEVEN = 0.32
WEIGHT_DEF_SECONDARY = 0.26
WEIGHT_DEF_EXPERIENCE = 0.14
WEIGHT_DEF_RECRUITING = 0.0  # folded into roster_strength

# Direct index blend: keep qb_situation_index as a hard lever after compose.
QB_INDEX_BLEND = 0.42  # offense_index = (1-b)*base + b*(base*qb_index/1.0) effectively
# Applied as: offense_index *= (1 - QB_INDEX_BLEND) + QB_INDEX_BLEND * qb_situation_index

# ---------------------------------------------------------------------------
# Early-season uncertainty (weeks 1–4) — wider than NFL analog
# ---------------------------------------------------------------------------
EARLY_SEASON_LAST_WEEK = 4
EARLY_SEASON_SCORE_NOISE_MULT: Dict[int, float] = {
    1: 1.32,
    2: 1.24,
    3: 1.16,
    4: 1.08,
}
EARLY_SEASON_MARGIN_SD_MULT: Dict[int, float] = {
    1: 1.38,
    2: 1.26,
    3: 1.16,
    4: 1.08,
}
EARLY_SEASON_SEPARATION_SOFTEN: Dict[int, float] = {
    1: 0.68,
    2: 0.76,
    3: 0.85,
    4: 0.93,
}
# Extra CFB-specific: roster/QB identity still forming.
EARLY_SEASON_ROSTER_IDENTITY_UNCERTAINTY: Dict[int, float] = {
    1: 0.55,
    2: 0.45,
    3: 0.35,
    4: 0.25,
}


def early_season_factor(
    week: int,
    table: Mapping[int, float],
    *,
    default: float = 1.0,
) -> float:
    w = int(week or 0)
    if w < 1 or w > EARLY_SEASON_LAST_WEEK:
        return float(default)
    return float(table.get(w, default))


def early_season_uncertainty(week: int) -> Dict[str, Any]:
    """Inspectable early-season uncertainty posture (CFB-wider than NFL)."""
    w = int(week or 0)
    active = 1 <= w <= EARLY_SEASON_LAST_WEEK
    score_mult = early_season_factor(w, EARLY_SEASON_SCORE_NOISE_MULT)
    margin_mult = early_season_factor(w, EARLY_SEASON_MARGIN_SD_MULT)
    soften = early_season_factor(w, EARLY_SEASON_SEPARATION_SOFTEN)
    roster_u = early_season_factor(w, EARLY_SEASON_ROSTER_IDENTITY_UNCERTAINTY, default=0.12)
    return {
        "week": w,
        "active": active,
        "last_week": EARLY_SEASON_LAST_WEEK,
        "score_noise_mult": round(score_mult, 4),
        "score_noise_sd": round(SCORE_NOISE_SD * score_mult, 4),
        "margin_sd_mult": round(margin_mult, 4),
        "win_prob_margin_sd": round(WIN_PROB_MARGIN_SD * margin_mult, 4),
        "separation_soften": round(soften, 4),
        "matchup_response_effective": round(MATCHUP_RESPONSE * soften, 4),
        "roster_identity_uncertainty": round(roster_u, 4),
        "note": (
            "W1–W4 CFB: inflate outcome SD more than NFL, soften separation, "
            "and flag high roster/QB identity uncertainty (portal + NIL churn)."
            if active
            else "Mid/late season: base priors (no early-season inflate)."
        ),
        "fidelity": "approximate",
    }


def score_noise_sd_for_week(week: int) -> float:
    return SCORE_NOISE_SD * early_season_factor(week, EARLY_SEASON_SCORE_NOISE_MULT)


def win_prob_margin_sd_for_week(week: int) -> float:
    return WIN_PROB_MARGIN_SD * early_season_factor(week, EARLY_SEASON_MARGIN_SD_MULT)


def matchup_response_for_week(week: int) -> float:
    return MATCHUP_RESPONSE * early_season_factor(week, EARLY_SEASON_SEPARATION_SOFTEN)


def documentation() -> Dict[str, Any]:
    return {
        "engine_version": ENGINE_VERSION,
        "calibration_tag": CALIBRATION_TAG,
        "fidelity": "approximate",
        "assumptions": [
            "Historical team ratings alone are insufficient for CFB 2026.",
            "roster_strength + qb_situation_index are the primary drivers of "
            "offense/defense indices (v0.2).",
            "Returning production is snap/start weighted, not starter-count only.",
            "QB class multipliers are intentional and sharp (true_freshman << incumbent).",
            "Packaged priors are approximate stand-ins until portal/recruiting "
            "feeds are wired; do not treat unit grades as calibrated SP+.",
            "Early-season (W1–W4) uncertainty is intentionally wider than NFL.",
            "FBS focus; FCS opponents treated as external when scheduled.",
        ],
        "league_env": {
            "league_team_ppg": LEAGUE_TEAM_PPG,
            "home_field_points": HOME_FIELD_POINTS,
            "score_noise_sd": SCORE_NOISE_SD,
            "win_prob_margin_sd": WIN_PROB_MARGIN_SD,
        },
        "roster_strength_weights": {
            "returning_production": ROSTER_STRENGTH_RETURNING,
            "portal_net": ROSTER_STRENGTH_PORTAL_NET,
            "recruiting_class_score": ROSTER_STRENGTH_RECRUITING,
            "experience_index": ROSTER_STRENGTH_EXPERIENCE,
            "snap_weight": ROSTER_SNAP_WEIGHT,
            "start_weight": ROSTER_START_WEIGHT,
        },
        "qb_class_offense_mult": dict(QB_CLASS_OFFENSE_MULT),
        "composition_weights": {
            "offense": {
                "roster_strength": WEIGHT_ROSTER_STRENGTH,
                "qb_situation": WEIGHT_QB_SITUATION,
                "skill_group": WEIGHT_SKILL_GROUP,
                "ol_group": WEIGHT_OL_GROUP,
                "qb_index_blend": QB_INDEX_BLEND,
            },
            "defense": {
                "roster_strength": WEIGHT_DEF_ROSTER_STRENGTH,
                "front_seven": WEIGHT_DEF_FRONT_SEVEN,
                "secondary": WEIGHT_DEF_SECONDARY,
                "experience": WEIGHT_DEF_EXPERIENCE,
            },
        },
    }
