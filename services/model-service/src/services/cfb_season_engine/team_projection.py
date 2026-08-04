"""Layer 4 — Team projection + game-level matchup.

Composes roster construction + QB situation + position groups into
offense/defense indices, then projects a single game:

    strength indices → expected points (unit matchup) → margin
      → spread / total / win probability

Historical team ratings are *not* the primary driver — ``roster_strength``,
``qb_situation_index``, and position-group unit grades are.
"""

from __future__ import annotations

import math
import random
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Tuple

from src.services.cfb_season_engine import priors as P
from src.services.cfb_season_engine.position_groups import groups_to_dict
from src.services.cfb_season_engine.qb_situation import qb_to_dict
from src.services.cfb_season_engine.roster_construction import roster_to_dict
from src.services.cfb_season_engine.types import (
    EngineUniverse,
    GameProjection,
    PositionGroupGrades,
    QbSituation,
    RosterConstruction,
    ScheduledGame,
    TeamProjectionState,
)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def _score_to_index(score_0_100: float) -> float:
    """Map 0–100 unit score to ~0.7–1.35 strength index (1.0 at 50)."""
    return _clamp(1.0 + (float(score_0_100) - 50.0) / 80.0, 0.65, 1.45)


def _unit_index(grade_0_100: float) -> float:
    return _score_to_index(grade_0_100)


def compose_team_projection(
    team: str,
    roster: RosterConstruction,
    qb: QbSituation,
    groups: PositionGroupGrades,
) -> TeamProjectionState:
    """Compose Layers 1–3 into team O/D indices.

    Offense: roster_strength + qb_situation + OL + skill (all material).
    Defense: roster_strength + front_seven + secondary + experience.
    Post-compose unit blends keep OL / skill / F7 / secondary as hard levers.
    """
    roster_s = float(roster.roster_strength)
    qb_score = float(qb.qb_situation_score)
    qb_index = float(qb.qb_situation_index)

    offense_score = (
        P.WEIGHT_ROSTER_STRENGTH * roster_s
        + P.WEIGHT_QB_SITUATION * qb_score
        + P.WEIGHT_SKILL_GROUP * groups.skill
        + P.WEIGHT_OL_GROUP * groups.ol
    )

    defense_score = (
        P.WEIGHT_DEF_ROSTER_STRENGTH * roster_s
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
    # Hard OL / skill levers (position groups as real drivers).
    ol_idx = _unit_index(groups.ol)
    skill_idx = _unit_index(groups.skill)
    offense_index = (1.0 - P.OL_INDEX_BLEND) * offense_index + P.OL_INDEX_BLEND * (
        offense_index * ol_idx
    )
    offense_index = (1.0 - P.SKILL_INDEX_BLEND) * offense_index + P.SKILL_INDEX_BLEND * (
        offense_index * skill_idx
    )
    offense_index = _clamp(offense_index, *P.STRENGTH_CLAMP)

    defense_index = _score_to_index(defense_score)
    f7_idx = _unit_index(groups.front_seven)
    sec_idx = _unit_index(groups.secondary)
    def_unit = P.UNIT_FRONT_SEVEN_SHARE * f7_idx + P.UNIT_SECONDARY_SHARE * sec_idx
    defense_index = (1.0 - P.DEF_UNIT_BLEND) * defense_index + P.DEF_UNIT_BLEND * (
        defense_index * def_unit
    )
    defense_index = _clamp(defense_index, *P.STRENGTH_CLAMP)

    pace = _clamp(1.0 + (groups.skill - groups.front_seven) / 200.0, 0.85, 1.20)
    pass_bias = _clamp(
        (qb.qb_talent - 50.0) / 200.0
        + (groups.skill - 50.0) / 250.0
        + (qb_index - 1.0) * 0.08
        - (groups.secondary - 50.0) / 400.0,
        -0.14,
        0.16,
    )

    # Early uncertainty: QB situation dominates; roster continuity tempers;
    # thin/placeholder units add a little identity noise.
    unit_noise = 0.0
    if groups.fidelity == "placeholder":
        unit_noise = 0.08
    elif groups.fidelity == "approximate":
        unit_noise = 0.03
    early_u = (
        0.55 * qb.uncertainty
        + 0.35 * (1.0 - roster.continuity_score / 100.0)
        + unit_noise
    )
    early_u = _clamp(early_u, 0.05, 0.85)

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
        source="hierarchical_compose",
        fidelity="approximate",
        notes={
            "compose": (
                "roster_strength+qb_situation+position_groups; "
                "historical rating not primary"
            ),
            "offense_score": f"{offense_score:.1f}",
            "defense_score": f"{defense_score:.1f}",
            "roster_strength": f"{roster_s:.1f}",
            "qb_situation_index": f"{qb_index:.4f}",
            "qb_situation_score": f"{qb_score:.1f}",
            "qb_class": qb.qb_class,
            "ol": f"{groups.ol:.1f}",
            "skill": f"{groups.skill:.1f}",
            "front_seven": f"{groups.front_seven:.1f}",
            "secondary": f"{groups.secondary:.1f}",
            "weights_offense": (
                f"roster={P.WEIGHT_ROSTER_STRENGTH},"
                f"qb={P.WEIGHT_QB_SITUATION},"
                f"skill={P.WEIGHT_SKILL_GROUP},"
                f"ol={P.WEIGHT_OL_GROUP},"
                f"qb_blend={P.QB_INDEX_BLEND},"
                f"ol_blend={P.OL_INDEX_BLEND},"
                f"skill_blend={P.SKILL_INDEX_BLEND}"
            ),
            "weights_defense": (
                f"roster={P.WEIGHT_DEF_ROSTER_STRENGTH},"
                f"front_seven={P.WEIGHT_DEF_FRONT_SEVEN},"
                f"secondary={P.WEIGHT_DEF_SECONDARY},"
                f"experience={P.WEIGHT_DEF_EXPERIENCE},"
                f"def_unit_blend={P.DEF_UNIT_BLEND}"
            ),
        },
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
) -> Tuple[float, Dict[str, float]]:
    """Expected points with unit-aware matchup.

    Returns (points, diagnostics).
    """
    response = P.matchup_response_for_week(week)
    ratio = offense.offense_index / max(0.50, opponent_defense.defense_index)
    matchup = ratio ** response
    off_boost = unit_offense_boost(offense.groups)
    def_dampen = unit_defense_dampen(opponent_defense.groups)
    pace = 0.5 * (offense.pace_factor + opponent_defense.pace_factor)
    base = P.LEAGUE_TEAM_PPG * matchup * off_boost * def_dampen * pace
    if neutral_site:
        base += P.NEUTRAL_SITE_HFA
    elif home:
        base += P.HOME_FIELD_POINTS
    points = _clamp(base, *P.EXPECTED_POINTS_CLAMP)
    diag = {
        "matchup_ratio": round(ratio, 4),
        "matchup_response": round(response, 4),
        "offense_boost": round(off_boost, 4),
        "defense_dampen": round(def_dampen, 4),
        "pace": round(pace, 4),
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
    }


def project_game_formula_doc() -> Dict[str, Any]:
    return {
        "steps": [
            "compose offense/defense indices from roster + QB + position groups",
            "expected_points = league_ppg * (off/def)^response * ol/skill_boost "
            "* opponent_(f7+secondary)_dampen * pace + HFA",
            "margin = home_exp - away_exp",
            "spread_home = away_exp - home_exp  (neg = home favorite)",
            "total = home_exp + away_exp (+ thin ST nudge)",
            "home_wp = Φ(margin / margin_sd)",
        ],
        "weights": P.documentation()["composition_weights"],
        "early_season": (
            "W1–W4: inflate margin_sd, soften matchup response, flag "
            "roster/QB identity uncertainty"
        ),
    }


def project_game(
    universe: EngineUniverse,
    *,
    home_team: str,
    away_team: str,
    week: int = 1,
    season: Optional[int] = None,
    neutral_site: bool = False,
    engine_version: str = P.ENGINE_VERSION,
    player_hook_summaries: Optional[List[Dict[str, Any]]] = None,
) -> GameProjection:
    """Team-level projection for a matchup (strength → margin → lines/WP)."""
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
    # Team-specific early uncertainty widens margin SD further.
    team_u = 0.5 * (home.early_season_uncertainty + away.early_season_uncertainty)
    margin_sd *= 1.0 + 0.25 * team_u

    home_exp, home_diag = expected_team_points(
        home, away, home=True, neutral_site=neutral_site, week=week
    )
    away_exp, away_diag = expected_team_points(
        away, home, home=False, neutral_site=neutral_site, week=week
    )

    # Thin special-teams nudge on total only (not a real ST model).
    st_home = home.groups.special_teams if home.groups else 50.0
    st_away = away.groups.special_teams if away.groups else 50.0
    st_nudge = P.SPECIAL_TEAMS_TOTAL_SCALE * ((st_home + st_away) / 2.0 - 50.0)
    total = home_exp + away_exp + st_nudge
    # Keep individual scores consistent with nudged total (split evenly).
    home_exp_adj = home_exp + 0.5 * st_nudge
    away_exp_adj = away_exp + 0.5 * st_nudge

    margin = home_exp_adj - away_exp_adj
    home_wp = win_prob_from_expected_scores(
        home_exp_adj, away_exp_adj, margin_sd=margin_sd
    )
    spread = round(away_exp_adj - home_exp_adj, 2)  # home spread (neg = favorite)

    game_id = f"{season or universe.season}_w{week}_{away_team}@{home_team}"
    notes = {
        "fidelity": "approximate",
        "method": "strength→margin→spread/total/WP (unit-aware matchup)",
        "formula": (
            "pts = league_ppg*(off/def)^resp*ol_skill_boost*opp_def_dampen*pace+HFA; "
            "spread_home=away-home; wp=Φ(margin/margin_sd)"
        ),
        "does_not_touch": "edge_board_markets_only_cfb",
        "home_matchup": str(home_diag),
        "away_matchup": str(away_diag),
        "margin": f"{margin:.2f}",
        "st_total_nudge": f"{st_nudge:.3f}",
        **{f"universe_{k}": v for k, v in list(universe.notes.items())[:6]},
    }
    return GameProjection(
        season=int(season or universe.season),
        week=int(week),
        game_id=game_id,
        home_team=home_team,
        away_team=away_team,
        engine_version=engine_version,
        home_win_prob=round(home_wp, 4),
        away_win_prob=round(1.0 - home_wp, 4),
        expected_home_score=round(home_exp_adj, 2),
        expected_away_score=round(away_exp_adj, 2),
        expected_total=round(total, 2),
        spread_home=spread,
        margin_sd=round(margin_sd, 3),
        early_season_uncertainty=early,
        home_layers=layers_snapshot(home),
        away_layers=layers_snapshot(away),
        player_hooks=list(player_hook_summaries or []),
        notes=notes,
        fidelity="approximate",
    )


def project_game_to_dict(proj: GameProjection) -> Dict[str, Any]:
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
        "home_layers": proj.home_layers,
        "away_layers": proj.away_layers,
        "player_hooks": proj.player_hooks,
        "notes": proj.notes,
        "fidelity": proj.fidelity,
        "projection_formula": project_game_formula_doc(),
    }


def evolve_after_game(
    teams: MutableMapping[str, TeamProjectionState],
    *,
    home_team: str,
    away_team: str,
    home_won: bool,
    home_score: float,
    away_score: float,
    rng: Optional[random.Random] = None,
) -> None:
    """PLACEHOLDER in-path strength evolution (not calibrated)."""
    rng = rng or random.Random()
    home = teams[home_team]
    away = teams[away_team]
    home_margin = float(home_score) - float(away_score)
    surprise = _clamp((home_margin - 2.5) / 16.0, -1.5, 1.5)

    def _bump(state: TeamProjectionState, direction: float) -> None:
        noise_o = rng.gauss(0.0, P.STRENGTH_NOISE)
        noise_d = rng.gauss(0.0, P.STRENGTH_NOISE)
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
    home_exp, _ = expected_team_points(
        home, away, home=True, neutral_site=game.neutral_site, week=game.week
    )
    away_exp, _ = expected_team_points(
        away, home, home=False, neutral_site=game.neutral_site, week=game.week
    )
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
            "Composition structure is REAL (inspectable weights; roster_strength "
            "+ qb_situation_index + position groups are drivers). Numeric indices "
            "and game probabilities are APPROXIMATE — not calibrated market-grade "
            "fair lines."
        ),
        "feeds": [
            "roster_construction.roster_strength",
            "qb_situation.qb_situation_index",
            "position_groups.ol/skill/front_seven/secondary",
            "priors.early_season_uncertainty",
        ],
        "primary_drivers": {
            "offense": ["roster_strength", "qb_situation_index", "ol", "skill"],
            "defense": ["front_seven", "secondary", "roster_strength"],
        },
        "project_game_formula": project_game_formula_doc(),
    }
