"""Per-component measurement validation (Phase 1B).

NFL and CFB are evaluated separately. Objectives are football-only:
next-game EPA / success / explosiveness / finishing / pace. ATS, close,
ROI, CLV, and market residuals are forbidden.

No composite weights. Incremental-on-EPA is reported, not used to drop
a valid distinct construct.
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from src.services.ke_football.aggregate import TeamGame, snapshots_for_week
from src.services.ke_football.plays import CanonicalPlay
from src.services.ke_football.validation import _bias, _corr, _mae, _rmse

FORBIDDEN_OBJECTIVES = ("ats", "close", "roi", "kei", "clv", "issue_562", "market_residual")

# Trailing snapshot → next-game football targets (not ATS).
OWN_UNIT = "own_unit"
EPA_OFF = "next_off_epa"
EPA_DEF = "next_def_epa"
SUCCESS = "next_success"
EXPL = "next_expl"
FINISH = "next_finish"
PPO = "next_ppo"


def _rate(n: float, d: float) -> Optional[float]:
    if d <= 0:
        return None
    return n / d


def _quantile(xs: Sequence[float], q: float) -> Optional[float]:
    if not xs:
        return None
    ys = sorted(xs)
    if len(ys) == 1:
        return ys[0]
    pos = q * (len(ys) - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return ys[lo]
    return ys[lo] * (hi - pos) + ys[hi] * (pos - lo)


def _spearman(xs: Sequence[float], ys: Sequence[float]) -> Optional[float]:
    if len(xs) < 3 or len(xs) != len(ys):
        return None

    def ranks(vals: Sequence[float]) -> List[float]:
        order = sorted(range(len(vals)), key=lambda i: vals[i])
        out = [0.0] * len(vals)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and vals[order[j + 1]] == vals[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                out[order[k]] = avg
            i = j + 1
        return out

    return _corr(ranks(xs), ranks(ys))


def team_game_metric(g: TeamGame, cid: str) -> Optional[float]:
    """Native team-game value. None if the denominator is empty."""
    if cid == "ke.off_eff":
        return g.off_epa
    if cid == "ke.def_eff":
        return g.def_epa
    if cid == "ke.success_native":
        return _rate(g.success_n, g.success_d)
    if cid == "ke.success_standard":
        return _rate(g.std_n, g.std_d)
    if cid == "ke.success_allowed":
        return _rate(g.success_allowed_n, g.success_allowed_d)
    if cid == "ke.pace":
        return float(g.n_off_plays) if g.n_off_plays else None
    if cid == "ke.pace_competitive":
        return float(g.comp_plays) if g.n_off_plays else None
    if cid == "ke.pace_seconds":
        return (sum(g.clock_deltas) / len(g.clock_deltas)) if g.clock_deltas else None
    if cid == "ke.expl":
        return _rate(g.expl_n, g.expl_d)
    if cid == "ke.expl_pass":
        return _rate(g.expl_pass_n, g.expl_pass_d)
    if cid == "ke.expl_rush":
        return _rate(g.expl_rush_n, g.expl_rush_d)
    if cid == "ke.expl_allowed":
        return _rate(g.expl_allowed_n, g.expl_allowed_d)
    if cid == "ke.off_pass_epa":
        return _rate(g.pass_epa_sum, g.pass_epa_n)
    if cid == "ke.off_rush_epa":
        return _rate(g.rush_epa_sum, g.rush_epa_n)
    if cid == "ke.off_early_epa":
        return _rate(g.early_epa_sum, g.early_epa_n)
    if cid == "ke.ppo":
        return _rate(g.opp_points, g.n_opp)
    if cid == "ke.finish":
        return _rate(g.finished_opp, g.n_opp)
    if cid == "ke.opp_rate":
        return _rate(g.n_opp, g.n_drives)
    if cid == "ke.rz_td":
        return _rate(g.rz_td, g.rz_plays)
    if cid == "ke.st":
        return _rate(g.st_epa_sum, g.st_n) if g.sport == "nfl" else None
    return None


# Components validated independently. Disruption / havoc handled separately
# so sparse flags cannot become a 1.0 rate via this path.
COMPONENT_SPECS: List[Dict[str, Any]] = [
    {"id": "ke.off_eff", "family": "epa", "side": "off", "higher_better": True, "oos_targets": [OWN_UNIT, EPA_OFF]},
    {"id": "ke.def_eff", "family": "epa", "side": "def", "higher_better": False, "oos_targets": [OWN_UNIT, EPA_DEF]},
    {
        "id": "ke.success_native",
        "family": "success",
        "side": "off",
        "higher_better": True,
        "oos_targets": [OWN_UNIT, EPA_OFF, SUCCESS],
    },
    {
        "id": "ke.success_standard",
        "family": "success",
        "side": "off",
        "higher_better": True,
        "oos_targets": [OWN_UNIT, EPA_OFF, SUCCESS],
    },
    {
        "id": "ke.success_allowed",
        "family": "success",
        "side": "def",
        "higher_better": False,
        "oos_targets": [OWN_UNIT, EPA_DEF],
    },
    {"id": "ke.pace", "family": "pace", "side": "off", "higher_better": None, "oos_targets": [OWN_UNIT]},
    {
        "id": "ke.pace_competitive",
        "family": "pace",
        "side": "off",
        "higher_better": None,
        "oos_targets": [OWN_UNIT],
    },
    {"id": "ke.pace_seconds", "family": "pace", "side": "off", "higher_better": None, "oos_targets": [OWN_UNIT]},
    {"id": "ke.expl", "family": "expl", "side": "off", "higher_better": True, "oos_targets": [OWN_UNIT, EPA_OFF, EXPL]},
    {
        "id": "ke.expl_pass",
        "family": "expl",
        "side": "off",
        "higher_better": True,
        "oos_targets": [OWN_UNIT, EPA_OFF],
    },
    {
        "id": "ke.expl_rush",
        "family": "expl",
        "side": "off",
        "higher_better": True,
        "oos_targets": [OWN_UNIT, EPA_OFF],
    },
    {
        "id": "ke.expl_allowed",
        "family": "expl",
        "side": "def",
        "higher_better": False,
        "oos_targets": [OWN_UNIT, EPA_DEF],
    },
    {
        "id": "ke.off_pass_epa",
        "family": "epa_split",
        "side": "off",
        "higher_better": True,
        "oos_targets": [OWN_UNIT, EPA_OFF],
    },
    {
        "id": "ke.off_rush_epa",
        "family": "epa_split",
        "side": "off",
        "higher_better": True,
        "oos_targets": [OWN_UNIT, EPA_OFF],
    },
    {
        "id": "ke.off_early_epa",
        "family": "epa_split",
        "side": "off",
        "higher_better": True,
        "oos_targets": [OWN_UNIT, EPA_OFF],
    },
    {"id": "ke.ppo", "family": "finishing", "side": "off", "higher_better": True, "oos_targets": [OWN_UNIT, EPA_OFF, PPO]},
    {
        "id": "ke.finish",
        "family": "finishing",
        "side": "off",
        "higher_better": True,
        "oos_targets": [OWN_UNIT, EPA_OFF, FINISH],
    },
    {
        "id": "ke.opp_rate",
        "family": "finishing",
        "side": "off",
        "higher_better": True,
        "oos_targets": [OWN_UNIT, EPA_OFF],
    },
    {"id": "ke.rz_td", "family": "finishing", "side": "off", "higher_better": True, "oos_targets": [OWN_UNIT, EPA_OFF]},
    {"id": "ke.st", "family": "st", "side": "st", "higher_better": True, "oos_targets": [OWN_UNIT, EPA_OFF]},
]


def _trailing(
    games: Sequence[TeamGame],
    *,
    team: str,
    as_of_week: int,
    cid: str,
) -> Optional[float]:
    mine = [g for g in games if g.team == team and g.week < as_of_week]
    vals = [(team_game_metric(g, cid), _weight(g, cid)) for g in mine]
    usable = [(v, w) for v, w in vals if v is not None and w > 0]
    if not usable:
        return None
    den = sum(w for _v, w in usable)
    return sum(v * w for v, w in usable) / den


def _weight(g: TeamGame, cid: str) -> int:
    if cid in {"ke.off_eff", "ke.off_pass_epa", "ke.off_rush_epa", "ke.off_early_epa"}:
        return g.off_epa_n
    if cid == "ke.def_eff":
        return g.def_epa_n
    if cid in {"ke.success_native"}:
        return g.success_d
    if cid == "ke.success_standard":
        return g.std_d
    if cid == "ke.success_allowed":
        return g.success_allowed_d
    if cid in {"ke.expl"}:
        return g.expl_d
    if cid == "ke.expl_pass":
        return g.expl_pass_d
    if cid == "ke.expl_rush":
        return g.expl_rush_d
    if cid == "ke.expl_allowed":
        return g.expl_allowed_d
    if cid in {"ke.ppo", "ke.finish"}:
        return g.n_opp
    if cid == "ke.opp_rate":
        return g.n_drives
    if cid == "ke.rz_td":
        return g.rz_plays
    if cid == "ke.st":
        return g.st_n
    if cid == "ke.pace_seconds":
        return len(g.clock_deltas)
    return max(g.n_off_plays, 1)


def _target(g: TeamGame, name: str) -> Optional[float]:
    if name == OWN_UNIT:
        return None  # filled by caller with the component's own next-game value
    if name == EPA_OFF:
        return g.off_epa
    if name == EPA_DEF:
        return g.def_epa
    if name == SUCCESS:
        return _rate(g.success_n, g.success_d)
    if name == EXPL:
        return _rate(g.expl_n, g.expl_d)
    if name == FINISH:
        return _rate(g.finished_opp, g.n_opp)
    if name == PPO:
        return _rate(g.opp_points, g.n_opp)
    return None


def _pack_pairs(pairs: Sequence[Tuple[float, float]]) -> Dict[str, Any]:
    if len(pairs) < 2:
        return {"n": len(pairs), "mae": _mae(pairs), "rmse": _rmse(pairs), "bias": _bias(pairs), "pearson": None}
    xs = [a for a, _b in pairs]
    ys = [b for _a, b in pairs]
    return {
        "n": len(pairs),
        "mae": _mae(pairs),
        "rmse": _rmse(pairs),
        "bias": _bias(pairs),
        "pearson": _corr(xs, ys),
        "spearman": _spearman(xs, ys),
    }


def _ols_residualize(x: Sequence[float], y: Sequence[float]) -> List[float]:
    """y residual after univariate OLS on x (with intercept)."""
    n = len(x)
    if n < 3:
        return []
    mx = sum(x) / n
    my = sum(y) / n
    var = sum((xi - mx) ** 2 for xi in x)
    if var <= 0:
        return [yi - my for yi in y]
    b = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y)) / var
    a = my - b * mx
    return [yi - (a + b * xi) for xi, yi in zip(x, y)]


def sample_size_curve(games: Sequence[TeamGame], cid: str) -> List[Dict[str, Any]]:
    """Split-half: first n games vs next n games, play-weighted means."""
    by_team: Dict[str, List[TeamGame]] = defaultdict(list)
    for g in games:
        by_team[g.team].append(g)
    for rows in by_team.values():
        rows.sort(key=lambda g: (g.week, g.game_id))
    out: List[Dict[str, Any]] = []
    for n in (1, 2, 3, 4, 6, 8, 10):
        xs: List[float] = []
        ys: List[float] = []
        for rows in by_team.values():
            if len(rows) < 2 * n:
                continue
            a = _play_mean(rows[:n], cid)
            b = _play_mean(rows[n : 2 * n], cid)
            if a is None or b is None:
                continue
            xs.append(a)
            ys.append(b)
        out.append(
            {
                "n_prior_games": n,
                "n_teams": len(xs),
                "pearson": _corr(xs, ys) if len(xs) >= 3 else None,
                "spearman": _spearman(xs, ys),
            }
        )
    return out


def _play_mean(rows: Sequence[TeamGame], cid: str) -> Optional[float]:
    vals = [(team_game_metric(g, cid), _weight(g, cid)) for g in rows]
    usable = [(v, w) for v, w in vals if v is not None and w > 0]
    if not usable:
        return None
    den = sum(w for _v, w in usable)
    return sum(v * w for v, w in usable) / den


def early_late_persistence(
    games: Sequence[TeamGame],
    cid: str,
    *,
    early_through: int,
    late_from: int,
) -> Dict[str, Any]:
    by_team: Dict[str, List[TeamGame]] = defaultdict(list)
    for g in games:
        by_team[g.team].append(g)
    xs: List[float] = []
    ys: List[float] = []
    for rows in by_team.values():
        early = [g for g in rows if g.week <= early_through]
        late = [g for g in rows if g.week >= late_from]
        a = _play_mean(early, cid)
        b = _play_mean(late, cid)
        if a is None or b is None:
            continue
        xs.append(a)
        ys.append(b)
    return {
        "early_through_week": early_through,
        "late_from_week": late_from,
        "n_teams": len(xs),
        "pearson": _corr(xs, ys) if len(xs) >= 3 else None,
        "spearman": _spearman(xs, ys),
    }


def week_to_week(games: Sequence[TeamGame], cid: str) -> Dict[str, Any]:
    by_week: Dict[int, Dict[str, float]] = defaultdict(dict)
    for g in games:
        val = team_game_metric(g, cid)
        if val is None:
            continue
        by_week[g.week][g.team] = val
    weeks = sorted(by_week)
    pairs: List[Dict[str, Any]] = []
    for a, b in zip(weeks, weeks[1:]):
        teams = [t for t in by_week[a] if t in by_week[b]]
        xs = [by_week[a][t] for t in teams]
        ys = [by_week[b][t] for t in teams]
        pairs.append({"from": a, "to": b, "n": len(teams), "pearson": _corr(xs, ys) if len(teams) >= 3 else None})
    late = [p["pearson"] for p in pairs if p["from"] >= 8 and p["pearson"] is not None]
    return {
        "pairs": pairs,
        "late_mean_pearson": (sum(late) / len(late)) if late else None,
        "early_pair": pairs[0] if pairs else None,
    }


def oos_predict(
    games: Sequence[TeamGame],
    cid: str,
    targets: Sequence[str],
    *,
    min_as_of: int = 3,
) -> Dict[str, Any]:
    by_week: Dict[int, List[TeamGame]] = defaultdict(list)
    for g in games:
        by_week[g.week].append(g)
    out: Dict[str, Any] = {}
    for tgt in targets:
        pairs: List[Tuple[float, float]] = []
        for w, rows in by_week.items():
            if w < min_as_of:
                continue
            for g in rows:
                pred = _trailing(games, team=g.team, as_of_week=w, cid=cid)
                actual = team_game_metric(g, cid) if tgt == OWN_UNIT else _target(g, tgt)
                if pred is None or actual is None:
                    continue
                pairs.append((pred, actual))
        out[tgt] = _pack_pairs(pairs)
    return out


def incremental_on_epa(games: Sequence[TeamGame], cid: str, *, min_as_of: int = 3) -> Dict[str, Any]:
    """Does trailing component add next-game EPA signal after trailing EPA?"""
    spec = next((s for s in COMPONENT_SPECS if s["id"] == cid), None)
    side = (spec or {}).get("side")
    epa_cid = "ke.off_eff" if side != "def" else "ke.def_eff"
    target_fn: Callable[[TeamGame], Optional[float]] = (lambda g: g.def_epa) if side == "def" else (lambda g: g.off_epa)
    xs: List[float] = []
    ys: List[float] = []
    zs: List[float] = []
    by_week: Dict[int, List[TeamGame]] = defaultdict(list)
    for g in games:
        by_week[g.week].append(g)
    for w, rows in by_week.items():
        if w < min_as_of:
            continue
        for g in rows:
            epa_hat = _trailing(games, team=g.team, as_of_week=w, cid=epa_cid)
            z_hat = _trailing(games, team=g.team, as_of_week=w, cid=cid)
            y = target_fn(g)
            if epa_hat is None or z_hat is None or y is None:
                continue
            xs.append(epa_hat)
            ys.append(y)
            zs.append(z_hat)
    resid = _ols_residualize(xs, ys)
    if len(resid) < 3:
        return {"n": len(zs), "partial_pearson": None, "note": "insufficient pairs"}
    return {
        "n": len(resid),
        "partial_pearson": _corr(zs, resid),
        "base_epa_pearson": _corr(xs, ys),
        "raw_component_pearson": _corr(zs, ys),
        "conditioned_on": epa_cid,
        "target": "next_def_epa" if side == "def" else "next_off_epa",
    }


def distribution(games: Sequence[TeamGame], cid: str) -> Dict[str, Any]:
    by_team: Dict[str, List[float]] = defaultdict(list)
    for g in games:
        val = team_game_metric(g, cid)
        if val is None:
            continue
        by_team[g.team].append(val)
    team_means = {t: sum(vs) / len(vs) for t, vs in by_team.items() if vs}
    xs = list(team_means.values())
    if not xs:
        return {"n_teams": 0}
    mu = sum(xs) / len(xs)
    var = sum((x - mu) ** 2 for x in xs) / len(xs)
    sd = math.sqrt(var)
    p05 = _quantile(xs, 0.05)
    p95 = _quantile(xs, 0.95)
    outliers = []
    if sd > 0:
        for team, val in team_means.items():
            z = (val - mu) / sd
            if abs(z) >= 2.5:
                outliers.append({"team": team, "value": val, "z": z})
    outliers.sort(key=lambda r: -abs(r["z"]))
    return {
        "n_teams": len(xs),
        "n_team_games": sum(len(v) for v in by_team.values()),
        "mean": mu,
        "sd": sd,
        "min": min(xs),
        "p05": p05,
        "p50": _quantile(xs, 0.50),
        "p95": p95,
        "max": max(xs),
        "outliers_z25": outliers[:8],
    }


def missingness_by_week(games: Sequence[TeamGame], cid: str) -> Dict[str, Any]:
    by_week: Dict[int, Dict[str, int]] = defaultdict(lambda: {"present": 0, "missing": 0})
    for g in games:
        if team_game_metric(g, cid) is None:
            by_week[g.week]["missing"] += 1
        else:
            by_week[g.week]["present"] += 1
    weeks = []
    for w in sorted(by_week):
        tot = by_week[w]["present"] + by_week[w]["missing"]
        weeks.append(
            {
                "week": w,
                "present": by_week[w]["present"],
                "missing": by_week[w]["missing"],
                "missing_rate": (by_week[w]["missing"] / tot) if tot else None,
            }
        )
    tot_p = sum(w["present"] for w in weeks)
    tot_m = sum(w["missing"] for w in weeks)
    return {
        "weeks": weeks,
        "season_missing_rate": (tot_m / (tot_p + tot_m)) if (tot_p + tot_m) else None,
    }


def off_def_symmetry(games: Sequence[TeamGame]) -> Dict[str, Any]:
    """League identity: mean off EPA ≈ mean def EPA (same plays, opposite sides)."""
    offs = [g.off_epa for g in games if g.off_epa is not None]
    defs = [g.def_epa for g in games if g.def_epa is not None]
    team_off: Dict[str, List[float]] = defaultdict(list)
    team_def: Dict[str, List[float]] = defaultdict(list)
    for g in games:
        if g.off_epa is not None:
            team_off[g.team].append(g.off_epa)
        if g.def_epa is not None:
            team_def[g.team].append(g.def_epa)
    teams = sorted(set(team_off) & set(team_def))
    xs = [sum(team_off[t]) / len(team_off[t]) for t in teams]
    ys = [sum(team_def[t]) / len(team_def[t]) for t in teams]
    return {
        "league_mean_off_epa": (sum(offs) / len(offs)) if offs else None,
        "league_mean_def_epa": (sum(defs) / len(defs)) if defs else None,
        "identity_gap": (
            abs((sum(offs) / len(offs)) - (sum(defs) / len(defs))) if offs and defs else None
        ),
        "team_off_def_pearson": _corr(xs, ys) if len(xs) >= 3 else None,
        "n_teams": len(teams),
        "note": "same-play identity: league off mean should match league def mean",
    }


def correlation_matrix(games: Sequence[TeamGame], cids: Sequence[str]) -> Dict[str, Any]:
    by_team: Dict[str, Dict[str, float]] = defaultdict(dict)
    for cid in cids:
        means: Dict[str, List[float]] = defaultdict(list)
        for g in games:
            val = team_game_metric(g, cid)
            if val is None:
                continue
            means[g.team].append(val)
        for team, vs in means.items():
            by_team[team][cid] = sum(vs) / len(vs)
    matrix: Dict[str, Dict[str, Optional[float]]] = {}
    for a in cids:
        matrix[a] = {}
        for b in cids:
            xs: List[float] = []
            ys: List[float] = []
            for row in by_team.values():
                if a in row and b in row:
                    xs.append(row[a])
                    ys.append(row[b])
            matrix[a][b] = _corr(xs, ys) if len(xs) >= 3 else None
    return {"n_teams": len(by_team), "pearson": matrix}


def snapshot_missingness(
    plays: Sequence[CanonicalPlay],
    *,
    sport: str,
    season: int,
    as_of_week: int,
) -> Dict[str, Any]:
    snaps = snapshots_for_week(plays, sport=sport, season=season, as_of_week=as_of_week)
    counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for snap in snaps:
        for cid, cell in (snap.get("components") or {}).items():
            counts[cid][str(cell.get("status"))] += 1
    return {cid: dict(st) for cid, st in counts.items()}


def validate_component(
    games: Sequence[TeamGame],
    spec: Dict[str, Any],
    *,
    sport: str,
    early_through: int,
    late_from: int,
) -> Dict[str, Any]:
    cid = spec["id"]
    if sport != "nfl" and cid == "ke.st":
        return {
            "id": cid,
            "family": spec["family"],
            "sport": sport,
            "status_hint": "DATA_INSUFFICIENT",
            "reason": "CFB ST uncertified — omit; do not manufacture",
            "forbidden_objectives": list(FORBIDDEN_OBJECTIVES),
        }
    return {
        "id": cid,
        "family": spec["family"],
        "side": spec["side"],
        "higher_better": spec["higher_better"],
        "sport": sport,
        "forbidden_objectives": list(FORBIDDEN_OBJECTIVES),
        "sample_size_curve": sample_size_curve(games, cid),
        "week_to_week": week_to_week(games, cid),
        "early_late_persistence": early_late_persistence(
            games, cid, early_through=early_through, late_from=late_from
        ),
        "oos": oos_predict(games, cid, spec["oos_targets"]),
        "incremental_on_epa": incremental_on_epa(games, cid),
        "distribution": distribution(games, cid),
        "missingness": missingness_by_week(games, cid),
    }


def validate_all_components(
    games: Sequence[TeamGame],
    *,
    sport: str,
    season: int,
    early_through: int,
    late_from: int,
) -> Dict[str, Any]:
    rows = [
        validate_component(
            games, spec, sport=sport, early_through=early_through, late_from=late_from
        )
        for spec in COMPONENT_SPECS
    ]
    cids = [s["id"] for s in COMPONENT_SPECS if not (sport != "nfl" and s["id"] == "ke.st")]
    return {
        "sport": sport,
        "season": season,
        "forbidden_objectives": list(FORBIDDEN_OBJECTIVES),
        "n_team_games": len(games),
        "components": rows,
        "correlation_matrix": correlation_matrix(games, cids),
        "off_def_symmetry": off_def_symmetry(games),
        "production_promote": False,
        "no_composite_weights": True,
    }
