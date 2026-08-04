"""Layer 4 — Production (usage + matchup + script → box score).

Turns Layer 3 usage into yards / TDs / receptions / INTs using each
player's efficiency priors from ``PlayerRole`` and a thin opponent
matchup multiplier from Layer 1 defense indices.

**Yards path:** general usage (attempts / carries / targets) × efficiency.

**TD path (v1.7):** primarily red-zone / scoring opportunities on
``PlayerUsage`` (I20/I10 carries & targets) × role finish rates from
``red_zone.py``, plus a small non-RZ residual of the legacy
``usage × td_rate`` poisson so explosive TDs are not zeroed. RZ volume
is **not** added into yards (no double count).

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
    USAGE_OTHER_BUCKET_FLOOR,
)
from src.services.nfl_season_engine.red_zone import (
    NON_RZ_TD_RESIDUAL,
    RZ_FINISH_PASS_I10,
    RZ_FINISH_PASS_I20,
    RZ_FINISH_REC_I10,
    RZ_FINISH_REC_I20,
    RZ_FINISH_RUSH_I10,
    RZ_FINISH_RUSH_I20,
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


def _rush_td_lambda(u: PlayerUsage, role: PlayerRole) -> float:
    """RZ opportunity × finish + small non-RZ residual."""
    c10 = max(0.0, float(getattr(u, "rz_carries_i10", 0.0) or 0.0))
    c20 = max(0.0, float(getattr(u, "rz_carries_i20", 0.0) or 0.0))
    c20_out = max(0.0, c20 - c10)
    rz_lam = c10 * RZ_FINISH_RUSH_I10 + c20_out * RZ_FINISH_RUSH_I20
    residual = max(0.0, u.carries) * role.rush_td_rate * NON_RZ_TD_RESIDUAL
    # If RZ fields were never attached, fall back to legacy rate.
    if c20 <= 1e-12 and c10 <= 1e-12 and u.carries > 0:
        return max(0.0, u.carries * role.rush_td_rate)
    return max(0.0, rz_lam + residual)


def _rec_td_lambda(u: PlayerUsage, role: PlayerRole, receptions: float) -> float:
    t10 = max(0.0, float(getattr(u, "rz_targets_i10", 0.0) or 0.0))
    t20 = max(0.0, float(getattr(u, "rz_targets_i20", 0.0) or 0.0))
    t20_out = max(0.0, t20 - t10)
    rz_lam = t10 * RZ_FINISH_REC_I10 + t20_out * RZ_FINISH_REC_I20
    residual = max(0.0, receptions) * role.rec_td_rate * NON_RZ_TD_RESIDUAL
    if t20 <= 1e-12 and t10 <= 1e-12 and receptions > 0:
        return max(0.0, receptions * role.rec_td_rate)
    return max(0.0, rz_lam + residual)


def _team_rz_pass_td_lambda(usage_rows: Sequence[PlayerUsage], team: str) -> float:
    """Expected team receiving TDs from RZ targets — feeds QB pass TD mean.

    Named skill cores leave a residual "other" RZ target bucket (same spirit
    as Layer 3). Inflate named finishes slightly so QB pass TDs are not
    starved on sparse demo/depth rosters; yards path is unchanged.
    """
    lam = 0.0
    for u in usage_rows:
        if u.team != team:
            continue
        if (u.position or "").upper() == "QB":
            continue
        t10 = max(0.0, float(getattr(u, "rz_targets_i10", 0.0) or 0.0))
        t20 = max(0.0, float(getattr(u, "rz_targets_i20", 0.0) or 0.0))
        t20_out = max(0.0, t20 - t10)
        lam += t10 * RZ_FINISH_REC_I10 + t20_out * RZ_FINISH_REC_I20
    # ~half the other-bucket floor is recoverable as unnamed RZ finishes.
    inflate = 1.0 / max(0.75, 1.0 - 0.55 * USAGE_OTHER_BUCKET_FLOOR)
    return max(0.0, lam * inflate)


def _pass_td_lambda(
    u: PlayerUsage,
    role: PlayerRole,
    *,
    team_rz_pass_lam: float,
    team_pass_attempts: float,
) -> float:
    """QB pass TDs from team RZ receiving opportunities (+ residual).

    Dual path (documented): yards from general attempts×YPA; pass TDs from
    team RZ target finishes allocated by this QB's share of team attempts,
    plus a small non-RZ residual of legacy attempts×pass_td_rate.
    """
    if u.pass_attempts <= 0.0:
        return 0.0
    att_share = u.pass_attempts / max(1.0, team_pass_attempts)
    rz_lam = team_rz_pass_lam * att_share
    # Mild cross-check with RZ pass-attempt finish rates when team RZ lam is thin.
    if team_rz_pass_lam <= 1e-9:
        rz_att = u.pass_attempts * 0.055
        rz_lam = rz_att * 0.36 * RZ_FINISH_PASS_I10 + rz_att * 0.64 * RZ_FINISH_PASS_I20
    residual = u.pass_attempts * role.pass_td_rate * NON_RZ_TD_RESIDUAL
    # Legacy fallback when no RZ annotation on the game.
    has_rz = any(
        float(getattr(row, "rz_targets_i20", 0.0) or 0.0) > 1e-9
        or float(getattr(row, "rz_carries_i20", 0.0) or 0.0) > 1e-9
        for row in (u,)
    )
    if not has_rz and team_rz_pass_lam <= 1e-9:
        return max(0.0, u.pass_attempts * role.pass_td_rate)
    return max(0.0, rz_lam + residual)


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

    teams = {u.team for u in usage_rows}
    team_rz_pass: Dict[str, float] = {
        t: _team_rz_pass_td_lambda(usage_rows, t) for t in teams
    }
    team_pass_att: Dict[str, float] = {
        t: sum(u.pass_attempts for u in usage_rows if u.team == t) for t in teams
    }

    out: List[PlayerBoxScore] = []
    for u in usage_rows:
        role = role_lookup.get(u.player_key)
        if role is None:
            continue
        opp = script.away_team if u.team == script.home_team else script.home_team
        pass_m = _matchup_pass_mult(u.team, opp, strengths)
        rush_m = _matchup_rush_mult(u.team, opp, strengths)

        # Thin script efficiency only — volume shifts already come from Layer 2/3
        # play-mix + SCRIPT_USAGE_MATRIX. Keep these mild and intensity-scaled
        # so we do not double-count script with opaque multipliers.
        ypa = role.ypa * pass_m
        ypc = role.ypc * rush_m
        ypr = role.ypr * pass_m
        inten = _clamp(float(getattr(u, "script_intensity", 0.55) or 0.55), 0.0, 1.0)
        late_boost = 1.15 if getattr(u, "time_bucket", "") == "late" else 1.0
        eff_scale = 0.55 + 0.45 * inten * late_boost
        if u.script == "trail":
            ypa *= 1.0 - 0.03 * eff_scale
            ypr *= 1.0 - 0.02 * eff_scale
        elif u.script == "lead":
            ypc *= 1.0 + 0.025 * eff_scale

        pass_yards = 0.0
        pass_tds = 0.0
        ints = 0.0
        if u.pass_attempts > 0.0:
            ypa_i = max(3.5, rng.gauss(ypa, abs(ypa) * EFFICIENCY_CV_PASS))
            pass_yards = u.pass_attempts * ypa_i
            pass_tds = float(
                _poisson(
                    rng,
                    _pass_td_lambda(
                        u,
                        role,
                        team_rz_pass_lam=team_rz_pass.get(u.team, 0.0),
                        team_pass_attempts=team_pass_att.get(u.team, 0.0),
                    ),
                )
            )
            ints = float(_poisson(rng, u.pass_attempts * role.int_rate))

        rush_yards = 0.0
        rush_tds = 0.0
        if u.carries > 0.0 or float(getattr(u, "rz_carries_i20", 0.0) or 0.0) > 0.0:
            if u.carries > 0.0:
                ypc_i = max(0.5, rng.gauss(ypc, abs(ypc) * EFFICIENCY_CV_RUSH + 0.22))
                rush_yards = u.carries * ypc_i
            rush_tds = float(_poisson(rng, _rush_td_lambda(u, role)))

        receptions = 0.0
        rec_yards = 0.0
        rec_tds = 0.0
        if u.targets > 0.0 or float(getattr(u, "rz_targets_i20", 0.0) or 0.0) > 0.0:
            if u.targets > 0.0:
                catch = _clamp(rng.gauss(role.catch_rate, CATCH_RATE_NOISE), 0.28, 0.92)
                receptions = u.targets * catch
                ypr_i = max(2.0, rng.gauss(ypr, abs(ypr) * EFFICIENCY_CV_REC))
                rec_yards = receptions * ypr_i
            rec_tds = float(_poisson(rng, _rec_td_lambda(u, role, receptions)))

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
