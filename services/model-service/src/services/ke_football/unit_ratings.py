"""KE Off/Def Efficiency unit ratings (Phase 2A).

Hierarchy: plays → measurements → unit ratings → (later) team strength.
Does not weight Team Strength. Does not reopen opponent adjustment.
Does not fit ATS / close / ROI / CLV.

Complexity must beat the strongest constituent (trailing EPA). If it does
not, the published candidate is shrunken or raw EPA — that is acceptable.
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any, Dict, List, Optional, Sequence, Tuple

from src.services.ke_football.aggregate import TeamGame
from src.services.ke_football.provenance import (
    THIN_GAMES_STD,
    THIN_PLAYS_STD,
    Layer,
    Status,
    derived,
    modeled,
    omitted,
)
from src.services.ke_football.unit_features import (
    EPA_ID,
    assert_not_excluded,
    pass_core_ids,
    trailing_metric,
    trailing_n,
    trailing_vector,
    teams_at,
)
from src.services.ke_football.validation import _corr, _mae

FORBIDDEN_OBJECTIVES = ("ats", "close", "roi", "kei", "clv", "market_residual", "issue_562")
UNIT_IDS = {"off": "ke.off_unit", "def": "ke.def_unit"}


def _mean(xs: Sequence[float]) -> Optional[float]:
    if not xs:
        return None
    return sum(xs) / len(xs)


def _sd(xs: Sequence[float]) -> Optional[float]:
    if len(xs) < 2:
        return None
    mu = sum(xs) / len(xs)
    var = sum((x - mu) ** 2 for x in xs) / len(xs)
    return math.sqrt(var) if var > 0 else None


def _solve(A: List[List[float]], b: List[float]) -> Optional[List[float]]:
    n = len(b)
    if n == 0 or any(len(row) != n for row in A):
        return None
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(M[r][col]))
        if abs(M[pivot][col]) < 1e-12:
            return None
        if pivot != col:
            M[col], M[pivot] = M[pivot], M[col]
        div = M[col][col]
        for j in range(col, n + 1):
            M[col][j] /= div
        for r in range(n):
            if r == col:
                continue
            fac = M[r][col]
            for j in range(col, n + 1):
                M[r][j] -= fac * M[col][j]
    return [M[i][n] for i in range(n)]


def ridge_fit(X: Sequence[Sequence[float]], y: Sequence[float], *, lam: float) -> Optional[List[float]]:
    """Intercept + slopes. λ applies to slopes only."""
    n = len(y)
    if n < 3 or not X or len(X[0]) == 0:
        return None
    p = len(X[0])
    # Design: [1, x1, ..., xp]
    xtx = [[0.0] * (p + 1) for _ in range(p + 1)]
    xty = [0.0] * (p + 1)
    for i in range(n):
        row = [1.0] + list(X[i])
        for a in range(p + 1):
            xty[a] += row[a] * y[i]
            for b in range(p + 1):
                xtx[a][b] += row[a] * row[b]
    for j in range(1, p + 1):
        xtx[j][j] += float(lam)
    return _solve(xtx, xty)


def pca_loadings(X: Sequence[Sequence[float]]) -> Optional[List[float]]:
    """First principal component via power iteration on covariance."""
    if not X or not X[0]:
        return None
    n = len(X)
    p = len(X[0])
    if n < 3:
        return None
    mus = [_mean([row[j] for row in X]) for j in range(p)]
    if any(m is None for m in mus):
        return None
    C = [[0.0] * p for _ in range(p)]
    for row in X:
        d = [row[j] - float(mus[j]) for j in range(p)]
        for a in range(p):
            for b in range(p):
                C[a][b] += d[a] * d[b]
    for a in range(p):
        for b in range(p):
            C[a][b] /= n
    v = [1.0] * p
    for _ in range(40):
        nv = [sum(C[i][j] * v[j] for j in range(p)) for i in range(p)]
        norm = math.sqrt(sum(x * x for x in nv))
        if norm < 1e-12:
            return None
        v = [x / norm for x in nv]
    return v


def shrink(value: Optional[float], n: float, k: float, league: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    if league is None or k <= 0:
        return value
    w = n / (n + k) if (n + k) else 0.0
    return w * value + (1.0 - w) * league


class LeagueZ:
    """PIT league mean/sd of trailing features at as_of_week."""

    def __init__(self, mu: Dict[str, float], sd: Dict[str, float], epa_mu: float, epa_sd: float):
        self.mu = mu
        self.sd = sd
        self.epa_mu = epa_mu
        self.epa_sd = epa_sd

    def z(self, cid: str, value: Optional[float], *, higher_better: bool) -> Optional[float]:
        if value is None or cid not in self.sd or self.sd[cid] <= 0:
            return None
        raw = (value - self.mu[cid]) / self.sd[cid]
        return raw if higher_better else -raw

    def to_epa(self, z_bar: float, *, side: str) -> float:
        if side == "def":
            return self.epa_mu - z_bar * self.epa_sd
        return self.epa_mu + z_bar * self.epa_sd


_ZCACHE: Dict[Tuple[int, int, Tuple[str, ...]], Optional[LeagueZ]] = {}


def clear_z_cache() -> None:
    _ZCACHE.clear()


def league_z(
    games: Sequence[TeamGame],
    *,
    sport: str,
    side: str,
    as_of_week: int,
    cids: Sequence[str],
    higher: Dict[str, bool],
) -> Optional[LeagueZ]:
    key = (id(games), as_of_week, tuple(cids))
    if key in _ZCACHE:
        return _ZCACHE[key]
    teams = teams_at(games, as_of_week=as_of_week)
    cols: Dict[str, List[float]] = {c: [] for c in cids}
    epa_id = EPA_ID[side]
    epa_vals: List[float] = []
    for team in teams:
        vec = trailing_vector(games, team=team, as_of_week=as_of_week, cids=list(cids) + [epa_id])
        for cid in cids:
            if vec.get(cid) is not None:
                cols[cid].append(float(vec[cid]))
        if vec.get(epa_id) is not None:
            epa_vals.append(float(vec[epa_id]))
    mu: Dict[str, float] = {}
    sd: Dict[str, float] = {}
    for cid in cids:
        m = _mean(cols[cid])
        s = _sd(cols[cid])
        if m is None or s is None:
            continue
        mu[cid] = m
        sd[cid] = s
    epa_mu = _mean(epa_vals)
    epa_sd = _sd(epa_vals)
    if epa_mu is None or epa_sd is None or epa_sd <= 0:
        _ZCACHE[key] = None
        return None
    book = LeagueZ(mu, sd, epa_mu, epa_sd)
    _ZCACHE[key] = book
    return book


def _z_mean(
    vec: Dict[str, Optional[float]],
    zbook: LeagueZ,
    cids: Sequence[str],
    higher: Dict[str, bool],
) -> Optional[float]:
    zs = []
    for cid in cids:
        z = zbook.z(cid, vec.get(cid), higher_better=higher.get(cid, True))
        if z is not None:
            zs.append(z)
    if not zs:
        return None
    return sum(zs) / len(zs)


def _higher_map(sport: str, side: str, cids: Sequence[str]) -> Dict[str, bool]:
    from src.services.ke_football.unit_features import LOWER_BETTER

    return {cid: cid not in LOWER_BETTER for cid in cids}


class MethodFit:
    """Frozen selection-window artifacts. Confirmation never refits."""

    def __init__(self) -> None:
        self.shrink_k: float = 40.0
        self.ridge_lam: float = 16.0
        self.ridge_beta: Optional[List[float]] = None
        self.ridge_cids: List[str] = []
        self.pca_w: Optional[List[float]] = None
        self.pca_cids: List[str] = []
        self.earned_partial: List[str] = []
        self.notes: Dict[str, Any] = {}


def _pairs_for_method(
    games: Sequence[TeamGame],
    *,
    sport: str,
    side: str,
    week_min: int,
    week_max: int,
    predict,
) -> List[Tuple[float, float]]:
    by_week: Dict[int, List[TeamGame]] = defaultdict(list)
    for g in games:
        by_week[g.week].append(g)
    pairs: List[Tuple[float, float]] = []
    cache: Dict[Tuple[str, int], Optional[float]] = {}
    for w in sorted(by_week):
        if w < week_min or w > week_max:
            continue
        for g in by_week[w]:
            actual = g.def_epa if side == "def" else g.off_epa
            if actual is None:
                continue
            key = (g.team, w)
            if key not in cache:
                cache[key] = predict(team=g.team, as_of_week=w)
            pred = cache[key]
            if pred is None:
                continue
            pairs.append((pred, actual))
    return pairs


def _epa_predict(games, *, team, as_of_week, side, k=0.0, league_by_week=None):
    cid = EPA_ID[side]
    raw = trailing_metric(games, team=team, as_of_week=as_of_week, cid=cid)
    if k <= 0:
        return raw
    n_games, n_plays = trailing_n(games, team=team, as_of_week=as_of_week, side=side)
    league = None
    if league_by_week:
        league = league_by_week.get(as_of_week)
    return shrink(raw, float(n_plays), k, league)


def _league_epa_by_week(games: Sequence[TeamGame], side: str) -> Dict[int, float]:
    cid = EPA_ID[side]
    weeks = sorted({g.week for g in games})
    out: Dict[int, float] = {}
    for w in weeks:
        vals = []
        for team in teams_at(games, as_of_week=w):
            v = trailing_metric(games, team=team, as_of_week=w, cid=cid)
            if v is not None:
                vals.append(v)
        mu = _mean(vals)
        if mu is not None:
            out[w] = mu
    return out


def fit_selection(
    games: Sequence[TeamGame],
    *,
    sport: str,
    side: str,
    selection_weeks: Tuple[int, int],
) -> MethodFit:
    """Fit shrink k, earned PARTIAL set, ridge, PCA on the selection window only."""
    from src.services.ke_football.unit_features import specs_for

    fit = MethodFit()
    higher = {s.cid: s.higher_better for s in specs_for(sport, side)}
    core = pass_core_ids(sport, side)
    partial = [s.cid for s in specs_for(sport, side) if s.grade == "PARTIAL"]
    assert_not_excluded(core + partial, sport=sport)

    league_by_week = _league_epa_by_week(games, side)
    # Shrink k: pick on selection MAE vs next-game EPA.
    best_k = 0.0
    best_mae = None
    for k in (0.0, 20.0, 40.0, 80.0, 160.0):
        pairs = _pairs_for_method(
            games,
            sport=sport,
            side=side,
            week_min=selection_weeks[0],
            week_max=selection_weeks[1],
            predict=lambda team, as_of_week, k=k: _epa_predict(
                games, team=team, as_of_week=as_of_week, side=side, k=k, league_by_week=league_by_week
            ),
        )
        mae = _mae(pairs)
        if mae is None:
            continue
        if best_mae is None or mae < best_mae:
            best_mae = mae
            best_k = k
    fit.shrink_k = best_k
    fit.notes["shrink_k_selection_mae"] = best_mae

    # Incremental PARTIAL gate: z_pass vs z_pass+feature on selection MAE.
    def z_predict(cids, team, as_of_week):
        zbook = league_z(games, sport=sport, side=side, as_of_week=as_of_week, cids=cids, higher=higher)
        if zbook is None:
            return None
        vec = trailing_vector(games, team=team, as_of_week=as_of_week, cids=cids)
        if any(vec.get(c) is None for c in core if c in cids):
            return _epa_predict(games, team=team, as_of_week=as_of_week, side=side, k=fit.shrink_k, league_by_week=league_by_week)
        zb = _z_mean(vec, zbook, cids, higher)
        if zb is None:
            return None
        return zbook.to_epa(zb, side=side)

    base_pairs = _pairs_for_method(
        games,
        sport=sport,
        side=side,
        week_min=selection_weeks[0],
        week_max=selection_weeks[1],
        predict=lambda team, as_of_week: z_predict(core, team, as_of_week),
    )
    base_mae = _mae(base_pairs)
    earned: List[str] = []
    earned_notes: Dict[str, Any] = {}
    for cid in partial:
        trial = core + [cid]
        pairs = _pairs_for_method(
            games,
            sport=sport,
            side=side,
            week_min=selection_weeks[0],
            week_max=selection_weeks[1],
            predict=lambda team, as_of_week, trial=trial: z_predict(trial, team, as_of_week),
        )
        mae = _mae(pairs)
        improve = False
        if base_mae and mae is not None and mae <= base_mae * 0.99:
            improve = True
        earned_notes[cid] = {"selection_mae": mae, "base_mae": base_mae, "earned": improve}
        if improve:
            earned.append(cid)
    fit.earned_partial = earned
    fit.notes["partial_gate"] = earned_notes
    fit.notes["finishing_earned"] = {
        cid: cid in earned for cid in ("ke.ppo", "ke.finish") if cid in partial
    }

    # Ridge + PCA on earned feature set (core + earned partial).
    feat = core + earned
    fit.ridge_cids = feat
    fit.pca_cids = feat
    X: List[List[float]] = []
    y: List[float] = []
    Xp: List[List[float]] = []
    by_week: Dict[int, List[TeamGame]] = defaultdict(list)
    for g in games:
        by_week[g.week].append(g)
    zbooks: Dict[int, LeagueZ] = {}
    for w in sorted(by_week):
        if w < selection_weeks[0] or w > selection_weeks[1]:
            continue
        zb = league_z(games, sport=sport, side=side, as_of_week=w, cids=feat, higher=higher)
        if zb is None:
            continue
        zbooks[w] = zb
        for g in by_week[w]:
            actual = g.def_epa if side == "def" else g.off_epa
            if actual is None:
                continue
            vec = trailing_vector(games, team=g.team, as_of_week=w, cids=feat)
            if any(vec.get(c) is None for c in feat):
                continue
            zs = [zb.z(c, vec[c], higher_better=higher[c]) for c in feat]
            if any(z is None for z in zs):
                continue
            X.append([float(z) for z in zs])
            y.append(float(actual))
            Xp.append([float(z) for z in zs])

    best_lam = 16.0
    best_ridge_mae = None
    best_beta = None
    for lam in (1.0, 4.0, 16.0, 64.0):
        beta = ridge_fit(X, y, lam=lam)
        if beta is None:
            continue
        # in-sample selection MAE (hyperparameter only; confirmation is frozen)
        hats = []
        for row, yi in zip(X, y):
            pred = beta[0] + sum(beta[j + 1] * row[j] for j in range(len(row)))
            hats.append((pred, yi))
        mae = _mae(hats)
        if mae is not None and (best_ridge_mae is None or mae < best_ridge_mae):
            best_ridge_mae = mae
            best_lam = lam
            best_beta = beta
    fit.ridge_lam = best_lam
    fit.ridge_beta = best_beta
    fit.notes["ridge_selection_mae"] = best_ridge_mae
    fit.pca_w = pca_loadings(Xp)
    if fit.pca_w is not None and X:
        # Align PC with EPA (higher z-mean → better; offense higher EPA, defense lower).
        scores = [sum(fit.pca_w[j] * row[j] for j in range(len(fit.pca_w))) for row in X]
        r = _corr(scores, y)
        if r is not None and ((side == "off" and r < 0) or (side == "def" and r > 0)):
            fit.pca_w = [-w for w in fit.pca_w]
    return fit


def predict_method(
    games: Sequence[TeamGame],
    *,
    sport: str,
    side: str,
    team: str,
    as_of_week: int,
    method: str,
    fit: MethodFit,
) -> Optional[float]:
    from src.services.ke_football.unit_features import specs_for

    higher = {s.cid: s.higher_better for s in specs_for(sport, side)}
    core = pass_core_ids(sport, side)
    league_by_week = None  # computed lazily below for shrink only
    if method == "epa_raw":
        return trailing_metric(games, team=team, as_of_week=as_of_week, cid=EPA_ID[side])
    if method == "epa_shrunken":
        raw = trailing_metric(games, team=team, as_of_week=as_of_week, cid=EPA_ID[side])
        _n_g, n_plays = trailing_n(games, team=team, as_of_week=as_of_week, side=side)
        vals = []
        for t in teams_at(games, as_of_week=as_of_week):
            v = trailing_metric(games, team=t, as_of_week=as_of_week, cid=EPA_ID[side])
            if v is not None:
                vals.append(v)
        return shrink(raw, float(n_plays), fit.shrink_k, _mean(vals))
    if method in {"z_pass", "z_earned"}:
        cids = core if method == "z_pass" else core + fit.earned_partial
        zbook = league_z(games, sport=sport, side=side, as_of_week=as_of_week, cids=cids, higher=higher)
        if zbook is None:
            return None
        vec = trailing_vector(games, team=team, as_of_week=as_of_week, cids=cids)
        if any(vec.get(c) is None for c in core):
            return predict_method(
                games, sport=sport, side=side, team=team, as_of_week=as_of_week, method="epa_shrunken", fit=fit
            )
        zb = _z_mean(vec, zbook, cids, higher)
        if zb is None:
            return None
        return zbook.to_epa(zb, side=side)
    if method == "pca_earned":
        cids = fit.pca_cids or core
        if not fit.pca_w or len(fit.pca_w) != len(cids):
            return None
        zbook = league_z(games, sport=sport, side=side, as_of_week=as_of_week, cids=cids, higher=higher)
        if zbook is None:
            return None
        vec = trailing_vector(games, team=team, as_of_week=as_of_week, cids=cids)
        if any(vec.get(c) is None for c in cids):
            return predict_method(
                games, sport=sport, side=side, team=team, as_of_week=as_of_week, method="epa_shrunken", fit=fit
            )
        zs = [zbook.z(c, vec[c], higher_better=higher[c]) for c in cids]
        if any(z is None for z in zs):
            return None
        score = sum(fit.pca_w[j] * float(zs[j]) for j in range(len(cids)))
        return zbook.to_epa(score, side=side)
    if method == "ridge_earned":
        cids = fit.ridge_cids or core
        if not fit.ridge_beta or len(fit.ridge_beta) != len(cids) + 1:
            return None
        zbook = league_z(games, sport=sport, side=side, as_of_week=as_of_week, cids=cids, higher=higher)
        if zbook is None:
            return None
        vec = trailing_vector(games, team=team, as_of_week=as_of_week, cids=cids)
        if any(vec.get(c) is None for c in cids):
            return predict_method(
                games, sport=sport, side=side, team=team, as_of_week=as_of_week, method="epa_shrunken", fit=fit
            )
        zs = [zbook.z(c, vec[c], higher_better=higher[c]) for c in cids]
        if any(z is None for z in zs):
            return None
        return fit.ridge_beta[0] + sum(fit.ridge_beta[j + 1] * float(zs[j]) for j in range(len(cids)))
    raise KeyError(method)


METHODS = ("epa_raw", "epa_shrunken", "z_pass", "z_earned", "pca_earned", "ridge_earned")


def method_layer(method: str) -> str:
    if method in {"epa_raw", "epa_shrunken", "z_pass", "z_earned"}:
        return Layer.DERIVED.value
    return Layer.MODELED.value


def contributions(
    games: Sequence[TeamGame],
    *,
    sport: str,
    side: str,
    team: str,
    as_of_week: int,
    fit: MethodFit,
    method: str,
) -> Dict[str, Any]:
    from src.services.ke_football.unit_features import specs_for

    higher = {s.cid: s.higher_better for s in specs_for(sport, side)}
    core = pass_core_ids(sport, side)
    cids = core if method in {"epa_raw", "epa_shrunken", "z_pass"} else core + fit.earned_partial
    zbook = league_z(games, sport=sport, side=side, as_of_week=as_of_week, cids=cids, higher=higher)
    vec = trailing_vector(games, team=team, as_of_week=as_of_week, cids=cids)
    rows = []
    for cid in cids:
        z = zbook.z(cid, vec.get(cid), higher_better=higher.get(cid, True)) if zbook else None
        rows.append(
            {
                "id": cid,
                "value": vec.get(cid),
                "z": z,
                "earned_partial": cid in fit.earned_partial,
                "grade": next((s.grade for s in specs_for(sport, side) if s.cid == cid), None),
            }
        )
    return {
        "method": method,
        "earned_partial": list(fit.earned_partial),
        "features": rows,
        "shrink_k": fit.shrink_k,
        "ridge_lam": fit.ridge_lam if method == "ridge_earned" else None,
        "ridge_beta": fit.ridge_beta if method == "ridge_earned" else None,
        "pca_loadings": fit.pca_w if method == "pca_earned" else None,
    }


def unit_cell(
    games: Sequence[TeamGame],
    *,
    sport: str,
    side: str,
    team: str,
    as_of_week: int,
    method: str,
    fit: MethodFit,
) -> Dict[str, Any]:
    value = predict_method(
        games, sport=sport, side=side, team=team, as_of_week=as_of_week, method=method, fit=fit
    )
    n_games, n_plays = trailing_n(games, team=team, as_of_week=as_of_week, side=side)
    uid = UNIT_IDS[side]
    unit = "epa_per_play" if side == "off" else "epa_per_play_allowed"
    notes = {
        "method": method,
        "layer_reason": method_layer(method),
        "shrink_k": fit.shrink_k,
        "earned_partial": list(fit.earned_partial),
        "not_team_strength": True,
        "opp_adj_used": False,
        "forbidden_objectives": list(FORBIDDEN_OBJECTIVES),
        "n_games": n_games,
        "n_plays": n_plays,
        "sample_strength": (n_plays / (n_plays + fit.shrink_k)) if (n_plays + fit.shrink_k) else 0.0,
        "higher_better": side == "off",
    }
    layer = method_layer(method)
    if layer == Layer.MODELED.value:
        cell = modeled(uid, value, unit=unit, n=n_plays, thin_n=THIN_PLAYS_STD, notes=notes)
    else:
        cell = derived(uid, value, unit=unit, n=n_plays, thin_n=THIN_PLAYS_STD, notes=notes)
    if n_games < THIN_GAMES_STD and cell.value is not None:
        cell.status = Status.THIN
        cell.notes["thin_games"] = n_games
    blob = cell.to_dict()
    blob["contributions"] = contributions(
        games, sport=sport, side=side, team=team, as_of_week=as_of_week, fit=fit, method=method
    )
    return blob


def snapshot_book(
    games: Sequence[TeamGame],
    *,
    sport: str,
    season: int,
    as_of_week: int,
    fits: Dict[str, MethodFit],
    methods: Dict[str, str],
) -> List[Dict[str, Any]]:
    teams = teams_at(games, as_of_week=as_of_week)
    out = []
    for team in teams:
        off = unit_cell(
            games,
            sport=sport,
            side="off",
            team=team,
            as_of_week=as_of_week,
            method=methods["off"],
            fit=fits["off"],
        )
        deff = unit_cell(
            games,
            sport=sport,
            side="def",
            team=team,
            as_of_week=as_of_week,
            method=methods["def"],
            fit=fits["def"],
        )
        out.append(
            {
                "sport": sport,
                "season": season,
                "as_of_week": as_of_week,
                "cutoff": "week < as_of_week",
                "team": team,
                "components": {
                    "ke.off_unit": off,
                    "ke.def_unit": deff,
                    "ke.team_strength": omitted(
                        "ke.team_strength",
                        unit="net_epa_per_play",
                        reason="Phase 2A hard stop — unit ratings only, no Team Strength",
                    ).to_dict(),
                },
                "production_promote": False,
            }
        )
    return out
