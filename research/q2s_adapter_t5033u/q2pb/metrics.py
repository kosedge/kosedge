"""DEV-only maps, screens, ICC, and EVAL bootstrap (no post-EVAL tuning)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np

from .data import Game, parse_record, win_pct


@dataclass
class LinearMap:
    a: float
    b: float
    n: int

    def predict(self, x: np.ndarray) -> np.ndarray:
        return self.a + self.b * np.asarray(x, dtype=float)


@dataclass
class LogisticMap:
    c: float
    d: float
    n: int
    n_ties_excluded: int

    def predict(self, x: np.ndarray) -> np.ndarray:
        z = self.c + self.d * np.asarray(x, dtype=float)
        z = np.clip(z, -30.0, 30.0)
        return 1.0 / (1.0 + np.exp(-z))


def ols(x: Sequence[float], y: Sequence[float]) -> LinearMap:
    xa = np.asarray(x, dtype=float)
    ya = np.asarray(y, dtype=float)
    mask = np.isfinite(xa) & np.isfinite(ya)
    xa, ya = xa[mask], ya[mask]
    n = int(xa.size)
    if n < 2:
        return LinearMap(a=float(ya.mean()) if n else 0.0, b=0.0, n=n)
    xm = xa.mean()
    ym = ya.mean()
    den = float(((xa - xm) ** 2).sum())
    b = float(((xa - xm) * (ya - ym)).sum() / den) if den > 0 else 0.0
    a = float(ym - b * xm)
    return LinearMap(a=a, b=b, n=n)


def logistic_mle(x: Sequence[float], y: Sequence[float], n_ties: int) -> LogisticMap:
    """IRLS logistic. y in {0,1}. Ties already excluded by caller."""
    xa = np.asarray(x, dtype=float)
    ya = np.asarray(y, dtype=float)
    mask = np.isfinite(xa) & np.isfinite(ya)
    xa, ya = xa[mask], ya[mask]
    n = int(xa.size)
    if n < 2 or ya.min() == ya.max():
        p = float(ya.mean()) if n else 0.5
        p = min(max(p, 1e-6), 1 - 1e-6)
        c = float(np.log(p / (1 - p)))
        return LogisticMap(c=c, d=0.0, n=n, n_ties_excluded=n_ties)
    # design [1, x]
    X = np.column_stack([np.ones(n), xa])
    beta = np.zeros(2, dtype=float)
    for _ in range(40):
        z = np.clip(X @ beta, -30.0, 30.0)
        p = 1.0 / (1.0 + np.exp(-z))
        w = np.clip(p * (1.0 - p), 1e-9, None)
        grad = X.T @ (ya - p)
        hess = X.T @ (X * w[:, None])
        try:
            delta = np.linalg.solve(hess, grad)
        except np.linalg.LinAlgError:
            delta = np.linalg.lstsq(hess, grad, rcond=None)[0]
        beta = beta + delta
        if float(np.max(np.abs(delta))) < 1e-10:
            break
    return LogisticMap(c=float(beta[0]), d=float(beta[1]), n=n, n_ties_excluded=n_ties)


def ranks(x: np.ndarray) -> np.ndarray:
    order = np.argsort(x, kind="mergesort")
    ranks_out = np.empty_like(x, dtype=float)
    i = 0
    n = x.size
    while i < n:
        j = i
        while j + 1 < n and x[order[j + 1]] == x[order[i]]:
            j += 1
        avg = 0.5 * (i + j) + 1.0
        ranks_out[order[i : j + 1]] = avg
        i = j + 1
    return ranks_out


def pearson(x: Sequence[float], y: Sequence[float]) -> float:
    xa = np.asarray(x, dtype=float)
    ya = np.asarray(y, dtype=float)
    mask = np.isfinite(xa) & np.isfinite(ya)
    xa, ya = xa[mask], ya[mask]
    if xa.size < 2:
        return float("nan")
    xa = xa - xa.mean()
    ya = ya - ya.mean()
    den = float(np.sqrt((xa @ xa) * (ya @ ya)))
    if den == 0:
        return float("nan")
    return float((xa @ ya) / den)


def spearman(x: Sequence[float], y: Sequence[float]) -> float:
    xa = np.asarray(x, dtype=float)
    ya = np.asarray(y, dtype=float)
    mask = np.isfinite(xa) & np.isfinite(ya)
    xa, ya = xa[mask], ya[mask]
    if xa.size < 2:
        return float("nan")
    return pearson(ranks(xa), ranks(ya))


def mae(yhat: Sequence[float], y: Sequence[float]) -> float:
    a = np.asarray(yhat, dtype=float)
    b = np.asarray(y, dtype=float)
    return float(np.mean(np.abs(a - b)))


def rmse(yhat: Sequence[float], y: Sequence[float]) -> float:
    a = np.asarray(yhat, dtype=float)
    b = np.asarray(y, dtype=float)
    return float(np.sqrt(np.mean((a - b) ** 2)))


def brier(p: Sequence[float], y: Sequence[float]) -> float:
    a = np.asarray(p, dtype=float)
    b = np.asarray(y, dtype=float)
    return float(np.mean((a - b) ** 2))


def icc_oneway(residuals: Sequence[float], groups: Sequence[str]) -> dict[str, float]:
    """One-way random-effects ICC on residuals, grouped by team-season."""
    by: dict[str, list[float]] = {}
    for r, g in zip(residuals, groups):
        if not np.isfinite(r):
            continue
        by.setdefault(g, []).append(float(r))
    groups_v = [np.asarray(v, dtype=float) for v in by.values() if len(v) >= 1]
    k = len(groups_v)
    if k < 2:
        return {"icc": float("nan"), "k": k, "N": 0, "n0": float("nan")}
    N = int(sum(v.size for v in groups_v))
    grand = float(np.concatenate(groups_v).mean())
    ssb = 0.0
    ssw = 0.0
    sum_n2 = 0.0
    for v in groups_v:
        ni = v.size
        sum_n2 += ni * ni
        m = float(v.mean())
        ssb += ni * (m - grand) ** 2
        ssw += float(((v - m) ** 2).sum())
    dfb = k - 1
    dfw = N - k
    if dfw <= 0:
        return {"icc": float("nan"), "k": k, "N": N, "n0": float("nan")}
    msb = ssb / dfb
    msw = ssw / dfw
    n0 = (N - sum_n2 / N) / dfb
    icc = (msb - msw) / (msb + (n0 - 1.0) * msw) if (msb + (n0 - 1.0) * msw) != 0 else float("nan")
    return {
        "icc": float(icc),
        "k": float(k),
        "N": float(N),
        "n0": float(n0),
        "msb": float(msb),
        "msw": float(msw),
    }


def cluster_bootstrap(
    values: np.ndarray,
    cluster_ids: Sequence[str],
    stat_fn,
    *,
    B: int,
    seed: int,
) -> dict[str, float]:
    """Resample clusters with replacement; apply stat_fn to concatenated rows."""
    clusters: dict[str, list[int]] = {}
    for i, cid in enumerate(cluster_ids):
        clusters.setdefault(str(cid), []).append(i)
    keys = list(clusters)
    idx_groups = [np.asarray(clusters[k], dtype=int) for k in keys]
    rng = np.random.default_rng(seed)
    stats = np.empty(B, dtype=float)
    k = len(idx_groups)
    for b in range(B):
        draw = rng.integers(0, k, size=k)
        take = np.concatenate([idx_groups[j] for j in draw])
        stats[b] = float(stat_fn(values[take]))
    return {
        "mean": float(stats.mean()),
        "ci_lo": float(np.quantile(stats, 0.025)),
        "ci_hi": float(np.quantile(stats, 0.975)),
        "B": float(B),
        "seed": float(seed),
        "n_clusters": float(k),
    }


def asof_wl_diff(game: Game, history: Sequence[Game]) -> float:
    """Current-season as-of win% home − away; kickoff < target; ties = 0.5 win."""
    hw = hl = ht = 0
    aw = al = at = 0
    for h in history:
        if h.season != game.season or h.margin is None:
            continue
        if h.kickoff_utc >= game.kickoff_utc:
            continue
        if h.home == game.home:
            if h.margin > 0:
                hw += 1
            elif h.margin < 0:
                hl += 1
            else:
                ht += 1
        elif h.away == game.home:
            if h.margin < 0:
                hw += 1
            elif h.margin > 0:
                hl += 1
            else:
                ht += 1
        if h.home == game.away:
            if h.margin > 0:
                aw += 1
            elif h.margin < 0:
                al += 1
            else:
                at += 1
        elif h.away == game.away:
            if h.margin < 0:
                aw += 1
            elif h.margin > 0:
                al += 1
            else:
                at += 1
    return win_pct(hw, hl, ht) - win_pct(aw, al, at)


def record_wl_diff(game: Game) -> float:
    hw, hl, ht = parse_record(game.record_entering_home)
    aw, al, at = parse_record(game.record_entering_away)
    return win_pct(hw, hl, ht) - win_pct(aw, al, at)


def home_team_season(game: Game) -> str:
    return f"{game.home}:{game.season}"


def week_cluster(game: Game) -> str:
    return f"{game.season}:W{game.week}"
