"""Layer 4 — Production (usage + matchup + script → box score).

Turns Layer 3 usage into yards / TDs / receptions / INTs using each
player's efficiency priors from ``PlayerRole`` and a thin opponent
matchup multiplier from Layer 1 defense indices.

Efficiency CVs and default rates are centralized in ``calibration.py``.
INT modeling remains thin when roles lack baseline-derived INT rates.
"""

from __future__ import annotations

import math
import random
from typing import Dict, List, Mapping, Optional, Sequence

from src.services.nfl_season_engine.calibration import (
    CATCH_RATE_NOISE,
    EFFICIENCY_CV_PASS,
    EFFICIENCY_CV_REC,
    EFFICIENCY_CV_RUSH,
)
from src.services.nfl_season_engine.types import (
    GameScript,
    PlayerBoxScore,
    PlayerRole,
    PlayerUsage,
    TeamStrengthState,
)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _poisson(rng: random.Random, lam: float) -> int:
    if lam <= 0.0:
        return 0
    if lam > 30.0:
        return max(0, int(round(rng.gauss(lam, math.sqrt(lam)))))
    threshold = math.exp(-lam)
    k = 0
    p = 1.0
    while True:
        k += 1
        p *= rng.random()
        if p <= threshold:
            return k - 1


def _matchup_pass_mult(offense_team: str, defense_team: str, strengths: Mapping[str, TeamStrengthState]) -> float:
    opp_def = strengths.get(defense_team)
    if opp_def is None:
        return 1.0
    # Higher defense_index = better D → suppress opponent production.
    return _clamp(1.0 / max(0.72, opp_def.defense_index), 0.84, 1.18)


def _matchup_rush_mult(offense_team: str, defense_team: str, strengths: Mapping[str, TeamStrengthState]) -> float:
    opp_def = strengths.get(defense_team)
    if opp_def is None:
        return 1.0
    return _clamp(1.0 / max(0.72, opp_def.defense_index) * 0.99, 0.86, 1.16)


def _role_map(roles: Sequence[PlayerRole]) -> Dict[str, PlayerRole]:
    return {r.player_key: r for r in roles}


def produce_box_scores(
    *,
    usage_rows: Sequence[PlayerUsage],
    roles: Mapping[str, Sequence[PlayerRole]],
    script: GameScript,
    strengths: Mapping[str, TeamStrengthState],
    rng: Optional[random.Random] = None,
) -> List[PlayerBoxScore]:
    """Sample one coherent box-score replicate for every usage row."""
    rng = rng or random.Random()
    role_lookup: Dict[str, PlayerRole] = {}
    for team_roles in roles.values():
        role_lookup.update(_role_map(team_roles))

    out: List[PlayerBoxScore] = []
    for u in usage_rows:
        role = role_lookup.get(u.player_key)
        if role is None:
            continue
        opp = script.away_team if u.team == script.home_team else script.home_team
        pass_m = _matchup_pass_mult(u.team, opp, strengths)
        rush_m = _matchup_rush_mult(u.team, opp, strengths)

        # Script efficiency: trailing offenses throw a bit shorter; leading
        # rush attacks get slightly better YPC (clock-kill lanes).
        ypa = role.ypa * pass_m
        ypc = role.ypc * rush_m
        ypr = role.ypr * pass_m
        if u.script == "trail":
            ypa *= 0.97
            ypr *= 0.98
        elif u.script == "lead":
            ypc *= 1.025

        pass_yards = 0.0
        pass_tds = 0.0
        ints = 0.0
        if u.pass_attempts > 0.0:
            ypa_i = max(3.5, rng.gauss(ypa, abs(ypa) * EFFICIENCY_CV_PASS))
            pass_yards = u.pass_attempts * ypa_i
            pass_tds = float(_poisson(rng, u.pass_attempts * role.pass_td_rate))
            ints = float(_poisson(rng, u.pass_attempts * role.int_rate))

        rush_yards = 0.0
        rush_tds = 0.0
        if u.carries > 0.0:
            ypc_i = max(0.5, rng.gauss(ypc, abs(ypc) * EFFICIENCY_CV_RUSH + 0.22))
            rush_yards = u.carries * ypc_i
            rush_tds = float(_poisson(rng, u.carries * role.rush_td_rate))

        receptions = 0.0
        rec_yards = 0.0
        rec_tds = 0.0
        if u.targets > 0.0:
            catch = _clamp(rng.gauss(role.catch_rate, CATCH_RATE_NOISE), 0.28, 0.92)
            receptions = u.targets * catch
            ypr_i = max(2.0, rng.gauss(ypr, abs(ypr) * EFFICIENCY_CV_REC))
            rec_yards = receptions * ypr_i
            rec_tds = float(_poisson(rng, max(0.0, receptions) * role.rec_td_rate))

        out.append(
            PlayerBoxScore(
                player_key=u.player_key,
                player_name=u.player_name,
                team=u.team,
                position=u.position,
                pass_yards=round(pass_yards, 2),
                pass_tds=pass_tds,
                ints=ints,
                rush_yards=round(rush_yards, 2),
                rush_tds=rush_tds,
                rec_yards=round(rec_yards, 2),
                receptions=round(receptions, 2),
                rec_tds=rec_tds,
                pass_attempts=round(u.pass_attempts, 2),
                carries=round(u.carries, 2),
                targets=round(u.targets, 2),
            )
        )
    return out


def box_score_to_stat_dict(box: PlayerBoxScore) -> Dict[str, float]:
    """Flatten a box score into the position-relevant stat keys."""
    pos = box.position.upper()
    if pos == "QB":
        return {
            "pass_yards": box.pass_yards,
            "pass_tds": box.pass_tds,
            "ints": box.ints,
            "rush_yards": box.rush_yards,
        }
    if pos == "RB":
        return {
            "rush_yards": box.rush_yards,
            "rush_tds": box.rush_tds,
            "rec_yards": box.rec_yards,
            "receptions": box.receptions,
        }
    # WR / TE
    return {
        "rec_yards": box.rec_yards,
        "receptions": box.receptions,
        "rec_tds": box.rec_tds,
    }
