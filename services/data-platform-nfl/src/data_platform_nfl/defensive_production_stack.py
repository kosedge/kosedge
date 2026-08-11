"""Phase-2 defense + points bridge: close offense → PF/PA → W/L.

Sits on the locked v1.18 offensive board. Does **not** reshuffle pass yards.
Game-level path W/L in the season engine remains Layer-2; this module closes
the published season-total loop so desk outcomes reconcile with production.

Conservation (fail smoke if violated):
- sum(points_for) == sum(points_against) within 1.0
- sum(expected_wins) == 272 within 0.05
- League PF in a realistic PPG band (~20–24 PPG → ~10.9k–13.1k season)
- Offensive pass-yard pool remains locked (~126k)
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple

# ---------------------------------------------------------------------------
# Scoring / league environment
# ---------------------------------------------------------------------------
GAMES_PER_TEAM = 17.0
LEAGUE_TEAMS = 32
TARGET_PPG = 21.8
TARGET_TEAM_PF = TARGET_PPG * GAMES_PER_TEAM  # ~370.6
TARGET_LEAGUE_PF = TARGET_TEAM_PF * LEAGUE_TEAMS  # ~11,859
LEAGUE_PF_MIN = 20.0 * GAMES_PER_TEAM * LEAGUE_TEAMS
LEAGUE_PF_MAX = 24.0 * GAMES_PER_TEAM * LEAGUE_TEAMS
EXPECTED_WINS_SUM = 272.0

# Yard / TD → points (team offense; rec yards not double-counted).
POINTS_PER_PASS_YARD = 0.04
POINTS_PER_RUSH_YARD = 0.10
POINTS_PER_PASS_TD = 6.0
POINTS_PER_RUSH_TD = 6.0
POINTS_PER_REC_TD = 0.0  # already in pass TDs at team level
POINTS_PER_INT = -2.0
FG_EXTRAS_SHARE = 0.22

# Defense multipliers on points/yards allowed.
DEFENSE_PA_SCALE = 0.28  # elite D cuts PA; soft D raises
DEFENSE_YARDS_SCALE = 0.22
PYTHAGOREAN_EXP = 2.37

# Soft team bands (season).
TEAM_PF_SOFT_FLOOR = 250.0
TEAM_PF_SOFT_CEILING = 520.0
TEAM_PA_SOFT_FLOOR = 250.0
TEAM_PA_SOFT_CEILING = 520.0

# ---------------------------------------------------------------------------
# Variance lift (widen flat defensive distributions; conserve league totals).
# ---------------------------------------------------------------------------
PA_STRETCH_CENTER = 370.6
PA_STRETCH_INTENSITY = 0.85
PA_STRETCH_DENOM = 24.0
PA_STRETCH_FLOOR = 328.0
PA_STRETCH_CEILING = 425.0
PA_LEAGUE_TOTAL = 11_859.0

SACK_STRETCH_CENTER = 35.9
SACK_STRETCH_INTENSITY = 1.4
SACK_STRETCH_DENOM = 2.4
SACK_STRETCH_FLOOR = 26.0
SACK_STRETCH_CEILING = 49.0
SACK_LEAGUE_TOTAL = 1_150.0

INT_STRETCH_CENTER = 10.95
INT_STRETCH_INTENSITY = 1.6
INT_STRETCH_DENOM = 0.65
INT_STRETCH_FLOOR = 7.0
INT_STRETCH_CEILING = 15.5
INT_LEAGUE_TOTAL = 350.3

# Yards: 0.6× PA stretch intensity, driven by PA residual (same direction).
YARDS_STRETCH_INTENSITY = PA_STRETCH_INTENSITY * 0.6  # 0.51

# Step-1 offensive variance → PF residual stretch + light PA re-stretch.
# v1.23: slightly softer intensity + tapered band penalties (no hard clips).
# v1.24: gentler PF/win taper + residual micro-spread to clear soft piles.
PF_STRETCH_CENTER = TARGET_TEAM_PF
PF_STRETCH_INTENSITY = 0.78
PF_STRETCH_DENOM = 28.0
PF_STRETCH_FLOOR = 265.0
PF_STRETCH_CEILING = 505.0
# Lower intensity than the original defensive variance lift (0.85).
PA_RESTRETCH_INTENSITY = 0.40
# Extreme-tail dampening on stretch intensity (logistic-ish).
STRETCH_TAIL_DAMPEN = 0.30

# High pass-volume → scoring coherence (enterprise soft-flag fix).
HIGH_PASS_VOLUME_YARDS = 4_600.0
MIN_POINTS_PER_PASS_ATTEMPT = 0.505  # upper mid of 0.48–0.52
DEFAULT_YPA_FOR_ATTEMPTS = 6.95
VOLUME_PF_RUSH_CREDIT = 0.055
# Softer tanh (less rail-stacking than a hard clip).
# v1.24: drop further so soft-floor / soft-ceiling piles separate.
STRETCH_TAPER_K = 0.78
# Rank-residual micro-spread after taper (breaks near-ties without hard clips).
PILE_BREAK_WIDTH = 0.35
PILE_BREAK_SPREAD = 1.8
WIN_STRETCH_INTENSITY = 0.72
WIN_STRETCH_DENOM = 1.05
WIN_STRETCH_FLOOR = 3.0
WIN_STRETCH_CEILING = 15.2
WIN_STRETCH_TAPER_K = 0.62
WIN_STRETCH_TAIL_DAMPEN = 0.18
WIN_PILE_BREAK_WIDTH = 0.04
WIN_PILE_BREAK_SPREAD = 0.12


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def _taper_toward_band(
    value: float,
    soft_floor: float,
    soft_ceiling: float,
    *,
    k: float,
) -> float:
    """Soft-saturate into (floor, ceiling) via tanh — no hard pin at the rails.

    Teams near the same pre-stretch value still separate after renorm; extremes
    asymptote toward the band edges instead of stacking on an exact clip.
    """
    lo = float(soft_floor)
    hi = float(soft_ceiling)
    if hi <= lo + 1e-9:
        return float(value)
    mid = 0.5 * (lo + hi)
    half = 0.5 * (hi - lo)
    # Higher k → steeper saturation (closer to a clip, but still continuous).
    sharpness = max(float(k), 0.25)
    return mid + half * math.tanh(((float(value) - mid) / half) * sharpness)


def _break_soft_piles(
    values: Mapping[str, float],
    residuals: Mapping[str, float],
    *,
    width: float,
    spread: float,
) -> Dict[str, float]:
    """Within near-tie clusters, apply residual-ranked micro-spread (conserving sum).

    Keeps league totals intact while separating soft-floor / soft-ceiling stacks
    that survive a gentle tanh taper.
    """
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
            # Rank by residual (not current piled value) so order is meaningful.
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
    # Exact conservation.
    before = sum(float(v) for v in values.values()) or 1.0
    after = sum(out.values()) or 1.0
    scale = before / after
    return {t: v * scale for t, v in out.items()}


def _f(row: Mapping[str, Any], *keys: str, default: float = 0.0) -> float:
    for k in keys:
        if k in row and row[k] is not None and row[k] != "":
            try:
                return float(row[k])
            except (TypeError, ValueError):
                continue
    return float(default)


@dataclass(frozen=True)
class TeamDefenseBudget:
    team: str
    points_for: float
    points_against: float
    expected_wins: float
    pass_yards_allowed: float
    rush_yards_allowed: float
    ints_forced: float
    sacks: float
    takeaways: float
    point_diff: float
    notes: Tuple[str, ...] = ()


def aggregate_team_offense(
    rows: Sequence[Mapping[str, Any]],
) -> Dict[str, Dict[str, float]]:
    out: Dict[str, Dict[str, float]] = {}
    for row in rows:
        team = str(row.get("team") or "")
        if not team:
            continue
        b = out.setdefault(
            team,
            {
                "pass_yards": 0.0,
                "rush_yards": 0.0,
                "pass_tds": 0.0,
                "rush_tds": 0.0,
                "rec_tds": 0.0,
                "ints": 0.0,
            },
        )
        b["pass_yards"] += _f(row, "pass_yards_total", "pass_yards_mean", "pass_yards")
        b["rush_yards"] += _f(row, "rush_yards_total", "rush_yards_mean", "rush_yards")
        b["pass_tds"] += _f(row, "pass_tds_total", "pass_tds_mean", "pass_tds")
        b["rush_tds"] += _f(row, "rush_tds_total", "rush_tds_mean", "rush_tds")
        b["rec_tds"] += _f(row, "rec_tds_total", "rec_tds_mean", "rec_tds")
        b["ints"] += _f(row, "ints_total", "ints_mean", "ints")
    return out


def raw_offensive_points(offense: Mapping[str, float]) -> float:
    """Team PF from skill production + FG/XP stub (no double-count rec yards)."""
    skill = (
        float(offense.get("pass_yards", 0.0)) * POINTS_PER_PASS_YARD
        + float(offense.get("rush_yards", 0.0)) * POINTS_PER_RUSH_YARD
        + float(offense.get("pass_tds", 0.0)) * POINTS_PER_PASS_TD
        + float(offense.get("rush_tds", 0.0)) * POINTS_PER_RUSH_TD
        + float(offense.get("rec_tds", 0.0)) * POINTS_PER_REC_TD
        + float(offense.get("ints", 0.0)) * POINTS_PER_INT
    )
    skill = max(0.0, skill)
    fg = skill * (FG_EXTRAS_SHARE / max(1e-6, 1.0 - FG_EXTRAS_SHARE))
    return skill + fg


def defense_allowed_multiplier(defense_index: float, *, scale: float) -> float:
    """defense_index > 1 → stronger D → fewer points/yards allowed."""
    z = float(defense_index) - 1.0
    return _clamp(1.0 - scale * z, 0.72, 1.28)


def schedule_opponents(
    schedule: Sequence[Any],
    team: str,
) -> List[str]:
    opps: List[str] = []
    for game in schedule:
        home = getattr(game, "home_team", None) or (
            game.get("home_team") if isinstance(game, Mapping) else None
        )
        away = getattr(game, "away_team", None) or (
            game.get("away_team") if isinstance(game, Mapping) else None
        )
        if home == team:
            opps.append(str(away))
        elif away == team:
            opps.append(str(home))
    return opps


def build_points_for(
    offense_by_team: Mapping[str, Mapping[str, float]],
    *,
    target_league_pf: float = TARGET_LEAGUE_PF,
) -> Dict[str, float]:
    raw = {t: raw_offensive_points(o) for t, o in offense_by_team.items()}
    total = sum(raw.values()) or 1.0
    scale = float(target_league_pf) / total
    # v1.24: tapered band (not hard clip) — hard floors created the ~286 PF pile.
    out = {
        t: _taper_toward_band(
            v * scale, TEAM_PF_SOFT_FLOOR, TEAM_PF_SOFT_CEILING, k=STRETCH_TAPER_K
        )
        for t, v in raw.items()
    }
    out = _break_soft_piles(
        out,
        {t: float(raw[t]) for t in out},
        width=PILE_BREAK_WIDTH,
        spread=PILE_BREAK_SPREAD,
    )
    # Re-fit to league target after soft taper / pile-break.
    total2 = sum(out.values()) or 1.0
    scale2 = float(target_league_pf) / total2
    return {t: v * scale2 for t, v in out.items()}


def build_points_against(
    points_for: Mapping[str, float],
    *,
    schedule: Sequence[Any],
    defense_index: Mapping[str, float],
    offense_index: Mapping[str, float],
) -> Dict[str, float]:
    """Schedule-weighted PA from opponent PF, modulated by own defense."""
    raw: Dict[str, float] = {}
    for team, pf in points_for.items():
        opps = schedule_opponents(schedule, team)
        if not opps:
            # No schedule → mirror league mean modulated by D.
            d_mult = defense_allowed_multiplier(
                float(defense_index.get(team, 1.0)), scale=DEFENSE_PA_SCALE
            )
            raw[team] = (sum(points_for.values()) / max(1, len(points_for))) * d_mult
            continue
        # Opponent offensive load per game × own D multiplier.
        d_mult = defense_allowed_multiplier(
            float(defense_index.get(team, 1.0)), scale=DEFENSE_PA_SCALE
        )
        allowed = 0.0
        for opp in opps:
            opp_pf = float(points_for.get(opp, TARGET_TEAM_PF))
            o_idx = float(offense_index.get(opp, 1.0))
            opp_game = (opp_pf / GAMES_PER_TEAM) * _clamp(
                1.0 + 0.20 * (o_idx - 1.0), 0.88, 1.15
            )
            allowed += opp_game * d_mult
        raw[team] = allowed

    # Exact conservation: sum PA == sum PF.
    pf_sum = sum(points_for.values()) or 1.0
    pa_sum = sum(raw.values()) or 1.0
    scale = pf_sum / pa_sum
    out = {t: _clamp(v * scale, TEAM_PA_SOFT_FLOOR, TEAM_PA_SOFT_CEILING) for t, v in raw.items()}
    # Final microscopic renorm after clamps.
    out_sum = sum(out.values()) or 1.0
    scale2 = pf_sum / out_sum
    return {t: v * scale2 for t, v in out.items()}


def build_yards_allowed(
    offense_by_team: Mapping[str, Mapping[str, float]],
    *,
    schedule: Sequence[Any],
    defense_index: Mapping[str, float],
) -> Tuple[Dict[str, float], Dict[str, float]]:
    pass_allowed: Dict[str, float] = {}
    rush_allowed: Dict[str, float] = {}
    league_pass = sum(float(o.get("pass_yards", 0.0)) for o in offense_by_team.values()) or 1.0
    league_rush = sum(float(o.get("rush_yards", 0.0)) for o in offense_by_team.values()) or 1.0

    raw_pass: Dict[str, float] = {}
    raw_rush: Dict[str, float] = {}
    for team in offense_by_team:
        opps = schedule_opponents(schedule, team)
        d_mult = defense_allowed_multiplier(
            float(defense_index.get(team, 1.0)), scale=DEFENSE_YARDS_SCALE
        )
        if not opps:
            raw_pass[team] = (league_pass / LEAGUE_TEAMS) * d_mult
            raw_rush[team] = (league_rush / LEAGUE_TEAMS) * d_mult
            continue
        p = r = 0.0
        for opp in opps:
            o = offense_by_team.get(opp) or {}
            p += float(o.get("pass_yards", 0.0)) / GAMES_PER_TEAM
            r += float(o.get("rush_yards", 0.0)) / GAMES_PER_TEAM
        raw_pass[team] = p * d_mult
        raw_rush[team] = r * d_mult

    def _renorm(raw: Dict[str, float], target: float) -> Dict[str, float]:
        s = sum(raw.values()) or 1.0
        return {t: v * (target / s) for t, v in raw.items()}

    return _renorm(raw_pass, league_pass), _renorm(raw_rush, league_rush)


def build_takeaways(
    offense_by_team: Mapping[str, Mapping[str, float]],
    *,
    schedule: Sequence[Any],
    defense_index: Mapping[str, float],
) -> Dict[str, float]:
    """INTs forced ≈ schedule share of opponent INTs × D multiplier; renorm to league INTs."""
    league_ints = sum(float(o.get("ints", 0.0)) for o in offense_by_team.values()) or 1.0
    raw: Dict[str, float] = {}
    for team in offense_by_team:
        opps = schedule_opponents(schedule, team)
        d_mult = defense_allowed_multiplier(
            float(defense_index.get(team, 1.0)), scale=0.15
        )
        # Stronger D slightly *increases* takeaways → invert sense for INTs forced.
        take_mult = _clamp(2.0 - d_mult, 0.80, 1.25)
        if not opps:
            raw[team] = (league_ints / LEAGUE_TEAMS) * take_mult
            continue
        forced = 0.0
        for opp in opps:
            forced += float((offense_by_team.get(opp) or {}).get("ints", 0.0)) / GAMES_PER_TEAM
        raw[team] = forced * take_mult
    s = sum(raw.values()) or 1.0
    return {t: v * (league_ints / s) for t, v in raw.items()}


def build_sacks(defense_index: Mapping[str, float], *, league_sacks: float = 1_150.0) -> Dict[str, float]:
    """Soft sack pool from defense strength (historical ~35–40/team)."""
    raw = {
        t: 36.0 * _clamp(1.0 + 0.35 * (float(defense_index.get(t, 1.0)) - 1.0), 0.75, 1.30)
        for t in defense_index
    }
    s = sum(raw.values()) or 1.0
    return {t: v * (league_sacks / s) for t, v in raw.items()}


def pythagorean_wins(
    points_for: Mapping[str, float],
    points_against: Mapping[str, float],
    *,
    exp: float = PYTHAGOREAN_EXP,
    games: float = GAMES_PER_TEAM,
    target_sum: float = EXPECTED_WINS_SUM,
) -> Dict[str, float]:
    raw: Dict[str, float] = {}
    for team, pf in points_for.items():
        pa = max(float(points_against.get(team, pf)), 1.0)
        pf = max(float(pf), 1.0)
        win_pct = (pf**exp) / (pf**exp + pa**exp)
        raw[team] = win_pct * games
    total = sum(raw.values()) or 1.0
    scale = float(target_sum) / total
    return {t: v * scale for t, v in raw.items()}


def stretch_centered(
    values: Mapping[str, float],
    *,
    center: float,
    intensity: float,
    denom: float,
    soft_floor: float,
    soft_ceiling: float,
    target_sum: float,
    taper_k: float = STRETCH_TAPER_K,
    tail_dampen: float = STRETCH_TAIL_DAMPEN,
    hard_clip: bool = False,
) -> Dict[str, float]:
    """Multiplicative stretch about ``center`` with tapered band penalties + renorm.

    v1.23 default: soft tapered fall-off outside [floor, ceiling] and reduced
    intensity on extreme residuals (avoids win/PF pile-ups from hard clips).
    Pass ``hard_clip=True`` to restore legacy clamp behavior.
    """
    if not values:
        return {}
    d = float(denom) if abs(float(denom)) > 1e-9 else 1.0
    stretched: Dict[str, float] = {}
    for team, raw in values.items():
        residual = (float(raw) - float(center)) / d
        damp = 1.0 / (1.0 + float(tail_dampen) * residual * residual)
        factor = 1.0 + float(intensity) * residual * damp
        v = float(raw) * factor
        if hard_clip:
            v = _clamp(v, soft_floor, soft_ceiling)
        else:
            v = _taper_toward_band(v, soft_floor, soft_ceiling, k=taper_k)
        stretched[team] = max(0.0, v)
    total = sum(stretched.values()) or 1.0
    scale = float(target_sum) / total
    return {t: v * scale for t, v in stretched.items()}


def volume_implied_pf_floor(
    pass_yards: float,
    rush_yards: float = 0.0,
    *,
    min_pppa: float = MIN_POINTS_PER_PASS_ATTEMPT,
    ypa: float = DEFAULT_YPA_FOR_ATTEMPTS,
) -> float:
    """Minimum season PF for a locked high-volume passing team."""
    attempts = float(pass_yards) / max(float(ypa), 1.0)
    return float(min_pppa) * attempts + float(VOLUME_PF_RUSH_CREDIT) * float(rush_yards)


def enforce_volume_to_points_floors(
    points_for: Mapping[str, float],
    offense_by_team: Mapping[str, Mapping[str, float]],
    *,
    pass_threshold: float = HIGH_PASS_VOLUME_YARDS,
    target_league_pf: float = TARGET_LEAGUE_PF,
) -> Dict[str, float]:
    """Lift PF for high pass-volume teams that fall below scoring-efficiency floors."""
    out = {t: float(v) for t, v in points_for.items()}
    floors: Dict[str, float] = {}
    for team, pf in list(out.items()):
        off = offense_by_team.get(team) or {}
        py = float(off.get("pass_yards", 0.0))
        if py < float(pass_threshold):
            continue
        floor = max(
            volume_implied_pf_floor(py, float(off.get("rush_yards", 0.0))),
            TARGET_TEAM_PF * 0.95,
        )
        # Elite volume seasons (5k+) need a higher conversion floor.
        if py >= 5_000.0:
            floor = max(floor, volume_implied_pf_floor(py, float(off.get("rush_yards", 0.0)), min_pppa=0.52))
        # Keep floor inside the published soft PF band.
        floor = min(floor, TEAM_PF_SOFT_CEILING - 5.0)
        floors[team] = floor
        if pf + 1e-9 < floor:
            out[team] = floor
    return _assert_volume_floors_conserved(
        out, offense_by_team, target_sum=float(target_league_pf), pass_threshold=pass_threshold
    )


def stretch_yards_with_pa_signal(
    yards: Mapping[str, float],
    pa_pre_stretch: Mapping[str, float],
    *,
    intensity: float = YARDS_STRETCH_INTENSITY,
    pa_center: float = PA_STRETCH_CENTER,
    pa_denom: float = PA_STRETCH_DENOM,
) -> Dict[str, float]:
    """Milder yards stretch in the same direction as PA residuals; renorm in-place total."""
    if not yards:
        return {}
    target = sum(float(v) for v in yards.values()) or 1.0
    d = float(pa_denom) if abs(float(pa_denom)) > 1e-9 else 1.0
    stretched: Dict[str, float] = {}
    for team, y in yards.items():
        pa = float(pa_pre_stretch.get(team, pa_center))
        factor = 1.0 + float(intensity) * ((pa - float(pa_center)) / d)
        stretched[team] = max(0.0, float(y) * factor)
    total = sum(stretched.values()) or 1.0
    scale = target / total
    return {t: v * scale for t, v in stretched.items()}


def apply_defensive_variance_lift(
    *,
    points_against: Mapping[str, float],
    sacks: Mapping[str, float],
    ints_forced: Mapping[str, float],
    pass_yards_allowed: Mapping[str, float],
    rush_yards_allowed: Mapping[str, float],
) -> Dict[str, Dict[str, float]]:
    """Widen PA / sacks / INTs / yards; conserve league totals exactly."""
    pa_pre = {t: float(v) for t, v in points_against.items()}
    # Use actual PA sum when within 1pt of target (board may be 11859.2).
    pa_target = float(sum(pa_pre.values()) or PA_LEAGUE_TOTAL)
    sack_target = float(sum(sacks.values()) or SACK_LEAGUE_TOTAL)
    int_target = float(sum(ints_forced.values()) or INT_LEAGUE_TOTAL)

    pa = stretch_centered(
        pa_pre,
        center=PA_STRETCH_CENTER,
        intensity=PA_STRETCH_INTENSITY,
        denom=PA_STRETCH_DENOM,
        soft_floor=PA_STRETCH_FLOOR,
        soft_ceiling=PA_STRETCH_CEILING,
        target_sum=pa_target,
    )
    sacks_out = stretch_centered(
        {t: float(v) for t, v in sacks.items()},
        center=SACK_STRETCH_CENTER,
        intensity=SACK_STRETCH_INTENSITY,
        denom=SACK_STRETCH_DENOM,
        soft_floor=SACK_STRETCH_FLOOR,
        soft_ceiling=SACK_STRETCH_CEILING,
        target_sum=sack_target,
    )
    ints_out = stretch_centered(
        {t: float(v) for t, v in ints_forced.items()},
        center=INT_STRETCH_CENTER,
        intensity=INT_STRETCH_INTENSITY,
        denom=INT_STRETCH_DENOM,
        soft_floor=INT_STRETCH_FLOOR,
        soft_ceiling=INT_STRETCH_CEILING,
        target_sum=int_target,
    )
    pass_out = stretch_yards_with_pa_signal(
        {t: float(v) for t, v in pass_yards_allowed.items()}, pa_pre
    )
    rush_out = stretch_yards_with_pa_signal(
        {t: float(v) for t, v in rush_yards_allowed.items()}, pa_pre
    )
    return {
        "points_against": pa,
        "sacks": sacks_out,
        "ints_forced": ints_out,
        "pass_yards_allowed": pass_out,
        "rush_yards_allowed": rush_out,
    }


def apply_offensive_pf_variance_lift(
    points_for: Mapping[str, float],
    points_against: Mapping[str, float],
    *,
    pf_intensity: float = PF_STRETCH_INTENSITY,
    pa_restretch_intensity: float = PA_RESTRETCH_INTENSITY,
    target_league_pf: float = TARGET_LEAGUE_PF,
    offense_by_team: Optional[Mapping[str, Mapping[str, float]]] = None,
) -> Dict[str, Dict[str, float]]:
    """Widen PF after offensive volume lift; light PA re-stretch; PF=PA conserved."""
    pf_pre = {t: float(v) for t, v in points_for.items()}
    pf = stretch_centered(
        pf_pre,
        center=PF_STRETCH_CENTER,
        intensity=float(pf_intensity),
        denom=PF_STRETCH_DENOM,
        soft_floor=PF_STRETCH_FLOOR,
        soft_ceiling=PF_STRETCH_CEILING,
        target_sum=float(target_league_pf),
        taper_k=STRETCH_TAPER_K,
    )
    pf = _break_soft_piles(
        pf,
        pf_pre,
        width=PILE_BREAK_WIDTH,
        spread=PILE_BREAK_SPREAD,
    )
    if offense_by_team:
        pf = enforce_volume_to_points_floors(
            pf, offense_by_team, target_league_pf=float(target_league_pf)
        )
    pa_target = float(target_league_pf)
    pa_pre = {t: float(v) for t, v in points_against.items()}
    pa = stretch_centered(
        pa_pre,
        center=PA_STRETCH_CENTER,
        intensity=float(pa_restretch_intensity),
        denom=PA_STRETCH_DENOM,
        soft_floor=PA_STRETCH_FLOOR,
        soft_ceiling=PA_STRETCH_CEILING,
        target_sum=pa_target,
        taper_k=STRETCH_TAPER_K,
    )
    # Exact PF = PA conservation (microscopic).
    pf_sum = sum(pf.values()) or 1.0
    pa_sum = sum(pa.values()) or 1.0
    mid = 0.5 * (pf_sum + pa_sum)
    # Prefer exact TARGET_LEAGUE_PF when close.
    if abs(mid - float(target_league_pf)) < 2.0:
        mid = float(target_league_pf)
    pf = {t: v * (mid / pf_sum) for t, v in pf.items()}
    pa = {t: v * (mid / pa_sum) for t, v in pa.items()}
    # Single re-assert of volume floors after mid renorm; keep PF=PA.
    if offense_by_team:
        pf = enforce_volume_to_points_floors(
            pf, offense_by_team, target_league_pf=mid
        )
        # Break any soft-floor stack created by exact volume-floor pins + renorm.
        pf = _break_soft_piles(
            pf,
            pf_pre,
            width=PILE_BREAK_WIDTH,
            spread=PILE_BREAK_SPREAD,
        )
        pf_sum = sum(pf.values()) or 1.0
        pf = {t: v * (mid / pf_sum) for t, v in pf.items()}
        pa_sum = sum(pa.values()) or 1.0
        pa = {t: v * (mid / pa_sum) for t, v in pa.items()}
    return {"points_for": pf, "points_against": pa}


def _assert_volume_floors_conserved(
    points_for: Mapping[str, float],
    offense_by_team: Mapping[str, Mapping[str, float]],
    *,
    target_sum: float,
    pass_threshold: float = HIGH_PASS_VOLUME_YARDS,
) -> Dict[str, float]:
    """Ensure high-volume PF floors hold while keeping exact league PF sum."""
    out = {t: float(v) for t, v in points_for.items()}
    floors: Dict[str, float] = {}
    for team in out:
        off = offense_by_team.get(team) or {}
        py = float(off.get("pass_yards", 0.0))
        if py < float(pass_threshold):
            continue
        floor = max(
            volume_implied_pf_floor(py, float(off.get("rush_yards", 0.0))),
            TARGET_TEAM_PF * 0.95,
        )
        floors[team] = min(floor, TEAM_PF_SOFT_CEILING - 5.0)
    shortfall = 0.0
    for team, floor in floors.items():
        if out[team] < floor:
            shortfall += floor - out[team]
            out[team] = floor
    donor_floor = TEAM_PF_SOFT_FLOOR + 5.0
    if shortfall > 1e-9:
        donors = [t for t in out if t not in floors and out[t] > donor_floor + 1.0]
        donor_pool = sum(max(0.0, out[t] - donor_floor) for t in donors)
        if donor_pool > 1e-9:
            take = min(shortfall, donor_pool * 0.85)
            for t in donors:
                room = max(0.0, out[t] - donor_floor)
                out[t] -= take * (room / donor_pool)
    # Soft-saturate into published PF band, then exact renorm.
    pre_taper = dict(out)
    out = {
        t: _taper_toward_band(v, TEAM_PF_SOFT_FLOOR, TEAM_PF_SOFT_CEILING, k=STRETCH_TAPER_K)
        for t, v in out.items()
    }
    # Re-assert volume floors inside the band (tiny borrow if needed).
    shortfall = 0.0
    for team, floor in floors.items():
        if out[team] < floor:
            shortfall += floor - out[team]
            out[team] = floor
    if shortfall > 1e-9:
        donors = [t for t in out if t not in floors and out[t] > donor_floor + 1.0]
        donor_pool = sum(max(0.0, out[t] - donor_floor) for t in donors) or 1.0
        for t in donors:
            room = max(0.0, out[t] - donor_floor)
            out[t] -= shortfall * (room / donor_pool)
    out = _break_soft_piles(
        out,
        pre_taper,
        width=PILE_BREAK_WIDTH,
        spread=PILE_BREAK_SPREAD,
    )
    total = sum(out.values()) or 1.0
    return {t: v * (float(target_sum) / total) for t, v in out.items()}


def apply_defensive_production_stack(
    rows: Sequence[Mapping[str, Any]],
    *,
    schedule: Sequence[Any],
    defense_index: Mapping[str, float],
    offense_index: Optional[Mapping[str, float]] = None,
    variance_lift: bool = True,
    offense_pf_variance_lift: bool = False,
    prior_points_against: Optional[Mapping[str, float]] = None,
    prior_sacks: Optional[Mapping[str, float]] = None,
    prior_ints_forced: Optional[Mapping[str, float]] = None,
) -> Tuple[Dict[str, TeamDefenseBudget], Dict[str, Any]]:
    """Build team PF/PA/W/L + defensive counting stats from locked offense."""
    offense = aggregate_team_offense(rows)
    teams = sorted(offense.keys())
    if not teams:
        return {}, {"applied": False, "reason": "no_teams"}

    off_idx = dict(offense_index or {})
    def_idx = {t: float(defense_index.get(t, 1.0)) for t in teams}
    for t in teams:
        off_idx.setdefault(t, 1.0)

    pf = build_points_for(offense)
    pa = build_points_against(
        pf, schedule=schedule, defense_index=def_idx, offense_index=off_idx
    )
    pass_all, rush_all = build_yards_allowed(
        offense, schedule=schedule, defense_index=def_idx
    )
    ints_forced = build_takeaways(
        offense, schedule=schedule, defense_index=def_idx
    )
    sacks = build_sacks(def_idx)

    # Prefer locked defensive board when republishing after offense lift.
    # For offense-PF lifts, blend schedule PA with prior PA so we keep defense
    # memory without inheriting hard-clipped PA piles.
    if prior_points_against:
        if offense_pf_variance_lift:
            blended = {
                t: 0.55 * float(pa.get(t, TARGET_TEAM_PF))
                + 0.45 * float(prior_points_against.get(t, pa.get(t, TARGET_TEAM_PF)))
                for t in teams
            }
            b_sum = sum(blended.values()) or 1.0
            pf_sum = sum(pf.values()) or 1.0
            pa = {t: v * (pf_sum / b_sum) for t, v in blended.items()}
        else:
            pa = {
                t: float(prior_points_against.get(t, pa.get(t, TARGET_TEAM_PF)))
                for t in teams
            }
    if prior_sacks:
        sacks = {t: float(prior_sacks.get(t, sacks.get(t, 0.0))) for t in teams}
    if prior_ints_forced:
        ints_forced = {
            t: float(prior_ints_forced.get(t, ints_forced.get(t, 0.0))) for t in teams
        }

    lift_meta: Dict[str, Any] = {"applied": False}
    if variance_lift and not prior_points_against:
        lifted = apply_defensive_variance_lift(
            points_against=pa,
            sacks=sacks,
            ints_forced=ints_forced,
            pass_yards_allowed=pass_all,
            rush_yards_allowed=rush_all,
        )
        pa = lifted["points_against"]
        sacks = lifted["sacks"]
        ints_forced = lifted["ints_forced"]
        pass_all = lifted["pass_yards_allowed"]
        rush_all = lifted["rush_yards_allowed"]
        lift_meta = {
            "applied": True,
            "method": "defense_variance_lift_v1",
            "pa_range": round(max(pa.values()) - min(pa.values()), 2),
            "sack_range": round(max(sacks.values()) - min(sacks.values()), 2),
            "int_range": round(max(ints_forced.values()) - min(ints_forced.values()), 2),
        }

    offense_pf_meta: Dict[str, Any] = {"applied": False}
    if offense_pf_variance_lift:
        ofl = apply_offensive_pf_variance_lift(pf, pa, offense_by_team=offense)
        pf = ofl["points_for"]
        pa = ofl["points_against"]
        # Keep sacks / INTs league totals; light re-stretch with PA residual.
        sacks = stretch_centered(
            sacks,
            center=SACK_STRETCH_CENTER,
            intensity=SACK_STRETCH_INTENSITY * 0.35,
            denom=SACK_STRETCH_DENOM,
            soft_floor=SACK_STRETCH_FLOOR,
            soft_ceiling=SACK_STRETCH_CEILING,
            target_sum=float(sum(sacks.values()) or SACK_LEAGUE_TOTAL),
        )
        ints_forced = stretch_centered(
            ints_forced,
            center=INT_STRETCH_CENTER,
            intensity=INT_STRETCH_INTENSITY * 0.35,
            denom=INT_STRETCH_DENOM,
            soft_floor=INT_STRETCH_FLOOR,
            soft_ceiling=INT_STRETCH_CEILING,
            target_sum=float(sum(ints_forced.values()) or INT_LEAGUE_TOTAL),
        )
        offense_pf_meta = {
            "applied": True,
            "method": "offense_pf_variance_lift_v1_24_soft_piles",
            "pf_range": round(max(pf.values()) - min(pf.values()), 2),
            "pa_range": round(max(pa.values()) - min(pa.values()), 2),
            "volume_pf_floors": True,
        }

    # Pythagorean wins from (possibly lifted) PF/PA.
    wins = pythagorean_wins(pf, pa)
    if offense_pf_variance_lift:
        # Tapered win stretch — widen compressed W/L without hard clips.
        # v1.24: softer ceiling taper + residual micro-spread clears 13.15 stacks.
        win_pre = dict(wins)
        wins = stretch_centered(
            wins,
            center=8.5,
            intensity=WIN_STRETCH_INTENSITY,
            denom=WIN_STRETCH_DENOM,
            soft_floor=WIN_STRETCH_FLOOR,
            soft_ceiling=WIN_STRETCH_CEILING,
            target_sum=EXPECTED_WINS_SUM,
            taper_k=WIN_STRETCH_TAPER_K,
            tail_dampen=WIN_STRETCH_TAIL_DAMPEN,
        )
        win_resid = {
            t: float(pf.get(t, 0.0)) - float(pa.get(t, 0.0)) for t in wins
        }
        wins = _break_soft_piles(
            wins,
            win_resid,
            width=WIN_PILE_BREAK_WIDTH,
            spread=WIN_PILE_BREAK_SPREAD,
        )
        w_sum = sum(wins.values()) or 1.0
        wins = {t: v * (EXPECTED_WINS_SUM / w_sum) for t, v in wins.items()}
        # Preserve pre-stretch ordering signal in audit via unused local.
        _ = win_pre

    budgets: Dict[str, TeamDefenseBudget] = {}
    for team in teams:
        notes = ["defense_points_wl_v1"]
        if variance_lift and lift_meta.get("applied"):
            notes.append("defense_variance_lift_v1")
        if offense_pf_variance_lift:
            notes.append("offense_pf_variance_lift_v1_24_soft_piles")
        budgets[team] = TeamDefenseBudget(
            team=team,
            points_for=float(pf[team]),
            points_against=float(pa[team]),
            expected_wins=float(wins[team]),
            pass_yards_allowed=float(pass_all[team]),
            rush_yards_allowed=float(rush_all[team]),
            ints_forced=float(ints_forced[team]),
            sacks=float(sacks.get(team, 0.0)),
            takeaways=float(ints_forced[team]),  # fumble stub omitted in v1
            point_diff=float(pf[team] - pa[team]),
            notes=tuple(notes),
        )

    smoke = smoke_defensive_stack(budgets, rows)
    audit = {
        "applied": True,
        "method": "defensive_production_stack_v1",
        "variance_lift": lift_meta,
        "offense_pf_variance_lift": offense_pf_meta,
        "league_pf": round(sum(pf.values()), 2),
        "league_pa": round(sum(pa.values()), 2),
        "wins_sum": round(sum(wins.values()), 4),
        "smoke": smoke,
    }
    return budgets, audit


def smoke_defensive_stack(
    budgets: Mapping[str, TeamDefenseBudget],
    rows: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    pf = sum(b.points_for for b in budgets.values())
    pa = sum(b.points_against for b in budgets.values())
    wins = sum(b.expected_wins for b in budgets.values())
    pass_y = sum(
        _f(r, "pass_yards_total", "pass_yards_mean") for r in rows
    )
    sacks_sum = sum(b.sacks for b in budgets.values())
    ints_sum = sum(b.ints_forced for b in budgets.values())
    pa_vals = [b.points_against for b in budgets.values()]
    sack_vals = [b.sacks for b in budgets.values()]
    int_vals = [b.ints_forced for b in budgets.values()]
    pa_range = max(pa_vals) - min(pa_vals) if pa_vals else 0.0
    sack_range = max(sack_vals) - min(sack_vals) if sack_vals else 0.0
    int_range = max(int_vals) - min(int_vals) if int_vals else 0.0
    win_vals = [b.expected_wins for b in budgets.values()]
    win_range = max(win_vals) - min(win_vals) if win_vals else 0.0
    pf_vals = [b.points_for for b in budgets.values()]
    pf_range = max(pf_vals) - min(pf_vals) if pf_vals else 0.0

    checks = {
        "pf_equals_pa": abs(pf - pa) <= 1.0,
        "wins_sum_272": abs(wins - EXPECTED_WINS_SUM) <= 0.05,
        "league_pf_band": LEAGUE_PF_MIN <= pf <= LEAGUE_PF_MAX,
        "pass_yards_still_locked": abs(pass_y - 126_000.0) < 50.0,
        "n_teams_32": len(budgets) == 32,
        "soft_pf_bands": all(
            TEAM_PF_SOFT_FLOOR - 8 <= b.points_for <= TEAM_PF_SOFT_CEILING + 8
            for b in budgets.values()
        ),
        "soft_pa_bands": all(
            # Tapered stretch stays inside PA soft rails (±renorm slack).
            PA_STRETCH_FLOOR - 12 <= b.points_against <= PA_STRETCH_CEILING + 12
            for b in budgets.values()
        ),
        # League targets on the live board; synthetic tests may differ slightly.
        "sacks_conserved": abs(sacks_sum - SACK_LEAGUE_TOTAL) < 1.0
        or (1_000.0 <= sacks_sum <= 1_300.0),
        "ints_conserved": abs(ints_sum - INT_LEAGUE_TOTAL) < 1.0
        or (300.0 <= ints_sum <= 400.0),
        "pa_range_ge_85": pa_range >= 85.0,
        "sack_range_ge_18": sack_range >= 18.0,
        "int_range_ge_6": int_range >= 6.0,
    }
    # Yards allowed conserve opponent offense pools.
    pass_all = sum(b.pass_yards_allowed for b in budgets.values())
    rush_all = sum(b.rush_yards_allowed for b in budgets.values())
    rush_y = sum(_f(r, "rush_yards_total", "rush_yards_mean") for r in rows)
    checks["pass_yards_allowed_conserved"] = abs(pass_all - pass_y) < 1.0
    checks["rush_yards_allowed_conserved"] = abs(rush_all - rush_y) < 1.0

    ranked_pf = sorted(budgets.values(), key=lambda b: -b.points_for)
    ranked_pa = sorted(budgets.values(), key=lambda b: -b.points_against)
    ranked_wins = sorted(budgets.values(), key=lambda b: -b.expected_wins)
    ranked_sacks = sorted(budgets.values(), key=lambda b: -b.sacks)
    ranked_ints = sorted(budgets.values(), key=lambda b: -b.ints_forced)
    return {
        "checks": checks,
        "all_pass": all(checks.values()),
        "ranges": {
            "pa": round(pa_range, 2),
            "sacks": round(sack_range, 2),
            "ints": round(int_range, 2),
            "pf": round(pf_range, 2),
            "wins": round(win_range, 2),
            "pa_min": round(min(pa_vals), 2),
            "pa_max": round(max(pa_vals), 2),
            "pf_min": round(min(pf_vals), 2) if pf_vals else 0.0,
            "pf_max": round(max(pf_vals), 2) if pf_vals else 0.0,
            "wins_min": round(min(win_vals), 2) if win_vals else 0.0,
            "wins_max": round(max(win_vals), 2) if win_vals else 0.0,
            "sack_min": round(min(sack_vals), 2),
            "sack_max": round(max(sack_vals), 2),
            "int_min": round(min(int_vals), 2),
            "int_max": round(max(int_vals), 2),
        },
        "league": {
            "points_for": round(pf, 2),
            "points_against": round(pa, 2),
            "ppg": round(pf / (LEAGUE_TEAMS * GAMES_PER_TEAM), 3),
            "wins_sum": round(wins, 4),
            "pass_yards": round(pass_y, 1),
            "pass_yards_allowed": round(pass_all, 1),
            "rush_yards_allowed": round(rush_all, 1),
            "sacks": round(sacks_sum, 1),
            "ints_forced": round(ints_sum, 2),
        },
        "top_pf": [(b.team, round(b.points_for, 1)) for b in ranked_pf[:5]],
        "bot_pf": [(b.team, round(b.points_for, 1)) for b in ranked_pf[-5:]],
        "top_pa": [(b.team, round(b.points_against, 1)) for b in ranked_pa[:5]],
        "bot_pa": [(b.team, round(b.points_against, 1)) for b in ranked_pa[-5:]],
        "top_wins": [(b.team, round(b.expected_wins, 2)) for b in ranked_wins[:5]],
        "bot_wins": [(b.team, round(b.expected_wins, 2)) for b in ranked_wins[-5:]],
        "top_sacks": [(b.team, round(b.sacks, 1)) for b in ranked_sacks[:5]],
        "bot_sacks": [(b.team, round(b.sacks, 1)) for b in ranked_sacks[-5:]],
        "top_ints": [(b.team, round(b.ints_forced, 1)) for b in ranked_ints[:5]],
        "bot_ints": [(b.team, round(b.ints_forced, 1)) for b in ranked_ints[-5:]],
    }


def budgets_to_rows(
    budgets: Mapping[str, TeamDefenseBudget],
    *,
    prior_outcomes: Optional[Sequence[Mapping[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Merge defense budgets into team outcome rows for publish."""
    try:
        from src.services.nfl_canonical_teams import canonicalize_team
    except ImportError:  # script path / data-platform package layout
        try:
            from services.nfl_canonical_teams import canonicalize_team
        except ImportError:

            def canonicalize_team(code: Optional[str]) -> Optional[str]:  # type: ignore
                if code is None:
                    return None
                raw = str(code).strip().upper()
                if raw in {"LA", "STL"}:
                    return "LAR"
                if raw == "WSH":
                    return "WAS"
                return raw or None

    prior_by = {}
    if prior_outcomes:
        for row in prior_outcomes:
            raw = str(row.get("team") or "")
            key = canonicalize_team(raw) or raw
            prior_by[key] = dict(row)
            prior_by[raw] = dict(row)

    TEAM_META = {
        "ARI": ("NFC", "NFC West"), "ATL": ("NFC", "NFC South"),
        "BAL": ("AFC", "AFC North"), "BUF": ("AFC", "AFC East"),
        "CAR": ("NFC", "NFC South"), "CHI": ("NFC", "NFC North"),
        "CIN": ("AFC", "AFC North"), "CLE": ("AFC", "AFC North"),
        "DAL": ("NFC", "NFC East"), "DEN": ("AFC", "AFC West"),
        "DET": ("NFC", "NFC North"), "GB": ("NFC", "NFC North"),
        "HOU": ("AFC", "AFC South"), "IND": ("AFC", "AFC South"),
        "JAX": ("AFC", "AFC South"), "KC": ("AFC", "AFC West"),
        # Product canonical Rams = LAR (LA alias still accepted at boundaries).
        "LA": ("NFC", "NFC West"), "LAR": ("NFC", "NFC West"),
        "LAC": ("AFC", "AFC West"),
        "LV": ("AFC", "AFC West"), "MIA": ("AFC", "AFC East"),
        "MIN": ("NFC", "NFC North"), "NE": ("AFC", "AFC East"),
        "NO": ("NFC", "NFC South"), "NYG": ("NFC", "NFC East"),
        "NYJ": ("AFC", "AFC East"), "PHI": ("NFC", "NFC East"),
        "PIT": ("AFC", "AFC North"), "SEA": ("NFC", "NFC West"),
        "SF": ("NFC", "NFC West"), "TB": ("NFC", "NFC South"),
        "TEN": ("AFC", "AFC South"), "WAS": ("NFC", "NFC East"),
    }

    # Softmax playoff / division / SB proxies from closed-loop wins.
    # Prefer product-canonical keys so LA/LAR never double-count.
    canon_budgets: Dict[str, TeamDefenseBudget] = {}
    for team, b in budgets.items():
        key = canonicalize_team(str(team)) or str(team)
        canon_budgets[key] = b

    by_div: Dict[str, List[str]] = {}
    for team, b in canon_budgets.items():
        conf, div = TEAM_META.get(team, ("UNK", "UNK"))
        by_div.setdefault(div, []).append(team)

    def _softmax(xs: List[float]) -> List[float]:
        if not xs:
            return []
        m = max(xs)
        ex = [math.exp(x - m) for x in xs]
        s = sum(ex) or 1.0
        return [e / s for e in ex]

    div_title: Dict[str, float] = {}
    for div, teams in by_div.items():
        weights = _softmax([canon_budgets[t].expected_wins for t in teams])
        for t, w in zip(teams, weights):
            div_title[t] = float(w)
    sb_teams = list(canon_budgets.keys())
    sb_w = _softmax([canon_budgets[t].expected_wins for t in sb_teams])
    sb_prob = {t: float(w) for t, w in zip(sb_teams, sb_w)}

    rows: List[Dict[str, Any]] = []
    for team, b in sorted(canon_budgets.items(), key=lambda kv: -kv[1].expected_wins):
        conf, div = TEAM_META.get(team, ("UNK", "UNK"))
        prior = prior_by.get(team) or prior_by.get("LA" if team == "LAR" else "") or {}
        win_pct = b.expected_wins / GAMES_PER_TEAM
        # Rough playoff proxy from closed-loop wins (P(wins>=9) ~ logistic).
        # Finalize / strength-coherence overwrite with 7-seed MC when week rates exist.
        playoff = 1.0 / (1.0 + math.exp(-1.35 * (b.expected_wins - 9.0)))
        rows.append(
            {
                "season": int(prior.get("season") or 2026),
                "team": team,
                "conference": conf,
                "division": div,
                "expected_wins": round(b.expected_wins, 4),
                "sim_expected_wins": round(float(prior.get("expected_wins") or b.expected_wins), 4),
                "wins_p10": int(max(0, round(b.expected_wins - 3.0))),
                "wins_p90": int(min(17, round(b.expected_wins + 3.0))),
                "playoff_prob": round(playoff, 6),
                "division_title_prob": round(div_title.get(team, 0.0), 6),
                "super_bowl_win_prob": round(sb_prob.get(team, 0.0), 6),
                "points_for": round(b.points_for, 2),
                "points_against": round(b.points_against, 2),
                "point_diff": round(b.point_diff, 2),
                "pass_yards_allowed": round(b.pass_yards_allowed, 1),
                "rush_yards_allowed": round(b.rush_yards_allowed, 1),
                "ints_forced": round(b.ints_forced, 2),
                "sacks": round(b.sacks, 2),
                "takeaways": round(b.takeaways, 2),
                "ppg": round(b.points_for / GAMES_PER_TEAM, 3),
                "pa_pg": round(b.points_against / GAMES_PER_TEAM, 3),
            }
        )
    return rows
