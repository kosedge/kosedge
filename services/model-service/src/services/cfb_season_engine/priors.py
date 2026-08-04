"""Modest CFB priors + early-season uncertainty (approximate, labeled).

College football 2026 reality drives these knobs:
- Extreme roster turnover (portal + NIL + draft + freshmen)
- Weak YoY team identity → historical team ratings alone are NOT enough
- QB situation is a first-class lever
- Early-season uncertainty is *wider* than NFL W1–W4

Calibration is intentionally thin — foundation structure first.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping

# Bump when priors / architecture change in a material way.
ENGINE_VERSION = "cfb-season-engine-v0.1-foundation"
CALIBRATION_TAG = "cfb-season-engine-priors-v0"

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

# Composition weights: roster + QB + groups → offense/defense indices.
# Historical team strength is deliberately *not* a dominant term.
WEIGHT_RETURNING_PROD = 0.22
WEIGHT_PORTAL_NET = 0.18
WEIGHT_RECRUITING = 0.12
WEIGHT_EXPERIENCE = 0.10
WEIGHT_QB = 0.28
WEIGHT_SKILL_GROUP = 0.10

WEIGHT_DEF_FRONT_SEVEN = 0.38
WEIGHT_DEF_SECONDARY = 0.32
WEIGHT_DEF_EXPERIENCE = 0.15
WEIGHT_DEF_RECRUITING = 0.15

# QB class uncertainty priors (0–1).
QB_CLASS_UNCERTAINTY: Dict[str, float] = {
    "incumbent": 0.18,
    "portal": 0.42,
    "open_competition": 0.55,
    "true_freshman": 0.62,
    "unknown": 0.50,
}

# QB talent → offense index contribution scale.
QB_TALENT_TO_OFFENSE = 0.0045  # per talent point above/below 50

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
            "Roster construction + QB situation dominate early-season identity.",
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
        "composition_weights": {
            "offense": {
                "returning_production": WEIGHT_RETURNING_PROD,
                "portal_net": WEIGHT_PORTAL_NET,
                "recruiting": WEIGHT_RECRUITING,
                "experience": WEIGHT_EXPERIENCE,
                "qb": WEIGHT_QB,
                "skill_group": WEIGHT_SKILL_GROUP,
            },
            "defense": {
                "front_seven": WEIGHT_DEF_FRONT_SEVEN,
                "secondary": WEIGHT_DEF_SECONDARY,
                "experience": WEIGHT_DEF_EXPERIENCE,
                "recruiting": WEIGHT_DEF_RECRUITING,
            },
        },
    }
