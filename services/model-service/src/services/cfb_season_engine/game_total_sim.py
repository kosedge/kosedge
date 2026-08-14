"""P3 — independent margin + total sim distributions (research only).

Closest existing approach: Gaussian margin around the strength-path mean
(``expected_team_points`` + HFA + coaching) with week-inflated σ, then Φ.
P3 keeps that **margin path** and adds a **separate total path** that does
not use spread, HFA, or ``home_exp + away_exp``.

    margin ~ N(strength_margin, σ_m)
    total  ~ N(pace × off_env × explosiveness, σ_t)
    home   = (total + margin) / 2
    away   = (total - margin) / 2

Weather is not applied. Key numbers are reported, not bet rules.
``used_in_spread`` stays false. Default N = 5,000 (15 is too thin).
"""

from __future__ import annotations

import math
import random
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

from src.services.cfb_season_engine import priors as P
from src.services.cfb_season_engine.fbs_universe import (
    fcs_or_unknown_label,
    is_official_fbs,
)
from src.services.cfb_season_engine.types import TeamProjectionState, dist_block

GAME_SIM_N_DEFAULT = 5000
GAME_SIM_N_MIN = 200
GAME_SIM_N_MAX = 25_000
USED_IN_SPREAD = False
WEATHER_STATUS = "not applied"

OPEN_QB_CLASSES = frozenset(
    {"open_competition", "true_freshman", "unknown", "portal"}
)
KEY_MARGINS = (3, 7, 10, 14)
KEY_TOTALS = (41.5, 44.5, 47.5, 51.5, 54.5, 58.5)

# Total-path environment (independent of the HFA score path).
TOTAL_SD_BASE = 13.6
TOTAL_ENV_EXPONENT = 0.55
MARGIN_SD_CLIP = (12.0, 26.0)
TOTAL_SD_CLIP = (10.0, 22.0)
OPEN_QB_MARGIN_ADD = 2.4
OPEN_QB_TOTAL_ADD = 1.8
FCS_MARGIN_ADD = 2.0
FCS_TOTAL_ADD = 1.4


def clamp_sim_n(n_sims: Optional[int]) -> int:
    if n_sims is None:
        return GAME_SIM_N_DEFAULT
    return max(GAME_SIM_N_MIN, min(GAME_SIM_N_MAX, int(n_sims)))


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def _qb_class(state: TeamProjectionState) -> str:
    qb = state.qb
    return str(qb.qb_class) if qb is not None else "unknown"


def _is_open_qb(state: TeamProjectionState) -> bool:
    return _qb_class(state) in OPEN_QB_CLASSES


def _explosiveness(state: TeamProjectionState) -> float:
    if state.efficiency is None:
        return 50.0
    return float(state.efficiency.explosiveness)


def _fcs_side(team: str) -> Tuple[bool, str]:
    if is_official_fbs(team, include_transition=True):
        return False, ""
    return True, fcs_or_unknown_label(team)


def total_path_mean(
    home: TeamProjectionState,
    away: TeamProjectionState,
    *,
    st_nudge: float = 0.0,
) -> Tuple[float, Dict[str, Any]]:
    """Fair total from pace × both-offense environment × explosiveness.

    Does **not** take spread, HFA, or strength-path expected scores.
    """
    league_total = 2.0 * float(P.LEAGUE_TEAM_PPG)
    home_ratio = home.offense_index / max(0.50, away.defense_index)
    away_ratio = away.offense_index / max(0.50, home.defense_index)
    off_env = 0.5 * (home_ratio + away_ratio)
    off_env = _clamp(off_env, 0.55, 1.85)
    pace = 0.5 * (home.pace_factor + away.pace_factor)
    pace = _clamp(pace, 0.85, 1.20)
    expl = 0.5 * (_explosiveness(home) + _explosiveness(away))
    expl_mult = _clamp(1.0 + (expl - 50.0) / 400.0, 0.92, 1.10)
    mean = league_total * pace * (off_env**TOTAL_ENV_EXPONENT) * expl_mult
    mean = _clamp(mean + float(st_nudge), 30.0, 90.0)
    diag = {
        "path": "pace_off_env_explosiveness",
        "not_spread_hack": True,
        "league_total": round(league_total, 3),
        "home_off_def_ratio": round(home_ratio, 4),
        "away_off_def_ratio": round(away_ratio, 4),
        "off_env": round(off_env, 4),
        "pace": round(pace, 4),
        "explosiveness": round(expl, 2),
        "explosiveness_mult": round(expl_mult, 4),
        "st_nudge": round(float(st_nudge), 3),
        "weather": WEATHER_STATUS,
    }
    return mean, diag


def research_sigmas(
    home: TeamProjectionState,
    away: TeamProjectionState,
    *,
    week: int,
    base_margin_sd: float,
) -> Dict[str, Any]:
    """Widen margin/total bands for early season, open QB, FCS, high identity σ."""
    early = P.early_season_uncertainty(week)
    team_u = 0.5 * (
        home.early_season_uncertainty + away.early_season_uncertainty
    )
    home_open = _is_open_qb(home)
    away_open = _is_open_qb(away)
    open_count = int(home_open) + int(away_open)
    home_fcs, home_fcs_label = _fcs_side(home.team)
    away_fcs, away_fcs_label = _fcs_side(away.team)
    fcs = home_fcs or away_fcs

    margin_sd = float(base_margin_sd) * (1.0 + 0.20 * team_u)
    margin_sd += OPEN_QB_MARGIN_ADD * open_count
    if fcs:
        margin_sd += FCS_MARGIN_ADD
    margin_sd = _clamp(margin_sd, *MARGIN_SD_CLIP)

    early_mult = 1.12 if early.get("active") else 1.0
    total_sd = TOTAL_SD_BASE * early_mult + 4.0 * team_u
    total_sd += OPEN_QB_TOTAL_ADD * open_count
    if fcs:
        total_sd += FCS_TOTAL_ADD
    total_sd = _clamp(total_sd, *TOTAL_SD_CLIP)

    return {
        "margin_sd": round(margin_sd, 3),
        "total_sd": round(total_sd, 3),
        "team_identity_uncertainty_blend": round(team_u, 4),
        "home_open_qb": home_open,
        "away_open_qb": away_open,
        "home_qb_class": _qb_class(home),
        "away_qb_class": _qb_class(away),
        "open_qb_count": open_count,
        "home_fcs": home_fcs,
        "away_fcs": away_fcs,
        "home_fcs_label": home_fcs_label,
        "away_fcs_label": away_fcs_label,
        "early_season": bool(early.get("active")),
        "week": int(week),
    }


def _percentiles(xs: Sequence[float]) -> Tuple[float, float, float, float, float]:
    ordered = sorted(float(x) for x in xs)
    n = len(ordered)
    if n == 0:
        return 0.0, 0.0, 0.0, 0.0, 0.0

    def _at(p: float) -> float:
        if n == 1:
            return ordered[0]
        idx = (n - 1) * p
        lo = int(math.floor(idx))
        hi = int(math.ceil(idx))
        if lo == hi:
            return ordered[lo]
        w = idx - lo
        return ordered[lo] * (1.0 - w) + ordered[hi] * w

    mean = sum(ordered) / n
    var = sum((x - mean) ** 2 for x in ordered) / n
    return mean, math.sqrt(var), _at(0.10), _at(0.50), _at(0.90)


def _cover_probs(margins: Sequence[float], totals: Sequence[float]) -> Dict[str, Any]:
    n = max(1, len(margins))
    home_covers: Dict[str, float] = {}
    for key in KEY_MARGINS:
        # Home line −key: home covers if margin > key.
        home_covers[str(key)] = round(sum(1 for m in margins if m > key) / n, 4)
    over: Dict[str, float] = {}
    for line in KEY_TOTALS:
        over[str(line)] = round(sum(1 for t in totals if t > line) / n, 4)
    return {
        "note": (
            "Reporting only — not an auto-bet rule. Home cover at k is "
            "P(home_margin > k) i.e. home −k."
        ),
        "home_cover_at": home_covers,
        "over_at": over,
    }


def simulate_game_distributions(
    home: TeamProjectionState,
    away: TeamProjectionState,
    *,
    margin_mean: float,
    total_mean: float,
    week: int,
    base_margin_sd: float,
    n_sims: Optional[int] = None,
    seed: Optional[int] = None,
    st_nudge: float = 0.0,
) -> Dict[str, Any]:
    """Draw independent margin + total Gaussians; recover team scores."""
    n = clamp_sim_n(n_sims)
    sig = research_sigmas(home, away, week=week, base_margin_sd=base_margin_sd)
    margin_sd = float(sig["margin_sd"])
    total_sd = float(sig["total_sd"])
    rng = random.Random(seed)

    home_scores = []
    away_scores = []
    margins = []
    totals = []
    for _ in range(n):
        margin = rng.gauss(margin_mean, margin_sd)
        total = max(20.0, rng.gauss(total_mean, total_sd))
        home_pts = max(0.0, 0.5 * (total + margin))
        away_pts = max(0.0, 0.5 * (total - margin))
        # Re-anchor total/margin to clipped scores so sums stay coherent.
        total = home_pts + away_pts
        margin = home_pts - away_pts
        home_scores.append(home_pts)
        away_scores.append(away_pts)
        margins.append(margin)
        totals.append(total)

    h_mean, h_sd, h_p10, h_p50, h_p90 = _percentiles(home_scores)
    a_mean, a_sd, a_p10, a_p50, a_p90 = _percentiles(away_scores)
    m_mean, m_sd, m_p10, m_p50, m_p90 = _percentiles(margins)
    t_mean, t_sd, t_p10, t_p50, t_p90 = _percentiles(totals)

    home_wins = sum(1 for h, a in zip(home_scores, away_scores) if h > a)
    ties = sum(1 for h, a in zip(home_scores, away_scores) if h == a)
    sim_wp = (home_wins + 0.5 * ties) / n
    over_fair = sum(1 for t in totals if t > t_mean) / n

    home_r = round(h_mean, 2)
    away_r = round(a_mean, 2)
    total_r = round(home_r + away_r, 2)
    spread_r = round(away_r - home_r, 2)

    return {
        "n_sims": n,
        "method": (
            "independent Gaussian margin (strength→margin + HFA) and "
            "Gaussian total (pace × off_env × explosiveness); "
            "scores = (total ± margin) / 2"
        ),
        "used_in_spread": USED_IN_SPREAD,
        "weather": WEATHER_STATUS,
        "fair_spread": spread_r,
        "fair_total": total_r,
        "team_total_home": home_r,
        "team_total_away": away_r,
        "sim_home_win_prob": round(_clamp(sim_wp, 0.02, 0.98), 4),
        "over_prob_at_fair": round(over_fair, 4),
        "margin": dist_block(m_mean, m_sd, m_p10, m_p50, m_p90),
        "total": dist_block(t_mean, t_sd, t_p10, t_p50, t_p90),
        "home_score": dist_block(h_mean, h_sd, h_p10, h_p50, h_p90),
        "away_score": dist_block(a_mean, a_sd, a_p10, a_p50, a_p90),
        "key_numbers": _cover_probs(margins, totals),
        "sigma": sig,
        "inputs": {
            "margin_mean": round(float(margin_mean), 3),
            "total_mean": round(float(total_mean), 3),
            "st_nudge": round(float(st_nudge), 3),
        },
    }


def documentation() -> Dict[str, Any]:
    return {
        "module": "src.services.cfb_season_engine.game_total_sim",
        "engine_layer": "v0.11-game-total-sim",
        "used_in_spread": USED_IN_SPREAD,
        "kei": False,
        "n_sims_default": GAME_SIM_N_DEFAULT,
        "n_sims_min": GAME_SIM_N_MIN,
        "n_sims_max": GAME_SIM_N_MAX,
        "margin_path": (
            "Gaussian around strength-path expected margin "
            "(unit matchup + variable HFA + coaching). Closest existing "
            "approach: WIN_PROB_MARGIN_SD + Φ."
        ),
        "total_path": (
            "Separate: league_total * pace * off_env^0.55 * explosiveness. "
            "Not total = f(spread) and not home_exp + away_exp."
        ),
        "weather": WEATHER_STATUS,
        "key_numbers": {
            "margins": list(KEY_MARGINS),
            "totals": list(KEY_TOTALS),
            "role": "reporting_only",
        },
        "season_futures": {
            "cfp_make": None,
            "natty": None,
            "status": "placeholder",
            "note": (
                "Densified approximate slate cannot emit honest CFP/natty. "
                "P4 stays stub until an official 2026 FBS schedule exists."
            ),
        },
    }
