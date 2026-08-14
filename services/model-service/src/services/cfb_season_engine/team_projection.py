"""Layer 4 — Team projection + game-level matchup.

Composes opponent-adjusted efficiency + roster + QB + position groups into
offense/defense indices (the single Power SoT — same table as Team DNA and
frozen season projections), then projects a single game:

    strength indices → expected points (unit matchup) → margin
      → spread / total / win probability

v0.8: efficiency (2025 SP+ carry) is a primary complementary driver alongside
``roster_strength`` / ``qb_situation_index``. Unit grades remain material but
are down-weighted to avoid double-counting SP+-embedded unit quality.
"""

from __future__ import annotations

import math
import random
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Tuple

from src.services.cfb_season_engine import priors as P
from src.services.cfb_season_engine.margin_calibration import (
    apply_calibrated_scores,
    calibrate_margin,
    fcs_matchup_from_states,
)
from src.services.cfb_season_engine.game_total_sim import (
    GAME_SIM_N_DEFAULT,
    USED_IN_SPREAD,
    simulate_game_distributions,
    total_path_mean,
)
from src.services.cfb_season_engine.coaching_continuity import (
    coaching_to_dict,
    coaching_week_adjustment,
    team_game_point_adjustment,
)
from src.services.cfb_season_engine.efficiency import (
    efficiency_index,
    efficiency_to_dict,
)
from src.services.cfb_season_engine.home_field import profile_to_dict, resolve_hfa_points
from src.services.cfb_season_engine.position_groups import groups_to_dict
from src.services.cfb_season_engine.qb_situation import qb_to_dict
from src.services.cfb_season_engine.roster_construction import roster_to_dict
from src.services.cfb_season_engine.types import (
    CoachingContinuity,
    EfficiencyProfile,
    EngineUniverse,
    GameProjection,
    HomeFieldProfile,
    PositionGroupGrades,
    QbSituation,
    RosterConstruction,
    ScheduledGame,
    TeamProjectionState,
)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def _soft_clamp_ratio(raw: float, low: float, high: float, retain: float) -> float:
    """Clamp extreme O/D ratios while retaining a fraction of the excess.

    Hard clamps collapse peer favorites against weak placeholders to the same
    ratio; retaining some excess keeps ordering without inventing 45-pt spreads.
    """
    r = float(raw)
    lo, hi = float(low), float(high)
    keep = _clamp(float(retain), 0.0, 1.0)
    if r > hi:
        return hi + keep * (r - hi)
    if r < lo:
        return lo + keep * (r - lo)
    return r


def _score_to_index(score_0_100: float) -> float:
    """Map 0–100 unit score to strength index (1.0 at 50).

    Slope / clamp come from priors (v0.6.1 steepens vs /80 to reduce compression).
    """
    lo, hi = P.SCORE_TO_INDEX_CLAMP
    return _clamp(
        1.0 + (float(score_0_100) - 50.0) / P.SCORE_TO_INDEX_DIVISOR,
        lo,
        hi,
    )


def _unit_index(grade_0_100: float) -> float:
    return _score_to_index(grade_0_100)


def compose_team_projection(
    team: str,
    roster: RosterConstruction,
    qb: QbSituation,
    groups: PositionGroupGrades,
    *,
    efficiency: Optional[EfficiencyProfile] = None,
    home_field: Optional[HomeFieldProfile] = None,
    coaching: Optional[CoachingContinuity] = None,
) -> TeamProjectionState:
    """Compose efficiency + Layers 1–3 (+ HFA/coaching) into team O/D indices.

    Offense: off_eff + roster_strength + qb_situation + OL + skill.
    Defense: def_eff + roster_strength + front_seven + secondary + experience.
    Post-compose: mild QB / unit / efficiency index blends; coaching mults.
    """
    roster_s = float(roster.roster_strength)
    qb_score = float(qb.qb_situation_score)
    qb_index = float(qb.qb_situation_index)
    off_eff = float(efficiency.off_eff) if efficiency is not None else 50.0
    def_eff = float(efficiency.def_eff) if efficiency is not None else 50.0

    offense_score = (
        P.WEIGHT_OFF_EFF * off_eff
        + P.WEIGHT_ROSTER_STRENGTH * roster_s
        + P.WEIGHT_QB_SITUATION * qb_score
        + P.WEIGHT_SKILL_GROUP * groups.skill
        + P.WEIGHT_OL_GROUP * groups.ol
    )

    defense_score = (
        P.WEIGHT_DEF_EFF * def_eff
        + P.WEIGHT_DEF_ROSTER_STRENGTH * roster_s
        + P.WEIGHT_DEF_FRONT_SEVEN * groups.front_seven
        + P.WEIGHT_DEF_SECONDARY * groups.secondary
        + P.WEIGHT_DEF_EXPERIENCE * roster.experience_index
    )

    offense_index = _score_to_index(offense_score)
    # Hard QB lever.
    blend_qb = P.QB_INDEX_BLEND
    offense_index = (1.0 - blend_qb) * offense_index + blend_qb * (
        offense_index * qb_index
    )
    # Softened OL / skill levers (efficiency already embeds unit quality).
    ol_idx = _unit_index(groups.ol)
    skill_idx = _unit_index(groups.skill)
    offense_index = (1.0 - P.OL_INDEX_BLEND) * offense_index + P.OL_INDEX_BLEND * (
        offense_index * ol_idx
    )
    offense_index = (1.0 - P.SKILL_INDEX_BLEND) * offense_index + P.SKILL_INDEX_BLEND * (
        offense_index * skill_idx
    )
    # Mild pull toward efficiency index (transparent complementary lever).
    off_eff_idx = efficiency_index(off_eff)
    offense_index = (1.0 - P.EFF_OFF_INDEX_BLEND) * offense_index + P.EFF_OFF_INDEX_BLEND * (
        offense_index * off_eff_idx
    )
    # Coaching continuity — mild permanent index drag for new staff.
    if coaching is not None:
        offense_index *= float(coaching.offense_index_mult)
    offense_index = _clamp(offense_index, *P.STRENGTH_CLAMP)

    defense_index = _score_to_index(defense_score)
    f7_idx = _unit_index(groups.front_seven)
    sec_idx = _unit_index(groups.secondary)
    def_unit = P.UNIT_FRONT_SEVEN_SHARE * f7_idx + P.UNIT_SECONDARY_SHARE * sec_idx
    defense_index = (1.0 - P.DEF_UNIT_BLEND) * defense_index + P.DEF_UNIT_BLEND * (
        defense_index * def_unit
    )
    def_eff_idx = efficiency_index(def_eff)
    defense_index = (1.0 - P.EFF_DEF_INDEX_BLEND) * defense_index + P.EFF_DEF_INDEX_BLEND * (
        defense_index * def_eff_idx
    )
    if coaching is not None:
        defense_index *= float(coaching.defense_index_mult)
    defense_index = _clamp(defense_index, *P.STRENGTH_CLAMP)
    league_reg = 0.0
    eff_src = str(efficiency.source or "") if efficiency is not None else ""
    if efficiency is not None and eff_src in (
        "league_average_fill",
        "thin_sample_labeled",
    ):
        league_reg = float(P.LEAGUE_REG_PLACEHOLDER)
        offense_index = 1.0 + (1.0 - league_reg) * (offense_index - 1.0)
        defense_index = 1.0 + (1.0 - league_reg) * (defense_index - 1.0)
        offense_index = _clamp(offense_index, *P.STRENGTH_CLAMP)
        defense_index = _clamp(defense_index, *P.STRENGTH_CLAMP)

    pace = _clamp(1.0 + (groups.skill - groups.front_seven) / 200.0, 0.85, 1.20)
    if efficiency is not None:
        # Explosiveness proxy nudges pace slightly (labeled approximate).
        pace = _clamp(pace + (efficiency.explosiveness - 50.0) / 400.0, 0.85, 1.20)
    pass_bias = _clamp(
        (qb.qb_talent - 50.0) / 200.0
        + (groups.skill - 50.0) / 250.0
        + (qb_index - 1.0) * 0.08
        - (groups.secondary - 50.0) / 400.0,
        -0.14,
        0.16,
    )

    # Early uncertainty: QB situation dominates; roster continuity tempers;
    # prior-year efficiency carry + thin units + coaching change boost.
    unit_noise = 0.0
    if groups.fidelity == "placeholder":
        unit_noise = 0.08
    elif groups.fidelity == "approximate":
        unit_noise = 0.03
    eff_noise = 0.0
    if efficiency is None or efficiency.fidelity == "placeholder":
        eff_noise = 0.06
    elif efficiency.prior_year < efficiency.carry_to_season:
        # Preseason carry — prior-year adj efficiency is informative but stale.
        eff_noise = 0.04
    coach_u = float(coaching.uncertainty_boost) if coaching is not None else 0.0
    early_u = (
        0.42 * qb.uncertainty
        + 0.26 * (1.0 - roster.continuity_score / 100.0)
        + 0.16 * coach_u
        + 0.10 * eff_noise / 0.06
        + unit_noise
    )
    early_u = _clamp(early_u, 0.05, 0.85)

    notes: Dict[str, str] = {
        "compose": (
            "off_eff/def_eff+roster_strength+qb_situation+position_groups+coaching; "
            "prior-year SP+ efficiency complementary (not sole driver); "
            "HFA applied at game time"
        ),
        "offense_score": f"{offense_score:.1f}",
        "defense_score": f"{defense_score:.1f}",
        "off_eff": f"{off_eff:.1f}",
        "def_eff": f"{def_eff:.1f}",
        "roster_strength": f"{roster_s:.1f}",
        "qb_situation_index": f"{qb_index:.4f}",
        "qb_situation_score": f"{qb_score:.1f}",
        "qb_class": qb.qb_class,
        "ol": f"{groups.ol:.1f}",
        "skill": f"{groups.skill:.1f}",
        "front_seven": f"{groups.front_seven:.1f}",
        "secondary": f"{groups.secondary:.1f}",
        "weights_offense": (
            f"eff={P.WEIGHT_OFF_EFF},"
            f"roster={P.WEIGHT_ROSTER_STRENGTH},"
            f"qb={P.WEIGHT_QB_SITUATION},"
            f"skill={P.WEIGHT_SKILL_GROUP},"
            f"ol={P.WEIGHT_OL_GROUP},"
            f"qb_blend={P.QB_INDEX_BLEND},"
            f"ol_blend={P.OL_INDEX_BLEND},"
            f"skill_blend={P.SKILL_INDEX_BLEND},"
            f"eff_blend={P.EFF_OFF_INDEX_BLEND}"
        ),
        "weights_defense": (
            f"eff={P.WEIGHT_DEF_EFF},"
            f"roster={P.WEIGHT_DEF_ROSTER_STRENGTH},"
            f"front_seven={P.WEIGHT_DEF_FRONT_SEVEN},"
            f"secondary={P.WEIGHT_DEF_SECONDARY},"
            f"experience={P.WEIGHT_DEF_EXPERIENCE},"
            f"def_unit_blend={P.DEF_UNIT_BLEND},"
            f"eff_blend={P.EFF_DEF_INDEX_BLEND}"
        ),
        "anti_double_count": (
            "unit weights/blends + game unit matchup scales reduced vs v0.7"
        ),
    }
    if efficiency is not None:
        notes["efficiency_source"] = efficiency.source
        notes["efficiency_fidelity"] = efficiency.fidelity
        notes["sp_plus"] = f"{efficiency.sp_plus:.1f}"
        notes["sp_rank"] = str(efficiency.sp_rank) if efficiency.sp_rank is not None else ""
        notes["success_off"] = f"{efficiency.success_off:.1f}"
        notes["success_def"] = f"{efficiency.success_def:.1f}"
        notes["explosiveness"] = f"{efficiency.explosiveness:.1f}"
    if coaching is not None:
        notes["coaching_new_hc"] = str(coaching.new_hc)
        notes["coaching_new_oc"] = str(coaching.new_oc)
        notes["coaching_new_dc"] = str(coaching.new_dc)
        notes["coaching_continuity_score"] = f"{coaching.continuity_score:.1f}"
        notes["coaching_off_mult"] = f"{coaching.offense_index_mult:.4f}"
        notes["coaching_def_mult"] = f"{coaching.defense_index_mult:.4f}"
    if home_field is not None:
        notes["hfa_bucket"] = home_field.bucket
        notes["hfa_points"] = f"{home_field.hfa_points:.2f}"
    if league_reg:
        notes["league_regression"] = (
            f"placeholder_sp_plus shrink {league_reg:.2f} toward index 1.0"
        )

    return TeamProjectionState(
        team=str(team),
        offense_index=round(offense_index, 4),
        defense_index=round(defense_index, 4),
        pace_factor=round(pace, 4),
        pass_rate_bias=round(pass_bias, 4),
        early_season_uncertainty=round(early_u, 4),
        roster=roster,
        qb=qb,
        groups=groups,
        efficiency=efficiency,
        home_field=home_field,
        coaching=coaching,
        source="hierarchical_compose",
        fidelity="approximate",
        notes=notes,
    )


def copy_strength_book(
    teams: Mapping[str, TeamProjectionState],
) -> Dict[str, TeamProjectionState]:
    return {k: v.copy() for k, v in teams.items()}


def unit_offense_boost(groups: Optional[PositionGroupGrades]) -> float:
    """Multiplicative offense boost from OL + skill (± scale at extremes)."""
    if groups is None:
        return 1.0
    ol_term = (groups.ol - 50.0) / 50.0
    skill_term = (groups.skill - 50.0) / 50.0
    signed = P.UNIT_OL_SHARE * ol_term + P.UNIT_SKILL_SHARE * skill_term
    return _clamp(1.0 + P.UNIT_OFFENSE_BOOST_SCALE * signed, 0.85, 1.15)


def unit_defense_dampen(groups: Optional[PositionGroupGrades]) -> float:
    """Opponent scoring multiplier from front_seven + secondary.

    Strong defense → value < 1.0 (dampens opponent points).
    """
    if groups is None:
        return 1.0
    f7_term = (groups.front_seven - 50.0) / 50.0
    sec_term = (groups.secondary - 50.0) / 50.0
    signed = P.UNIT_FRONT_SEVEN_SHARE * f7_term + P.UNIT_SECONDARY_SHARE * sec_term
    # Higher defense grade → lower opponent scoring multiplier.
    return _clamp(1.0 - P.UNIT_DEFENSE_DAMPEN_SCALE * signed, 0.82, 1.18)


def expected_team_points(
    offense: TeamProjectionState,
    opponent_defense: TeamProjectionState,
    *,
    home: bool,
    neutral_site: bool = False,
    week: int = 5,
    night_game: bool = False,
    home_hfa_profile: Optional[HomeFieldProfile] = None,
) -> Tuple[float, Dict[str, Any]]:
    """Expected points with unit-aware matchup + variable HFA + coaching.

    Returns (points, diagnostics).
    """
    response = P.matchup_response_for_week(week)
    raw_ratio = offense.offense_index / max(0.50, opponent_defense.defense_index)
    ratio_lo, ratio_hi = P.MATCHUP_RATIO_CLAMP
    ratio = _soft_clamp_ratio(
        raw_ratio, ratio_lo, ratio_hi, P.MATCHUP_RATIO_EXCESS_RETAIN
    )
    matchup = ratio ** response
    off_boost = unit_offense_boost(offense.groups)
    def_dampen = unit_defense_dampen(opponent_defense.groups)
    pace = 0.5 * (offense.pace_factor + opponent_defense.pace_factor)
    base = P.LEAGUE_TEAM_PPG * matchup * off_boost * def_dampen * pace

    # Variable HFA — only the designated home side, never on neutral.
    hfa_profile = home_hfa_profile
    if hfa_profile is None and home:
        hfa_profile = offense.home_field
    hfa = resolve_hfa_points(
        hfa_profile,
        home=home,
        neutral_site=neutral_site,
        night_game=night_game,
    )
    base += float(hfa["hfa_points"])

    # Coaching: own offense penalty (week-decayed) + opponent new-DC boost.
    own_coach = coaching_week_adjustment(offense.coaching, week=week, side="offense")
    opp_def_pen = coaching_week_adjustment(
        opponent_defense.coaching, week=week, side="defense"
    )
    # Opponent defense penalty → they allow more → boost our scoring.
    coach_adj = float(own_coach["points"]) + abs(float(opp_def_pen["points"]))
    base += coach_adj

    points = _clamp(base, *P.EXPECTED_POINTS_CLAMP)
    diag: Dict[str, Any] = {
        "matchup_ratio_raw": round(raw_ratio, 4),
        "matchup_ratio": round(ratio, 4),
        "matchup_ratio_clamped": abs(raw_ratio - ratio) > 1e-9,
        "matchup_response": round(response, 4),
        "offense_boost": round(off_boost, 4),
        "defense_dampen": round(def_dampen, 4),
        "pace": round(pace, 4),
        "hfa": hfa,
        "coaching_own_scoring_adj": own_coach,
        "coaching_opp_defense_penalty": opp_def_pen,
        "coaching_net_adj": round(coach_adj, 3),
        "pre_clamp": round(base, 3),
    }
    return points, diag


def win_prob_from_expected_scores(
    home_points: float,
    away_points: float,
    *,
    margin_sd: float,
) -> float:
    margin = home_points - away_points
    z = margin / max(8.0, margin_sd)
    return _clamp(0.5 * (1.0 + math.erf(z / math.sqrt(2.0))), 0.02, 0.98)


def layers_snapshot(state: TeamProjectionState) -> Dict[str, Any]:
    return {
        "offense_index": state.offense_index,
        "defense_index": state.defense_index,
        "pace_factor": state.pace_factor,
        "pass_rate_bias": state.pass_rate_bias,
        "early_season_uncertainty": state.early_season_uncertainty,
        "fidelity": state.fidelity,
        "source": state.source,
        "compose_notes": dict(state.notes),
        "roster": roster_to_dict(state.roster) if state.roster else None,
        "qb": qb_to_dict(state.qb) if state.qb else None,
        "position_groups": groups_to_dict(state.groups) if state.groups else None,
        "efficiency": efficiency_to_dict(state.efficiency),
        "home_field": profile_to_dict(state.home_field),
        "coaching": coaching_to_dict(state.coaching),
    }


def project_game_formula_doc() -> Dict[str, Any]:
    return {
        "steps": [
            "compose offense/defense indices from off_eff/def_eff + roster + QB "
            "+ position groups + coaching index multipliers",
            "expected_points = league_ppg * (off/def)^response * ol/skill_boost "
            "* opponent_(f7+secondary)_dampen * pace + variable_HFA "
            "+ coaching_week_adj",
            "variable_HFA = bucket_points(+ night_bump) when home & not neutral "
            f"(baseline={P.HFA_BASELINE_POINTS})",
            "coaching_week_adj = week-decayed new HC/OC/DC penalties "
            "(strongest W1–W4)",
            "optional thin ST nudge on the total path only",
            "margin_mean = home_exp - away_exp  (HFA + coaching live here)",
            "v0.13: cal_margin = TAU*tanh(SCALE*matchup/TAU) + HFA "
            "(SCALE=0.80, TAU=26; HFA added after compress); total path unchanged",
            "total_mean = league_total * pace * off_env^0.55 * expl  "
            "(separate path; not f(spread) and not home_exp+away_exp)",
            "sim: independent Gaussian margin + total; scores = (total±margin)/2",
            "spread_home = away_sim - home_sim  (neg = home favorite)",
            "fair_total = home_sim + away_sim",
            "home_wp = Φ(margin_mean / margin_sd); sim WP also reported",
        ],
        "weights": P.documentation()["composition_weights"],
        "efficiency": (
            "Prior-year opponent-adjusted efficiency (final-2025 SP+ carry) "
            "blended with roster/QB/units. success/explosiveness are proxies "
            "(no full PBP). Unit weights reduced to avoid double-counting."
        ),
        "early_season": (
            "W1–W4: inflate margin_sd, soften matchup response, flag "
            "roster/QB/coaching/prior-year-efficiency carry uncertainty; "
            "narrows on week-indexed schedule. Coaching penalties also decay "
            "on the same early window."
        ),
        "coherence": {
            "spread_home": "away_score - home_score",
            "expected_total": "home_score + away_score",
            "win_probs": "home_wp + away_wp == 1",
            "team_totals": "team_total_home + team_total_away == fair_total",
        },
        "total_path": "separate_from_spread",
        "n_sims_default": GAME_SIM_N_DEFAULT,
        "used_in_spread": USED_IN_SPREAD,
    }


def _layer_drivers(state: TeamProjectionState) -> Dict[str, Any]:
    """Inspectable layer contributions for project-game diagnostics."""
    roster = state.roster
    qb = state.qb
    groups = state.groups
    eff = state.efficiency
    return {
        "roster_strength": round(float(roster.roster_strength), 2) if roster else None,
        "roster_fidelity": roster.fidelity if roster else None,
        "qb_situation_index": round(float(qb.qb_situation_index), 4) if qb else None,
        "qb_situation_score": round(float(qb.qb_situation_score), 2) if qb else None,
        "qb_class": qb.qb_class if qb else None,
        "qb_uncertainty": round(float(qb.uncertainty), 4) if qb else None,
        "efficiency": efficiency_to_dict(eff),
        "off_eff": round(float(eff.off_eff), 2) if eff else None,
        "def_eff": round(float(eff.def_eff), 2) if eff else None,
        "success_off": round(float(eff.success_off), 2) if eff else None,
        "success_def": round(float(eff.success_def), 2) if eff else None,
        "explosiveness": round(float(eff.explosiveness), 2) if eff else None,
        "sp_plus": round(float(eff.sp_plus), 2) if eff else None,
        "sp_rank": eff.sp_rank if eff else None,
        "unit_grades": {
            "ol": round(float(groups.ol), 2) if groups else None,
            "skill": round(float(groups.skill), 2) if groups else None,
            "front_seven": round(float(groups.front_seven), 2) if groups else None,
            "secondary": round(float(groups.secondary), 2) if groups else None,
            "special_teams": round(float(groups.special_teams), 2) if groups else None,
            "fidelity": groups.fidelity if groups else None,
        },
        "blend_weights": {
            "offense": {
                "efficiency": P.WEIGHT_OFF_EFF,
                "roster": P.WEIGHT_ROSTER_STRENGTH,
                "qb": P.WEIGHT_QB_SITUATION,
                "skill": P.WEIGHT_SKILL_GROUP,
                "ol": P.WEIGHT_OL_GROUP,
            },
            "defense": {
                "efficiency": P.WEIGHT_DEF_EFF,
                "roster": P.WEIGHT_DEF_ROSTER_STRENGTH,
                "front_seven": P.WEIGHT_DEF_FRONT_SEVEN,
                "secondary": P.WEIGHT_DEF_SECONDARY,
                "experience": P.WEIGHT_DEF_EXPERIENCE,
            },
        },
        "home_field": profile_to_dict(state.home_field),
        "coaching": coaching_to_dict(state.coaching),
        "offense_index": state.offense_index,
        "defense_index": state.defense_index,
        "pace_factor": state.pace_factor,
        "early_season_uncertainty": state.early_season_uncertainty,
        "compose_notes": dict(state.notes),
    }


def project_game(
    universe: EngineUniverse,
    *,
    home_team: str,
    away_team: str,
    week: int = 1,
    season: Optional[int] = None,
    neutral_site: bool = False,
    night_game: bool = False,
    engine_version: str = P.ENGINE_VERSION,
    player_hook_summaries: Optional[List[Dict[str, Any]]] = None,
    n_sims: Optional[int] = None,
    seed: Optional[int] = None,
) -> GameProjection:
    """Team-level projection: strength→margin + separate total sim."""
    home_team = home_team.upper()
    away_team = away_team.upper()
    if home_team not in universe.teams:
        raise KeyError(f"Unknown home team: {home_team}")
    if away_team not in universe.teams:
        raise KeyError(f"Unknown away team: {away_team}")

    home = universe.teams[home_team]
    away = universe.teams[away_team]
    early = P.early_season_uncertainty(week)
    margin_sd = P.win_prob_margin_sd_for_week(week)
    team_u = 0.5 * (home.early_season_uncertainty + away.early_season_uncertainty)

    home_exp, home_diag = expected_team_points(
        home,
        away,
        home=True,
        neutral_site=neutral_site,
        week=week,
        night_game=night_game,
        home_hfa_profile=home.home_field,
    )
    away_exp, away_diag = expected_team_points(
        away,
        home,
        home=False,
        neutral_site=neutral_site,
        week=week,
        night_game=False,
        home_hfa_profile=home.home_field,
    )

    # Thin ST nudge belongs on the total path only (does not invent spread).
    st_home = home.groups.special_teams if home.groups else 50.0
    st_away = away.groups.special_teams if away.groups else 50.0
    st_nudge = P.SPECIAL_TEAMS_TOTAL_SCALE * ((st_home + st_away) / 2.0 - 50.0)
    strength_home = round(home_exp, 2)
    strength_away = round(away_exp, 2)
    strength_total = round(strength_home + strength_away + st_nudge, 2)
    strength_spread = round(strength_away - strength_home, 2)
    fcs_game = fcs_matchup_from_states(home, away)
    hfa_pts = float((home_diag.get("hfa") or {}).get("hfa_points") or 0.0)
    cal_block = calibrate_margin(
        (strength_home - hfa_pts) - strength_away, fcs_matchup=fcs_game
    )
    cal_block["hfa_added_after"] = round(hfa_pts, 4)
    margin_mean = float(cal_block["calibrated_margin"]) + hfa_pts
    total_mean, total_diag = total_path_mean(home, away, st_nudge=st_nudge)

    sim_seed = seed
    if sim_seed is None:
        sim_seed = (
            2026_0813
            + int(week) * 1009
            + sum(ord(c) for c in f"{home_team}{away_team}")
        )
    dist = simulate_game_distributions(
        home,
        away,
        margin_mean=margin_mean,
        total_mean=total_mean,
        week=week,
        base_margin_sd=margin_sd,
        n_sims=n_sims,
        seed=sim_seed,
        st_nudge=st_nudge,
    )
    margin_sd = float(dist["sigma"]["margin_sd"])
    home_exp_adj = float(dist["team_total_home"])
    away_exp_adj = float(dist["team_total_away"])
    total = float(dist["fair_total"])
    spread = float(dist["fair_spread"])
    margin = home_exp_adj - away_exp_adj
    home_wp = win_prob_from_expected_scores(
        home_exp_adj, away_exp_adj, margin_sd=margin_sd
    )
    away_wp = round(1.0 - home_wp, 4)
    home_wp = round(home_wp, 4)

    home_drivers = _layer_drivers(home)
    away_drivers = _layer_drivers(away)
    home_coach_adj = team_game_point_adjustment(home.coaching, week=week)
    away_coach_adj = team_game_point_adjustment(away.coaching, week=week)
    drivers = {
        "home": home_drivers,
        "away": away_drivers,
        "matchup": {
            "home_points_diag": home_diag,
            "away_points_diag": away_diag,
            "hfa": home_diag.get("hfa"),
            "home_coaching_adj": home_coach_adj,
            "away_coaching_adj": away_coach_adj,
            "st_total_nudge": round(st_nudge, 3),
            "margin": round(margin, 2),
            "spread_home": spread,
            "expected_total": total,
            "margin_sd": round(margin_sd, 3),
            "team_identity_uncertainty_blend": round(team_u, 4),
            "night_game": bool(night_game),
            "neutral_site": bool(neutral_site),
            "strength_path_diagnostic": {
                "home_exp": strength_home,
                "away_exp": strength_away,
                "total_if_summed": strength_total,
                "spread_if_from_scores": strength_spread,
                "note": (
                    "Diagnostic only. Published total uses the separate "
                    "total path, not home_exp+away_exp."
                ),
            },
            "total_path": total_diag,
            "margin_calibration": cal_block,
            "n_sims": dist["n_sims"],
        },
        "primary_signals": {
            "home_off_eff": home_drivers.get("off_eff"),
            "away_off_eff": away_drivers.get("off_eff"),
            "home_def_eff": home_drivers.get("def_eff"),
            "away_def_eff": away_drivers.get("def_eff"),
            "home_sp_plus": home_drivers.get("sp_plus"),
            "away_sp_plus": away_drivers.get("sp_plus"),
            "home_roster_strength": home_drivers.get("roster_strength"),
            "away_roster_strength": away_drivers.get("roster_strength"),
            "home_qb_situation_index": home_drivers.get("qb_situation_index"),
            "away_qb_situation_index": away_drivers.get("qb_situation_index"),
            "home_unit_grades": home_drivers.get("unit_grades"),
            "away_unit_grades": away_drivers.get("unit_grades"),
            "home_hfa_bucket": (home.home_field.bucket if home.home_field else None),
            "home_hfa_points": (home.home_field.hfa_points if home.home_field else None),
            "home_coaching_flags": {
                "new_hc": bool(home.coaching.new_hc) if home.coaching else False,
                "new_oc": bool(home.coaching.new_oc) if home.coaching else False,
                "new_dc": bool(home.coaching.new_dc) if home.coaching else False,
            },
            "away_coaching_flags": {
                "new_hc": bool(away.coaching.new_hc) if away.coaching else False,
                "new_oc": bool(away.coaching.new_oc) if away.coaching else False,
                "new_dc": bool(away.coaching.new_dc) if away.coaching else False,
            },
            "blend_weights": home_drivers.get("blend_weights"),
        },
        "note": (
            "Drivers are inspectable layer inputs/indices — not calibrated "
            "market attribution weights. Efficiency is prior-year SP+ carry."
        ),
    }
    uncertainty = {
        **early,
        "team_identity_uncertainty_blend": round(team_u, 4),
        "home_team_early_uncertainty": home.early_season_uncertainty,
        "away_team_early_uncertainty": away.early_season_uncertainty,
        "home_coaching_uncertainty_boost": (
            home.coaching.uncertainty_boost if home.coaching else 0.0
        ),
        "away_coaching_uncertainty_boost": (
            away.coaching.uncertainty_boost if away.coaching else 0.0
        ),
        "effective_margin_sd": round(margin_sd, 3),
        "effective_total_sd": dist["total"]["std"],
        "open_qb": {
            "home": dist["sigma"]["home_open_qb"],
            "away": dist["sigma"]["away_open_qb"],
            "home_class": dist["sigma"]["home_qb_class"],
            "away_class": dist["sigma"]["away_qb_class"],
        },
        "fcs": {
            "home": dist["sigma"]["home_fcs"],
            "away": dist["sigma"]["away_fcs"],
            "home_label": dist["sigma"]["home_fcs_label"],
            "away_label": dist["sigma"]["away_fcs_label"],
        },
        "n_sims": dist["n_sims"],
        "weather": dist["weather"],
        "narrowing_schedule": P.early_season_narrowing_schedule(),
        "honesty": (
            "Wide W1–W4 priors; week-indexed narrowing. Open QB / FCS "
            "widen margin and total σ. Coaching change penalties decay "
            "on the same early window. Not a claim of known early-season "
            "identity. Research only — used_in_spread=false."
        ),
    }

    game_id = f"{season or universe.season}_w{week}_{away_team}@{home_team}"
    notes = {
        "fidelity": "approximate",
        "method": (
            "strength→margin (HFA/coaching) + separate total sim "
            "(pace/off_env/explosiveness); scores=(total±margin)/2"
        ),
        "formula": (
            "margin=home_exp-away_exp; "
            "total=league_ppg*2*pace*off_env^0.55*expl; "
            "sim N Gaussian; spread_home=away-home; wp=Φ(margin/margin_sd)"
        ),
        "coherence": "spread=away-home; total=home+away; wp_home+wp_away=1",
        "does_not_touch": "edge_board_markets_only_cfb",
        "used_in_spread": "false",
        "calibration_id": cal_block["calibration_id"],
        "n_sims": str(dist["n_sims"]),
        "weather": dist["weather"],
        "margin": f"{margin:.2f}",
        "st_total_nudge": f"{st_nudge:.3f}",
        "hfa_bucket": home.home_field.bucket if home.home_field else "n/a",
        **{f"universe_{k}": v for k, v in list(universe.notes.items())[:6]},
    }
    return GameProjection(
        season=int(season or universe.season),
        week=int(week),
        game_id=game_id,
        home_team=home_team,
        away_team=away_team,
        engine_version=engine_version,
        home_win_prob=home_wp,
        away_win_prob=away_wp,
        expected_home_score=home_exp_adj,
        expected_away_score=away_exp_adj,
        expected_total=total,
        spread_home=spread,
        margin_sd=round(margin_sd, 3),
        early_season_uncertainty=early,
        home_layers=layers_snapshot(home),
        away_layers=layers_snapshot(away),
        player_hooks=list(player_hook_summaries or []),
        drivers=drivers,
        uncertainty=uncertainty,
        notes=notes,
        fidelity="approximate",
        distributions=dist,
        n_sims=int(dist["n_sims"]),
    )


def project_game_to_dict(proj: GameProjection) -> Dict[str, Any]:
    from src.services.cfb_warehouse.preseason_prior import research_prior_block

    return {
        "season": proj.season,
        "week": proj.week,
        "game_id": proj.game_id,
        "home_team": proj.home_team,
        "away_team": proj.away_team,
        "engine_version": proj.engine_version,
        "home_win_prob": proj.home_win_prob,
        "away_win_prob": proj.away_win_prob,
        "expected_home_score": proj.expected_home_score,
        "expected_away_score": proj.expected_away_score,
        "expected_total": proj.expected_total,
        "spread_home": proj.spread_home,
        "margin_sd": proj.margin_sd,
        "early_season_uncertainty": proj.early_season_uncertainty,
        "uncertainty": proj.uncertainty,
        "drivers": proj.drivers,
        "home_layers": proj.home_layers,
        "away_layers": proj.away_layers,
        "player_hooks": proj.player_hooks,
        "player_projections": proj.player_projections,
        # Alias for UI / clients that prefer a shorter key.
        "players": proj.player_projections,
        "notes": proj.notes,
        "fidelity": proj.fidelity,
        "fair_spread": proj.spread_home,
        "fair_total": proj.expected_total,
        "team_total_home": proj.expected_home_score,
        "team_total_away": proj.expected_away_score,
        "distributions": proj.distributions,
        "n_sims": proj.n_sims,
        "used_in_spread": USED_IN_SPREAD,
        "projection_formula": project_game_formula_doc(),
        # Research-only. Does not change spread / WP / KEI.
        "research_prior": research_prior_block(
            proj.home_team, proj.away_team, season=int(proj.season)
        ),
    }


def evolve_after_game(
    teams: MutableMapping[str, TeamProjectionState],
    *,
    home_team: str,
    away_team: str,
    home_won: bool,
    home_score: float,
    away_score: float,
    week: int = 5,
    rng: Optional[random.Random] = None,
) -> None:
    """Mild in-path strength evolution (not calibrated); extra early-season noise."""
    rng = rng or random.Random()
    home = teams[home_team]
    away = teams[away_team]
    home_margin = float(home_score) - float(away_score)
    surprise = _clamp((home_margin - 2.5) / 16.0, -1.5, 1.5)
    noise_sd = P.strength_noise_sd_for_week(week)

    def _bump(state: TeamProjectionState, direction: float) -> None:
        noise_o = rng.gauss(0.0, noise_sd)
        noise_d = rng.gauss(0.0, noise_sd)
        state.offense_index = _clamp(
            state.offense_index
            + P.STRENGTH_UPDATE_RATE * direction
            + P.STRENGTH_MEAN_REVERT * (1.0 - state.offense_index)
            + noise_o,
            *P.STRENGTH_CLAMP,
        )
        state.defense_index = _clamp(
            state.defense_index
            + P.STRENGTH_UPDATE_RATE * 0.7 * direction
            + P.STRENGTH_MEAN_REVERT * (1.0 - state.defense_index)
            + noise_d,
            *P.STRENGTH_CLAMP,
        )
        # Identity uncertainty shrinks slowly as games accumulate.
        state.early_season_uncertainty = _clamp(
            state.early_season_uncertainty * 0.92, 0.05, 0.85
        )
        state.games_played += 1

    _bump(home, surprise if home_won else -abs(surprise) * 0.8)
    _bump(away, -surprise if home_won else abs(surprise) * 0.8)


def realize_game_scores(
    game: ScheduledGame,
    teams: Mapping[str, TeamProjectionState],
    *,
    rng: random.Random,
) -> Dict[str, float]:
    home = teams[game.home_team]
    away = teams[game.away_team]
    night = bool(getattr(game, "night_game", False))
    home_exp, _ = expected_team_points(
        home,
        away,
        home=True,
        neutral_site=game.neutral_site,
        week=game.week,
        night_game=night,
        home_hfa_profile=home.home_field,
    )
    away_exp, _ = expected_team_points(
        away,
        home,
        home=False,
        neutral_site=game.neutral_site,
        week=game.week,
        night_game=False,
        home_hfa_profile=home.home_field,
    )
    hfa_pts = float(
        resolve_hfa_points(
            home.home_field,
            home=True,
            neutral_site=game.neutral_site,
            night_game=night,
        ).get("hfa_points")
        or 0.0
    )
    cal_scores = apply_calibrated_scores(
        home_exp - hfa_pts,
        away_exp,
        fcs_matchup=fcs_matchup_from_states(home, away)
        or bool(getattr(game, "fcs_home", False) or getattr(game, "fcs_away", False)),
    )
    home_exp = float(cal_scores["home_exp_cal"]) + hfa_pts
    away_exp = float(cal_scores["away_exp_cal"])
    sd = P.score_noise_sd_for_week(game.week)
    home_score = max(0.0, rng.gauss(home_exp, sd))
    away_score = max(0.0, rng.gauss(away_exp, sd))
    return {
        "home_score": home_score,
        "away_score": away_score,
        "home_won": 1.0 if home_score >= away_score else 0.0,
    }


def documentation() -> Dict[str, Any]:
    return {
        "layer": 4,
        "name": "team_projection",
        "module": "src.services.cfb_season_engine.team_projection",
        "real_vs_approximate": (
            "Composition structure is REAL (inspectable weights; off_eff/def_eff "
            "+ roster_strength + qb_situation_index + position groups + coaching "
            "multipliers are drivers; variable HFA is applied at game time). "
            "Numeric indices and game probabilities are APPROXIMATE — not "
            "calibrated market-grade fair lines. Efficiency is prior-year SP+ carry."
        ),
        "feeds": [
            "efficiency.off_eff/def_eff",
            "roster_construction.roster_strength",
            "qb_situation.qb_situation_index",
            "position_groups.ol/skill/front_seven/secondary",
            "home_field.variable_hfa",
            "coaching_continuity.week_decayed_penalties",
            "priors.early_season_uncertainty",
        ],
        "primary_drivers": {
            "offense": [
                "off_eff",
                "roster_strength",
                "qb_situation_index",
                "ol",
                "skill",
                "coaching_continuity",
            ],
            "defense": [
                "def_eff",
                "front_seven",
                "secondary",
                "roster_strength",
                "coaching_continuity",
            ],
            "game_env": ["variable_hfa", "night_game_note"],
        },
        "project_game_formula": project_game_formula_doc(),
    }
