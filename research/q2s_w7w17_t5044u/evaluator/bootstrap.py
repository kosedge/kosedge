"""Paired game-bootstrap for ΔMAE. B and seed frozen before any real look.

t5053u protocol: B=10000, seed=20261102 (not the t5033u seed 20261101).
"""

from __future__ import annotations

from typing import Sequence

import numpy as np

BOOT_B = 10_000
BOOT_SEED = 20261102
WEEK_BLOCKS = tuple(range(7, 18))  # 11 weeks: W7–W17


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
    """11 week blocks W7–W17. Same B/seed re-seeded per block. Missing week refuses."""
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
        boot = paired_game_bootstrap_ci(d[ix], B=B, seed=seed)
        out[str(week)] = {
            "n": float(ix.size),
            "mae_baseline": float(np.mean(np.abs(base[ix] - act[ix]))),
            "mae_candidate": float(np.mean(np.abs(cand[ix] - act[ix]))),
            "delta_mae": float(d[ix].mean()),
            "rmse_baseline": float(np.sqrt(np.mean((base[ix] - act[ix]) ** 2))),
            "rmse_candidate": float(np.sqrt(np.mean((cand[ix] - act[ix]) ** 2))),
            "bootstrap": boot,
        }
    return out
