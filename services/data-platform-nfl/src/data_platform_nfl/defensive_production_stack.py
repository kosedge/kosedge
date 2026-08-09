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


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


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
    out = {t: _clamp(v * scale, TEAM_PF_SOFT_FLOOR, TEAM_PF_SOFT_CEILING) for t, v in raw.items()}
    # Re-fit to league target after soft clamps.
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


def apply_defensive_production_stack(
    rows: Sequence[Mapping[str, Any]],
    *,
    schedule: Sequence[Any],
    defense_index: Mapping[str, float],
    offense_index: Optional[Mapping[str, float]] = None,
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
    wins = pythagorean_wins(pf, pa)
    pass_all, rush_all = build_yards_allowed(
        offense, schedule=schedule, defense_index=def_idx
    )
    ints_forced = build_takeaways(
        offense, schedule=schedule, defense_index=def_idx
    )
    sacks = build_sacks(def_idx)

    budgets: Dict[str, TeamDefenseBudget] = {}
    for team in teams:
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
            notes=("defense_points_wl_v1",),
        )

    smoke = smoke_defensive_stack(budgets, rows)
    audit = {
        "applied": True,
        "method": "defensive_production_stack_v1",
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
    checks = {
        "pf_equals_pa": abs(pf - pa) <= 1.0,
        "wins_sum_272": abs(wins - EXPECTED_WINS_SUM) <= 0.05,
        "league_pf_band": LEAGUE_PF_MIN <= pf <= LEAGUE_PF_MAX,
        "pass_yards_still_locked": abs(pass_y - 126_000.0) < 50.0,
        "n_teams_32": len(budgets) == 32,
        "soft_pf_bands": all(
            TEAM_PF_SOFT_FLOOR - 1 <= b.points_for <= TEAM_PF_SOFT_CEILING + 1
            for b in budgets.values()
        ),
        "soft_pa_bands": all(
            TEAM_PA_SOFT_FLOOR - 1 <= b.points_against <= TEAM_PA_SOFT_CEILING + 1
            for b in budgets.values()
        ),
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
    return {
        "checks": checks,
        "all_pass": all(checks.values()),
        "league": {
            "points_for": round(pf, 2),
            "points_against": round(pa, 2),
            "ppg": round(pf / (LEAGUE_TEAMS * GAMES_PER_TEAM), 3),
            "wins_sum": round(wins, 4),
            "pass_yards": round(pass_y, 1),
            "pass_yards_allowed": round(pass_all, 1),
            "rush_yards_allowed": round(rush_all, 1),
            "sacks": round(sum(b.sacks for b in budgets.values()), 1),
            "ints_forced": round(sum(b.ints_forced for b in budgets.values()), 2),
        },
        "top_pf": [(b.team, round(b.points_for, 1)) for b in ranked_pf[:5]],
        "bot_pf": [(b.team, round(b.points_for, 1)) for b in ranked_pf[-5:]],
        "top_pa": [(b.team, round(b.points_against, 1)) for b in ranked_pa[:5]],
        "bot_pa": [(b.team, round(b.points_against, 1)) for b in ranked_pa[-5:]],
        "top_wins": [(b.team, round(b.expected_wins, 2)) for b in ranked_wins[:5]],
        "bot_wins": [(b.team, round(b.expected_wins, 2)) for b in ranked_wins[-5:]],
    }


def budgets_to_rows(
    budgets: Mapping[str, TeamDefenseBudget],
    *,
    prior_outcomes: Optional[Sequence[Mapping[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Merge defense budgets into team outcome rows for publish."""
    prior_by = {}
    if prior_outcomes:
        for row in prior_outcomes:
            prior_by[str(row.get("team") or "")] = dict(row)

    TEAM_META = {
        "ARI": ("NFC", "NFC West"), "ATL": ("NFC", "NFC South"),
        "BAL": ("AFC", "AFC North"), "BUF": ("AFC", "AFC East"),
        "CAR": ("NFC", "NFC South"), "CHI": ("NFC", "NFC North"),
        "CIN": ("AFC", "AFC North"), "CLE": ("AFC", "AFC North"),
        "DAL": ("NFC", "NFC East"), "DEN": ("AFC", "AFC West"),
        "DET": ("NFC", "NFC North"), "GB": ("NFC", "NFC North"),
        "HOU": ("AFC", "AFC South"), "IND": ("AFC", "AFC South"),
        "JAX": ("AFC", "AFC South"), "KC": ("AFC", "AFC West"),
        "LA": ("NFC", "NFC West"), "LAC": ("AFC", "AFC West"),
        "LV": ("AFC", "AFC West"), "MIA": ("AFC", "AFC East"),
        "MIN": ("NFC", "NFC North"), "NE": ("AFC", "AFC East"),
        "NO": ("NFC", "NFC South"), "NYG": ("NFC", "NFC East"),
        "NYJ": ("AFC", "AFC East"), "PHI": ("NFC", "NFC East"),
        "PIT": ("AFC", "AFC North"), "SEA": ("NFC", "NFC West"),
        "SF": ("NFC", "NFC West"), "TB": ("NFC", "NFC South"),
        "TEN": ("AFC", "AFC South"), "WAS": ("NFC", "NFC East"),
    }

    # Softmax playoff / division / SB proxies from closed-loop wins.
    by_div: Dict[str, List[str]] = {}
    for team, b in budgets.items():
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
        weights = _softmax([budgets[t].expected_wins for t in teams])
        for t, w in zip(teams, weights):
            div_title[t] = float(w)
    sb_teams = list(budgets.keys())
    sb_w = _softmax([budgets[t].expected_wins for t in sb_teams])
    sb_prob = {t: float(w) for t, w in zip(sb_teams, sb_w)}

    rows: List[Dict[str, Any]] = []
    for team, b in sorted(budgets.items(), key=lambda kv: -kv[1].expected_wins):
        conf, div = TEAM_META.get(team, ("UNK", "UNK"))
        prior = prior_by.get(team) or {}
        win_pct = b.expected_wins / GAMES_PER_TEAM
        # Rough playoff proxy from closed-loop wins (P(wins>=9) ~ logistic).
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
