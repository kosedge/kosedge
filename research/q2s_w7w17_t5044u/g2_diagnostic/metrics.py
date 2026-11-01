"""Pure descriptive metrics for t5075u G2. No I/O. No PASS/edge/selection."""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

import numpy as np

from constants import (
    COVERAGE_LEVELS,
    LOGLOSS_EPS,
    LOGLOSS_N,
    N_DRAWS,
    UNAVAILABLE,
    WEEK_BLOCKS,
)


class MetricRefuse(RuntimeError):
    pass


def _as_1d(x: Sequence[float], name: str) -> np.ndarray:
    arr = np.asarray(x, dtype=np.float64)
    if arr.ndim != 1:
        raise MetricRefuse(f"{name} must be 1-d")
    if arr.size == 0:
        raise MetricRefuse(f"{name} empty")
    if not np.isfinite(arr).all():
        raise MetricRefuse(f"{name} non-finite")
    return arr


def mae(pred: Sequence[float], actual: Sequence[float]) -> float:
    p = _as_1d(pred, "pred")
    a = _as_1d(actual, "actual")
    if p.shape != a.shape:
        raise MetricRefuse("mae shape mismatch")
    return float(np.mean(np.abs(p - a)))


def rmse(pred: Sequence[float], actual: Sequence[float]) -> float:
    p = _as_1d(pred, "pred")
    a = _as_1d(actual, "actual")
    if p.shape != a.shape:
        raise MetricRefuse("rmse shape mismatch")
    return float(np.sqrt(np.mean((p - a) ** 2)))


def paired_mae_diff(
    pred_a: Sequence[float],
    pred_b: Sequence[float],
    actual: Sequence[float],
) -> float:
    """mean(|a−act| − |b−act|) == MAE_a − MAE_b. Descriptive only."""
    a = _as_1d(pred_a, "pred_a")
    b = _as_1d(pred_b, "pred_b")
    y = _as_1d(actual, "actual")
    if a.shape != b.shape or a.shape != y.shape:
        raise MetricRefuse("paired mae shape mismatch")
    return float(np.mean(np.abs(a - y) - np.abs(b - y)))


def point_mae_rmse(
    pred: Sequence[float] | None,
    actual: Sequence[float],
) -> dict[str, Any]:
    if pred is None:
        return {"mae": UNAVAILABLE, "rmse": UNAVAILABLE}
    return {"mae": mae(pred, actual), "rmse": rmse(pred, actual)}


def brier_score(prob: Sequence[float], y: Sequence[float]) -> float:
    p = _as_1d(prob, "prob")
    yy = _as_1d(y, "y")
    if p.shape != yy.shape:
        raise MetricRefuse("brier shape mismatch")
    if np.any((yy != 0.0) & (yy != 1.0)):
        raise MetricRefuse("brier y must be in {0,1}")
    if np.any((p < 0.0) | (p > 1.0)):
        raise MetricRefuse("brier p outside [0,1]")
    return float(np.mean((p - yy) ** 2))


def _log_loss_from_p(p: np.ndarray, y: np.ndarray) -> float:
    with np.errstate(divide="ignore", invalid="ignore"):
        ll = -(y * np.log(p) + (1.0 - y) * np.log(1.0 - p))
    if not np.isfinite(ll).all():
        return float("inf")
    return float(np.mean(ll))


def log_loss_with_clip(
    prob: Sequence[float],
    y: Sequence[float],
    *,
    n_draws: int = LOGLOSS_N,
) -> dict[str, Any]:
    """Log loss on originals and on the predeclared [1/(2N), 1−1/(2N)] clip.

    Original vector is retained. Clip is disclosure, not a retune.
    """
    if int(n_draws) != LOGLOSS_N:
        raise MetricRefuse(f"log-loss N {n_draws} != frozen {LOGLOSS_N}")
    p = _as_1d(prob, "prob")
    yy = _as_1d(y, "y")
    if p.shape != yy.shape:
        raise MetricRefuse("logloss shape mismatch")
    if np.any((yy != 0.0) & (yy != 1.0)):
        raise MetricRefuse("logloss y must be in {0,1}")
    if np.any((p < 0.0) | (p > 1.0)):
        raise MetricRefuse("logloss p outside [0,1]")
    eps = 1.0 / (2.0 * float(n_draws))
    if not math.isclose(eps, LOGLOSS_EPS, rel_tol=0.0, abs_tol=0.0):
        raise MetricRefuse("log-loss eps drifted")
    clipped = np.clip(p, eps, 1.0 - eps)
    n_clipped = int(np.sum(clipped != p))
    return {
        "n": int(p.size),
        "n_draws": int(n_draws),
        "eps": float(eps),
        "clip_interval": [float(eps), float(1.0 - eps)],
        "originals_retained": True,
        "n_probs_clipped": n_clipped,
        "log_loss_original": _log_loss_from_p(p, yy),
        "log_loss_clipped": _log_loss_from_p(clipped, yy),
        "prob_original": p.tolist(),
        "prob_clipped": clipped.tolist(),
    }


def exclude_actual_ties(
    prob: Sequence[float],
    margin: Sequence[float],
) -> dict[str, Any]:
    """Drop actual ties from binary scores. Report the tie count."""
    p = _as_1d(prob, "prob")
    m = _as_1d(margin, "margin")
    if p.shape != m.shape:
        raise MetricRefuse("tie-filter shape mismatch")
    ties = m == 0.0
    keep = ~ties
    y = np.where(m[keep] > 0.0, 1.0, 0.0)
    return {
        "n_total": int(p.size),
        "n_ties": int(np.sum(ties)),
        "n_binary": int(np.sum(keep)),
        "prob": p[keep],
        "y": y,
        "tie_mask": ties,
    }


def binary_scores(
    prob: Sequence[float] | None,
    margin: Sequence[float],
    *,
    source: str,
    legacy_rounding: str | None = None,
) -> dict[str, Any]:
    if prob is None:
        return {
            "source": source,
            "status": UNAVAILABLE,
            "n_ties": None,
            "n_binary": None,
        }
    filtered = exclude_actual_ties(prob, margin)
    if filtered["n_binary"] < 1:
        raise MetricRefuse(f"{source}: no non-tie games for binary scores")
    ll = log_loss_with_clip(filtered["prob"], filtered["y"])
    out: dict[str, Any] = {
        "source": source,
        "status": "computed",
        "n_total": filtered["n_total"],
        "n_ties": filtered["n_ties"],
        "n_binary": filtered["n_binary"],
        "brier": brier_score(filtered["prob"], filtered["y"]),
        "log_loss": {
            "n": ll["n"],
            "n_draws": ll["n_draws"],
            "eps": ll["eps"],
            "clip_interval": ll["clip_interval"],
            "originals_retained": ll["originals_retained"],
            "n_probs_clipped": ll["n_probs_clipped"],
            "log_loss_original": ll["log_loss_original"],
            "log_loss_clipped": ll["log_loss_clipped"],
        },
        "legacy_rounding": legacy_rounding,
    }
    return out


def empirical_crps_one(draws: Sequence[float], actual: float) -> float:
    x = _as_1d(draws, "draws")
    if not math.isfinite(float(actual)):
        raise MetricRefuse("crps actual non-finite")
    return float(empirical_crps(x.reshape(1, -1), np.asarray([actual]))[0])


def empirical_crps(draws: np.ndarray, actual: Sequence[float]) -> np.ndarray:
    """Empirical CRPS: n⁻¹Σ|xᵢ−y| − (2n²)⁻¹ΣᵢΣⱼ|xᵢ−xⱼ|."""
    d = np.asarray(draws, dtype=np.float64)
    y = _as_1d(actual, "actual")
    if d.ndim != 2:
        raise MetricRefuse("crps draws must be (n_games, n_draws)")
    if d.shape[0] != y.size:
        raise MetricRefuse("crps games mismatch")
    if d.shape[1] < 1:
        raise MetricRefuse("crps empty draws")
    if not np.isfinite(d).all():
        raise MetricRefuse("crps draws non-finite")
    n = int(d.shape[1])
    term1 = np.mean(np.abs(d - y[:, None]), axis=1)
    ordered = np.sort(d, axis=1)
    idx = np.arange(n, dtype=np.float64)
    weights = 2.0 * idx - n + 1.0
    term2 = (ordered * weights).sum(axis=1) / (n * n)
    return term1 - term2


def equal_tail_coverage_width(
    draws: np.ndarray,
    actual: Sequence[float],
    *,
    levels: Sequence[float] = COVERAGE_LEVELS,
) -> dict[str, Any]:
    d = np.asarray(draws, dtype=np.float64)
    y = _as_1d(actual, "actual")
    if d.ndim != 2 or d.shape[0] != y.size:
        raise MetricRefuse("coverage shape mismatch")
    if not np.isfinite(d).all():
        raise MetricRefuse("coverage draws non-finite")
    out: dict[str, Any] = {}
    for level in levels:
        lv = float(level)
        if lv <= 0.0 or lv >= 1.0:
            raise MetricRefuse(f"bad coverage level {lv}")
        lo_q = (1.0 - lv) / 2.0
        hi_q = 1.0 - lo_q
        lo = np.quantile(d, lo_q, axis=1)
        hi = np.quantile(d, hi_q, axis=1)
        inside = (y >= lo) & (y <= hi)
        key = f"{int(round(lv * 100))}pct"
        out[key] = {
            "level": lv,
            "equal_tail": [float(lo_q), float(hi_q)],
            "coverage": float(np.mean(inside)),
            "mean_width": float(np.mean(hi - lo)),
            "n": int(y.size),
            "n_inside": int(np.sum(inside)),
        }
    return out


def per_week_summaries(
    *,
    weeks: Sequence[int],
    actual_margin: Sequence[float],
    actual_total: Sequence[float],
    preds: Mapping[str, Mapping[str, Sequence[float] | None]],
) -> dict[str, Any]:
    """Fixed W7–W17 blocks. Missing week = refuse."""
    w = np.asarray(weeks, dtype=int)
    am = _as_1d(actual_margin, "actual_margin")
    at = _as_1d(actual_total, "actual_total")
    if w.shape != am.shape or w.shape != at.shape:
        raise MetricRefuse("per-week shape mismatch")
    present = {int(x) for x in w.tolist()}
    if present != set(WEEK_BLOCKS):
        raise MetricRefuse(f"week blocks {sorted(present)} != W7–W17")
    blocks: dict[str, Any] = {}
    for week in WEEK_BLOCKS:
        mask = w == int(week)
        n = int(np.sum(mask))
        if n < 1:
            raise MetricRefuse(f"empty week {week}")
        y_m = am[mask]
        y_t = at[mask]
        entry: dict[str, Any] = {"n": n, "week": int(week)}
        margin_preds: dict[str, np.ndarray] = {}
        total_preds: dict[str, np.ndarray] = {}
        for name, fields in preds.items():
            mp = fields.get("margin")
            tp = fields.get("total")
            if mp is None:
                entry[f"{name}_margin"] = UNAVAILABLE
            else:
                arr = _as_1d(mp, f"{name}.margin")
                if arr.shape != am.shape:
                    raise MetricRefuse(f"{name} margin length mismatch")
                margin_preds[name] = arr[mask]
                entry[f"{name}_margin"] = {
                    "mae": mae(margin_preds[name], y_m),
                    "rmse": rmse(margin_preds[name], y_m),
                }
            if tp is None:
                entry[f"{name}_total"] = UNAVAILABLE
            else:
                arr = _as_1d(tp, f"{name}.total")
                if arr.shape != at.shape:
                    raise MetricRefuse(f"{name} total length mismatch")
                total_preds[name] = arr[mask]
                entry[f"{name}_total"] = {
                    "mae": mae(total_preds[name], y_t),
                    "rmse": rmse(total_preds[name], y_t),
                }
        entry["paired_mae_diff_margin"] = _pairwise_mae_diffs(margin_preds, y_m)
        entry["paired_mae_diff_total"] = _pairwise_mae_diffs(total_preds, y_t)
        blocks[str(week)] = entry
    return {
        "n_week_blocks": len(WEEK_BLOCKS),
        "week_blocks_role": "descriptive_only",
        "blocks": blocks,
    }


def _pairwise_mae_diffs(
    named: Mapping[str, np.ndarray],
    actual: np.ndarray,
) -> dict[str, Any]:
    pairs = (("joint", "if"), ("joint", "point"), ("point", "if"))
    out: dict[str, Any] = {}
    for left, right in pairs:
        key = f"{left}_minus_{right}"
        if left not in named or right not in named:
            out[key] = UNAVAILABLE
        else:
            out[key] = paired_mae_diff(named[left], named[right], actual)
    return out


def mae_rmse_bundle(
    *,
    actual_margin: Sequence[float],
    actual_total: Sequence[float],
    preds: Mapping[str, Mapping[str, Sequence[float] | None]],
) -> dict[str, Any]:
    margin: dict[str, Any] = {}
    total: dict[str, Any] = {}
    margin_arr: dict[str, np.ndarray] = {}
    total_arr: dict[str, np.ndarray] = {}
    for name, fields in preds.items():
        margin[name] = point_mae_rmse(fields.get("margin"), actual_margin)
        total[name] = point_mae_rmse(fields.get("total"), actual_total)
        if fields.get("margin") is not None:
            margin_arr[name] = _as_1d(fields["margin"], f"{name}.margin")
        if fields.get("total") is not None:
            total_arr[name] = _as_1d(fields["total"], f"{name}.total")
    y_m = _as_1d(actual_margin, "actual_margin")
    y_t = _as_1d(actual_total, "actual_total")
    return {
        "margin": margin,
        "total": total,
        "paired_mae_diff_margin": _pairwise_mae_diffs(margin_arr, y_m),
        "paired_rmse_diff_margin": _pairwise_rmse_diffs(margin),
        "paired_mae_diff_total": _pairwise_mae_diffs(total_arr, y_t),
        "paired_rmse_diff_total": _pairwise_rmse_diffs(total),
    }


def _pairwise_rmse_diffs(named: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    pairs = (("joint", "if"), ("joint", "point"), ("point", "if"))
    out: dict[str, Any] = {}
    for left, right in pairs:
        key = f"{left}_minus_{right}"
        lv = named.get(left, {}).get("rmse")
        rv = named.get(right, {}).get("rmse")
        if lv is None or rv is None or lv == UNAVAILABLE or rv == UNAVAILABLE:
            out[key] = UNAVAILABLE
        else:
            out[key] = float(lv) - float(rv)
    return out


def draw_diagnostics(
    *,
    H: np.ndarray,
    A: np.ndarray,
    actual_margin: Sequence[float],
    actual_total: Sequence[float],
) -> dict[str, Any]:
    h = np.asarray(H, dtype=np.float64)
    a = np.asarray(A, dtype=np.float64)
    if h.shape != a.shape or h.ndim != 2:
        raise MetricRefuse("draw pair shape mismatch")
    if h.shape[1] != N_DRAWS:
        raise MetricRefuse(f"N_DRAWS {h.shape[1]} != {N_DRAWS}")
    margin_draws = h - a
    total_draws = h + a
    crps_m = empirical_crps(margin_draws, actual_margin)
    crps_t = empirical_crps(total_draws, actual_total)
    return {
        "n": int(h.shape[0]),
        "N": int(h.shape[1]),
        "crps_margin_mean": float(crps_m.mean()),
        "crps_total_mean": float(crps_t.mean()),
        "coverage_width_margin": equal_tail_coverage_width(
            margin_draws, actual_margin
        ),
        "coverage_width_total": equal_tail_coverage_width(
            total_draws, actual_total
        ),
        "if_distribution": UNAVAILABLE,
    }


def refuse_if_distribution_regen() -> None:
    """Hard refuse. IF draws are not synthesized."""
    raise MetricRefuse(
        "IF distribution UNAVAILABLE (IF_MUS means-only); regen refused"
    )
