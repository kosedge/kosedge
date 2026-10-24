#!/usr/bin/env python3
"""Injury residual evaluator v3 — acceptance 54bc78ec / ruling a0501d57.

Dry-run only. Holdout STOPPED. No CLEAR/IMV tokens. No 2024–25.
Expected answers T-1..T-10 must already be on disk (sha 8319a63a) before this runs.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

HERE = Path(__file__).resolve().parent
REQUIRED_SPEC = "a156459b545e3b7d6a483f1db34cda7a4d32fc3afc70ed499b3adc726b1b6881"
REQUIRED_ACCEPT = "54bc78ecc70e6a440481253b9c7eeef0e749690e893f501862f5dd5c54444574"
REQUIRED_RULING = "a0501d575a42cb4c05b2d1937753b36ca761f613e8c0d011d56fd3d05246d6e9"
REQUIRED_EXPORT = "d87e6129c451bbdc51d49eb7745a31ebb64ab6108ac58d8f8c4948dcc13e18e8"
REQUIRED_FIT = "6a5490dbc09b160f4509ea65b3b2257f9703f9d43635092d0da94c1577abb657"
REQUIRED_EXPECTED = "8319a63a674f22a52b1bce168c15de9e1a510429b14e78d1e4dd48f30fcd1b79"
REQUIRED_HEAD = "8e2a15ac581277ecda71ea745c3b3477185d733b"
PINNED_SEED = 20261023
N_BOOT = 10000
HOLM_ALPHA = 0.05
SIGMA_MARGIN = 13.5
SIGMA_TOTAL = 14.0
K4_LL = 0.002
K4_BR = 0.0005
K4_SLOPE = (0.9, 1.1)
I2_MIN = 500
FORBIDDEN = {2024, 2025, 2026}
CLOSE_LABEL = "comparative research, not certified CLV"
CVO_LABEL = "close vs outcome"
TOKEN_NAMES = ("RYAN_CLEAR_ON_FROZEN_RECORD", "IMV_PASS", "CLEAR", "RYAN_CLEAR")
HOLM_NINE = (
    "spread_clv_delta",
    "spread_ats_delta",
    "spread_logloss_delta",
    "total_clv_delta",
    "total_ats_delta",
    "total_logloss_delta",
    "ml_clv_implied_prob_delta",
    "ml_ats_delta",
    "ml_logloss_delta",
)
PRIMARY = "spread_clv_delta"
CLIP = {"n": 0}

I1_VERBATIM = (
    "Paired comparison, adjusted vs base, same games, priced at the same as_of_ts, against "
    "the CLOSING line: CLV (points and implied-prob), ATS win rate, log-loss delta."
)
I2_VERBATIM = (
    "Minimum sample: >= 500 games with a non-zero adjustment in the sealed holdout and "
    ">= 2 full seasons; below that the result is INCONCLUSIVE (no claim)."
)
I3_VERBATIM = (
    "Multiple comparisons: 3 markets x 3 metrics = 9 tests; Holm-Bonferroni at family "
    "alpha 0.05. Primary endpoint = mean CLV delta (spread) - stated now, not chosen later."
)
I4_VERBATIM = (
    "Decision rule: VALUE PROVEN only if primary endpoint significant after Holm, its 95% "
    "block-bootstrap CI excludes 0, and K-4 passes. Anything else = NO CLAIM."
)
I5_VERBATIM = (
    "Soft, borderline or insignificant results cannot become a product claim, marketing "
    'copy, or a "improves accuracy" statement. Report them as null results.'
)
K2_VERBATIM = (
    "Metrics, base vs adjusted on the same games: Brier and log loss (win prob); "
    "cover reliability for spread and total (predicted cover prob vs actual); "
    "reliability diagram in 10 bins with counts."
)
K3_VERBATIM = "CIs: block bootstrap by NFL week, 10,000 resamples, 95% percentile CI, paired."
K4_VERBATIM = (
    "Gate: adjusted must not be worse than base: upper 95% CI of (adj - base) log loss "
    "<= 0.002 and Brier <= 0.0005. Calibration slope of adjusted within [0.9, 1.1]. "
    "Failing = layer stays off."
)


def log(msg: str) -> None:
    sys.stderr.write(msg + "\n")
    sys.stderr.flush()


def die(msg: str) -> None:
    log("STOP: " + msg)
    raise SystemExit(2)


def sha256_file(path: Path) -> str:
    if not path.is_file():
        die(f"missing file (fail-closed, not a crash): {path}")
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve(name: str, required: Optional[str], candidates: Sequence[Path]) -> Path:
    for path in candidates:
        if path.is_file():
            if required and sha256_file(path) != required:
                die(f"{name} sha mismatch at {path}")
            return path
    die(f"SEEDED MISSING {name}; looked {list(candidates)}")
    raise AssertionError


def alias(team: str) -> str:
    t = str(team or "").strip().upper()
    return {"LAR": "LA", "STL": "LA", "SD": "LAC", "OAK": "LV", "WSH": "WAS", "JAC": "JAX"}.get(t, t)


def clip_p(p: float) -> float:
    lo, hi = 1e-15, 1.0 - 1e-15
    if p < lo:
        CLIP["n"] += 1
        return lo
    if p > hi:
        CLIP["n"] += 1
        return hi
    return p


def phi(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def p_home(pred_m: float, sigma: float = SIGMA_MARGIN) -> float:
    if sigma <= 0:
        die("sigma must be > 0")
    return clip_p(phi(pred_m / sigma))


def p_cover(pred_m: float, close_s: float, sigma: float = SIGMA_MARGIN) -> float:
    return clip_p(phi((pred_m + close_s) / sigma))


def p_over(pred_t: float, close_t: float, sigma: float = SIGMA_TOTAL) -> float:
    return clip_p(phi((pred_t - close_t) / sigma))


def log_loss(y: float, p: float) -> float:
    p = clip_p(p)
    y = min(1.0, max(0.0, y))
    return -(y * math.log(p) + (1.0 - y) * math.log(1.0 - p))


def brier(y: float, p: float) -> float:
    return (p - y) ** 2


def logit(p: float) -> float:
    p = clip_p(p)
    return math.log(p / (1.0 - p))


def expit(z: float) -> float:
    if z >= 0:
        e = math.exp(-z)
        return 1.0 / (1.0 + e)
    e = math.exp(z)
    return e / (1.0 + e)


def ols_slope(xs: Sequence[float], ys: Sequence[float]) -> Optional[float]:
    if len(xs) < 2:
        return None
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    den = sum((x - mx) ** 2 for x in xs)
    if den == 0:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den


def calibration_slope_logit(ys: Sequence[float], ps: Sequence[float]) -> Optional[float]:
    """Registered K-4 slope: logit(y) ~ logit(p_adj) via logistic IRLS (fractional y ok)."""
    if len(ys) < 8:
        return None
    xs = [logit(p) for p in ps]
    a, b = 0.0, 1.0
    for _ in range(40):
        waa = wab = wbb = za = zb = 0.0
        for y, x in zip(ys, xs):
            mu = expit(a + b * x)
            w = max(mu * (1.0 - mu), 1e-18)
            r = y - mu
            waa += w
            wab += w * x
            wbb += w * x * x
            za += r
            zb += r * x
        det = waa * wbb - wab * wab
        if abs(det) < 1e-18:
            return None
        da = (wbb * za - wab * zb) / det
        db = (-wab * za + waa * zb) / det
        a += da
        b += db
        if abs(da) + abs(db) < 1e-12:
            break
    return b


def reliability(ps: Sequence[float], ys: Sequence[float], bins: int = 10) -> List[Dict[str, Any]]:
    out = []
    for i in range(bins):
        lo, hi = i / bins, (i + 1) / bins
        idx = [j for j, p in enumerate(ps) if (p >= lo and p < hi) or (i == bins - 1 and p >= lo)]
        if not idx:
            out.append({"bin": i, "lo": lo, "hi": hi, "n": 0, "mean_p": None, "mean_y": None, "nan_reason": "bin empty; not a stub"})
            continue
        out.append(
            {
                "bin": i,
                "lo": lo,
                "hi": hi,
                "n": len(idx),
                "mean_p": sum(ps[j] for j in idx) / len(idx),
                "mean_y": sum(ys[j] for j in idx) / len(idx),
                "nan_reason": None,
            }
        )
    return out


def percentile(xs: Sequence[float], q: float) -> float:
    s = sorted(xs)
    if not s:
        die("percentile on empty sample")
    k = q * (len(s) - 1)
    f = int(math.floor(k))
    c = int(math.ceil(k))
    if f == c:
        return s[f]
    return s[f] + (s[c] - s[f]) * (k - f)


def mean(xs: Sequence[float]) -> Optional[float]:
    return None if not xs else sum(xs) / len(xs)


def cvo_points(close: float, actual: float, spread_arm: float) -> Optional[float]:
    """Close-vs-outcome points. Edge 0 = beats close by 0 (T-1), not a silent drop."""
    if spread_arm == close:
        return 0.0
    return (1.0 if close > spread_arm else -1.0) * (close - actual)


def cvo_prob(p_arm: float, p_close: float, y: float) -> Optional[float]:
    if p_arm == p_close:
        return 0.0
    return (y - p_close) * (1.0 if p_arm > p_close else -1.0)


def holm_bonferroni(pvalues: Sequence[Tuple[str, float]], alpha: float = HOLM_ALPHA) -> List[Dict[str, Any]]:
    if len(pvalues) != 9:
        die(f"I-3 requires 9 tests; got {len(pvalues)}")
    if {n for n, _ in pvalues} != set(HOLM_NINE):
        die("I-3 test ids must be the 3x3 family")
    ranked = sorted(pvalues, key=lambda kv: kv[1])
    out = []
    keep = True
    for i, (name, p) in enumerate(ranked):
        thresh = alpha / (9 - i)
        sig = bool(keep and p <= thresh)
        if not sig:
            keep = False
        out.append({"test_id": name, "p": p, "holm_rank": i + 1, "holm_threshold": thresh, "significant": sig})
    return out


def i2_status(n_nonzero: int, n_full: int) -> str:
    return "INCONCLUSIVE" if (n_nonzero < I2_MIN or n_full < 2) else "MET"


def i4_decision(i2: str, primary_sig: bool, ci_lo: Optional[float], k4: bool) -> str:
    if i2 != "MET":
        return "INCONCLUSIVE"
    if primary_sig and ci_lo is not None and ci_lo > 0.0 and k4:
        return "VALUE PROVEN"
    return "NO CLAIM"


def detect_leakage(rows: Sequence[Dict[str, Any]]) -> None:
    leaks = []
    for i, r in enumerate(rows):
        src, asof = r.get("source_ts"), r.get("as_of_ts")
        if src and asof and str(src) > str(asof):
            leaks.append(f"row{i} source_ts>{asof}")
        if r.get("outcome_joined_before_freeze") or r.get("close_joined_before_freeze"):
            leaks.append(f"row{i} joined_before_freeze")
    if leaks:
        die("LEAKAGE " + "; ".join(leaks))


def week_block_bootstrap(rows: Sequence[Dict[str, Any]], stat_fn: Callable, seed: int = PINNED_SEED) -> Dict[str, Any]:
    if seed != PINNED_SEED:
        die(f"K-3 seed {seed} != PINNED_SEED {PINNED_SEED}")
    if not rows:
        return {"n_blocks": 0, "obs": None, "ci_lo": None, "ci_hi": None, "p": 1.0, "excludes_0": False, "lo_gt_0": False, "seed": seed, "n_boot": N_BOOT, "undefined_draws": 0, "nan_reason": "no paired rows"}
    by_week: Dict[Tuple[int, int], List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_week[(int(row["season"]), int(row["week"]))].append(row)
    keys = list(by_week.keys())
    obs = stat_fn(list(rows))
    if obs is None:
        return {"n_blocks": len(keys), "obs": None, "ci_lo": None, "ci_hi": None, "p": 1.0, "excludes_0": False, "lo_gt_0": False, "seed": seed, "n_boot": N_BOOT, "undefined_draws": 0, "nan_reason": "statistic undefined on this cohort"}
    rng = np.random.default_rng(seed)
    boot: List[float] = []
    undefined = 0
    for _ in range(N_BOOT):
        val = None
        for attempt in range(32):
            drawn: List[Dict[str, Any]] = []
            picks = rng.integers(0, len(keys), size=len(keys))
            for j in picks:
                drawn.extend(by_week[keys[int(j)]])
            val = stat_fn(drawn)
            if val is not None:
                break
        if val is None:
            undefined += 1
        else:
            boot.append(float(val))
    if undefined or len(boot) != N_BOOT:
        return {"n_blocks": len(keys), "obs": obs, "ci_lo": None, "ci_hi": None, "p": 1.0, "excludes_0": False, "lo_gt_0": False, "seed": seed, "n_boot": N_BOOT, "undefined_draws": undefined, "nan_reason": "undefined bootstrap draw; not filled with 0.0"}
    lo, hi = percentile(boot, 0.025), percentile(boot, 0.975)
    n_le = sum(1 for x in boot if x <= 0.0)
    n_ge = sum(1 for x in boot if x >= 0.0)
    p = min(1.0, 2.0 * min(n_le, n_ge) / float(N_BOOT))
    return {"n_blocks": len(keys), "obs": obs, "ci_lo": lo, "ci_hi": hi, "p": p, "excludes_0": (lo > 0.0) or (hi < 0.0), "lo_gt_0": lo > 0.0, "seed": seed, "n_boot": N_BOOT, "undefined_draws": 0, "nan_reason": None}


def full_seasons(weeks_by_season: Dict[int, Sequence[int]]) -> Tuple[int, Dict[str, Any]]:
    detail = {}
    n_full = 0
    for season, weeks in sorted(weeks_by_season.items()):
        w = set(int(x) for x in weeks)
        need = 18 if season >= 2021 else 17
        is_full = set(range(1, need + 1)) <= w
        detail[str(season)] = {"weeks": sorted(w), "expected": need, "full": is_full}
        if is_full:
            n_full += 1
    return n_full, detail


def score_universe(name: str, universe: List[Dict[str, Any]], notes: str, dry_run_label: bool = False) -> Dict[str, Any]:
    detect_leakage(universe)
    weeks: Dict[int, set] = defaultdict(set)
    n_nonzero = 0
    n_nonzero_season: Dict[int, int] = Counter()
    close_present: List[Dict[str, Any]] = []
    missing = {
        "n_universe": len(universe),
        "n_incomplete_residual": 0,
        "n_missing_close": 0,
        "n_missing_actual": 0,
        "n_missing_baseline": 0,
        "n_null_flag": 0,
        "n_missing_close_by_season": Counter(),
        "n_missing_actual_by_season": Counter(),
        "n_missing_baseline_by_season": Counter(),
        "n_incomplete_by_season": Counter(),
        "n_universe_by_season": Counter(),
    }
    for row in universe:
        season = int(row["season"])
        if season in FORBIDDEN:
            die(f"{name} contains forbidden season {season}")
        missing["n_universe_by_season"][season] += 1
        weeks[season].add(int(row["week"]))
        if row.get("null_flag"):
            missing["n_null_flag"] += 1
        if not row.get("residual_complete"):
            missing["n_incomplete_residual"] += 1
            missing["n_incomplete_by_season"][season] += 1
            continue
        dm, dt = row.get("delta_margin"), row.get("delta_total")
        if dm is not None and dt is not None and (float(dm) != 0.0 or float(dt) != 0.0):
            n_nonzero += 1
            n_nonzero_season[season] += 1
        if row.get("close_spread_home") is None or row.get("close_total") is None:
            missing["n_missing_close"] += 1
            missing["n_missing_close_by_season"][season] += 1
            continue
        if row.get("actual_margin") is None or row.get("actual_total") is None:
            missing["n_missing_actual"] += 1
            missing["n_missing_actual_by_season"][season] += 1
            continue
        if row.get("baseline_margin") is None or row.get("baseline_total") is None:
            missing["n_missing_baseline"] += 1
            missing["n_missing_baseline_by_season"][season] += 1
            continue
        close_present.append(row)

    n_full, week_detail = full_seasons(weeks)
    i2 = i2_status(n_nonzero, n_full)
    scored = []
    n_edge0_base = n_edge0_adj = 0
    for r in close_present:
        bm, bt, dm, dt = float(r["baseline_margin"]), float(r["baseline_total"]), float(r["delta_margin"]), float(r["delta_total"])
        cs, ct, am, at = float(r["close_spread_home"]), float(r["close_total"]), float(r["actual_margin"]), float(r["actual_total"])
        pred_m_b, pred_m_a = bm, bm + dm
        pred_t_b, pred_t_a = bt, bt + dt
        spr_b, spr_a = -pred_m_b, -pred_m_a
        actual_spread = -am
        if spr_b == cs:
            n_edge0_base += 1
        if spr_a == cs:
            n_edge0_adj += 1
        y_home = 1.0 if am > 0 else 0.0
        y_cover = 1.0 if (am + cs) > 0 else 0.0
        y_over = 1.0 if at > ct else 0.0
        p_b, p_a = p_home(pred_m_b), p_home(pred_m_a)
        p_close = p_home(-cs)
        p_cov_b, p_cov_a = p_cover(pred_m_b, cs), p_cover(pred_m_a, cs)
        p_ov_b, p_ov_a = p_over(pred_t_b, ct), p_over(pred_t_a, ct)
        cvo_b = cvo_points(cs, actual_spread, spr_b)
        cvo_a = cvo_points(cs, actual_spread, spr_a)
        tcvo_b = cvo_points(ct, at, pred_t_b)
        tcvo_a = cvo_points(ct, at, pred_t_a)
        ml_b, ml_a = cvo_prob(p_b, p_close, y_home), cvo_prob(p_a, p_close, y_home)
        ats_b = None if cvo_b is None else (1.0 if ((spr_b < cs and y_cover == 1) or (spr_b > cs and y_cover == 0)) else 0.0)
        ats_a = None if cvo_a is None else (1.0 if ((spr_a < cs and y_cover == 1) or (spr_a > cs and y_cover == 0)) else 0.0)
        scored.append(
            {
                "season": r["season"],
                "week": r["week"],
                "game_id": r.get("game_id") or f"{r['season']}_{r['week']}_{r.get('away')}_{r.get('home')}",
                "spread_cvo_base": cvo_b,
                "spread_cvo_adj": cvo_a,
                "spread_clv_delta": None if cvo_a is None or cvo_b is None else cvo_a - cvo_b,
                "spread_ats_base": ats_b,
                "spread_ats_adj": ats_a,
                "spread_ll_base": log_loss(y_cover, p_cov_b),
                "spread_ll_adj": log_loss(y_cover, p_cov_a),
                "total_clv_delta": None if tcvo_a is None or tcvo_b is None else tcvo_a - tcvo_b,
                "total_ats_base": 1.0 if ((p_ov_b > 0.5 and y_over == 1) or (p_ov_b < 0.5 and y_over == 0)) else 0.0,
                "total_ats_adj": 1.0 if ((p_ov_a > 0.5 and y_over == 1) or (p_ov_a < 0.5 and y_over == 0)) else 0.0,
                "total_ll_base": log_loss(y_over, p_ov_b),
                "total_ll_adj": log_loss(y_over, p_ov_a),
                "ml_clv_delta": None if ml_a is None or ml_b is None else ml_a - ml_b,
                "ml_ats_base": 1.0 if ((p_b > 0.5 and y_home == 1) or (p_b < 0.5 and y_home == 0)) else 0.0,
                "ml_ats_adj": 1.0 if ((p_a > 0.5 and y_home == 1) or (p_a < 0.5 and y_home == 0)) else 0.0,
                "ml_ll_base": log_loss(y_home, p_b),
                "ml_ll_adj": log_loss(y_home, p_a),
                "brier_base": brier(y_home, p_b),
                "brier_adj": brier(y_home, p_a),
                "p_base": p_b,
                "p_adj": p_a,
                "p_cov_base": p_cov_b,
                "p_cov_adj": p_cov_a,
                "p_over_base": p_ov_b,
                "p_over_adj": p_ov_a,
                "y_home": y_home,
                "y_cover": y_cover,
                "y_over": y_over,
                "pred_m_base": pred_m_b,
                "pred_m_adj": pred_m_a,
                "close_spread": cs,
                "actual_margin": am,
                "abs_close": abs(cs),
                "abs_delta": abs(dm),
                "sigma_margin": SIGMA_MARGIN,
                "sigma_total": SIGMA_TOTAL,
            }
        )

    def col(key: str, rows: Sequence[Dict[str, Any]] = scored) -> List[float]:
        return [float(r[key]) for r in rows if r.get(key) is not None]

    def dmean(a: str, b: str) -> Optional[float]:
        xs = [float(r[a]) - float(r[b]) for r in scored if r.get(a) is not None and r.get(b) is not None]
        return mean(xs)

    metrics = {
        "spread_clv_delta": mean(col("spread_clv_delta")),
        "spread_ats_delta": dmean("spread_ats_adj", "spread_ats_base"),
        "spread_logloss_delta": dmean("spread_ll_adj", "spread_ll_base"),
        "total_clv_delta": mean(col("total_clv_delta")),
        "total_ats_delta": dmean("total_ats_adj", "total_ats_base"),
        "total_logloss_delta": dmean("total_ll_adj", "total_ll_base"),
        "ml_clv_implied_prob_delta": mean(col("ml_clv_delta")),
        "ml_ats_delta": dmean("ml_ats_adj", "ml_ats_base"),
        "ml_logloss_delta": dmean("ml_ll_adj", "ml_ll_base"),
        "mean_logloss_base": mean(col("ml_ll_base")),
        "mean_logloss_adj": mean(col("ml_ll_adj")),
        "mean_brier_base": mean(col("brier_base")),
        "mean_brier_adj": mean(col("brier_adj")),
        "logloss_delta_adj_minus_base": dmean("ml_ll_adj", "ml_ll_base"),
        "brier_delta_adj_minus_base": dmean("brier_adj", "brier_base"),
        "slope_adj": calibration_slope_logit(col("y_home"), col("p_adj")),
    }
    undefined = {
        k: (None if metrics[k] is not None else "no row with both arms defined (zero-edge on that market only); not a stub")
        for k in HOLM_NINE
    }
    if metrics["slope_adj"] is None:
        undefined["slope_adj"] = "logit slope uncomputable; not a stub"

    def tstat(key: str):
        def _fn(rows: Sequence[Dict[str, Any]]) -> Optional[float]:
            if key == "spread_clv_delta":
                xs = [r["spread_clv_delta"] for r in rows if r.get("spread_clv_delta") is not None]
            elif key == "spread_ats_delta":
                xs = [r["spread_ats_adj"] - r["spread_ats_base"] for r in rows if r.get("spread_ats_adj") is not None and r.get("spread_ats_base") is not None]
            elif key == "spread_logloss_delta":
                xs = [r["spread_ll_adj"] - r["spread_ll_base"] for r in rows]
            elif key == "total_clv_delta":
                xs = [r["total_clv_delta"] for r in rows if r.get("total_clv_delta") is not None]
            elif key == "total_ats_delta":
                xs = [r["total_ats_adj"] - r["total_ats_base"] for r in rows]
            elif key == "total_logloss_delta":
                xs = [r["total_ll_adj"] - r["total_ll_base"] for r in rows]
            elif key == "ml_clv_implied_prob_delta":
                xs = [r["ml_clv_delta"] for r in rows if r.get("ml_clv_delta") is not None]
            elif key == "ml_ats_delta":
                xs = [r["ml_ats_adj"] - r["ml_ats_base"] for r in rows]
            elif key == "ml_logloss_delta":
                xs = [r["ml_ll_adj"] - r["ml_ll_base"] for r in rows]
            else:
                die("unknown " + key)
            return mean(xs)

        return _fn

    boot = {k: week_block_bootstrap(scored, tstat(k)) for k in HOLM_NINE}
    holm = holm_bonferroni([(k, boot[k]["p"]) for k in HOLM_NINE])
    holm_by = {h["test_id"]: h for h in holm}
    ll_boot = week_block_bootstrap(scored, lambda rs: mean([r["ml_ll_adj"] - r["ml_ll_base"] for r in rs]))
    br_boot = week_block_bootstrap(scored, lambda rs: mean([r["brier_adj"] - r["brier_base"] for r in rs]))
    slope = metrics["slope_adj"]
    k4_notes = []
    k4 = False
    if not scored:
        k4_notes.append("no close-present rows")
    else:
        k4 = (
            ll_boot.get("ci_hi") is not None
            and br_boot.get("ci_hi") is not None
            and ll_boot["ci_hi"] <= K4_LL
            and br_boot["ci_hi"] <= K4_BR
            and slope is not None
            and K4_SLOPE[0] <= slope <= K4_SLOPE[1]
        )
        if ll_boot.get("ci_hi") is None or ll_boot["ci_hi"] > K4_LL:
            k4_notes.append(f"logloss_CI_hi {ll_boot.get('ci_hi')} > {K4_LL}")
        if br_boot.get("ci_hi") is None or br_boot["ci_hi"] > K4_BR:
            k4_notes.append(f"brier_CI_hi {br_boot.get('ci_hi')} > {K4_BR}")
        if slope is None:
            k4_notes.append("slope undefined")
        elif not (K4_SLOPE[0] <= slope <= K4_SLOPE[1]):
            k4_notes.append(f"slope {slope} outside [0.9,1.1]")
    decision = i4_decision(i2, bool(holm_by[PRIMARY]["significant"]), boot[PRIMARY].get("ci_lo"), k4)
    for key in ("n_missing_close_by_season", "n_missing_actual_by_season", "n_missing_baseline_by_season", "n_incomplete_by_season", "n_universe_by_season"):
        missing[key] = dict(missing[key])
    missing["n_identical_cohort"] = len(close_present)
    missing["n_close_present"] = len(close_present)
    missing["n_paired_cvo"] = sum(1 for r in scored if r.get("spread_clv_delta") is not None)
    missing["n_edge0_base"] = n_edge0_base
    missing["n_edge0_adj"] = n_edge0_adj
    ids_base = {r["game_id"] for r in scored}
    return {
        "name": name,
        "notes": notes,
        "metric_label": CVO_LABEL,
        "close_label": CLOSE_LABEL,
        "dry_run_not_a_result": dry_run_label,
        "i1_verbatim": I1_VERBATIM,
        "i2_verbatim": I2_VERBATIM,
        "i3_verbatim": I3_VERBATIM,
        "i4_verbatim": I4_VERBATIM,
        "i5_verbatim": I5_VERBATIM,
        "k2_verbatim": K2_VERBATIM,
        "k3_verbatim": K3_VERBATIM,
        "k4_verbatim": K4_VERBATIM,
        "n_nonzero_adjustment": n_nonzero,
        "n_nonzero_by_season": dict(n_nonzero_season),
        "n_full_seasons": n_full,
        "weeks": week_detail,
        "i2": i2,
        "missing": missing,
        "metrics": metrics,
        "metric_undefined": undefined,
        "reliability": {"spread": reliability(col("p_cov_adj"), col("y_cover")), "total": reliability(col("p_over_adj"), col("y_over")), "ml": reliability(col("p_adj"), col("y_home"))},
        "holm": holm,
        "bootstrap": boot,
        "same_ids_both_arms": True,
        "n_ids": len(ids_base),
        "k4": {
            "logloss_delta_ci_hi": ll_boot.get("ci_hi"),
            "brier_delta_ci_hi": br_boot.get("ci_hi"),
            "slope_adj": slope,
            "slope_definition": "logit(y)~logit(p_adj) logistic IRLS",
            "thresholds": {"logloss_upper": K4_LL, "brier_upper": K4_BR, "slope": list(K4_SLOPE)},
            "pass": k4,
            "notes": k4_notes,
        },
        "i4": {
            "primary_significant_after_holm": bool(holm_by[PRIMARY]["significant"]),
            "primary_ci_excludes_0": bool(boot[PRIMARY]["excludes_0"]),
            "primary_ci_lo_gt_0": bool(boot[PRIMARY].get("lo_gt_0")),
            "k4_pass": k4,
            "decision": decision,
            "decision_label": "DRY RUN - NOT A RESULT" if dry_run_label else decision,
            "product_claim": False,
            "i5": "null results reported as null; no product claim",
        },
        "scored_rows": scored,
    }


def modeling_challenges(res: Dict[str, Any]) -> Dict[str, Any]:
    rows = res.get("scored_rows") or []
    buckets = [(0, 3), (3, 7), (7, 10), (10, 1e9)]

    def bucket_stats(key: str, getter) -> List[Dict[str, Any]]:
        out = []
        for lo, hi in buckets:
            sub = [r for r in rows if lo <= getter(r) < hi]
            if not sub:
                out.append({"lo": lo, "hi": hi, "n": 0, "mean": None, "sd": None, "nan_reason": "empty bucket"})
                continue
            resid_b = [r["actual_margin"] - r["pred_m_base"] for r in sub]
            resid_a = [r["actual_margin"] - r["pred_m_adj"] for r in sub]
            def sd(xs):
                if len(xs) < 2:
                    return None
                m = sum(xs) / len(xs)
                return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))
            out.append({"lo": lo, "hi": hi, "n": len(sub), "mean_base": mean(resid_b), "sd_base": sd(resid_b), "mean_adj": mean(resid_a), "sd_adj": sd(resid_a)})
        return out

    mae_b = mean([abs(r["actual_margin"] - r["pred_m_base"]) for r in rows])
    mae_a = mean([abs(r["actual_margin"] - r["pred_m_adj"]) for r in rows])
    rmse_b = math.sqrt(mean([(r["actual_margin"] - r["pred_m_base"]) ** 2 for r in rows]) or 0.0) if rows else None
    rmse_a = math.sqrt(mean([(r["actual_margin"] - r["pred_m_adj"]) ** 2 for r in rows]) or 0.0) if rows else None
    mae_boot = week_block_bootstrap(rows, lambda rs: mean([abs(r["actual_margin"] - r["pred_m_adj"]) - abs(r["actual_margin"] - r["pred_m_base"]) for r in rs])) if rows else {}
    # 80% interval: pred ± 1.28155 * sigma
    z80 = 1.2815515655446004
    cover80 = None
    if rows:
        cover80 = mean([1.0 if abs(r["actual_margin"] - r["pred_m_adj"]) <= z80 * SIGMA_MARGIN else 0.0 for r in rows])
    slope = res["metrics"]["slope_adj"]
    intercept = None
    if rows and slope is not None:
        xs = [logit(r["p_adj"]) for r in rows]
        # intercept from last IRLS not stored; report None with note
        intercept = {"note": "logistic intercept not a gate; slope is K-4"}
    return {
        "M-1": {
            "by_abs_close": bucket_stats("close", lambda r: r["abs_close"]),
            "by_abs_delta": bucket_stats("delta", lambda r: r["abs_delta"]),
        },
        "M-2": {
            "mae_margin_base": mae_b,
            "mae_margin_adj": mae_a,
            "rmse_margin_base": rmse_b,
            "rmse_margin_adj": rmse_a,
            "ll_base": res["metrics"]["mean_logloss_base"],
            "ll_adj": res["metrics"]["mean_logloss_adj"],
            "brier_base": res["metrics"]["mean_brier_base"],
            "brier_adj": res["metrics"]["mean_brier_adj"],
            "mae_delta_ci": {"lo": mae_boot.get("ci_lo"), "hi": mae_boot.get("ci_hi"), "obs": mae_boot.get("obs")},
            "adj_beats_base": False if mae_a is None or mae_b is None else mae_a < mae_b,
            "null": "null" if mae_a is None or mae_b is None or mae_a >= mae_b else "adj lower MAE",
        },
        "M-3": {
            "reliability": res["reliability"],
            "slope": slope,
            "intercept": intercept,
            "coverage_80": cover80,
            "v_note": "80% interval = pred_margin ± 1.28155 σ_margin; V gate reported, not a pass cut here",
        },
        "M-4": {
            "status": "NOT RUN",
            "reason": "no timestamped open for <=2023 in the deposited nflverse close table (earliest price is not a true open; pre7d absent)",
        },
        "M-5": {
            "status": "DEFERRED",
            "reason": "OOS edge survival deferred to the single holdout opening; le2023 is in-sample-adjacent and may not be cited as edge (I-5)",
        },
    }


def game(season: int, week: int, i: int, **kw: Any) -> Dict[str, Any]:
    row = {
        "season": season,
        "week": week,
        "home": kw.get("home", "AAA"),
        "away": kw.get("away", "BBB"),
        "game_id": kw.get("game_id") or f"{season}_{week}_{i}",
        "residual_complete": kw.get("residual_complete", True),
        "delta_margin": kw.get("delta_margin", 0.0),
        "delta_total": kw.get("delta_total", 0.0),
        "baseline_margin": kw.get("baseline_margin", 3.0),
        "baseline_total": kw.get("baseline_total", 45.0),
        "close_spread_home": kw.get("close_spread_home", -3.0),
        "close_total": kw.get("close_total", 45.0),
        "actual_margin": kw.get("actual_margin", 4.5),
        "actual_total": kw.get("actual_total", 47.0),
        "close_label": CLOSE_LABEL,
        "source_ts": kw.get("source_ts"),
        "as_of_ts": kw.get("as_of_ts"),
        "outcome_joined_before_freeze": kw.get("outcome_joined_before_freeze", False),
        "close_joined_before_freeze": kw.get("close_joined_before_freeze", False),
        "null_flag": kw.get("null_flag"),
    }
    return row


def load_expected() -> Dict[str, Any]:
    path = HERE / "t_expected" / "T1_T10_EXPECTED.json"
    if sha256_file(path) != REQUIRED_EXPECTED:
        die("expected-answers sha mismatch; file must be the pre-run deposit")
    return json.loads(path.read_text(encoding="utf-8"))


def run_unit_tests(expected: Dict[str, Any]) -> Dict[str, Any]:
    results: Dict[str, Any] = {}
    # T-1
    exp = expected["T-1"]
    rows = [game(2018, 1, i, baseline_margin=3.0, delta_margin=1.5, close_spread_home=-3.0, actual_margin=4.5) for i in range(3)]
    # base spread = -3, adj = -(3+1.5)=-4.5
    t1 = score_universe("T-1", rows, "paired close-vs-outcome sign")
    d = t1["metrics"]["spread_clv_delta"]
    if abs((d or 0) - exp["delta_pts"]) > 1e-12:
        die(f"T-1 delta {d} != {exp['delta_pts']}")
    if (t1["metrics"]["ml_clv_implied_prob_delta"] or 0) <= 0:
        die("T-1 implied-prob delta sign must match points (+)")
    rows_m = [game(2018, 1, i, baseline_margin=3.0, delta_margin=-1.5, close_spread_home=-3.0, actual_margin=4.5) for i in range(3)]
    t1m = score_universe("T-1-mirror", rows_m, "mirror")
    if abs((t1m["metrics"]["spread_clv_delta"] or 0) - exp["mirror_delta_pts"]) > 1e-12:
        die(f"T-1 mirror {t1m['metrics']['spread_clv_delta']} != {exp['mirror_delta_pts']}")
    results["T-1"] = {"pass": True, "delta": d, "mirror": t1m["metrics"]["spread_clv_delta"], "label": CVO_LABEL}

    # T-2
    e2 = expected["T-2"]
    names = list(HOLM_NINE)
    holm = holm_bonferroni(list(zip(names, e2["p"])))
    sig = [h["test_id"] for h in holm if h["significant"]]
    if len(sig) != 1 or holm[0]["p"] != 0.001 or not holm[0]["significant"]:
        die(f"T-2 Holm {holm}")
    if holm_by_primary := next(h for h in holm if h["test_id"] == PRIMARY):
        pass
    results["T-2"] = {"pass": True, "significant": sig, "rejection_means": "SIGNIFICANT"}

    # T-3
    e3 = expected["T-3"]
    rows = []
    for w in range(1, 11):
        rows.append({"season": 2018, "week": w, "spread_clv_delta": e3["constant_delta"]})
    boot = week_block_bootstrap(rows, lambda rs: mean([r["spread_clv_delta"] for r in rs]))
    boot2 = week_block_bootstrap(rows, lambda rs: mean([r["spread_clv_delta"] for r in rs]))
    if boot["ci_lo"] != e3["ci"][0] or boot["ci_hi"] != e3["ci"][1]:
        die(f"T-3 CI {boot['ci_lo'], boot['ci_hi']}")
    if boot != boot2:
        die("T-3 rerun not bit-identical")
    results["T-3"] = {"pass": True, "ci": [boot["ci_lo"], boot["ci_hi"]], "bit_identical": True}

    # T-4
    e4 = expected["T-4"]
    p, y = e4["p"], e4["y"]
    br = sum(brier(yi, pi) for yi, pi in zip(y, p)) / 3
    ll = sum(log_loss(yi, pi) for yi, pi in zip(y, p)) / 3
    if abs(br - e4["brier"]) > e4["tol"] or abs(ll - e4["logloss_nats"]) > e4["tol"]:
        die(f"T-4 brier/ll {br} {ll}")
    rel = reliability(p, y)
    occ = [b["bin"] for b in rel if b["n"] > 0]
    if occ != e4["reliability_occupied_bins"]:
        die(f"T-4 bins {occ}")
    grid_p = [(i + 0.5) / 20.0 for i in range(20)]
    sl = calibration_slope_logit(grid_p, grid_p)
    if sl is None or abs(sl - 1.0) > 1e-6:
        die(f"T-4 perfect slope {sl}")
    results["T-4"] = {"pass": True, "brier": br, "logloss": ll, "bins": occ, "perfect_slope": sl, "clip_count": CLIP["n"]}

    # T-5
    e5 = expected["T-5"]
    got = phi((e5["pred_margin"] - e5["line_margin"]) / e5["sigma"])
    if abs(got - e5["phi"]) > e5["tol"]:
        die(f"T-5 {got}")
    if abs(p_cover(3.0, 0.0, 13.0) - got) > e5["tol"]:
        die("T-5 p_cover used a rescale")
    results["T-5"] = {"pass": True, "phi": got}

    # T-6
    def season_games(season: int, n_nonzero: int, weeks: int = 17, per: int = 16) -> List[Dict[str, Any]]:
        rows = []
        k = 0
        for w in range(1, weeks + 1):
            for i in range(per):
                nz = k < n_nonzero
                k += 1
                rows.append(game(season, w, i, delta_margin=1.0 if nz else 0.0, delta_total=0.0, baseline_margin=7.0, close_spread_home=-3.0, actual_margin=4.5))
        return rows

    u_pass = season_games(2018, 251) + season_games(2019, 250)
    r6 = score_universe("T-6-pass", u_pass, "501 nonzero")
    if r6["n_nonzero_adjustment"] != 501 or r6["i2"] != "MET":
        die(f"T-6 pass {r6['n_nonzero_adjustment']} {r6['i2']}")
    u_499 = season_games(2018, 250) + season_games(2019, 249)
    r499 = score_universe("T-6-499", u_499, "499")
    if r499["i2"] != "INCONCLUSIVE":
        die("T-6 499")
    u_part = season_games(2018, 501, weeks=17)
    rpart = score_universe("T-6-partial", u_part, "one season")
    if rpart["i2"] != "INCONCLUSIVE":
        die("T-6 partial")
    results["T-6"] = {"pass": True, "n_pass": 501, "i2_pass": r6["i2"], "i2_499": r499["i2"], "i2_partial": rpart["i2"]}

    # T-7
    rows = [game(2018, 1, i, close_spread_home=None if i < 2 else -3.0, close_total=None if i < 2 else 45.0) for i in range(10)]
    r7 = score_universe("T-7", rows, "missing close")
    if r7["missing"]["n_missing_close"] != 2 or r7["missing"]["n_identical_cohort"] != 8:
        die(f"T-7 {r7['missing']}")
    results["T-7"] = {"pass": True, "n_missing_close": 2, "n_identical": 8}

    # T-8
    flags = []
    for field in expected["T-8"]["inputs_removed_in_turn"]:
        kw = {field: None, "null_flag": f"FLAG_MISSING_{field}", "residual_complete": field not in {"delta_margin", "delta_total"}}
        if field in {"delta_margin", "delta_total"}:
            kw["residual_complete"] = False
        row = game(2018, 1, 0, **kw)
        if row.get(field) == 0.0:
            die("T-8 substituted 0")
        flags.append(row["null_flag"])
        r8 = score_universe("T-8-" + field, [row], "null")
        if r8["missing"]["n_identical_cohort"] != 0 and field in {"close_spread_home", "close_total", "actual_margin", "actual_total", "baseline_margin", "baseline_total"}:
            die(f"T-8 {field} not excluded")
    results["T-8"] = {"pass": True, "flags": flags}

    # T-9
    leak_rows = [
        game(2018, 1, 0, source_ts="2022-09-12T18:00:00Z", as_of_ts="2022-09-11T17:00:00Z"),
        game(2018, 1, 1, outcome_joined_before_freeze=True),
    ]
    leaked = False
    try:
        score_universe("T-9", leak_rows, "planted leak")
    except SystemExit:
        leaked = True
    if not leaked:
        die("T-9 did not detect LEAKAGE")
    results["T-9"] = {"pass": True, "detected": "LEAKAGE"}

    # T-10
    def t10_rows(kind: str) -> List[Dict[str, Any]]:
        slots = []
        n = 0
        for season in (2018, 2019):
            for w in range(1, 18):
                for i in range(16):
                    p = 0.2 + 0.6 * ((i % 8) / 7.0)
                    slots.append((season, w, i, p, n))
                    n += 1
        by_p: Dict[float, List[int]] = defaultdict(list)
        for idx, s in enumerate(slots):
            by_p[s[3]].append(idx)
        y_of = [0] * len(slots)
        for p, idxs in by_p.items():
            n_win = int(round(len(idxs) * p))
            for j, idx in enumerate(idxs):
                y_of[idx] = 1 if j < n_win else 0
        rows = []
        for (season, w, i, p, _n), y in zip(slots, y_of):
                    pred = SIGMA_MARGIN * math.sqrt(2.0) * _erfinv(2 * p - 1)
                    if kind == "a":
                        # p_adj varies with p; y tracks p (not perfectly separated).
                        # Base at close so cvo_base=0; adj picks with pred so mean Δcvo > 0.
                        close = 0.0
                        actual = 6.0 if y == 1 else -6.0
                        base_m = 0.0
                        dm = pred
                    elif kind == "b":
                        base_m = pred
                        dm = 0.4  # nonzero adj but same pick side / we force cvo equal by same spread? 
                        # same spread vs close: set base = adj = close so cvo 0? then I-2 still counts dm
                        # keep same spread both arms: base_m = 3, dm = 0 but then I-2 fail.
                        # Use dm!=0 on total only so spread cvo identical
                        base_m = 3.0
                        dm = 0.0
                        dt = 1.0
                        actual = 7.0
                        close = -3.0
                        rows.append(game(season, w, i, baseline_margin=base_m, delta_margin=0.0, delta_total=dt, close_spread_home=close, actual_margin=actual))
                        continue
                    else:
                        # worse LL: adj farther from outcome
                        actual = 7.0 if y else -7.0
                        close = -3.0
                        pred_a = pred
                        pred_b = pred_a + (2.0 if y == 1 else -2.0)  # base closer
                        base_m = pred_b
                        dm = pred_a - pred_b
                        rows.append(game(season, w, i, baseline_margin=base_m, delta_margin=dm, delta_total=0.2, close_spread_home=close, actual_margin=actual))
                        continue
                    rows.append(game(season, w, i, baseline_margin=base_m, delta_margin=dm, delta_total=0.2, close_spread_home=close, actual_margin=actual))
        return rows

    # T-10c constant LL delta 0.0021 via custom scored bootstrap path
    rows_a = t10_rows("a")
    ra = score_universe("T-10a", rows_a, "VALUE PROVEN fixture")
    if ra["i4"]["decision"] != "VALUE PROVEN":
        die(f"T-10a {ra['i4']} k4={ra['k4']}")
    rows_b = t10_rows("b")
    rb = score_universe("T-10b", rows_b, "CI includes 0")
    if rb["i4"]["decision"] != "NO CLAIM":
        die(f"T-10b {rb['i4']} {rb['bootstrap'][PRIMARY]}")
    # T-10c: force LL delta 0.0021 constant on a MET sample
    rows_c = []
    for season in (2018, 2019):
        for w in range(1, 18):
            for i in range(16):
                rows_c.append(game(season, w, i, baseline_margin=3.0, delta_margin=0.5, delta_total=0.2, close_spread_home=-3.0, actual_margin=7.0))
    rc = score_universe("T-10c-raw", rows_c, "will overlay LL")
    # overlay constant LL delta 0.0021 and re-bootstrap K-4
    for r in rc["scored_rows"]:
        r["ml_ll_base"] = 0.5
        r["ml_ll_adj"] = 0.5 + 0.0021
        r["brier_base"] = 0.2
        r["brier_adj"] = 0.2
    ll_boot = week_block_bootstrap(rc["scored_rows"], lambda rs: mean([r["ml_ll_adj"] - r["ml_ll_base"] for r in rs]))
    if abs((ll_boot.get("ci_hi") or 0) - 0.0021) > 1e-12:
        die(f"T-10c UCI {ll_boot}")
    k4c = ll_boot["ci_hi"] <= K4_LL
    if k4c:
        die("T-10c K-4 should fail")
    dec = i4_decision(rc["i2"], True, 0.1, False)
    if dec != "NO CLAIM":
        die("T-10c decision")
    results["T-10"] = {"pass": True, "a": ra["i4"]["decision"], "b": rb["i4"]["decision"], "c": dec, "c_ll_uci": ll_boot["ci_hi"]}
    return results


def _erfinv(x: float) -> float:
    a = 0.147
    sgn = 1.0 if x >= 0 else -1.0
    ln = math.log(max(1e-15, 1.0 - x * x))
    t = 2.0 / (math.pi * a) + ln / 2.0
    return sgn * math.sqrt(max(0.0, math.sqrt(t * t - ln / a) - t))


def load_nflverse_close() -> Dict[Tuple[int, int, str, str], Dict[str, Any]]:
    path = HERE / "inputs" / "nflverse_close_le2023.csv"
    out = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            season = int(row["season"])
            if season in FORBIDDEN:
                die("nflverse close file contains holdout season")
            key = (season, int(row["week"]), alias(row["home"]), alias(row["away"]))
            out[key] = {
                "close_spread_home": float(row["nflverse_spread_line_home"]),
                "close_total": float(row["nflverse_total_line"]),
                "actual_margin": float(row["home_score"]) - float(row["away_score"]),
                "actual_total": float(row["home_score"]) + float(row["away_score"]),
            }
    return out


def load_export_games(export_path: Path) -> List[Dict[str, Any]]:
    doc = json.loads(export_path.read_text(encoding="utf-8"))
    games = []
    for g in doc.get("games") or []:
        season = int(g["season"])
        if season in FORBIDDEN:
            die(f"export contains holdout {season}")
        gid = str(g.get("game_id") or "")
        parts = gid.split("_")
        away = alias(parts[2]) if len(parts) >= 4 else ""
        home = alias("_".join(parts[3:]) if len(parts) > 4 else parts[3]) if len(parts) >= 4 else ""
        games.append(
            {
                "game_id": gid,
                "season": season,
                "week": int(g["week"]),
                "away": away,
                "home": home,
                "complete": bool(g.get("complete")),
                "delta_margin": g.get("delta_margin"),
                "delta_total": g.get("delta_total"),
            }
        )
    return games


def join_fold(games: List[Dict[str, Any]], close: Dict, seasons: Sequence[int]) -> List[Dict[str, Any]]:
    universe = []
    for g in games:
        if g["season"] not in seasons:
            continue
        rec = close.get((g["season"], g["week"], g["home"], g["away"]))
        universe.append(
            {
                "season": g["season"],
                "week": g["week"],
                "home": g["home"],
                "away": g["away"],
                "game_id": g["game_id"],
                "residual_complete": bool(g["complete"] and g["delta_margin"] is not None and g["delta_total"] is not None),
                "delta_margin": g["delta_margin"],
                "delta_total": g["delta_total"],
                "baseline_margin": None,
                "baseline_total": None,
                "close_spread_home": None if rec is None else rec["close_spread_home"],
                "close_total": None if rec is None else rec["close_total"],
                "actual_margin": None if rec is None else rec["actual_margin"],
                "actual_total": None if rec is None else rec["actual_total"],
                "close_label": CLOSE_LABEL,
            }
        )
    # baseline from OOS record book is not required by (c); use record-style 0-HFA if missing? 
    # Fit used record/HFA baseline. Join from same close file does not have record_spread.
    # Use actual-adjacent? NO. Load record from historical oos but only <=2023.
    return universe


def attach_record_baseline(universe: List[Dict[str, Any]]) -> None:
    """Attach record/HFA baseline from historical OOS, skipping 2024+ before store."""
    src = Path("/workspace/data/ops/nfl-reopening-packet-20260916/historical-oos/historical_oos_games.csv")
    book = {}
    if src.is_file():
        with src.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                try:
                    season = int(row["season"])
                except (TypeError, ValueError):
                    continue
                if season in FORBIDDEN:
                    continue
                key = (season, int(row["week"]), alias(row.get("home") or ""), alias(row.get("away") or ""))
                try:
                    book[key] = (-float(row["record_spread"]), float(row["record_total"]))
                except (TypeError, ValueError):
                    continue
    for row in universe:
        rec = book.get((row["season"], row["week"], row["home"], row["away"]))
        if rec:
            row["baseline_margin"], row["baseline_total"] = rec


def slim(res: Dict[str, Any]) -> Dict[str, Any]:
    out = {k: v for k, v in res.items() if k != "scored_rows"}
    return out


def write_report(path: Path, tests: Dict[str, Any], folds: List[Dict[str, Any]], cmd: str, head: str) -> None:
    lines = [
        "# Evaluator v3 dry-run report (acceptance 54bc78ec)",
        "",
        f"**Frozen-fit HEAD:** `{REQUIRED_HEAD}`",
        f"**Run HEAD:** `{head}`",
        f"**SoT spec:** `{REQUIRED_SPEC}`",
        f"**Acceptance:** `{REQUIRED_ACCEPT}`",
        f"**Ruling:** `{REQUIRED_RULING}`",
        f"**Expected answers:** `{REQUIRED_EXPECTED}` (filed before run)",
        f"**Seed:** `{PINNED_SEED}` n_boot={N_BOOT} rng=numpy.default_rng",
        f"**σ_margin:** {SIGMA_MARGIN}  **σ_total:** {SIGMA_TOTAL}",
        f"**Close:** nflverse REG spread_line — {CLOSE_LABEL}",
        f"**Metric label:** {CVO_LABEL}",
        f"**Holdout:** STOPPED. No CLEAR.",
        "",
        "Command (no secrets):",
        "",
        "```",
        cmd,
        "```",
        "",
        "## T-1..T-10",
        "",
    ]
    for k in [f"T-{i}" for i in range(1, 11)]:
        rec = tests.get(k) or tests.get(k.replace("-", ""))
        # keys are T-1
        rec = tests.get(k)
        lines.append(f"- `{k}`: **{'PASS' if rec and rec.get('pass') else 'FAIL'}** {json.dumps({kk: vv for kk, vv in (rec or {}).items() if kk != 'pass'}, default=str)}")
    lines += ["", "## Folds (DRY RUN - NOT A RESULT)", ""]
    for res in folds:
        m = res["missing"]
        i4 = res["i4"]
        k4 = res["k4"]
        lines += [
            f"### `{res['name']}` — **{i4['decision_label']}**",
            "",
            f"- I-2: `{res['i2']}` n_nonzero={res['n_nonzero_adjustment']} by_season={res['n_nonzero_by_season']} full={res['n_full_seasons']}",
            f"- I-4: {i4['decision']} holm={i4['primary_significant_after_holm']} lo>0={i4['primary_ci_lo_gt_0']} k4={i4['k4_pass']}",
            f"- Identical n={m['n_identical_cohort']} cvo-both={m['n_paired_cvo']} edge0 base/adj={m['n_edge0_base']}/{m['n_edge0_adj']}",
            f"- Missing: incomplete={m['n_incomplete_residual']} close={m['n_missing_close']} actual={m['n_missing_actual']} baseline={m['n_missing_baseline']}",
            f"- Missing by season: incomplete={m['n_incomplete_by_season']} close={m['n_missing_close_by_season']}",
            f"- Universe by season: {m['n_universe_by_season']}",
            f"- K-4: LLhi={k4['logloss_delta_ci_hi']} Bhi={k4['brier_delta_ci_hi']} slope={k4['slope_adj']} pass={k4['pass']} {k4['notes']}",
            "",
            "| metric | value |",
            "|---|---|",
        ]
        for key in HOLM_NINE:
            val = res["metrics"][key]
            why = (res.get("metric_undefined") or {}).get(key) or ""
            lines.append(f"| `{key}` | {val if val is not None else 'undefined — ' + why} |")
        lines += ["", "Holm:", ""]
        for h in res["holm"]:
            lines.append(f"- `{h['test_id']}` p={h['p']} sig={h['significant']}")
        b = res["bootstrap"][PRIMARY]
        lines.append(f"- primary CI [{b['ci_lo']}, {b['ci_hi']}] lo>0={b.get('lo_gt_0')} seed={b['seed']}")
        if res.get("modeling"):
            lines += ["", "#### M-1..M-5", "", f"```json\n{json.dumps(res['modeling'], indent=2, default=str)}\n```", ""]
        lines.append("Baseline and adjusted used the same close-present set. Zero-edge drops CLV/ATS only.")
        lines.append("")
    lines += [
        "## Hard rules",
        "",
        "- No 2024/2025/2026 scored.",
        "- No tokens created.",
        "- Seed 20261023. VALUE PROVEN requires CI lo>0.",
        "- Close vs outcome, not certified CLV.",
        "",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def assert_env() -> Tuple[str, Path, Path]:
    leaked = sorted(k for k in os.environ if k.startswith("NFL_TOTALS_"))
    if leaked:
        die(f"NFL_TOTALS_* must be unset; found {leaked}")
    for tok in TOKEN_NAMES:
        if (HERE / tok).exists() or (HERE / "out" / tok).exists():
            die("token present")
    spec = resolve("spec", REQUIRED_SPEC, [HERE / "seeded" / "IMV_SPEC_NFL_INJURY_ADJUSTMENT_TESTS_v1.txt", Path("/cursor/stores/self/imv-inputs/IMV_SPEC_NFL_INJURY_ADJUSTMENT_TESTS_v1.txt")])
    resolve("acceptance", REQUIRED_ACCEPT, [HERE / "seeded" / "IMV_SPEC_NFL_INJURY_PRE_HOLDOUT_ACCEPTANCE_v1.txt"])
    resolve("ruling", REQUIRED_RULING, [HERE / "seeded" / "IMV_RULING_NFL_INJURY_EVALUATOR_READINESS_v1.txt"])
    export = resolve("export", REQUIRED_EXPORT, [HERE / "seeded" / "sealed_injury_export.json", Path("/opt/cursor/artifacts/injury-fit-le2023/sealed_injury_export.json")])
    resolve("fit", REQUIRED_FIT, [HERE / "seeded" / "fit_object.json", Path("/opt/cursor/artifacts/injury-fit-le2023/fit_object.json")])
    head = os.popen("git -C /workspace rev-parse HEAD").read().strip()
    # gates must match a156459b text
    text = spec.read_text(encoding="utf-8")
    for block in (K4_VERBATIM.split("Failing")[0], I4_VERBATIM):
        if " ".join(block.split()) not in " ".join(text.split()):
            die("gate verbatim missing from SoT spec")
    return head, spec, export


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--out", default=str(HERE / "out"))
    p.add_argument("--mode", default="all", choices=("tests", "folds", "all"))
    args = p.parse_args()
    CLIP["n"] = 0
    head, spec, export = assert_env()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    cmd = f"python3 {HERE}/run_injury_residual_evaluator.py --out {out} --mode {args.mode}"
    log(f"cmd={cmd}")
    expected = load_expected()
    tests = {}
    if args.mode in {"tests", "all"}:
        tests = run_unit_tests(expected)
        log("T-1..T-10 PASS")
    folds = []
    if args.mode in {"folds", "all"}:
        close = load_nflverse_close()
        games = load_export_games(export)
        for name, seasons, n_expect in (("F1", (2022,), 268), ("F2", (2023,), 271), ("pooled", (2022, 2023), 539)):
            uni = join_fold(games, close, seasons)
            attach_record_baseline(uni)
            res = score_universe(name, uni, f"inner fold {seasons}", dry_run_label=True)
            if res["missing"]["n_identical_cohort"] != n_expect:
                log(f"note: {name} n_identical={res['missing']['n_identical_cohort']} expected {n_expect}")
            res["modeling"] = modeling_challenges(res)
            folds.append(res)
            log(f"{name} n={res['missing']['n_identical_cohort']} i4={res['i4']['decision']}")
    payload = {
        "kind": "evaluator_v3",
        "holdout": "STOPPED",
        "head": head,
        "frozen_fit_head": REQUIRED_HEAD,
        "spec_sha": REQUIRED_SPEC,
        "acceptance_sha": REQUIRED_ACCEPT,
        "ruling_sha": REQUIRED_RULING,
        "export_sha": REQUIRED_EXPORT,
        "fit_object_sha": REQUIRED_FIT,
        "expected_sha": REQUIRED_EXPECTED,
        "seed": PINNED_SEED,
        "n_boot": N_BOOT,
        "sigma_margin": SIGMA_MARGIN,
        "sigma_total": SIGMA_TOTAL,
        "close_label": CLOSE_LABEL,
        "metric_label": CVO_LABEL,
        "command": cmd,
        "clip_count": CLIP["n"],
        "tests": tests,
        "folds": [slim(f) for f in folds],
    }
    (out / "evaluator_results.json").write_text(json.dumps(payload, sort_keys=True, indent=2, default=str) + "\n", encoding="utf-8")
    write_report(out / "dry-run-report.md", tests, folds, cmd, head)
    prov = [
        "# Provenance v3",
        "",
        "No secrets.",
        f"- Frozen-fit HEAD: `{REQUIRED_HEAD}`",
        f"- Run HEAD: `{head}`",
        f"- Spec `{REQUIRED_SPEC}` acceptance `{REQUIRED_ACCEPT}` ruling `{REQUIRED_RULING}`",
        f"- Export `{REQUIRED_EXPORT}` fit `{REQUIRED_FIT}` expected `{REQUIRED_EXPECTED}`",
        f"- Seed {PINNED_SEED} numpy.default_rng n_boot={N_BOOT}",
        f"- Sigma margin {SIGMA_MARGIN} total {SIGMA_TOTAL} (see inputs/sigma_from_fit.json)",
        f"- Command: `{cmd}`",
        f"- Close: nflverse REG spread_line, {CLOSE_LABEL}, metric {CVO_LABEL}",
        "- NFL_TOTALS_*: unset. Tokens: none.",
        "",
    ]
    (out / "provenance.md").write_text("\n".join(prov) + "\n", encoding="utf-8")
    if out.resolve() == (HERE / "out").resolve():
        (HERE / "provenance.md").write_text("\n".join(prov) + "\n", encoding="utf-8")
    print(json.dumps({"tests": {k: v.get("pass") for k, v in tests.items()}, "folds": {f["name"]: f["i4"]["decision"] for f in folds}}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
