"""Modest CFB priors + early-season uncertainty (approximate, labeled).

College football 2026 reality drives these knobs:
- Extreme roster turnover (portal + NIL + draft + freshmen)
- Weak YoY team identity → historical team ratings alone are NOT enough
- QB situation is a first-class lever
- Position groups (OL / skill / front seven / secondary) are real projection drivers
- Early-season uncertainty is *wider* than NFL W1–W4
- Home-field advantage is *variable* (not a flat 3-pt blanket)
- Coaching continuity / staff change is a first-class early-season lever

v0.5 adds variable HFA buckets + coaching continuity/change with week decay.
v0.5.1 tightens project-game coherence for first UI exposure (measured knobs).
v0.6 overlays real ESPN 2026 roster / depth / portal-history signals.
v0.6.1 measured projection calibration — decompress top O indices, temper
inflated QB proxies, widen blue-blood vs G5 spreads without inventing 45-pt lines.
v0.7 adds QB + skill player role-share hooks allocated from team totals
(does not mutate team scores/spreads).
v0.8 adds opponent-adjusted efficiency backbone (2025 SP+ carry) as a
primary complementary driver beside roster/QB; unit weights reduced to
avoid double-counting the same variance.

v0.8.1 historical closing-line calibration (SportsDataverse ESPN lines +
prior-year cfb_ratings efficiency proxy). Measured knobs only — architecture
intact. See data/ops/cfb-historical-calibration-20260805.md.

v0.8.2 adds live performance tracking + CLV logging (projection → close →
result → summary). Projection knobs unchanged from v0.8.1; capability bump
for the tracking schema + endpoints.

v0.8.3 player↔team coherence: game-script-aware role shares + soft-caps so
named player aggregates stay reconciled with team pools. Team scores /
spreads / totals still unchanged by the player layer.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping

# Bump when priors / architecture change in a material way.
ENGINE_VERSION = "cfb-season-engine-v0.14-efficiency-backbone"
CALIBRATION_TAG = "cfb-season-engine-priors-v0.13-calibration-scale"
CALIBRATION_AS_OF = "2026-08-14"
BACKBONE_VERSION = "cfb-efficiency-backbone-v0.14-20260814"

# ---------------------------------------------------------------------------
# League environment (FBS-ish)
# Approximate recent FBS averages — hist-cal vs 2023–24 closes trims PPG.
# ---------------------------------------------------------------------------
# Before hist-cal: 27.5 → totals ~+3.2 vs close. Target ~52–53 season mean.
LEAGUE_TEAM_PPG = 25.9
# Variable HFA baseline. Bucket deltas live in home_field.py.
# Hist-cal: home dogs were overrated vs close → trim baseline ~0.3.
HFA_BASELINE_POINTS = 1.7
HOME_FIELD_POINTS = HFA_BASELINE_POINTS
NEUTRAL_SITE_HFA = 0.0
SCORE_NOISE_SD = 12.5
# Mid-season WP↔spread alignment: slightly wider SD after spread decompress.
WIN_PROB_MARGIN_SD = 15.2
LEAGUE_BASE_PLAYS = 70.0
LEAGUE_BASE_PASS_RATE = 0.55
EXPECTED_POINTS_CLAMP = (7.0, 55.0)
PACE_PLAYS_CLAMP = (55.0, 90.0)

# ---------------------------------------------------------------------------
# Player hooks (v0.7) — approximate role-share allocation priors
# ---------------------------------------------------------------------------
# Team yards pool from expected points (includes FG inefficiency / specials).
PLAYER_YARDS_PER_POINT = 14.2
PLAYER_POINTS_PER_OFFENSIVE_TD = 7.2
PLAYER_PASS_YARDS_PER_ATTEMPT = 7.4
PLAYER_BASE_INT_RATE = 0.022
PLAYER_QB_RUSH_SHARE_BASE = 0.07
# Named-player residual so shares sum ≤ team (depth beyond packaged hooks).
PLAYER_PASS_RESIDUAL = 0.04
PLAYER_RUSH_RESIDUAL = 0.10
PLAYER_REC_RESIDUAL = 0.16
PLAYER_RUSH_TD_RESIDUAL = 0.08
# RB1/RB2 usage ratio above this ⇒ "feature"; else "committee".
PLAYER_RB_FEATURE_RATIO = 1.35
# ---------------------------------------------------------------------------
# Player coherence / game script (v0.8.3) — allocation-only knobs
# ---------------------------------------------------------------------------
# Projected-margin thresholds (own − opp expected points).
PLAYER_SCRIPT_LARGE_MARGIN = 14.0
PLAYER_SCRIPT_SMALL_MARGIN = 4.0
# Pass-rate delta applied to the *allocation pool* only (not team scores).
PLAYER_SCRIPT_PASS_DELTA_LEAD = -0.055
PLAYER_SCRIPT_PASS_DELTA_TRAIL = 0.065
# Within-position share multipliers at full script intensity.
PLAYER_SCRIPT_RB1_LEAD_MULT = 1.16
PLAYER_SCRIPT_RB_DEPTH_LEAD_MULT = 1.10  # RB2+ garbage-time / committee
PLAYER_SCRIPT_WR1_TRAIL_MULT = 1.14
PLAYER_SCRIPT_WR_DEPTH_LEAD_MULT = 1.12  # blowout → more WR depth targets
PLAYER_SCRIPT_RB_REC_TRAIL_MULT = 1.10  # checkdowns when trailing
# Soft-caps so one star cannot imply a larger team pool than the model.
PLAYER_STAR_PASS_SHARE_CAP = 0.92  # of named pass pool (post residual)
PLAYER_STAR_RUSH_SHARE_CAP = 0.48  # of team rush yards
PLAYER_STAR_REC_SHARE_CAP = 0.30  # of team pass yards (receiving)
# Hist-cal: spreads compressed vs close (home-fav bias +7 / dog −9) → decompress.
MATCHUP_RESPONSE = 1.40
# Soft-cap extreme O/D ratios so placeholder mismatches don't invent 45-pt spreads.
# Excess beyond the band is retained at MATCHUP_RATIO_EXCESS_RETAIN (keeps ordering).
MATCHUP_RATIO_CLAMP = (0.52, 1.45)
MATCHUP_RATIO_EXCESS_RETAIN = 0.42
# v0.13/v0.14: shrink O/D index toward 1.0 when efficiency is a labeled
# thin-sample / leftover league-average fill. Official FBS with warehouse
# or SP+ history does not hit this path.
LEAGUE_REG_PLACEHOLDER = 0.28

# Path evolution (mild; not backtested). Early weeks add extra noise.
STRENGTH_UPDATE_RATE = 0.028
STRENGTH_MEAN_REVERT = 0.010
STRENGTH_NOISE = 0.014
# Wider team-index band — v0.6 piled ~33 teams at the old 1.55 offense ceiling.
STRENGTH_CLAMP = (0.52, 1.68)
# QB situation alone must not invent power-conference offense from MAC talent proxies.
QB_SITUATION_INDEX_CLAMP = (0.62, 1.38)
EARLY_STRENGTH_NOISE_MULT: Dict[int, float] = {
    1: 1.55,
    2: 1.40,
    3: 1.25,
    4: 1.12,
}

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

# Class → offense multiplier. Still sharp (true_freshman << incumbent) but
# tempered so ESPN talent proxies + incumbent don't ceiling every P4 offense.
QB_CLASS_OFFENSE_MULT: Dict[str, float] = {
    "incumbent": 1.06,
    "portal": 0.95,
    "open_competition": 0.87,
    "true_freshman": 0.79,
    "unknown": 0.92,
}

QB_CAST_OL_WEIGHT = 0.55
QB_CAST_WEAPONS_WEIGHT = 0.45
QB_CAST_INDEX_SCALE = 0.11  # ±11% index from cast extremes

# ---------------------------------------------------------------------------
# Layer 3 — position group unit components
# unit_grade = talent*w_t + experience*w_e + portal_impact*w_p
# ---------------------------------------------------------------------------
UNIT_TALENT_WEIGHT = 0.50
UNIT_EXPERIENCE_WEIGHT = 0.30
UNIT_PORTAL_WEIGHT = 0.20

# ---------------------------------------------------------------------------
# Layer 4 — composition: efficiency + roster + QB + position groups
# Opponent-adjusted efficiency (2025 SP+ carry) is a primary complementary
# driver. Unit grades stay material but are down-weighted vs v0.7 so talent
# composites and SP+ do not both fully drive the same variance.
# Roster/QB remain first-class for 2026 portal/NIL identity.
# ---------------------------------------------------------------------------
# Hist-cal: raise efficiency share so prior-year adj strength drives spreads
# when roster/QB are noisy; roster/QB remain first-class (still ≥0.20 each).
WEIGHT_OFF_EFF = 0.34
WEIGHT_ROSTER_STRENGTH = 0.22
WEIGHT_QB_SITUATION = 0.24
WEIGHT_SKILL_GROUP = 0.10
WEIGHT_OL_GROUP = 0.10

# Legacy aliases retained for status docs / older call sites.
WEIGHT_RETURNING_PROD = ROSTER_STRENGTH_RETURNING
WEIGHT_PORTAL_NET = ROSTER_STRENGTH_PORTAL_NET
WEIGHT_RECRUITING = ROSTER_STRENGTH_RECRUITING
WEIGHT_EXPERIENCE = ROSTER_STRENGTH_EXPERIENCE
WEIGHT_QB = WEIGHT_QB_SITUATION

WEIGHT_DEF_EFF = 0.36
WEIGHT_DEF_ROSTER_STRENGTH = 0.12
WEIGHT_DEF_FRONT_SEVEN = 0.24
WEIGHT_DEF_SECONDARY = 0.20
WEIGHT_DEF_EXPERIENCE = 0.08
WEIGHT_DEF_RECRUITING = 0.0  # folded into roster_strength

# Direct index blends after compose (hard levers, like QB).
# Unit blends softened vs v0.7 — efficiency already embeds unit quality.
QB_INDEX_BLEND = 0.26
OL_INDEX_BLEND = 0.09
SKILL_INDEX_BLEND = 0.07
# Defense unit blend toward front_seven/secondary indices.
DEF_UNIT_BLEND = 0.14
# Mild post-compose pull toward efficiency indices (transparent, capped).
EFF_OFF_INDEX_BLEND = 0.12
EFF_DEF_INDEX_BLEND = 0.12

# Game-level unit matchup multipliers (applied in expected_team_points).
# Softened vs v0.7 so unit matchup + efficiency index don't double-count.
UNIT_OFFENSE_BOOST_SCALE = 0.07  # ±7% at unit grade extremes (0/100)
UNIT_DEFENSE_DAMPEN_SCALE = 0.09  # ±9% opponent scoring dampen
UNIT_FRONT_SEVEN_SHARE = 0.55  # of defense dampen from front seven
UNIT_SECONDARY_SHARE = 0.45
UNIT_OL_SHARE = 0.55  # of offense boost from OL
UNIT_SKILL_SHARE = 0.45
SPECIAL_TEAMS_TOTAL_SCALE = 0.015  # thin ST nudge on total only

# Score (0–100) → strength index slope. Steeper than /80 reduces mid-pack compression.
SCORE_TO_INDEX_DIVISOR = 68.0
SCORE_TO_INDEX_CLAMP = (0.58, 1.58)

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
# Hist-cal: early W1–W4 under-rated favorites vs close (bias +2.3) — soften less.
# Uncertainty stays in margin_sd / score noise, not by collapsing separation.
EARLY_SEASON_SEPARATION_SOFTEN: Dict[int, float] = {
    1: 0.90,
    2: 0.93,
    3: 0.96,
    4: 0.98,
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


def strength_noise_sd_for_week(week: int) -> float:
    """In-path strength evolution noise SD (wider W1–W4, then base)."""
    return STRENGTH_NOISE * early_season_factor(week, EARLY_STRENGTH_NOISE_MULT)


def early_season_narrowing_schedule() -> Dict[str, Any]:
    """Week-indexed uncertainty narrowing for status / ops honesty."""
    weeks = {}
    for w in range(1, 9):
        u = early_season_uncertainty(w)
        weeks[str(w)] = {
            "active": u["active"],
            "margin_sd_mult": u["margin_sd_mult"],
            "score_noise_mult": u["score_noise_mult"],
            "separation_soften": u["separation_soften"],
            "roster_identity_uncertainty": u["roster_identity_uncertainty"],
            "strength_noise_mult": round(
                early_season_factor(w, EARLY_STRENGTH_NOISE_MULT), 4
            ),
        }
    return {
        "last_early_week": EARLY_SEASON_LAST_WEEK,
        "weeks": weeks,
        "note": (
            "W1–W4: wide priors (inflate margin/score SD, soften separation, "
            "extra strength-path noise). Week 5+: base priors — uncertainty "
            "narrows on the schedule, not by pretending identity is known."
        ),
        "fidelity": "approximate",
    }


def documentation() -> Dict[str, Any]:
    return {
        "engine_version": ENGINE_VERSION,
        "calibration_tag": CALIBRATION_TAG,
        "calibration_as_of": CALIBRATION_AS_OF,
        "fidelity": "approximate",
        "assumptions": [
            "Historical team ratings alone are insufficient for CFB 2026.",
            "roster_strength + qb_situation_index remain material primary drivers.",
            "Position groups (OL/skill/front_seven/secondary) are real projection "
            "drivers with inspectable talent/experience/portal_impact components.",
            "Defense unit grades dampen opponent scoring at project-game time.",
            "Returning production is snap/start weighted, not starter-count only.",
            "QB class multipliers are intentional and sharp (true_freshman << incumbent).",
            "v0.6: ESPN 2026 roster snapshot feeds identities/QB class/portal-in; "
            "returning snap% and portal-out remain approximate proxies. "
            "Do not treat unit grades as calibrated SP+.",
            "v0.6.1: measured projection calibration — wider STRENGTH_CLAMP, "
            "separate QB_SITUATION_INDEX_CLAMP, steeper score→index, stronger "
            "matchup response; still approximate (not market-grade KEI).",
            "v0.7: QB + skill player hooks allocate team pass/rush/TD pools "
            "via depth-order role shares; team scores/spreads unchanged.",
            "v0.8: opponent-adjusted efficiency (final-2025 SP+ carry) is a "
            "primary complementary O/D driver; unit weights/blends reduced to "
            "avoid double-counting. success/explosiveness are SP+ proxies "
            "(no full PBP). Preseason 2026 = prior-year eff + roster/QB update.",
            "v0.8.1: historical closing-line calibration (SportsDataverse ESPN "
            "spreads/totals + scores; prior-year cfb_ratings efficiency proxy; "
            "league-avg roster/QB reconstruction). Measured: lower PPG, trim HFA, "
            "raise efficiency/matchup response, less early separation soften. "
            "Still approximate — not market-grade KEI / CLV.",
            "v0.8.3: player↔team coherence — projected margin/WP drives script "
            "detail (lead/trail/neutral); allocation pass/rush split + RB/WR "
            "shares respond; star soft-caps + residual reconcile keep named "
            "aggregates ≤ team pools. Team scores/spreads unchanged.",
            "Early-season (W1–W4) uncertainty is intentionally wider than NFL.",
            "HFA is variable by bucket (baseline ~1.7 pts); not a flat 3-pt blanket.",
            "Coaching continuity: new HC/OC/DC penalties decay after W1–W4.",
            "v0.13: FBS-FBS margin = TAU*tanh(SCALE*raw/TAU) after the strength "
            "path (SCALE=0.80, TAU=26). Placeholder-SP+ teams regress 28% to "
            "league index. Totals stay on the separate pace path. σ not shrunk.",
            "v0.14: warehouse opponent-adj EPA overlay replaces silent "
            "league_average_fill for official FBS with ≥8 prior-season games. "
            "Remaining missing codes are thin_sample_labeled (wider σ). "
            "tanh constants unchanged. used_in_spread stays false.",
            "Season sim uses official ESPN 2026 slate when packaged; densified "
            "seed is never labeled official. Win tables stay research-only.",
            "FBS focus; FCS opponents treated as external when scheduled.",
        ],
        "league_env": {
            "league_team_ppg": LEAGUE_TEAM_PPG,
            "hfa_baseline_points": HFA_BASELINE_POINTS,
            "home_field_points": HOME_FIELD_POINTS,
            "score_noise_sd": SCORE_NOISE_SD,
            "win_prob_margin_sd": WIN_PROB_MARGIN_SD,
            "matchup_response": MATCHUP_RESPONSE,
            "matchup_ratio_clamp": list(MATCHUP_RATIO_CLAMP),
            "matchup_ratio_excess_retain": MATCHUP_RATIO_EXCESS_RETAIN,
            "strength_clamp": list(STRENGTH_CLAMP),
            "qb_situation_index_clamp": list(QB_SITUATION_INDEX_CLAMP),
            "score_to_index_divisor": SCORE_TO_INDEX_DIVISOR,
            "league_reg_placeholder": LEAGUE_REG_PLACEHOLDER,
            "player_yards_per_point": PLAYER_YARDS_PER_POINT,
            "player_pass_residual": PLAYER_PASS_RESIDUAL,
            "player_rush_residual": PLAYER_RUSH_RESIDUAL,
            "player_rec_residual": PLAYER_REC_RESIDUAL,
        },
        "early_season_narrowing": early_season_narrowing_schedule(),
        "roster_strength_weights": {
            "returning_production": ROSTER_STRENGTH_RETURNING,
            "portal_net": ROSTER_STRENGTH_PORTAL_NET,
            "recruiting_class_score": ROSTER_STRENGTH_RECRUITING,
            "experience_index": ROSTER_STRENGTH_EXPERIENCE,
            "snap_weight": ROSTER_SNAP_WEIGHT,
            "start_weight": ROSTER_START_WEIGHT,
        },
        "unit_grade_weights": {
            "talent": UNIT_TALENT_WEIGHT,
            "experience": UNIT_EXPERIENCE_WEIGHT,
            "portal_impact": UNIT_PORTAL_WEIGHT,
        },
        "qb_class_offense_mult": dict(QB_CLASS_OFFENSE_MULT),
        "composition_weights": {
            "offense": {
                "efficiency": WEIGHT_OFF_EFF,
                "roster_strength": WEIGHT_ROSTER_STRENGTH,
                "qb_situation": WEIGHT_QB_SITUATION,
                "skill_group": WEIGHT_SKILL_GROUP,
                "ol_group": WEIGHT_OL_GROUP,
                "qb_index_blend": QB_INDEX_BLEND,
                "ol_index_blend": OL_INDEX_BLEND,
                "skill_index_blend": SKILL_INDEX_BLEND,
                "eff_index_blend": EFF_OFF_INDEX_BLEND,
            },
            "defense": {
                "efficiency": WEIGHT_DEF_EFF,
                "roster_strength": WEIGHT_DEF_ROSTER_STRENGTH,
                "front_seven": WEIGHT_DEF_FRONT_SEVEN,
                "secondary": WEIGHT_DEF_SECONDARY,
                "experience": WEIGHT_DEF_EXPERIENCE,
                "def_unit_blend": DEF_UNIT_BLEND,
                "eff_index_blend": EFF_DEF_INDEX_BLEND,
            },
            "anti_double_count": (
                "Efficiency + reduced unit weights/blends + softer game-level "
                "unit matchup scales — units remain ablation-testable but do "
                "not fully re-drive SP+-embedded variance."
            ),
            "game_matchup": {
                "unit_offense_boost_scale": UNIT_OFFENSE_BOOST_SCALE,
                "unit_defense_dampen_scale": UNIT_DEFENSE_DAMPEN_SCALE,
                "front_seven_share": UNIT_FRONT_SEVEN_SHARE,
                "secondary_share": UNIT_SECONDARY_SHARE,
                "ol_share": UNIT_OL_SHARE,
                "skill_share": UNIT_SKILL_SHARE,
            },
        },
    }
