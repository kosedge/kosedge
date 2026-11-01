"""Paired game-bootstrap for ΔMAE. Seed and B frozen before the look."""

from __future__ import annotations

from typing import Sequence

import numpy as np

BOOT_B = 10_000
BOOT_SEED = 20261101


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
    values = np.asarray(deltas, dtype=float)
    n = int(values.size)
    if n < 1:
        raise ValueError("empty delta vector")
    rng = np.random.default_rng(int(seed))
    stats = np.empty(int(B), dtype=float)
    for b in range(int(B)):
        take = rng.integers(0, n, size=n)
        stats[b] = float(values[take].mean())
    return {
        "mean": float(values.mean()),
        "ci_lo": float(np.quantile(stats, 0.025)),
        "ci_hi": float(np.quantile(stats, 0.975)),
        "B": float(B),
        "seed": float(seed),
        "n": float(n),
    }
