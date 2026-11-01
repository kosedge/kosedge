"""Paired game-bootstrap + week-cluster bootstrap for ΔMAE.

t5055u protocol: B=10000, seed=20261102.
W7–W17 are 11 clusters. Per-week tables are descriptive only.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np

BOOT_B = 10_000
BOOT_SEED = 20261102
WEEK_BLOCKS = tuple(range(7, 18))  # 11 weeks: W7–W17
N_CLUSTERS = 11


def paired_delta_mae(
    candidate: Sequence[float],
    baseline: Sequence[float],
    actual: Sequence[float],
) -> np.ndarray:
    cand = np.asarray(candidate, dtype=float)
    base = np.asarray(baseline, dtype=float)
    act = np.asarray(actual, dtype=float)
    if cand.shape != base.shape or cand.shape != act.shape:
        raise ValueError("paired arrays must share shape")
    return np.abs(cand - act) - np.abs(base - act)


def paired_game_bootstrap_ci(
    deltas: Sequence[float],
    *,
    B: int = BOOT_B,
    seed: int = BOOT_SEED,
) -> dict[str, float]:
    """Resample games with replacement. Games are treated as exchangeable.

    Repeated-team / week dependence is NOT modeled. CI crossing zero is
    inconclusive, not FQ PASS.
    """
    if int(B) != BOOT_B:
        raise ValueError(f"B {B} != frozen {BOOT_B}")
    if int(seed) != BOOT_SEED:
        raise ValueError(f"seed {seed} != frozen {BOOT_SEED}")
    values = np.asarray(deltas, dtype=float)
    n = int(values.size)
    if n < 1:
        raise ValueError("empty delta vector")
    rng = np.random.default_rng(int(seed))
    stats = np.empty(int(B), dtype=float)
    for _b in range(int(B)):
        take = rng.integers(0, n, size=n)
        stats[_b] = float(values[take].mean())
    return {
        "mean": float(values.mean()),
        "ci_lo": float(np.quantile(stats, 0.025)),
        "ci_hi": float(np.quantile(stats, 0.975)),
        "B": float(B),
        "seed": float(seed),
        "n": float(n),
        "method": "game",
    }


def cluster_week_sums(
    deltas: Sequence[float],
    weeks: Sequence[int],
) -> tuple[np.ndarray, np.ndarray]:
    """Per-week (sum of δ, game count) aligned to WEEK_BLOCKS.

    Missing week raises. Empty week raises.
    """
    week_a = np.asarray(weeks, dtype=int)
    d = np.asarray(deltas, dtype=float)
    if week_a.shape != d.shape:
        raise ValueError("deltas and weeks must share shape")
    present = set(int(w) for w in week_a.tolist())
    if present != set(WEEK_BLOCKS):
        raise ValueError(
            f"week-cluster set {sorted(present)} != {list(WEEK_BLOCKS)}"
        )
    sums = np.empty(N_CLUSTERS, dtype=float)
    counts = np.empty(N_CLUSTERS, dtype=float)
    for i, week in enumerate(WEEK_BLOCKS):
        ix = np.flatnonzero(week_a == week)
        if ix.size < 1:
            raise ValueError(f"week {week} has no rows")
        sums[i] = float(d[ix].sum())
        counts[i] = float(ix.size)
    return sums, counts


def week_cluster_stat(
    week_sums: Sequence[float],
    week_ns: Sequence[float],
    take: Sequence[int],
) -> float:
    """Game-weighted ΔMAE for one week-cluster draw.

    ``take`` is a length-11 index vector into the 11 week clusters
    (with replacement). Duplicated clusters contribute their full
    game-sum and game-count again. Omitted clusters contribute 0.
    """
    sums = np.asarray(week_sums, dtype=float)
    ns = np.asarray(week_ns, dtype=float)
    idx = np.asarray(take, dtype=int)
    if sums.size != N_CLUSTERS or ns.size != N_CLUSTERS:
        raise ValueError(f"cluster vectors must have length {N_CLUSTERS}")
    if idx.size != N_CLUSTERS:
        raise ValueError(f"week-cluster draw must have length {N_CLUSTERS}")
    if np.any(idx < 0) or np.any(idx >= N_CLUSTERS):
        raise ValueError("week-cluster index out of range")
    num = float(sums[idx].sum())
    den = float(ns[idx].sum())
    if den <= 0.0:
        raise ValueError("week-cluster draw has zero games")
    return num / den


def paired_week_cluster_bootstrap_ci(
    deltas: Sequence[float],
    weeks: Sequence[int],
    *,
    B: int = BOOT_B,
    seed: int = BOOT_SEED,
) -> dict[str, float]:
    """Pooled week-cluster bootstrap of game-weighted ΔMAE.

    Each of B resamples draws 11 week indices with replacement
    (numpy.random.default_rng(seed).integers). Every game in each
    selected week is retained, including duplicated clusters.

    Statistic = sum(selected week δ sums) / sum(selected week game counts).
    Reported mean is the observed game-weighted ΔMAE (all 11 weeks once).
    """
    if int(B) != BOOT_B:
        raise ValueError(f"B {B} != frozen {BOOT_B}")
    if int(seed) != BOOT_SEED:
        raise ValueError(f"seed {seed} != frozen {BOOT_SEED}")
    d = np.asarray(deltas, dtype=float)
    week_sums, week_ns = cluster_week_sums(d, weeks)
    observed = float(week_sums.sum() / week_ns.sum())
    rng = np.random.default_rng(int(seed))
    stats = np.empty(int(B), dtype=float)
    for _b in range(int(B)):
        take = rng.integers(0, N_CLUSTERS, size=N_CLUSTERS)
        stats[_b] = week_cluster_stat(week_sums, week_ns, take)
    return {
        "mean": observed,
        "ci_lo": float(np.quantile(stats, 0.025)),
        "ci_hi": float(np.quantile(stats, 0.975)),
        "B": float(B),
        "seed": float(seed),
        "n": float(d.size),
        "n_clusters": float(N_CLUSTERS),
        "method": "week_cluster",
    }


def week_block_sensitivity(
    deltas: Sequence[float],
    weeks: Sequence[int],
    candidate: Sequence[float],
    baseline: Sequence[float],
    actual: Sequence[float],
    *,
    B: int = BOOT_B,
    seed: int = BOOT_SEED,
) -> dict[str, dict[str, float]]:
    """Descriptive per-week table only. No within-week bootstrap.

    B/seed are accepted so callers keep the frozen constants; they are
    checked and otherwise unused. Uncertainty lives in the pooled
    week-cluster bootstrap, not in these rows.
    """
    if int(B) != BOOT_B:
        raise ValueError(f"B {B} != frozen {BOOT_B}")
    if int(seed) != BOOT_SEED:
        raise ValueError(f"seed {seed} != frozen {BOOT_SEED}")
    week_a = np.asarray(weeks, dtype=int)
    present = set(int(w) for w in week_a.tolist())
    if present != set(WEEK_BLOCKS):
        raise ValueError(
            f"week-block set {sorted(present)} != {list(WEEK_BLOCKS)}"
        )
    cand = np.asarray(candidate, dtype=float)
    base = np.asarray(baseline, dtype=float)
    act = np.asarray(actual, dtype=float)
    d = np.asarray(deltas, dtype=float)
    out: dict[str, dict[str, float]] = {}
    for week in WEEK_BLOCKS:
        ix = np.flatnonzero(week_a == week)
        if ix.size < 1:
            raise ValueError(f"week {week} has no rows")
        out[str(week)] = {
            "n": float(ix.size),
            "mae_baseline": float(np.mean(np.abs(base[ix] - act[ix]))),
            "mae_candidate": float(np.mean(np.abs(cand[ix] - act[ix]))),
            "delta_mae": float(d[ix].mean()),
            "rmse_baseline": float(np.sqrt(np.mean((base[ix] - act[ix]) ** 2))),
            "rmse_candidate": float(np.sqrt(np.mean((cand[ix] - act[ix]) ** 2))),
        }
    return out
