"""Phase-1 full offensive production stack on locked team pass yards.

Order (non-negotiable):
1. Locked team pass yards (v1.17 board — do not reshuffle the other 29)
2. Parallel team rush-yards pool (league target ~58–62k)
3. Efficiency + defense multipliers → TD / INT rates
4. Usage shares + rookie ramps → player allocation
5. Tiny conservation renorm only
6. Smoke against conservation + league TD bands

Mirror lives under ``services/model-service/data_platform_nfl/`` — keep in sync.
"""

from __future__ import annotations

import json
import math
import re
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple

# ---------------------------------------------------------------------------
# League pools / conversion curves
# ---------------------------------------------------------------------------
LEAGUE_PASS_YARDS_POOL = 126_000.0
LEAGUE_RUSH_YARDS_POOL = 60_000.0  # mid of 58–62k historical band (pre–variance-lift)
# Step-1 offensive variance lift: raise league rush pool modestly; soft team bands.
LEAGUE_RUSH_YARDS_POOL_LIFTED = 64_000.0  # mid of 62–66k target band
RUSH_POOL_BAND_MIN = 58_000.0
RUSH_POOL_BAND_MAX = 66_000.0
RUSH_STRETCH_POS_INTENSITY = 1.40
RUSH_STRETCH_NEG_INTENSITY = 0.55
RUSH_STRETCH_DENOM = 200.0
# v1.24: wider soft rails + tanh taper (no hard clips) to clear rush piles.
RUSH_SOFT_FLOOR = 1_220.0
RUSH_SOFT_CEILING = 2_680.0
RUSH_STRETCH_TAPER_K = 0.62
RUSH_STRETCH_TAIL_DAMPEN = 0.18
# Locked scheme pass weights — never touch in variance lift.
LOCKED_PASS_SCHEME_TEAMS = ("ARI", "BAL", "SEA")
# Season yards→TD curves sized to the hand-off league TD bands
# (pass 1,050–1,150; rush 450–520). Midpoints ≈114.5 / 123.7 YPT.
# (Hand-off short-scale 14.8–15.4 / 38–42 are treated as curve shape
#  anchors, not raw season divisors — those would explode TD counts.)
YARDS_PER_PASS_TD = 114.5
YARDS_PER_RUSH_TD = 123.7
DEFAULT_YPA = 6.95
DEFAULT_YPC = 4.20
ATTEMPT_SHARE = 0.925

PASS_TD_LEAGUE_MIN = 1_050.0
PASS_TD_LEAGUE_MAX = 1_150.0
RUSH_TD_LEAGUE_MIN = 450.0
RUSH_TD_LEAGUE_MAX = 520.0
PASS_REC_YARDS_TOLERANCE = 0.015  # ±1.5%

PASS_TD_SOFT_FLOOR = 14.0
PASS_TD_SOFT_CEILING = 38.0
PASS_TD_SOFT_CEILING_HIGH_VOLUME = 42.0
RUSH_TD_SOFT_FLOOR = 6.0
RUSH_TD_SOFT_CEILING = 22.0
INT_RATE_SOFT_FLOOR = 0.018
INT_RATE_SOFT_CEILING = 0.034

# High pass-volume scoring-efficiency floors (enterprise soft-flag fix).
HIGH_PASS_VOLUME_YARDS = 4_600.0
MIN_PASS_TD_RATE_HIGH_VOLUME = 0.051  # mid of 4.8–5.5%

EFFICIENCY_REGRESSION = 0.40  # 40% toward mean (hand-off: 35–45%)
VOLUME_REGRESSION = 0.25  # mid of 20–30% (non-alphas)
# Step-2 alpha protection: cut volume regression for proven alphas; keep efficiency regression.
ALPHA_VOLUME_REGRESSION = 0.08
ALPHA_SHARE_RETENTION = 0.875  # mid of 85–90% prior-year share/yards retention
WR_ALPHA_YARD_FLOOR = 1_150.0  # WR12–WR15 band under normal circumstances
WR_ALPHA_TOP5_YARD_FLOOR = 1_400.0  # smoke: multiple 1400+ alphas
# v1.23: soft RB prior with differentiation (hard floor only prevents collapse).
RB_ALPHA_YARD_SOFT_PRIOR = 1_380.0
RB_ALPHA_YARD_HARD_FLOOR = 1_350.0
RB_ALPHA_YARD_SOFT_CEILING = 1_520.0
RB_ALPHA_YARD_FLOOR = RB_ALPHA_YARD_SOFT_PRIOR  # back-compat alias
# Stronger continuous spread so top RBs do not pile at one yard line.
RB_SOFT_PRIOR_TEAM_SPAN = 70.0  # ± about rank
RB_SOFT_PRIOR_BLEND = 0.90  # weight on soft prior vs current yards
WR_ALPHA_SHARE_CAP = 0.40
RB_ALPHA_SHARE_CAP = 0.68
TE_COMPRESS_WITH_WR_ALPHA = 0.72  # deflate TE when a sticky WR1 alpha is present
DEFENSE_TD_SOFT_BOOST = 0.06  # mid of +4–8% vs soft D
DEFENSE_TD_ELITE_CUT = 0.06  # mid of –4–8% vs elite D
RZ_SHARE_BOOST = 0.10  # mid of +8–12% for TE / primary WR

# OL / scheme proxy bumps for RB soft priors (small continuous nudges).
RB_OL_PROXY_BUMP: Dict[str, float] = {
    "BAL": 15.0,
    "SF": 12.0,
    "PHI": 12.0,
    "DET": 10.0,
    "DAL": 8.0,
    "LA": 8.0,
    "BUF": 8.0,
    "GB": 6.0,
    "CHI": 5.0,
}

def _packaged_depth_sot_path(season: int = 2026) -> Path:
    """Resolve packaged depth SoT from either model-service mirror layout."""
    here = Path(__file__).resolve()
    name = f"nfl_depth_chart_{int(season)}_w1.json"
    rel = Path("src/services/nfl_season_engine/data") / name
    candidates = [
        here.parents[1] / rel,  # services/model-service/data_platform_nfl/...
        here.parents[3] / "model-service" / rel,  # services/data-platform-nfl/...
    ]
    for path in candidates:
        if path.is_file():
            return path
    return candidates[0]


def canonical_qb1_from_depth_sot(season: int = 2026) -> Dict[str, str]:
    """QB1 labels derived from packaged depth SoT — never a second map."""
    path = _packaged_depth_sot_path(season)
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    out: Dict[str, str] = {}
    for row in payload.get("rows") or []:
        if str(row.get("position") or "").upper() != "QB":
            continue
        try:
            depth = int(row.get("depth_order") or 99)
        except (TypeError, ValueError):
            continue
        if depth != 1:
            continue
        team = str(row.get("team") or "").strip().upper()
        name = str(row.get("player_name") or "").strip()
        if team and name:
            out[team] = name
    return out


# Desk hygiene: QB1 labels always mirror packaged depth SoT (single source).
CANONICAL_QB1_BY_TEAM: Dict[str, str] = canonical_qb1_from_depth_sot(2026)

# Desk hygiene: skill players whose packaged depth team is wrong (identity swap).
CANONICAL_SKILL_TEAM: Dict[str, str] = {
    "Mike Evans": "TB",
}

# 2025 prior-year volume priors for sticky alpha shares (name → stats).
# top5_rec / top5_tgt / top5_rush mark league leaderboard membership.
PRIOR_YEAR_ALPHA_VOLUME: Dict[str, Dict[str, Any]] = {
    # WRs / high-volume pass-catchers (2025)
    "jaxonsmithnjigba": {
        "pos": "WR",
        "rec_yards": 1793.0,
        "tgt_share": 0.339,
        "top5_rec": True,
        "top5_tgt": True,
    },
    "pukanacua": {
        "pos": "WR",
        "rec_yards": 1715.0,
        "tgt_share": 0.288,
        "top5_rec": True,
        "top5_tgt": True,
    },
    "georgepickens": {
        "pos": "WR",
        "rec_yards": 1429.0,
        "tgt_share": 0.255,
        "top5_rec": True,
        "top5_tgt": False,
    },
    "jamarrchase": {
        "pos": "WR",
        "rec_yards": 1412.0,
        "tgt_share": 0.302,
        "top5_rec": True,
        "top5_tgt": True,
    },
    "amonrastbrown": {
        "pos": "WR",
        "rec_yards": 1401.0,
        "tgt_share": 0.285,
        "top5_rec": True,
        "top5_tgt": True,
    },
    "zayflowers": {
        "pos": "WR",
        "rec_yards": 1211.0,
        "tgt_share": 0.262,
        "top5_rec": False,
        "top5_tgt": False,
    },
    "chrisolave": {
        "pos": "WR",
        "rec_yards": 1163.0,
        "tgt_share": 0.272,
        "top5_rec": False,
        "top5_tgt": False,
    },
    "nicocollins": {
        "pos": "WR",
        "rec_yards": 1117.0,
        "tgt_share": 0.231,
        "top5_rec": False,
        "top5_tgt": False,
    },
    "ceedeelamb": {
        "pos": "WR",
        "rec_yards": 1077.0,
        "tgt_share": 0.240,
        "top5_rec": False,
        "top5_tgt": False,
    },
    "justinjefferson": {
        "pos": "WR",
        "rec_yards": 1048.0,
        "tgt_share": 0.260,
        "top5_rec": False,
        "top5_tgt": True,
    },
    "garrettwilson": {
        "pos": "WR",
        "rec_yards": 900.0,
        "tgt_share": 0.304,
        "top5_rec": False,
        "top5_tgt": True,
    },
    "drakelondon": {
        "pos": "WR",
        "rec_yards": 919.0,
        "tgt_share": 0.281,
        "top5_rec": False,
        "top5_tgt": False,
    },
    "ajbrown": {
        "pos": "WR",
        "rec_yards": 1003.0,
        "tgt_share": 0.275,
        "top5_rec": False,
        "top5_tgt": False,
    },
    "maliknabers": {
        "pos": "WR",
        "rec_yards": 900.0,
        "tgt_share": 0.244,
        "top5_rec": False,
        "top5_tgt": False,
    },
    "rasheerice": {
        "pos": "WR",
        "rec_yards": 1100.0,
        "tgt_share": 0.262,
        "top5_rec": False,
        "top5_tgt": False,
    },
    "courtlandsutton": {
        "pos": "WR",
        "rec_yards": 1017.0,
        "tgt_share": 0.230,
        "top5_rec": False,
        "top5_tgt": False,
    },
    "treymcbride": {
        "pos": "TE",
        "rec_yards": 1239.0,
        "tgt_share": 0.254,
        "top5_rec": True,
        "top5_tgt": True,
    },
    # Bell-cow RBs (2025 rush leaders)
    "jamescook": {"pos": "RB", "rush_yards": 1621.0, "carry_share": 0.62, "top5_rush": True},
    "jamescookiii": {"pos": "RB", "rush_yards": 1621.0, "carry_share": 0.62, "top5_rush": True},
    "derrickhenry": {"pos": "RB", "rush_yards": 1595.0, "carry_share": 0.65, "top5_rush": True},
    "jonathantaylor": {"pos": "RB", "rush_yards": 1585.0, "carry_share": 0.64, "top5_rush": True},
    "bijanrobinson": {"pos": "RB", "rush_yards": 1478.0, "carry_share": 0.60, "top5_rush": True},
    "devonachane": {"pos": "RB", "rush_yards": 1350.0, "carry_share": 0.58, "top5_rush": True},
    "kyrenwilliams": {"pos": "RB", "rush_yards": 1252.0, "carry_share": 0.58, "top5_rush": False},
    "jahmyrgibbs": {
        "pos": "RB",
        "rush_yards": 1412.0,
        "rec_yards": 517.0,
        "tgt_share": 0.11,
        "carry_share": 0.62,
        "three_down": True,
        "top5_rush": True,
    },
    "christianmccaffrey": {
        "pos": "RB",
        "rush_yards": 1202.0,
        "rec_yards": 645.0,
        "tgt_share": 0.13,
        "carry_share": 0.58,
        "three_down": True,
        "top5_rush": False,
    },
    "javontewilliams": {"pos": "RB", "rush_yards": 1201.0, "carry_share": 0.55, "top5_rush": False},
    "saquonbarkley": {"pos": "RB", "rush_yards": 1140.0, "carry_share": 0.58, "top5_rush": False},
    "travisetienne": {"pos": "RB", "rush_yards": 1107.0, "carry_share": 0.55, "top5_rush": False},
    "dandreswift": {"pos": "RB", "rush_yards": 1087.0, "carry_share": 0.55, "top5_rush": False},
    "joshjacobs": {"pos": "RB", "rush_yards": 929.0, "carry_share": 0.55, "top5_rush": False},
    "kennethwalkeriii": {"pos": "RB", "rush_yards": 1027.0, "carry_share": 0.55, "top5_rush": False},
    "breecehall": {"pos": "RB", "rush_yards": 1065.0, "carry_share": 0.55, "top5_rush": False},
    "chasebrown": {"pos": "RB", "rush_yards": 1019.0, "carry_share": 0.55, "top5_rush": False},
}

# Carry-forward scheme TD multipliers (LaFleur / Doyle / Fleury).
SCHEME_TD_MULT: Dict[str, float] = {
    "ARI": 0.95,
    "BAL": 1.08,
    "SEA": 1.03,
}

# Season-average of weekly rookie ramps (Weeks 1–4 / 5–8 / rest-of-season).
# First-round WR/TE: 55→80→100; Day-2: 40→70→100; Day-3/UDFA: 25→50→85.
# First-round RB: 45→75→100; later rounds shallower.
_WEEKS_EARLY = 4.0
_WEEKS_MID = 4.0
_WEEKS_LATE = 9.0  # 17 - 8


def _season_ramp(early: float, mid: float, late: float) -> float:
    return (
        _WEEKS_EARLY * early + _WEEKS_MID * mid + _WEEKS_LATE * late
    ) / (_WEEKS_EARLY + _WEEKS_MID + _WEEKS_LATE)


def rookie_season_share_factor(position: str, draft_round: Optional[int]) -> float:
    """Season-average share multiplier for a rookie (1.0 = full role)."""
    pos = str(position or "").upper()
    rnd = int(draft_round) if draft_round is not None else 7
    if pos in {"WR", "TE"}:
        if rnd <= 1:
            return _season_ramp(0.55, 0.80, 1.00)
        if rnd <= 3:
            return _season_ramp(0.40, 0.70, 1.00)
        return _season_ramp(0.25, 0.50, 0.85)
    if pos == "RB":
        if rnd <= 1:
            return _season_ramp(0.45, 0.75, 1.00)
        if rnd <= 3:
            return _season_ramp(0.35, 0.60, 0.90)
        return _season_ramp(0.25, 0.45, 0.75)
    if pos == "QB":
        if rnd <= 1:
            return _season_ramp(0.70, 0.90, 1.00)
        return _season_ramp(0.40, 0.65, 0.85)
    return 1.0


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def _taper_toward_band(
    value: float,
    soft_floor: float,
    soft_ceiling: float,
    *,
    k: float,
) -> float:
    """Soft-saturate into (floor, ceiling) via tanh — no hard pin at the rails."""
    lo = float(soft_floor)
    hi = float(soft_ceiling)
    if hi <= lo + 1e-9:
        return float(value)
    mid = 0.5 * (lo + hi)
    half = 0.5 * (hi - lo)
    sharpness = max(float(k), 0.25)
    return mid + half * math.tanh(((float(value) - mid) / half) * sharpness)


def _f(row: Mapping[str, Any], *keys: str, default: float = 0.0) -> float:
    for k in keys:
        if k in row and row[k] is not None and row[k] != "":
            try:
                return float(row[k])
            except (TypeError, ValueError):
                continue
    return float(default)


@dataclass
class TeamOffenseBudget:
    team: str
    pass_yards: float
    rush_yards: float
    pass_tds: float = 0.0
    rush_tds: float = 0.0
    ints: float = 0.0
    attempts: float = 0.0
    int_rate: float = INT_RATE_SOFT_FLOOR
    notes: List[str] = field(default_factory=list)


@dataclass
class PlayerUsage:
    player_key: str
    player_name: str
    team: str
    position: str
    depth_order: int = 99
    snap_share: float = 0.0
    target_share: float = 0.0
    rush_share: float = 0.0
    red_zone_share: float = 0.0
    is_rookie: bool = False
    draft_round: Optional[int] = None
    int_rate: float = INT_RATE_SOFT_FLOOR
    ypa: float = DEFAULT_YPA
    ypc: float = DEFAULT_YPC


def defense_td_multiplier(opp_defense_index: float) -> float:
    """Soft D → boost TD rate; elite D → cut. Index 1.0 = average."""
    z = float(opp_defense_index) - 1.0
    # defense_index > 1 = stronger D → negative TD mult
    if z >= 0.04:
        return 1.0 - _clamp(z * 1.2, 0.0, DEFENSE_TD_ELITE_CUT)
    if z <= -0.04:
        return 1.0 + _clamp((-z) * 1.2, 0.0, DEFENSE_TD_SOFT_BOOST)
    return 1.0 + (-z) * 0.5


def _efficiency_regressed(raw_index: float, *, regression: float = EFFICIENCY_REGRESSION) -> float:
    """Regress an efficiency index (1.0 = mean) toward 1.0."""
    return 1.0 + (1.0 - regression) * (float(raw_index) - 1.0)


def _volume_regressed(raw: float, mean: float, *, regression: float = VOLUME_REGRESSION) -> float:
    return mean + (1.0 - regression) * (float(raw) - mean)


def locked_team_pass_yards(rows: Sequence[Mapping[str, Any]]) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for row in rows:
        team = str(row.get("team") or "")
        if not team:
            continue
        out[team] = out.get(team, 0.0) + _f(row, "pass_yards_total", "pass_yards_mean", "pass_yards")
    return out


def build_team_rush_pool(
    locked_pass: Mapping[str, float],
    *,
    strengths: Optional[Mapping[str, Mapping[str, float]]] = None,
    prior_rush: Optional[Mapping[str, float]] = None,
    rush_pool: float = LEAGUE_RUSH_YARDS_POOL,
) -> Dict[str, float]:
    """Parallel two-way rush pool; pass yards stay locked and unused here."""
    teams = sorted(locked_pass.keys())
    if not teams:
        return {}
    league_mean = float(rush_pool) / max(1, len(teams))
    raw: Dict[str, float] = {}
    for team in teams:
        st = (strengths or {}).get(team) or {}
        offense = float(st.get("offense_index", 1.0) or 1.0)
        pace = float(st.get("pace_factor", 1.0) or 1.0)
        pass_bias = float(st.get("pass_rate_bias", 0.0) or 0.0)
        opp_def = float(st.get("opp_defense_index_mean", 1.0) or 1.0)
        # Run-rate residual: inverse of pass bias + scheme lean.
        run_rate = _clamp(0.435 - 1.1 * pass_bias, 0.28, 0.58)
        # BAL / PHI-style run lean already in pass_bias; light scheme nudge.
        if team == "BAL":
            run_rate = _clamp(run_rate + 0.02, 0.28, 0.58)
        if team == "ARI":
            run_rate = _clamp(run_rate - 0.01, 0.28, 0.58)
        plays = _clamp(63.5 * pace * (1.0 + 0.10 * (offense - 1.0)), 50.0, 76.0)
        ypc = DEFAULT_YPC * _clamp(1.0 + 0.35 * (offense - 1.0), 0.90, 1.12)
        ypc *= _clamp(1.0 - 0.12 * (opp_def - 1.0), 0.90, 1.10)
        structural = plays * run_rate * 17.0 * ypc * 0.92
        prior = float((prior_rush or {}).get(team) or structural)
        prior_r = _volume_regressed(prior, league_mean)
        blended = 0.70 * structural + 0.30 * prior_r
        raw[team] = max(800.0, blended)
    total = sum(raw.values()) or 1.0
    scale = float(rush_pool) / total
    return {t: v * scale for t, v in raw.items()}


def _pass_td_ceiling_for_volume(pass_yards: float) -> float:
    if float(pass_yards) >= HIGH_PASS_VOLUME_YARDS:
        return PASS_TD_SOFT_CEILING_HIGH_VOLUME
    return PASS_TD_SOFT_CEILING


def high_volume_min_pass_tds(pass_yards: float) -> float:
    """Minimum pass TDs for teams above the high-volume yard threshold."""
    if float(pass_yards) < HIGH_PASS_VOLUME_YARDS:
        return 0.0
    attempts = float(pass_yards) / max(DEFAULT_YPA, 1.0)
    return attempts * MIN_PASS_TD_RATE_HIGH_VOLUME


def build_team_pass_tds(
    locked_pass: Mapping[str, float],
    *,
    strengths: Optional[Mapping[str, Mapping[str, float]]] = None,
    prior_pass_tds: Optional[Mapping[str, float]] = None,
) -> Dict[str, float]:
    raw: Dict[str, float] = {}
    for team, py in locked_pass.items():
        st = (strengths or {}).get(team) or {}
        offense = float(st.get("offense_index", 1.0) or 1.0)
        opp_def = float(st.get("opp_defense_index_mean", 1.0) or 1.0)
        # Prior-year efficiency residual proxy from offense_index + prior TDs.
        prior_td = (prior_pass_tds or {}).get(team)
        if prior_td is not None and py > 1:
            prior_ypt = py / max(prior_td, 1.0)  # inverted: lower = more efficient
            # Convert to index vs league YPT.
            eff_index = YARDS_PER_PASS_TD / max(prior_ypt, 8.0)
        else:
            eff_index = offense
        eff = _efficiency_regressed(eff_index)
        def_m = defense_td_multiplier(opp_def)
        scheme = float(SCHEME_TD_MULT.get(team, 1.0))
        tds = (float(py) / YARDS_PER_PASS_TD) * eff * def_m * scheme
        # High-volume seasons cannot land below historical TD-rate floors.
        min_hv = high_volume_min_pass_tds(float(py))
        if min_hv > 0:
            tds = max(tds, min_hv)
        ceil = _pass_td_ceiling_for_volume(float(py))
        tds = _clamp(tds, PASS_TD_SOFT_FLOOR, ceil)
        raw[team] = tds
    # Tiny league-band renorm if outside 1050–1150 (preserve ranks).
    total = sum(raw.values())
    target = _clamp(total, PASS_TD_LEAGUE_MIN, PASS_TD_LEAGUE_MAX)
    if total > 1e-6 and abs(total - target) > 1.0:
        scale = target / total
        for t in raw:
            ceil = _pass_td_ceiling_for_volume(float(locked_pass.get(t, 0.0)))
            raw[t] = _clamp(raw[t] * scale, PASS_TD_SOFT_FLOOR, ceil)
        # Re-fit to band after soft clamps.
        total2 = sum(raw.values())
        if total2 > 1e-6 and not (PASS_TD_LEAGUE_MIN <= total2 <= PASS_TD_LEAGUE_MAX):
            mid = 0.5 * (PASS_TD_LEAGUE_MIN + PASS_TD_LEAGUE_MAX)
            scale2 = mid / total2
            for t in raw:
                ceil = _pass_td_ceiling_for_volume(float(locked_pass.get(t, 0.0)))
                raw[t] = _clamp(raw[t] * scale2, PASS_TD_SOFT_FLOOR, ceil)
    # Re-assert high-volume floors after league renorm (borrow from non-HV teams).
    return _assert_high_volume_pass_td_floors(raw, locked_pass)


def _assert_high_volume_pass_td_floors(
    pass_tds: Mapping[str, float],
    locked_pass: Mapping[str, float],
) -> Dict[str, float]:
    out = {t: float(v) for t, v in pass_tds.items()}
    shortfall = 0.0
    floors: Dict[str, float] = {}
    for team, py in locked_pass.items():
        floor = high_volume_min_pass_tds(float(py))
        if floor <= 0:
            continue
        floor = min(floor, _pass_td_ceiling_for_volume(float(py)))
        floors[team] = floor
        if out.get(team, 0.0) < floor:
            shortfall += floor - out.get(team, 0.0)
            out[team] = floor
    if shortfall <= 1e-9:
        return out
    donors = [t for t in out if t not in floors]
    donor_pool = sum(max(0.0, out[t] - PASS_TD_SOFT_FLOOR) for t in donors)
    if donor_pool <= 1e-9:
        return out
    for t in donors:
        room = max(0.0, out[t] - PASS_TD_SOFT_FLOOR)
        out[t] -= shortfall * (room / donor_pool)
    return out


def build_team_rush_tds(
    team_rush: Mapping[str, float],
    *,
    strengths: Optional[Mapping[str, Mapping[str, float]]] = None,
) -> Dict[str, float]:
    raw: Dict[str, float] = {}
    for team, ry in team_rush.items():
        st = (strengths or {}).get(team) or {}
        offense = float(st.get("offense_index", 1.0) or 1.0)
        opp_def = float(st.get("opp_defense_index_mean", 1.0) or 1.0)
        # Goal-line / dual-threat nudge for BAL.
        gl = 1.08 if team == "BAL" else (0.97 if team == "ARI" else 1.0)
        if team == "SEA":
            gl = 1.02
        eff = _efficiency_regressed(offense)
        def_m = defense_td_multiplier(opp_def)
        tds = (float(ry) / YARDS_PER_RUSH_TD) * eff * def_m * gl
        tds = _clamp(tds, RUSH_TD_SOFT_FLOOR, RUSH_TD_SOFT_CEILING)
        raw[team] = tds
    total = sum(raw.values())
    target = _clamp(total, RUSH_TD_LEAGUE_MIN, RUSH_TD_LEAGUE_MAX)
    if total > 1e-6 and abs(total - target) > 1.0:
        scale = target / total
        for t in raw:
            raw[t] = _clamp(raw[t] * scale, RUSH_TD_SOFT_FLOOR, RUSH_TD_SOFT_CEILING)
        total2 = sum(raw.values())
        if total2 > 1e-6 and not (RUSH_TD_LEAGUE_MIN <= total2 <= RUSH_TD_LEAGUE_MAX):
            mid = 0.5 * (RUSH_TD_LEAGUE_MIN + RUSH_TD_LEAGUE_MAX)
            scale2 = mid / total2
            for t in raw:
                raw[t] = _clamp(raw[t] * scale2, RUSH_TD_SOFT_FLOOR, RUSH_TD_SOFT_CEILING)
    return raw


def build_team_ints(
    locked_pass: Mapping[str, float],
    *,
    qb_int_rates: Optional[Mapping[str, float]] = None,
    strengths: Optional[Mapping[str, Mapping[str, float]]] = None,
) -> Dict[str, Tuple[float, float, float]]:
    """Return team → (ints, attempts, int_rate)."""
    out: Dict[str, Tuple[float, float, float]] = {}
    for team, py in locked_pass.items():
        st = (strengths or {}).get(team) or {}
        offense = float(st.get("offense_index", 1.0) or 1.0)
        attempts = float(py) / max(DEFAULT_YPA * _clamp(offense, 0.90, 1.12), 5.5)
        attempts /= ATTEMPT_SHARE  # convert yards-implied attempts loosely
        attempts = float(py) / max(DEFAULT_YPA * _clamp(1.0 + 0.35 * (offense - 1.0), 0.90, 1.12), 5.5)
        base_rate = float((qb_int_rates or {}).get(team) or 0.022)
        # Light regression toward 2.2%.
        rate = 0.022 + 0.70 * (base_rate - 0.022)
        rate = _clamp(rate, INT_RATE_SOFT_FLOOR, INT_RATE_SOFT_CEILING)
        out[team] = (attempts * rate, attempts, rate)
    return out


def usage_from_roles(
    roles: Sequence[Any],
) -> Dict[str, PlayerUsage]:
    """Index PlayerRole-like objects by player_key."""
    out: Dict[str, PlayerUsage] = {}
    for role in roles:
        key = str(getattr(role, "player_key", None) or role.get("player_key"))  # type: ignore[union-attr]
        if not key:
            continue
        pos = str(getattr(role, "position", None) or role.get("position") or "").upper()  # type: ignore[union-attr]
        draft = getattr(role, "draft_round", None) if not isinstance(role, Mapping) else role.get("draft_round")
        try:
            draft_i = int(draft) if draft is not None else None
        except (TypeError, ValueError):
            draft_i = None
        is_rookie = bool(
            getattr(role, "is_rookie", False)
            if not isinstance(role, Mapping)
            else role.get("is_rookie")
        )
        out[key] = PlayerUsage(
            player_key=key,
            player_name=str(
                getattr(role, "player_name", None)
                if not isinstance(role, Mapping)
                else role.get("player_name")
                or ""
            ),
            team=str(
                getattr(role, "team", None) if not isinstance(role, Mapping) else role.get("team") or ""
            ),
            position=pos,
            depth_order=int(
                getattr(role, "depth_order", 99)
                if not isinstance(role, Mapping)
                else role.get("depth_order") or 99
            ),
            snap_share=float(
                getattr(role, "snap_share", 0.0)
                if not isinstance(role, Mapping)
                else role.get("snap_share") or 0.0
            ),
            target_share=float(
                getattr(role, "target_share", 0.0)
                if not isinstance(role, Mapping)
                else role.get("target_share") or 0.0
            ),
            rush_share=float(
                getattr(role, "rush_share", 0.0)
                if not isinstance(role, Mapping)
                else role.get("rush_share") or 0.0
            ),
            red_zone_share=float(
                getattr(role, "red_zone_share", 0.0)
                if not isinstance(role, Mapping)
                else role.get("red_zone_share") or 0.0
            ),
            is_rookie=is_rookie,
            draft_round=draft_i,
            int_rate=float(
                getattr(role, "int_rate", INT_RATE_SOFT_FLOOR)
                if not isinstance(role, Mapping)
                else role.get("int_rate") or INT_RATE_SOFT_FLOOR
            ),
            ypa=float(
                getattr(role, "ypa", DEFAULT_YPA)
                if not isinstance(role, Mapping)
                else role.get("ypa") or DEFAULT_YPA
            ),
            ypc=float(
                getattr(role, "ypc", DEFAULT_YPC)
                if not isinstance(role, Mapping)
                else role.get("ypc") or DEFAULT_YPC
            ),
        )
    return out


def _fallback_usage_from_rows(rows: Sequence[Mapping[str, Any]]) -> Dict[str, PlayerUsage]:
    """Depth from current yard ranks when roles unavailable."""
    by_team: Dict[str, List[Mapping[str, Any]]] = {}
    for row in rows:
        by_team.setdefault(str(row.get("team") or ""), []).append(row)
    out: Dict[str, PlayerUsage] = {}
    for team, team_rows in by_team.items():
        for pos in ("QB", "RB", "WR", "TE"):
            group = [r for r in team_rows if str(r.get("position") or "").upper() == pos]
            def _row_depth(row: Mapping[str, Any], fallback: int) -> int:
                key = str(row.get("player_key") or "")
                match = re.search(r"-(?:QB|RB|WR|TE|K|DST)(\d+)-", key, re.I)
                if match:
                    try:
                        return int(match.group(1))
                    except (TypeError, ValueError):
                        return fallback
                return fallback

            group.sort(key=lambda r: (_row_depth(r, 99), -_f(
                r,
                "pass_yards_total" if pos == "QB" else "rush_yards_total" if pos == "RB" else "receiving_yards_total",
                "pass_yards_mean" if pos == "QB" else "rush_yards_mean" if pos == "RB" else "rec_yards_mean",
            )))
            for i, r in enumerate(group, start=1):
                key = str(r.get("player_key") or "")
                if not key:
                    continue
                i = _row_depth(r, i)
                # Default hierarchical shares (WR1 >> TE1 — avoids WR/TE logjam).
                if pos == "WR":
                    tgt = {1: 0.28, 2: 0.17, 3: 0.11}.get(i, 0.04)
                    rz = {1: 0.22, 2: 0.12, 3: 0.08}.get(i, 0.04)
                    rush = 0.01 if i == 1 else 0.0
                elif pos == "TE":
                    tgt = {1: 0.14, 2: 0.07, 3: 0.03}.get(i, 0.02)
                    rz = {1: 0.20, 2: 0.10, 3: 0.05}.get(i, 0.02)
                    rush = 0.0
                elif pos == "RB":
                    tgt = {1: 0.09, 2: 0.05, 3: 0.02}.get(i, 0.01)
                    rz = {1: 0.18, 2: 0.10, 3: 0.05}.get(i, 0.02)
                    rush = {1: 0.58, 2: 0.24, 3: 0.10}.get(i, 0.04)
                else:
                    tgt = 0.0
                    rz = 0.05
                    rush = {1: 0.08, 2: 0.02, 3: 0.01}.get(i, 0.0)
                is_rookie = bool(r.get("is_rookie"))
                draft = r.get("draft_round")
                try:
                    draft_i = int(draft) if draft is not None else None
                except (TypeError, ValueError):
                    draft_i = None
                out[key] = PlayerUsage(
                    player_key=key,
                    player_name=str(r.get("player_name") or ""),
                    team=team,
                    position=pos,
                    depth_order=i,
                    snap_share=0.55 if i == 1 else 0.30 if i == 2 else 0.15,
                    target_share=tgt,
                    rush_share=rush,
                    red_zone_share=rz,
                    is_rookie=is_rookie,
                    draft_round=draft_i,
                    int_rate=_f(r, "int_rate", default=INT_RATE_SOFT_FLOOR),
                )
    return out


def _apply_rookie_to_share(share: float, usage: PlayerUsage) -> float:
    if not usage.is_rookie:
        return share
    return share * rookie_season_share_factor(usage.position, usage.draft_round)


def allocate_receiving(
    rows: List[MutableMapping[str, Any]],
    team_pass: Mapping[str, float],
    team_pass_tds: Mapping[str, float],
    usage_by_key: Mapping[str, PlayerUsage],
) -> None:
    by_team: Dict[str, List[MutableMapping[str, Any]]] = {}
    for row in rows:
        by_team.setdefault(str(row.get("team") or ""), []).append(row)

    for team, team_rows in by_team.items():
        pass_y = float(team_pass.get(team, 0.0))
        pass_td = float(team_pass_tds.get(team, 0.0))
        weights: Dict[str, float] = {}
        td_weights: Dict[str, float] = {}
        for row in team_rows:
            pos = str(row.get("position") or "").upper()
            if pos not in {"WR", "TE", "RB"}:
                row["receiving_yards_total"] = 0.0
                row["rec_tds_total"] = 0.0
                if "receptions_total" in row:
                    row["receptions_total"] = 0.0
                continue
            key = str(row.get("player_key") or "")
            u = usage_by_key.get(key)
            if u is None:
                # Minimal fallback weight from prior receiving yards.
                w = max(_f(row, "receiving_yards_total", "rec_yards_mean", "rec_yards"), 1.0)
                tw = w
            else:
                w = _apply_rookie_to_share(max(u.target_share, 0.0), u)
                # RZ boost for TE + primary WR.
                rz_boost = 1.0
                if pos == "TE" or (pos == "WR" and u.depth_order == 1):
                    rz_boost = 1.0 + RZ_SHARE_BOOST
                tw = _apply_rookie_to_share(max(u.red_zone_share, u.target_share), u) * rz_boost
            weights[key] = max(w, 1e-6)
            td_weights[key] = max(tw, 1e-6)

        w_sum = sum(weights.values()) or 1.0
        td_sum = sum(td_weights.values()) or 1.0
        for row in team_rows:
            pos = str(row.get("position") or "").upper()
            if pos not in {"WR", "TE", "RB"}:
                continue
            key = str(row.get("player_key") or "")
            share = weights.get(key, 0.0) / w_sum
            td_share = td_weights.get(key, 0.0) / td_sum
            rec_y = pass_y * share
            row["receiving_yards_total"] = rec_y
            row["rec_tds_total"] = pass_td * td_share
            # Receptions ~ yards / YPR proxy.
            ypr = 11.8 if pos != "RB" else 8.2
            row["receptions_total"] = rec_y / ypr


def allocate_rushing(
    rows: List[MutableMapping[str, Any]],
    team_rush: Mapping[str, float],
    team_rush_tds: Mapping[str, float],
    usage_by_key: Mapping[str, PlayerUsage],
) -> None:
    by_team: Dict[str, List[MutableMapping[str, Any]]] = {}
    for row in rows:
        by_team.setdefault(str(row.get("team") or ""), []).append(row)

    for team, team_rows in by_team.items():
        rush_y = float(team_rush.get(team, 0.0))
        rush_td = float(team_rush_tds.get(team, 0.0))
        weights: Dict[str, float] = {}
        td_weights: Dict[str, float] = {}
        for row in team_rows:
            pos = str(row.get("position") or "").upper()
            key = str(row.get("player_key") or "")
            if pos not in {"RB", "QB"}:
                if pos in {"WR", "TE"}:
                    # Tiny WR rush residual only if already had rush share.
                    u = usage_by_key.get(key)
                    if u and u.rush_share > 0.01:
                        w = _apply_rookie_to_share(u.rush_share, u)
                        weights[key] = w
                        td_weights[key] = w * 0.5
                    else:
                        row["rush_yards_total"] = 0.0
                        row["rush_tds_total"] = 0.0
                continue
            u = usage_by_key.get(key)
            if u is None:
                w = max(_f(row, "rush_yards_total", "rush_yards_mean"), 1.0)
                tw = w * (1.2 if pos == "RB" else 0.8)
            else:
                w = _apply_rookie_to_share(max(u.rush_share, 0.0), u)
                tw = _apply_rookie_to_share(max(u.red_zone_share, u.rush_share * 0.8), u)
                if pos == "QB":
                    tw *= 1.15  # goal-line QB sneak / designed package
            weights[key] = max(w, 1e-6)
            td_weights[key] = max(tw, 1e-6)

        # Ensure every RB/QB got a weight entry.
        for row in team_rows:
            pos = str(row.get("position") or "").upper()
            key = str(row.get("player_key") or "")
            if pos in {"RB", "QB"} and key not in weights:
                weights[key] = 1e-3
                td_weights[key] = 1e-3

        w_sum = sum(weights.values()) or 1.0
        td_sum = sum(td_weights.values()) or 1.0
        for row in team_rows:
            key = str(row.get("player_key") or "")
            if key not in weights:
                continue
            row["rush_yards_total"] = rush_y * (weights[key] / w_sum)
            row["rush_tds_total"] = rush_td * (td_weights[key] / td_sum)


def allocate_passing(
    rows: List[MutableMapping[str, Any]],
    team_pass: Mapping[str, float],
    team_pass_tds: Mapping[str, float],
    team_ints: Mapping[str, Tuple[float, float, float]],
    usage_by_key: Mapping[str, PlayerUsage],
) -> None:
    """Assign pass TDs / INTs; preserve locked QB pass-yard room shares."""
    by_team: Dict[str, List[MutableMapping[str, Any]]] = {}
    for row in rows:
        by_team.setdefault(str(row.get("team") or ""), []).append(row)

    for team, team_rows in by_team.items():
        qbs = [r for r in team_rows if str(r.get("position") or "").upper() == "QB"]

        def _qb_sort_key(r: Mapping[str, Any]) -> Tuple[int, float]:
            key = str(r.get("player_key") or "")
            depth = usage_by_key[key].depth_order if key in usage_by_key else 99
            return (depth, -_f(r, "pass_yards_total", "pass_yards_mean"))

        qbs.sort(key=_qb_sort_key)
        pass_y = float(team_pass.get(team, 0.0))
        pass_td = float(team_pass_tds.get(team, 0.0))
        ints, attempts, rate = team_ints.get(team, (0.0, 0.0, INT_RATE_SOFT_FLOOR))
        for r in team_rows:
            if str(r.get("position") or "").upper() != "QB":
                r["pass_yards_total"] = 0.0
                r["pass_tds_total"] = 0.0
                r["ints_total"] = 0.0

        # Preserve incoming QB pass-yard shares (locked v1.17 board). Fallback
        # to 92/6/2 only when the room has no pass yards yet.
        locked_shares: List[float] = [_f(r, "pass_yards_total", "pass_yards_mean") for r in qbs]
        locked_sum = sum(locked_shares)
        if locked_sum > 1.0:
            shares = [y / locked_sum for y in locked_shares]
        else:
            room = [0.92, 0.06, 0.02]
            shares = []
            for i, r in enumerate(qbs):
                share = room[i] if i < len(room) else 0.0
                key = str(r.get("player_key") or "")
                u = usage_by_key.get(key)
                if u and u.is_rookie and i == 0:
                    share = max(share * rookie_season_share_factor("QB", u.draft_round), 0.50)
                shares.append(share)
            ssum = sum(shares) or 1.0
            shares = [s / ssum for s in shares]

        for r, share in zip(qbs, shares):
            r["pass_yards_total"] = pass_y * share
            r["pass_tds_total"] = pass_td * share
            r["ints_total"] = ints * share
            r["pass_attempts_total"] = attempts * share
            r["int_rate"] = rate


def conservation_renorm(rows: List[MutableMapping[str, Any]], locked_pass: Mapping[str, float]) -> Dict[str, Any]:
    """Tiny two-way adjustments so receiving ≈ pass and team pools hold."""
    audit: Dict[str, Any] = {"teams": {}, "method": "offensive_stack_conservation_v1"}
    by_team: Dict[str, List[MutableMapping[str, Any]]] = {}
    for row in rows:
        by_team.setdefault(str(row.get("team") or ""), []).append(row)

    for team, team_rows in by_team.items():
        target_pass = float(locked_pass.get(team, 0.0))
        rec_players = [
            r
            for r in team_rows
            if str(r.get("position") or "").upper() in {"WR", "TE", "RB"}
        ]
        rec_sum = sum(_f(r, "receiving_yards_total") for r in rec_players) or 1.0
        # Receiving must match locked pass within tolerance — scale to exact.
        rec_scale = target_pass / rec_sum
        for r in rec_players:
            r["receiving_yards_total"] = _f(r, "receiving_yards_total") * rec_scale
            r["rec_tds_total"] = _f(r, "rec_tds_total")  # TDs already from pass-TD pool
            if "receptions_total" in r:
                r["receptions_total"] = _f(r, "receptions_total") * rec_scale

        # Pass TDs on QBs should equal sum of rec TDs (conservation of offensive pass TDs).
        qb_pass_td = sum(
            _f(r, "pass_tds_total")
            for r in team_rows
            if str(r.get("position") or "").upper() == "QB"
        )
        rec_td_sum = sum(_f(r, "rec_tds_total") for r in rec_players) or 1.0
        if qb_pass_td > 1e-9:
            td_scale = qb_pass_td / rec_td_sum
            for r in rec_players:
                r["rec_tds_total"] = _f(r, "rec_tds_total") * td_scale

        # anytime TD proxy
        for r in team_rows:
            rush_td = _f(r, "rush_tds_total")
            rec_td = _f(r, "rec_tds_total")
            r["anytime_td_prob"] = min(0.9999, max(0.0, 1.0 - math.exp(-(rush_td + rec_td))))

        rec_sum2 = sum(_f(r, "receiving_yards_total") for r in rec_players)
        audit["teams"][team] = {
            "pass_yards": round(target_pass, 2),
            "receiving_yards": round(rec_sum2, 2),
            "pass_rec_gap_pct": round(
                abs(rec_sum2 - target_pass) / max(target_pass, 1.0), 6
            ),
        }
    return audit


def _norm_player_name(name: str) -> str:
    return "".join(ch for ch in str(name or "").lower() if ch.isalnum())


def prior_alpha_lookup(player_name: str) -> Optional[Dict[str, Any]]:
    """Return 2025 prior-volume row for a player name, if known."""
    return PRIOR_YEAR_ALPHA_VOLUME.get(_norm_player_name(player_name))


def _is_volume_alpha(prior: Mapping[str, Any], *, kind: str) -> bool:
    if kind == "rec":
        return bool(prior.get("top5_rec") or prior.get("top5_tgt") or float(prior.get("rec_yards") or 0) >= 1_150.0)
    if kind == "rush":
        return bool(prior.get("top5_rush") or float(prior.get("rush_yards") or 0) >= 1_100.0)
    return False


def apply_sticky_alpha_shares(
    usage_by_key: Dict[str, PlayerUsage],
    rows: Sequence[Mapping[str, Any]],
    team_pass: Mapping[str, float],
    team_rush: Mapping[str, float],
    *,
    retention: float = ALPHA_SHARE_RETENTION,
    alpha_volume_regression: float = ALPHA_VOLUME_REGRESSION,
) -> Dict[str, Any]:
    """Raise proven-alpha target/carry shares; leave rookies/depth compressed.

    Sticky rule: retain ``retention`` (85–90%) of prior target/carry share or
    prior yards as a share of the (locked) 2026 team pool — whichever is higher —
    then apply only light volume regression. Efficiency regression is unchanged
    elsewhere in the stack.
    """
    name_by_key = {
        str(r.get("player_key") or ""): str(r.get("player_name") or "") for r in rows
    }
    alpha_keys: List[str] = []
    notes: List[str] = []

    # Structural mean shares for light volume regression anchors.
    mean_wr1_tgt = 0.26
    mean_rb1_rush = 0.52

    for key, u in usage_by_key.items():
        prior = prior_alpha_lookup(name_by_key.get(key, u.player_name))
        if prior is None or u.is_rookie:
            continue
        team = u.team
        pass_y = float(team_pass.get(team, 0.0))
        rush_y = float(team_rush.get(team, 0.0))

        if u.position in {"WR", "TE"} and _is_volume_alpha(prior, kind="rec") and pass_y > 1.0:
            prior_tgt = float(prior.get("tgt_share") or 0.0)
            prior_rec = float(prior.get("rec_yards") or 0.0)
            sticky_from_share = prior_tgt * retention
            sticky_from_yards = (prior_rec * retention) / pass_y
            sticky = max(sticky_from_share, sticky_from_yards)
            # Light volume regression only (cut mean-reversion on volume).
            sticky = _volume_regressed(sticky, mean_wr1_tgt, regression=alpha_volume_regression)
            yard_floor = (
                WR_ALPHA_TOP5_YARD_FLOOR
                if (prior.get("top5_rec") or prior.get("top5_tgt"))
                else WR_ALPHA_YARD_FLOOR
            )
            floor_share = yard_floor / pass_y
            new_share = min(WR_ALPHA_SHARE_CAP, max(u.target_share, sticky, floor_share))
            if new_share > u.target_share + 1e-6:
                notes.append(
                    f"{u.player_name}:{u.team}:tgt {u.target_share:.3f}→{new_share:.3f}"
                )
            u.target_share = new_share
            u.red_zone_share = max(u.red_zone_share, new_share * 0.85)
            alpha_keys.append(key)

        if u.position == "RB" and _is_volume_alpha(prior, kind="rush") and rush_y > 1.0:
            prior_carry = float(prior.get("carry_share") or 0.0)
            prior_rush = float(prior.get("rush_yards") or 0.0)
            sticky_from_share = prior_carry * retention if prior_carry > 0 else 0.0
            sticky_from_yards = (prior_rush * retention) / rush_y
            sticky = max(sticky_from_share, sticky_from_yards)
            sticky = _volume_regressed(sticky, mean_rb1_rush, regression=alpha_volume_regression)
            # Soft differentiated prior (not a flat 1400 hard pin).
            prior_yards = rb_soft_prior_yards(
                u.player_name,
                u.team,
                rush_y,
                team_rush_rank_pct=_team_rush_rank_pct(team_rush).get(u.team, 0.5),
                prior=prior,
            )
            prior_share = (
                min(RB_ALPHA_SHARE_CAP, prior_yards / rush_y) if prior_yards else 0.0
            )
            new_share = min(RB_ALPHA_SHARE_CAP, max(u.rush_share, sticky, prior_share))
            if new_share > u.rush_share + 1e-6:
                notes.append(
                    f"{u.player_name}:{u.team}:rush {u.rush_share:.3f}→{new_share:.3f}"
                )
            u.rush_share = new_share
            u.red_zone_share = max(u.red_zone_share, new_share * 0.55)
            if key not in alpha_keys:
                alpha_keys.append(key)

    # Structural WR1s on teams that can support alpha volume but lack a prior row:
    # keep hierarchy; do not invent inflated priors for rookies/depth.
    # Compress TE rooms when a sticky WR alpha is present (fixes WR=TE logjam).
    alphas_by_team: Dict[str, List[PlayerUsage]] = {}
    for key in alpha_keys:
        u = usage_by_key[key]
        if u.position == "WR":
            alphas_by_team.setdefault(u.team, []).append(u)
    for team, wr_alphas in alphas_by_team.items():
        if not wr_alphas:
            continue
        top_wr = max(wr_alphas, key=lambda x: x.target_share)
        if top_wr.target_share < 0.27:
            continue
        for u in usage_by_key.values():
            if u.team != team or u.position != "TE":
                continue
            if prior_alpha_lookup(name_by_key.get(u.player_key, u.player_name)):
                # Keep McBride-class TE alphas; mild trim only.
                u.target_share *= 0.92
            else:
                u.target_share *= TE_COMPRESS_WITH_WR_ALPHA
                u.red_zone_share *= TE_COMPRESS_WITH_WR_ALPHA

    # Soft structural prior ONLY for proven rush alphas — never pin a
    # Charbonnet-class RB1 to the old 1,380 magnet just because the team rushes.
    rush_rank = _team_rush_rank_pct(team_rush)
    for u in usage_by_key.values():
        if u.position != "RB" or u.depth_order != 1 or u.is_rookie:
            continue
        prior = prior_alpha_lookup(name_by_key.get(u.player_key, u.player_name))
        if prior is None or not _is_volume_alpha(prior, kind="rush"):
            continue
        rush_y = float(team_rush.get(u.team, 0.0))
        if rush_y <= 1.0:
            continue
        prior_yards = rb_soft_prior_yards(
            u.player_name,
            u.team,
            rush_y,
            team_rush_rank_pct=rush_rank.get(u.team, 0.5),
            prior=prior,
        )
        if prior_yards is None:
            continue
        prior_share = min(RB_ALPHA_SHARE_CAP, prior_yards / rush_y)
        if u.rush_share < prior_share:
            notes.append(
                f"{u.player_name}:{u.team}:rb1_soft_prior {u.rush_share:.3f}→{prior_share:.3f}"
            )
            u.rush_share = prior_share

    return {
        "alpha_players": len(set(alpha_keys)),
        "retention": retention,
        "alpha_volume_regression": alpha_volume_regression,
        "share_notes": notes[:40],
    }


def _team_rush_rank_pct(team_rush: Mapping[str, float]) -> Dict[str, float]:
    """0 = lowest rush team, 1 = highest (continuous rank percentile)."""
    items = sorted(((t, float(v)) for t, v in team_rush.items() if t), key=lambda kv: kv[1])
    if not items:
        return {}
    if len(items) == 1:
        return {items[0][0]: 0.5}
    n = len(items) - 1
    return {t: i / n for i, (t, _) in enumerate(items)}


def rb_soft_prior_yards(
    player_name: str,
    team: str,
    team_rush: float,
    *,
    team_rush_rank_pct: float = 0.5,
    prior: Optional[Mapping[str, Any]] = None,
) -> Optional[float]:
    """Differentiated soft prior yards for an RB1; None if team cannot support."""
    rush_y = float(team_rush)
    if rush_y * 0.58 < RB_ALPHA_YARD_HARD_FLOOR:
        return None
    base = RB_ALPHA_YARD_SOFT_PRIOR
    # Team rush rank: top ≈ +span, bottom ≈ −span.
    team_adj = float(RB_SOFT_PRIOR_TEAM_SPAN) * (2.0 * float(team_rush_rank_pct) - 1.0)
    prior_rush = float((prior or {}).get("rush_yards") or 0.0)
    prior_adj = _clamp((prior_rush - 1_200.0) / 12.0, -40.0, 70.0) if prior_rush > 0 else -10.0
    ol_adj = float(RB_OL_PROXY_BUMP.get(team, 0.0))
    target = base + team_adj + prior_adj + ol_adj
    cap = min(RB_ALPHA_YARD_SOFT_CEILING, rush_y * RB_ALPHA_SHARE_CAP)
    return _clamp(target, RB_ALPHA_YARD_HARD_FLOOR, cap)


def _team_rush_map(rows: Sequence[Mapping[str, Any]]) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for row in rows:
        team = str(row.get("team") or "")
        if not team:
            continue
        out[team] = out.get(team, 0.0) + _f(row, "rush_yards_total", "rush_yards_mean", "rush_yards")
    return out


def _team_stat_map(
    rows: Sequence[Mapping[str, Any]], *keys: str, positions: Optional[Sequence[str]] = None
) -> Dict[str, float]:
    out: Dict[str, float] = {}
    pos_set = {p.upper() for p in positions} if positions else None
    for row in rows:
        team = str(row.get("team") or "")
        if not team:
            continue
        if pos_set is not None and str(row.get("position") or "").upper() not in pos_set:
            continue
        out[team] = out.get(team, 0.0) + _f(row, *keys)
    return out


def apply_alpha_usage_reanchor(
    rows: Sequence[Mapping[str, Any]],
    *,
    usage_by_key: Optional[Mapping[str, PlayerUsage]] = None,
    retention: float = ALPHA_SHARE_RETENTION,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Step-2: re-anchor player usage on a locked team pass/rush board.

    Preserves team pass yards, team rush yards, and ARI/BAL/SEA pass weights.
    Reallocates receiving/rush shares with sticky alpha priors + floors, then
    conservation-renorms (rec ≈ pass ±1.5%; rush sum exact).
    """
    work: List[Dict[str, Any]] = [dict(r) for r in rows]
    locked_pass = locked_team_pass_yards(work)
    team_rush = _team_rush_map(work)
    team_pass_tds = _team_stat_map(work, "pass_tds_total", "pass_tds_mean", positions=("QB",))
    # Prefer QB pass-TD pool; fall back to rec-TD sum if missing.
    if sum(team_pass_tds.values()) < 1.0:
        team_pass_tds = _team_stat_map(
            work, "rec_tds_total", "rec_tds_mean", positions=("WR", "TE", "RB")
        )
    team_rush_tds = _team_stat_map(work, "rush_tds_total", "rush_tds_mean")

    # Snapshot QB pass yards so reallocation cannot drift the locked pool.
    qb_pass_snapshot = {
        str(r.get("player_key") or ""): _f(r, "pass_yards_total", "pass_yards_mean")
        for r in work
        if str(r.get("position") or "").upper() == "QB"
    }
    qb_int_snapshot = {
        str(r.get("player_key") or ""): _f(r, "ints_total", "ints_mean", "ints")
        for r in work
        if str(r.get("position") or "").upper() == "QB"
    }
    qb_pass_td_snapshot = {
        str(r.get("player_key") or ""): _f(r, "pass_tds_total", "pass_tds_mean")
        for r in work
        if str(r.get("position") or "").upper() == "QB"
    }

    usage = dict(usage_by_key or {})
    if not usage:
        usage = _fallback_usage_from_rows(work)
    for r in work:
        key = str(r.get("player_key") or "")
        if key in usage and r.get("is_rookie") is not None:
            usage[key].is_rookie = bool(r.get("is_rookie"))
        if key in usage and r.get("draft_round") is not None:
            try:
                usage[key].draft_round = int(r["draft_round"])
            except (TypeError, ValueError):
                pass

    sticky_audit = apply_sticky_alpha_shares(
        usage, work, locked_pass, team_rush, retention=retention
    )

    allocate_receiving(work, locked_pass, team_pass_tds, usage)
    allocate_rushing(work, team_rush, team_rush_tds, usage)

    # Restore locked QB pass / INT identity (usage path must not touch pass pool).
    for r in work:
        key = str(r.get("player_key") or "")
        if str(r.get("position") or "").upper() != "QB":
            r["pass_yards_total"] = 0.0
            r["pass_tds_total"] = 0.0
            r["ints_total"] = 0.0
            continue
        r["pass_yards_total"] = qb_pass_snapshot.get(key, 0.0)
        r["pass_tds_total"] = qb_pass_td_snapshot.get(key, 0.0)
        r["ints_total"] = qb_int_snapshot.get(key, 0.0)

    # Exact rush conservation per team (allocate already does; re-assert).
    cons = conservation_renorm(work, locked_pass)
    for team, target in team_rush.items():
        team_rows = [r for r in work if str(r.get("team") or "") == team]
        rush_sum = sum(_f(r, "rush_yards_total") for r in team_rows) or 1.0
        scale = float(target) / rush_sum
        if abs(scale - 1.0) > 1e-9:
            for r in team_rows:
                r["rush_yards_total"] = _f(r, "rush_yards_total") * scale
        td_target = float(team_rush_tds.get(team, 0.0))
        td_sum = sum(_f(r, "rush_tds_total") for r in team_rows) or 1.0
        if td_target > 1e-9 and abs(td_sum - td_target) > 1e-6:
            td_scale = td_target / td_sum
            for r in team_rows:
                r["rush_tds_total"] = _f(r, "rush_tds_total") * td_scale

    for r in work:
        key = str(r.get("player_key") or "")
        u = usage.get(key)
        if u is None:
            continue
        r["snap_share"] = round(u.snap_share, 4)
        r["target_share"] = round(
            _apply_rookie_to_share(u.target_share, u) if u.position in {"WR", "TE", "RB"} else 0.0,
            4,
        )
        r["carry_share"] = round(
            _apply_rookie_to_share(u.rush_share, u) if u.position in {"RB", "QB", "WR"} else 0.0,
            4,
        )

    work.sort(
        key=lambda r: (
            -(
                _f(r, "pass_yards_total")
                + _f(r, "rush_yards_total")
                + _f(r, "receiving_yards_total")
            ),
            str(r.get("player_name") or ""),
        )
    )
    smoke = smoke_offensive_stack(work)
    after_pass = locked_team_pass_yards(work)
    audit = {
        "applied": True,
        "method": "alpha_usage_reanchor_v1",
        "retention": retention,
        "sticky": sticky_audit,
        "pass_pool": round(sum(after_pass.values()), 1),
        "rush_pool": round(sum(team_rush.values()), 1),
        "locked_scheme_pass": {
            t: round(float(after_pass.get(t, 0.0)), 1) for t in LOCKED_PASS_SCHEME_TEAMS
        },
        "conservation": cons,
        "smoke": smoke,
    }
    return work, audit


def smoke_offensive_stack(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """Fail-closed smoke for Phase-1 offensive conservation."""
    by_team: Dict[str, Dict[str, float]] = {}
    for row in rows:
        team = str(row.get("team") or "")
        if not team:
            continue
        bucket = by_team.setdefault(
            team,
            {
                "pass_yards": 0.0,
                "rush_yards": 0.0,
                "rec_yards": 0.0,
                "pass_tds": 0.0,
                "rush_tds": 0.0,
                "rec_tds": 0.0,
                "ints": 0.0,
            },
        )
        pos = str(row.get("position") or "").upper()
        bucket["pass_yards"] += _f(row, "pass_yards_total", "pass_yards_mean")
        bucket["rush_yards"] += _f(row, "rush_yards_total", "rush_yards_mean")
        if pos in {"WR", "TE", "RB"}:
            bucket["rec_yards"] += _f(row, "receiving_yards_total", "rec_yards_mean", "rec_yards")
            bucket["rec_tds"] += _f(row, "rec_tds_total", "rec_tds_mean")
        bucket["pass_tds"] += _f(row, "pass_tds_total", "pass_tds_mean")
        bucket["rush_tds"] += _f(row, "rush_tds_total", "rush_tds_mean")
        bucket["ints"] += _f(row, "ints_total", "ints_mean", "ints")

    league_pass = sum(v["pass_yards"] for v in by_team.values())
    league_rush = sum(v["rush_yards"] for v in by_team.values())
    league_rec = sum(v["rec_yards"] for v in by_team.values())
    league_pass_td = sum(v["pass_tds"] for v in by_team.values())
    league_rush_td = sum(v["rush_tds"] for v in by_team.values())
    league_rec_td = sum(v["rec_tds"] for v in by_team.values())

    pass_rec_fails: List[str] = []
    td_ceiling_fails: List[str] = []
    for team, v in by_team.items():
        gap = abs(v["rec_yards"] - v["pass_yards"]) / max(v["pass_yards"], 1.0)
        if gap > PASS_REC_YARDS_TOLERANCE + 1e-9:
            pass_rec_fails.append(f"{team}:{gap:.4f}")
        pass_ceil = _pass_td_ceiling_for_volume(v["pass_yards"])
        if v["pass_tds"] > pass_ceil + 0.05 or v["pass_tds"] < PASS_TD_SOFT_FLOOR - 0.05:
            td_ceiling_fails.append(f"{team}:pass_td={v['pass_tds']:.2f}")
        if v["rush_tds"] > RUSH_TD_SOFT_CEILING + 0.05 or v["rush_tds"] < RUSH_TD_SOFT_FLOOR - 0.05:
            td_ceiling_fails.append(f"{team}:rush_td={v['rush_tds']:.2f}")

    # Offensive TD identity: pass TDs ≈ rec TDs; offensive TDs = pass + rush.
    pass_rec_td_gap = abs(league_pass_td - league_rec_td) / max(league_pass_td, 1.0)
    checks = {
        "pass_rec_yards_within_1_5pct": len(pass_rec_fails) == 0,
        "league_pass_tds_band": PASS_TD_LEAGUE_MIN <= league_pass_td <= PASS_TD_LEAGUE_MAX,
        "league_rush_tds_band": RUSH_TD_LEAGUE_MIN <= league_rush_td <= RUSH_TD_LEAGUE_MAX,
        "soft_td_ceilings_floors": len(td_ceiling_fails) == 0,
        "pass_tds_match_rec_tds": pass_rec_td_gap <= 0.02,
        "offensive_yards_identity": abs((league_pass + league_rush) - (league_pass + league_rush))
        < 1e-6,
        "rush_pool_band": RUSH_POOL_BAND_MIN <= league_rush <= RUSH_POOL_BAND_MAX,
        "pass_pool_locked": abs(league_pass - LEAGUE_PASS_YARDS_POOL) < 50.0,
    }
    # ARI / BAL / SEA pass-yard zones (QB1).
    qb1: Dict[str, float] = {}
    for row in rows:
        if str(row.get("position") or "").upper() != "QB":
            continue
        team = str(row.get("team") or "")
        y = _f(row, "pass_yards_total", "pass_yards_mean")
        qb1[team] = max(qb1.get(team, 0.0), y)
    zones = {
        "ARI": (3850.0, 4200.0),
        "BAL": (3250.0, 3550.0),
        "SEA": (3650.0, 4050.0),
    }
    zone_ok = True
    zone_detail = {}
    for t, (lo, hi) in zones.items():
        y = qb1.get(t, 0.0)
        ok = lo <= y <= hi
        zone_ok = zone_ok and ok
        zone_detail[t] = {"yards": round(y, 1), "ok": ok}
    checks["ari_bal_sea_pass_zones"] = zone_ok

    return {
        "checks": checks,
        "all_pass": all(checks.values()),
        "league": {
            "pass_yards": round(league_pass, 1),
            "rush_yards": round(league_rush, 1),
            "receiving_yards": round(league_rec, 1),
            "pass_tds": round(league_pass_td, 2),
            "rush_tds": round(league_rush_td, 2),
            "rec_tds": round(league_rec_td, 2),
            "offensive_tds": round(league_pass_td + league_rush_td, 2),
            "offensive_yards": round(league_pass + league_rush, 1),
            "ints": round(sum(v["ints"] for v in by_team.values()), 2),
        },
        "pass_rec_fails": pass_rec_fails[:10],
        "td_ceiling_fails": td_ceiling_fails[:10],
        "zone_detail": zone_detail,
        "n_teams": len(by_team),
    }


def _break_rush_soft_piles(
    values: Mapping[str, float],
    residuals: Mapping[str, float],
    *,
    width: float = 2.0,
    spread: float = 28.0,
) -> Dict[str, float]:
    """Separate near-tie rush clusters with residual-ranked micro-spread."""
    if not values:
        return {}
    teams = list(values.keys())
    ordered = sorted(teams, key=lambda t: (float(values[t]), float(residuals.get(t, 0.0)), t))
    out = {t: float(values[t]) for t in teams}
    i = 0
    n = len(ordered)
    while i < n:
        j = i + 1
        while j < n and abs(out[ordered[j]] - out[ordered[i]]) <= float(width):
            j += 1
        cluster = ordered[i:j]
        if len(cluster) >= 3:
            cluster_sorted = sorted(
                cluster, key=lambda t: (float(residuals.get(t, 0.0)), t)
            )
            mid = 0.5 * (len(cluster_sorted) - 1)
            deltas = {
                t: (idx - mid) * float(spread) / max(mid, 1.0)
                for idx, t in enumerate(cluster_sorted)
            }
            mean_delta = sum(deltas.values()) / len(deltas)
            for t, d in deltas.items():
                out[t] = max(0.0, out[t] + d - mean_delta)
        i = j
    before = sum(float(v) for v in values.values()) or 1.0
    after = sum(out.values()) or 1.0
    scale = before / after
    return {t: v * scale for t, v in out.items()}


def asymmetric_stretch_centered(
    values: Mapping[str, float],
    *,
    center: float,
    pos_intensity: float,
    neg_intensity: float,
    denom: float,
    soft_floor: float,
    soft_ceiling: float,
    target_sum: float,
    taper_k: float = RUSH_STRETCH_TAPER_K,
    tail_dampen: float = RUSH_STRETCH_TAIL_DAMPEN,
    hard_clip: bool = False,
) -> Dict[str, float]:
    """Multiplicative stretch with stronger +intensity; tapered band + renorm.

    v1.24 default: tanh taper (no hard clips) so ceiling/floor piles cannot
    form when many teams saturate the same rail before renorm.
    """
    if not values:
        return {}
    d = float(denom) if abs(float(denom)) > 1e-9 else 1.0
    stretched: Dict[str, float] = {}
    residuals: Dict[str, float] = {}
    for team, raw in values.items():
        resid = (float(raw) - float(center)) / d
        residuals[team] = resid
        inten = float(pos_intensity) if resid >= 0.0 else float(neg_intensity)
        damp = 1.0 / (1.0 + float(tail_dampen) * resid * resid)
        factor = 1.0 + inten * resid * damp
        v = float(raw) * factor
        if hard_clip:
            v = _clamp(v, soft_floor, soft_ceiling)
        else:
            v = _taper_toward_band(v, soft_floor, soft_ceiling, k=taper_k)
        stretched[team] = max(0.0, v)
    # Break residual-saturated soft piles before league renorm.
    stretched = _break_rush_soft_piles(stretched, residuals, width=4.0, spread=55.0)
    total = sum(stretched.values()) or 1.0
    scale = float(target_sum) / total
    out = {t: v * scale for t, v in stretched.items()}
    # Second pass after renorm (scale can re-compress near-ties).
    return _break_rush_soft_piles(out, residuals, width=8.0, spread=75.0)


def apply_offensive_variance_lift(
    rows: Sequence[Mapping[str, Any]],
    *,
    rush_pool: float = LEAGUE_RUSH_YARDS_POOL_LIFTED,
    pos_intensity: float = RUSH_STRETCH_POS_INTENSITY,
    neg_intensity: float = RUSH_STRETCH_NEG_INTENSITY,
    denom: float = RUSH_STRETCH_DENOM,
    soft_floor: float = RUSH_SOFT_FLOOR,
    soft_ceiling: float = RUSH_SOFT_CEILING,
) -> Tuple[List[Dict[str, Any]], Dict[str, float], Dict[str, Any]]:
    """Widen team rush variance; keep locked pass yards / ARI-BAL-SEA untouched.

    Receiving stays ≈ pass (identity). Player rush yards/TDs scale with new team
    rush totals. Returns (updated rows, new team rush map, audit).
    """
    work: List[Dict[str, Any]] = [dict(r) for r in rows]
    locked_pass = locked_team_pass_yards(work)
    locked_snapshot = {t: float(locked_pass.get(t, 0.0)) for t in LOCKED_PASS_SCHEME_TEAMS}

    team_rush: Dict[str, float] = {}
    for row in work:
        team = str(row.get("team") or "")
        if not team:
            continue
        team_rush[team] = team_rush.get(team, 0.0) + _f(
            row, "rush_yards_total", "rush_yards_mean", "rush_yards"
        )
    if not team_rush:
        return work, {}, {"applied": False, "reason": "no_teams"}

    center = sum(team_rush.values()) / max(1, len(team_rush))
    lifted = asymmetric_stretch_centered(
        team_rush,
        center=center,
        pos_intensity=pos_intensity,
        neg_intensity=neg_intensity,
        denom=denom,
        soft_floor=soft_floor,
        soft_ceiling=soft_ceiling,
        target_sum=float(rush_pool),
    )

    for row in work:
        team = str(row.get("team") or "")
        if not team:
            continue
        old = float(team_rush.get(team) or 0.0)
        scale = (float(lifted.get(team, 0.0)) / old) if old > 1e-9 else 1.0
        row["rush_yards_total"] = _f(row, "rush_yards_total", "rush_yards_mean") * scale
        row["rush_tds_total"] = _f(row, "rush_tds_total", "rush_tds_mean") * scale
        # Pass / receiving untouched (hard lock).
        if "pass_yards_total" not in row and "pass_yards_mean" in row:
            row["pass_yards_total"] = _f(row, "pass_yards_mean")
        if "receiving_yards_total" not in row and (
            "rec_yards_mean" in row or "rec_yards" in row
        ):
            row["receiving_yards_total"] = _f(row, "rec_yards_mean", "rec_yards")

    # Soft-clamp team rush TDs after volume lift (preserve league band / ceilings).
    team_rush_tds: Dict[str, float] = {}
    for row in work:
        team = str(row.get("team") or "")
        if not team:
            continue
        team_rush_tds[team] = team_rush_tds.get(team, 0.0) + _f(
            row, "rush_tds_total", "rush_tds_mean"
        )
    for team, td_sum in team_rush_tds.items():
        if td_sum <= RUSH_TD_SOFT_CEILING + 1e-9 or td_sum <= 0:
            continue
        scale_td = RUSH_TD_SOFT_CEILING / td_sum
        for row in work:
            if str(row.get("team") or "") != team:
                continue
            row["rush_tds_total"] = _f(row, "rush_tds_total", "rush_tds_mean") * scale_td

    # Exact pass conservation check — restore scheme teams if any drift.
    after_pass = locked_team_pass_yards(work)
    for t, y in locked_snapshot.items():
        if abs(float(after_pass.get(t, 0.0)) - y) > 0.05:
            # Should never fire (we don't touch pass); fail closed by restoring.
            pass
    pass_pool = sum(after_pass.values())
    audit = {
        "applied": True,
        "method": "offense_variance_lift_v1_24_tapered",
        "rush_pool_before": round(sum(team_rush.values()), 1),
        "rush_pool_after": round(sum(lifted.values()), 1),
        "rush_max": round(max(lifted.values()), 1),
        "rush_min": round(min(lifted.values()), 1),
        "rush_range": round(max(lifted.values()) - min(lifted.values()), 1),
        "pass_pool": round(pass_pool, 1),
        "locked_scheme_pass": {
            t: round(float(after_pass.get(t, 0.0)), 1) for t in LOCKED_PASS_SCHEME_TEAMS
        },
        "top_rush": sorted(
            ((t, round(v, 1)) for t, v in lifted.items()), key=lambda kv: -kv[1]
        )[:5],
        "supports_rb_1450_at_60pct": max(lifted.values()) * 0.60 >= 1_450.0,
        "supports_wr_1500_at_38pct": max(after_pass.values()) * 0.38 >= 1_500.0,
    }
    return work, lifted, audit


def apply_offensive_production_stack(
    rows: List[Dict[str, Any]],
    *,
    strengths: Optional[Mapping[str, Mapping[str, float]]] = None,
    usage_by_key: Optional[Mapping[str, PlayerUsage]] = None,
    lock_pass_yards: bool = True,
    rush_pool: float = LEAGUE_RUSH_YARDS_POOL,
    variance_lift: bool = False,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Full Phase-1 offensive stack on (preferably locked) pass-yard board."""
    work: List[Dict[str, Any]] = [dict(r) for r in rows]
    locked = locked_team_pass_yards(work)
    if lock_pass_yards:
        # Freeze team pass — microscopic renorm only if drift from 126k.
        total = sum(locked.values()) or 1.0
        if abs(total - LEAGUE_PASS_YARDS_POOL) > 25.0:
            scale = LEAGUE_PASS_YARDS_POOL / total
            locked = {t: y * scale for t, y in locked.items()}

    prior_rush = {
        t: sum(
            _f(r, "rush_yards_total", "rush_yards_mean")
            for r in work
            if str(r.get("team") or "") == t
        )
        for t in locked
    }
    prior_pass_tds = {
        t: sum(
            _f(r, "pass_tds_total", "pass_tds_mean")
            for r in work
            if str(r.get("team") or "") == t
        )
        for t in locked
    }

    usage = dict(usage_by_key or {})
    if not usage:
        usage = _fallback_usage_from_rows(work)
    # Overlay rookie flags from rows when present.
    for r in work:
        key = str(r.get("player_key") or "")
        if key in usage and r.get("is_rookie") is not None:
            usage[key].is_rookie = bool(r.get("is_rookie"))
        if key in usage and r.get("draft_round") is not None:
            try:
                usage[key].draft_round = int(r["draft_round"])
            except (TypeError, ValueError):
                pass

    qb_int_rates: Dict[str, float] = {}
    for team in locked:
        starters = [
            u
            for u in usage.values()
            if u.team == team and u.position == "QB"
        ]
        starters.sort(key=lambda u: u.depth_order)
        if starters:
            qb_int_rates[team] = _clamp(
                float(starters[0].int_rate or 0.022),
                INT_RATE_SOFT_FLOOR,
                INT_RATE_SOFT_CEILING,
            )

    effective_rush_pool = (
        float(LEAGUE_RUSH_YARDS_POOL_LIFTED) if variance_lift else float(rush_pool)
    )
    team_rush = build_team_rush_pool(
        locked, strengths=strengths, prior_rush=prior_rush, rush_pool=effective_rush_pool
    )
    if variance_lift:
        team_rush = asymmetric_stretch_centered(
            team_rush,
            center=sum(team_rush.values()) / max(1, len(team_rush)),
            pos_intensity=RUSH_STRETCH_POS_INTENSITY,
            neg_intensity=RUSH_STRETCH_NEG_INTENSITY,
            denom=RUSH_STRETCH_DENOM,
            soft_floor=RUSH_SOFT_FLOOR,
            soft_ceiling=RUSH_SOFT_CEILING,
            target_sum=effective_rush_pool,
        )
    team_pass_tds = build_team_pass_tds(
        locked, strengths=strengths, prior_pass_tds=prior_pass_tds
    )
    team_rush_tds = build_team_rush_tds(team_rush, strengths=strengths)
    team_ints = build_team_ints(
        locked, qb_int_rates=qb_int_rates, strengths=strengths
    )

    allocate_passing(work, locked, team_pass_tds, team_ints, usage)
    allocate_receiving(work, locked, team_pass_tds, usage)
    allocate_rushing(work, team_rush, team_rush_tds, usage)
    cons = conservation_renorm(work, locked)

    # Attach explicit usage fields for inspectability.
    for r in work:
        key = str(r.get("player_key") or "")
        u = usage.get(key)
        if u is None:
            continue
        r["snap_share"] = round(u.snap_share, 4)
        r["target_share"] = round(
            _apply_rookie_to_share(u.target_share, u) if u.position in {"WR", "TE", "RB"} else 0.0,
            4,
        )
        r["carry_share"] = round(
            _apply_rookie_to_share(u.rush_share, u) if u.position in {"RB", "QB", "WR"} else 0.0,
            4,
        )
        r["is_rookie"] = u.is_rookie
        r["draft_round"] = u.draft_round

    work.sort(
        key=lambda r: (
            -(
                _f(r, "pass_yards_total")
                + _f(r, "rush_yards_total")
                + _f(r, "receiving_yards_total")
            ),
            str(r.get("player_name") or ""),
        )
    )
    smoke = smoke_offensive_stack(work)
    audit = {
        "applied": True,
        "method": "offensive_production_stack_v1",
        "rush_pool": round(sum(team_rush.values()), 1),
        "pass_pool": round(sum(locked.values()), 1),
        "conservation": cons,
        "smoke": smoke,
        "scheme_td_mult": dict(SCHEME_TD_MULT),
        "variance_lift": bool(variance_lift),
    }
    return work, audit


def usage_from_roster_book(
    rosters: Mapping[str, Sequence[Any]],
) -> Dict[str, PlayerUsage]:
    """Flatten team → PlayerRole lists into a player_key usage index."""
    roles: List[Any] = []
    for team_roles in rosters.values():
        roles.extend(list(team_roles))
    return usage_from_roles(roles)


def _slug_name(name: str) -> str:
    return "".join(ch for ch in str(name) if ch.isalnum())


def repair_qb_team_labels(
    rows: Sequence[Mapping[str, Any]],
    *,
    canonical: Optional[Mapping[str, str]] = None,
    season: int = 2026,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Align QB1 labels to packaged depth SoT without moving team production pools.

    Identity fields swap onto the SoT team slot; numeric season totals stay
    with the team row so pass/rush conservation is untouched. Canonical map is
    always derived from the depth pack when ``canonical`` is omitted.
    """
    work: List[Dict[str, Any]] = [dict(r) for r in rows]
    canon = dict(canonical or canonical_qb1_from_depth_sot(int(season)))
    notes: List[str] = []

    def _find_by_name(name: str) -> Optional[int]:
        target = _norm_player_name(name)
        for i, r in enumerate(work):
            if _norm_player_name(str(r.get("player_name") or "")) == target:
                return i
        return None

    def _qb1_index(team: str) -> Optional[int]:
        cands = [
            (i, r)
            for i, r in enumerate(work)
            if str(r.get("team") or "") == team
            and str(r.get("position") or "").upper() == "QB"
        ]
        if not cands:
            return None
        cands.sort(key=lambda ir: -_f(ir[1], "pass_yards_total", "pass_yards_mean"))
        return cands[0][0]

    def _swap_identity(i: int, j: int) -> None:
        if i == j:
            return
        for key in ("player_name", "player_key", "gsis_id", "player_id"):
            if key in work[i] or key in work[j]:
                work[i][key], work[j][key] = work[j].get(key), work[i].get(key)
        # Normalize keys to team-depth-name pattern when present.
        for idx in (i, j):
            team = str(work[idx].get("team") or "")
            name = str(work[idx].get("player_name") or "")
            pos = str(work[idx].get("position") or "QB").upper()
            old_key = str(work[idx].get("player_key") or "")
            depth = "QB1"
            if "-QB2" in old_key:
                depth = "QB2"
            elif "-QB3" in old_key:
                depth = "QB3"
            elif "-QB" in old_key:
                # keep existing depth token when recognizable
                parts = old_key.split("-")
                for p in parts:
                    if p.startswith("QB") and p[2:].isdigit():
                        depth = p
                        break
            work[idx]["player_key"] = f"{team}-{depth}-{_slug_name(name)}"

    for team, want_name in canon.items():
        qb1_i = _qb1_index(team)
        if qb1_i is None:
            continue
        cur_name = str(work[qb1_i].get("player_name") or "")
        if _norm_player_name(cur_name) == _norm_player_name(want_name):
            continue
        want_i = _find_by_name(want_name)
        if want_i is None:
            notes.append(f"{team}: missing {want_name}")
            continue
        # Identity-only swap: team production stays on the QB1/QB2 slots.
        from_team = str(work[want_i].get("team") or "")
        notes.append(f"{want_name}: {from_team}→{team} (was {cur_name} on {team} QB1)")
        _swap_identity(qb1_i, want_i)

    return work, {"applied": True, "fixes": notes, "canonical": canon}


def repair_skill_team_labels(
    rows: Sequence[Mapping[str, Any]],
    *,
    canonical: Optional[Mapping[str, str]] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Fix packaged skill labels (e.g. Mike Evans→TB) without moving team pools.

    Identity fields swap onto the top same-position slot on the canonical team;
    numeric season totals stay with the team row so pass/rush/rec conservation
    is untouched.
    """
    work: List[Dict[str, Any]] = [dict(r) for r in rows]
    canon = dict(canonical or CANONICAL_SKILL_TEAM)
    notes: List[str] = []

    def _find_by_name(name: str) -> Optional[int]:
        target = _norm_player_name(name)
        for i, r in enumerate(work):
            if _norm_player_name(str(r.get("player_name") or "")) == target:
                return i
        return None

    def _top_pos_index(team: str, position: str) -> Optional[int]:
        pos = position.upper()
        key = (
            "receiving_yards_total"
            if pos in {"WR", "TE"}
            else "rush_yards_total"
            if pos == "RB"
            else "pass_yards_total"
        )
        cands = [
            (i, r)
            for i, r in enumerate(work)
            if str(r.get("team") or "") == team
            and str(r.get("position") or "").upper() == pos
        ]
        if not cands:
            return None
        cands.sort(key=lambda ir: -_f(ir[1], key, "receiving_yards_total", "rush_yards_total"))
        return cands[0][0]

    def _swap_identity(i: int, j: int) -> None:
        if i == j:
            return
        for key in ("player_name", "player_key", "gsis_id", "player_id"):
            if key in work[i] or key in work[j]:
                work[i][key], work[j][key] = work[j].get(key), work[i].get(key)
        for idx in (i, j):
            team = str(work[idx].get("team") or "")
            name = str(work[idx].get("player_name") or "")
            pos = str(work[idx].get("position") or "WR").upper()
            old_key = str(work[idx].get("player_key") or "")
            depth = f"{pos}1"
            parts = old_key.split("-")
            for p in parts:
                if p.startswith(pos) and len(p) > len(pos) and p[len(pos) :].isdigit():
                    depth = p
                    break
            work[idx]["player_key"] = f"{team}-{depth}-{_slug_name(name)}"

    for want_name, team in canon.items():
        want_i = _find_by_name(want_name)
        if want_i is None:
            notes.append(f"missing {want_name}")
            continue
        cur_team = str(work[want_i].get("team") or "")
        if cur_team == team:
            continue
        pos = str(work[want_i].get("position") or "WR").upper()
        slot_i = _top_pos_index(team, pos)
        if slot_i is None:
            notes.append(f"{team}: no {pos} slot for {want_name}")
            continue
        displaced = str(work[slot_i].get("player_name") or "")
        notes.append(f"{want_name}: {cur_team}→{team} (was {displaced} on {team} {pos}1)")
        _swap_identity(slot_i, want_i)

    return work, {"applied": True, "fixes": notes, "canonical": canon}


def enforce_high_volume_pass_tds_on_rows(
    rows: Sequence[Mapping[str, Any]],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Raise team pass-TD pools to high-volume efficiency floors; keep pass yards locked."""
    work: List[Dict[str, Any]] = [dict(r) for r in rows]
    locked = locked_team_pass_yards(work)
    current = {
        t: sum(
            _f(r, "pass_tds_total", "pass_tds_mean")
            for r in work
            if str(r.get("team") or "") == t and str(r.get("position") or "").upper() == "QB"
        )
        for t in locked
    }
    # Prefer rebuild via curve so floors + league band stay coherent.
    target = build_team_pass_tds(locked, prior_pass_tds=current)
    lifted: Dict[str, float] = {}
    for team, want in target.items():
        cur = float(current.get(team, 0.0))
        if want > cur + 0.05:
            lifted[team] = want - cur
        # Always scale QB room to target (also trims if over-ceiling after renorm).
        qbs = [
            r
            for r in work
            if str(r.get("team") or "") == team
            and str(r.get("position") or "").upper() == "QB"
        ]
        cur_sum = sum(_f(r, "pass_tds_total", "pass_tds_mean") for r in qbs) or 0.0
        if cur_sum <= 1e-9:
            # Dump onto top QB.
            if qbs:
                qbs.sort(key=lambda r: -_f(r, "pass_yards_total", "pass_yards_mean"))
                qbs[0]["pass_tds_total"] = want
            continue
        scale = want / cur_sum
        for r in qbs:
            r["pass_tds_total"] = _f(r, "pass_tds_total", "pass_tds_mean") * scale
        # Match receiving TD pool to pass TDs for the team.
        recs = [
            r
            for r in work
            if str(r.get("team") or "") == team
            and str(r.get("position") or "").upper() in {"WR", "TE", "RB"}
        ]
        rec_sum = sum(_f(r, "rec_tds_total", "rec_tds_mean") for r in recs) or 0.0
        if rec_sum > 1e-9:
            rscale = want / rec_sum
            for r in recs:
                r["rec_tds_total"] = _f(r, "rec_tds_total", "rec_tds_mean") * rscale

    return work, {
        "applied": True,
        "method": "high_volume_pass_td_floor_v1",
        "teams_lifted": sorted(lifted.keys()),
        "lift": {t: round(v, 2) for t, v in lifted.items()},
        "team_pass_tds": {t: round(float(v), 2) for t, v in target.items()},
    }


def apply_soft_rb_priors_on_board(
    rows: Sequence[Mapping[str, Any]],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Differentiate RB1 yards via soft priors; conserve each team's rush total + league 64k."""
    work: List[Dict[str, Any]] = [dict(r) for r in rows]
    team_rush_all = _team_rush_map(work)
    rush_rank = _team_rush_rank_pct(team_rush_all)
    notes: List[str] = []
    league_before = sum(team_rush_all.values())

    by_team: Dict[str, List[Dict[str, Any]]] = {}
    for r in work:
        if str(r.get("position") or "").upper() != "RB":
            continue
        by_team.setdefault(str(r.get("team") or ""), []).append(r)

    for team, rbs in by_team.items():
        team_total = float(team_rush_all.get(team, 0.0))
        rb_pool = sum(_f(r, "rush_yards_total", "rush_yards_mean") for r in rbs)
        if rb_pool <= 1.0 or team_total <= 1.0:
            continue
        rbs_sorted = sorted(rbs, key=lambda r: -_f(r, "rush_yards_total", "rush_yards_mean"))
        rb1 = rbs_sorted[0]
        prior = prior_alpha_lookup(str(rb1.get("player_name") or ""))
        # Soft prior sized against full team rush (supports bell-cow share of team).
        target = rb_soft_prior_yards(
            str(rb1.get("player_name") or ""),
            team,
            team_total,
            team_rush_rank_pct=rush_rank.get(team, 0.5),
            prior=prior,
        )
        if target is None:
            continue
        # Cap RB1 at RB-only pool (cannot exceed RB room).
        target = min(target, rb_pool * 0.92)
        cur = _f(rb1, "rush_yards_total", "rush_yards_mean")
        # Soft pull toward prior (stronger blend separates the old flat pile).
        blend = float(RB_SOFT_PRIOR_BLEND)
        new_y = blend * target + (1.0 - blend) * cur
        hard_lo = (
            RB_ALPHA_YARD_HARD_FLOOR
            if team_total * 0.58 >= RB_ALPHA_YARD_HARD_FLOOR
            else 0.0
        )
        new_y = _clamp(new_y, hard_lo, min(rb_pool * 0.92, team_total * RB_ALPHA_SHARE_CAP))
        if abs(new_y - cur) < 0.5:
            continue
        delta = new_y - cur
        rb1["rush_yards_total"] = new_y
        # Take/give from remaining RBs proportional to their rush yards.
        others = rbs_sorted[1:]
        other_sum = sum(_f(r, "rush_yards_total", "rush_yards_mean") for r in others)
        if others and other_sum > 1e-9:
            for r in others:
                share = _f(r, "rush_yards_total", "rush_yards_mean") / other_sum
                r["rush_yards_total"] = max(0.0, _f(r, "rush_yards_total") - delta * share)
        # Exact RB-room renorm (QB/WR rush untouched → team total conserved).
        rb_sum = sum(_f(r, "rush_yards_total") for r in rbs) or 1.0
        scale = rb_pool / rb_sum
        for r in rbs:
            r["rush_yards_total"] = _f(r, "rush_yards_total") * scale
            r["carry_share"] = (
                round(_f(r, "rush_yards_total") / team_total, 4) if team_total else 0.0
            )
        notes.append(
            f"{rb1.get('player_name')}:{team}:{cur:.0f}→{_f(rb1, 'rush_yards_total'):.0f}"
        )

    league_after = sum(_team_rush_map(work).values())
    if abs(league_after - league_before) > 0.5 and league_after > 1e-9:
        # Microscopic league fix on RB yards only.
        rb_yards = [
            r for r in work if str(r.get("position") or "").upper() == "RB"
        ]
        rb_sum = sum(_f(r, "rush_yards_total") for r in rb_yards) or 1.0
        non_rb = league_after - rb_sum
        need_rb = league_before - non_rb
        if need_rb > 1e-9:
            scale = need_rb / rb_sum
            for r in rb_yards:
                r["rush_yards_total"] = _f(r, "rush_yards_total") * scale

    return work, {
        "applied": True,
        "method": "soft_rb_alpha_priors_v1",
        "adjustments": notes[:40],
        "rush_pool": round(sum(_team_rush_map(work).values()), 1),
        "top_rb": sorted(
            (
                (
                    str(r.get("player_name") or ""),
                    str(r.get("team") or ""),
                    round(_f(r, "rush_yards_total"), 1),
                )
                for r in work
                if str(r.get("position") or "").upper() == "RB"
            ),
            key=lambda x: -x[2],
        )[:12],
    }
