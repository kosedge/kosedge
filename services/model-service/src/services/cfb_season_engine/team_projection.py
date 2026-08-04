"""Layer 4 — Team projection + game-level matchup skeleton.

Composes roster construction + QB situation + position groups into
offense/defense indices, then projects a single game. Historical team
ratings are *not* the primary driver — ``roster_strength`` and
``qb_situation_index`` are.
"""

from __future__ import annotations

import math
import random
from typing import Any, Dict, List, Mapping, MutableMapping, Optional

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


def compose_team_projection(
    team: str,
    roster: RosterConstruction,
    qb: QbSituation,
    groups: PositionGroupGrades,
) -> TeamProjectionState:
    """Compose Layers 1–3 into team O/D indices.

    Offense is driven primarily by ``roster_strength`` + ``qb_situation``;
    position groups supply the remaining unit context. QB class/cast also
    re-blend the offense index so true_freshman vs incumbent is material.
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
    # Hard QB lever: blend base index toward base*qb_situation_index.
    blend = P.QB_INDEX_BLEND
    offense_index = (1.0 - blend) * offense_index + blend * (offense_index * qb_index)
    offense_index = _clamp(offense_index, *P.STRENGTH_CLAMP)

    defense_index = _score_to_index(defense_score)
    defense_index = _clamp(defense_index, *P.STRENGTH_CLAMP)

    pace = _clamp(1.0 + (groups.skill - groups.front_seven) / 200.0, 0.85, 1.20)
    pass_bias = _clamp(
        (qb.qb_talent - 50.0) / 200.0
        + (groups.skill - 50.0) / 250.0
        + (qb_index - 1.0) * 0.08,
        -0.14,
        0.16,
    )

    # Early uncertainty: QB situation dominates; roster continuity tempers.
    early_u = 0.60 * qb.uncertainty + 0.40 * (1.0 - roster.continuity_score / 100.0)

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
            "compose": "roster_strength+qb_situation primary; historical rating not primary",
            "offense_score": f"{offense_score:.1f}",
            "defense_score": f"{defense_score:.1f}",
            "roster_strength": f"{roster_s:.1f}",
            "qb_situation_index": f"{qb_index:.4f}",
            "qb_situation_score": f"{qb_score:.1f}",
            "qb_class": qb.qb_class,
            "weights_offense": (
                f"roster={P.WEIGHT_ROSTER_STRENGTH},"
                f"qb={P.WEIGHT_QB_SITUATION},"
                f"skill={P.WEIGHT_SKILL_GROUP},"
                f"ol={P.WEIGHT_OL_GROUP},"
                f"qb_blend={P.QB_INDEX_BLEND}"
            ),
        },
    )


def copy_strength_book(
    teams: Mapping[str, TeamProjectionState],
) -> Dict[str, TeamProjectionState]:
    return {k: v.copy() for k, v in teams.items()}


def expected_team_points(
    offense: TeamProjectionState,
    opponent_defense: TeamProjectionState,
    *,
    home: bool,
    neutral_site: bool = False,
    week: int = 5,
) -> float:
    response = P.matchup_response_for_week(week)
    ratio = offense.offense_index / max(0.50, opponent_defense.defense_index)
    # Concave/convex response around 1.0
    matchup = ratio ** response
    base = P.LEAGUE_TEAM_PPG * matchup
    if neutral_site:
        base += P.NEUTRAL_SITE_HFA
    elif home:
        base += P.HOME_FIELD_POINTS
    return _clamp(base, *P.EXPECTED_POINTS_CLAMP)


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
    """Team-level projection for a matchup (foundation path)."""
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

    home_exp = expected_team_points(
        home, away, home=True, neutral_site=neutral_site, week=week
    )
    away_exp = expected_team_points(
        away, home, home=False, neutral_site=neutral_site, week=week
    )
    home_wp = win_prob_from_expected_scores(home_exp, away_exp, margin_sd=margin_sd)
    spread = round(away_exp - home_exp, 2)  # home spread (neg = favorite)

    game_id = f"{season or universe.season}_w{week}_{away_team}@{home_team}"
    notes = {
        "fidelity": "approximate",
        "method": "roster_strength+qb_situation compose + analytic matchup",
        "does_not_touch": "edge_board_markets_only_cfb",
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
        expected_home_score=round(home_exp, 2),
        expected_away_score=round(away_exp, 2),
        expected_total=round(home_exp + away_exp, 2),
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
    home_exp = expected_team_points(
        home, away, home=True, neutral_site=game.neutral_site, week=game.week
    )
    away_exp = expected_team_points(
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
            "+ qb_situation_index are primary drivers). Numeric indices and game "
            "probabilities are APPROXIMATE — not calibrated market-grade fair lines."
        ),
        "feeds": [
            "roster_construction.roster_strength",
            "qb_situation.qb_situation_index",
            "position_groups",
            "priors.early_season_uncertainty",
        ],
        "primary_drivers": {
            "offense": ["roster_strength", "qb_situation_index"],
            "defense": ["roster_strength", "front_seven", "secondary"],
        },
    }
