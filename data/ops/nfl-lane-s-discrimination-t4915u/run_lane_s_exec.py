#!/usr/bin/env python3
"""t4915u Lane S EXEC — frozen discrimination audit (one run).

RETRO_FIT / DEV_RESEARCH exploratory. CERT=0. NFL NO-GO.
Does not regenerate forecasts, change engine math, or search weights/cutoffs.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Callable, Optional

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
INPUTS = os.path.join(HERE, "inputs")

# --- Freeze pins (STOP if SCORE_RESULTS sha8 != 2b9f302e) ---
EXPECTED = {
    "SCORE_RESULTS.json": "2b9f302e097183ef275185a4edb100ab206565a087ca1ce78dbe8062524e877a",
    "SAMPLE_MANIFEST_70.json": "861a6264ea4727f4a3caf0a58e1d79bad60bc158443c12df90b2256dcbac5553",
    "RECON_MATRIX_w2_440314e4.csv": "708513db885fe362aca9446578154d58e9d8265857ec2385e475323b24f24182",
    "RECON_MATRIX_w3w6_f92aaea3.csv": "cdff011536a7cd9224b1238e08b707c36222243833f778f2df61b577e0c80235",
    "EXEC_FREEZE_t4915u_LANE_S_ANALYSIS_PLAN.md": "29dc400571da4f7bfdd7f99b195324d8e71042a7c133ce831cd929f6e3ac53fc",
    "OWNER_ACCEPT_t4915u_PHASE1_LANE_S.md": "dd4a2390a96568ab223fbc24031e4630d3f1607cccdc7bc38c0f5ec5481518c8",
}

BOOT_B = 2000
BOOT_SEED = 4915
WILSON_Z = 1.959963984540054  # Phi^{-1}(0.975)
WEEKS = (2, 3, 4, 5, 6)

SIGNAL_NAMES = [
    "wl_home_wpct",
    "wl_away_wpct",
    "wl_diff",
    "wl_index_off_diff",
    "wl_index_def_diff",
    "wl_index_net",
    "epa_off_diff",
    "epa_def_diff",
    "epa_net_diff",
    "success_off_diff",
    "success_def_diff",
    "success_net_diff",
    "matchup_diff_off_epa_5g",
    "matchup_diff_success_rate_5g",
]

RECON_NUMERIC = {
    "offense_index_home",
    "offense_index_away",
    "defense_index_home",
    "defense_index_away",
    "home_off_epa_5g",
    "away_off_epa_5g",
    "home_def_epa_allowed_5g",
    "away_def_epa_allowed_5g",
    "home_success_offense_5g",
    "away_success_offense_5g",
    "home_success_defense_allowed_5g",
    "away_success_defense_allowed_5g",
    "matchup_diff_off_epa_5g",
    "matchup_diff_success_rate_5g",
}


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def fnum(x: Any) -> Optional[float]:
    if x is None:
        return None
    if isinstance(x, float) and not math.isfinite(x):
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(v):
        return None
    return v


def jnum(x: Any) -> Any:
    """JSON-safe number (None -> null)."""
    if x is None:
        return None
    if isinstance(x, (bool, int)):
        return x
    if isinstance(x, float):
        if not math.isfinite(x):
            return None
        return x
    return x


def parse_record(rec: Optional[str]) -> tuple[Optional[float], Optional[int], Optional[int], Optional[int], Optional[int]]:
    """wins/(wins+losses); ties ignored in denom. Missing if denom==0 or unparsable.

    Returns (wpct, wins, losses, ties, denom).
    """
    if rec is None or str(rec).strip() == "":
        return None, None, None, None, None
    parts = str(rec).strip().split("-")
    if len(parts) < 2:
        return None, None, None, None, None
    try:
        wins = int(parts[0])
        losses = int(parts[1])
        ties = int(parts[2]) if len(parts) >= 3 else 0
    except ValueError:
        return None, None, None, None, None
    denom = wins + losses
    if denom == 0:
        return None, wins, losses, ties, 0
    return wins / denom, wins, losses, ties, denom


def sub(a: Optional[float], b: Optional[float]) -> Optional[float]:
    if a is None or b is None:
        return None
    return a - b


def add(a: Optional[float], b: Optional[float]) -> Optional[float]:
    if a is None or b is None:
        return None
    return a + b


def rankdata_average(a: np.ndarray) -> np.ndarray:
    """1-based average ranks for ties (scipy.stats.rankdata method='average')."""
    a = np.asarray(a, dtype=float)
    n = len(a)
    order = np.argsort(a, kind="mergesort")
    ranks = np.empty(n, dtype=float)
    i = 0
    while i < n:
        j = i + 1
        while j < n and a[order[j]] == a[order[i]]:
            j += 1
        avg = 0.5 * ((i + 1) + j)
        ranks[order[i:j]] = avg
        i = j
    return ranks


def pearson_r(x: np.ndarray, y: np.ndarray) -> Optional[float]:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if len(x) < 2:
        return None
    xd = x - x.mean()
    yd = y - y.mean()
    sx = float(np.dot(xd, xd))
    sy = float(np.dot(yd, yd))
    if sx <= 0.0 or sy <= 0.0:
        return None
    return float(np.dot(xd, yd) / math.sqrt(sx * sy))


def spearman_rho(x: np.ndarray, y: np.ndarray) -> Optional[float]:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if len(x) < 2:
        return None
    return pearson_r(rankdata_average(x), rankdata_average(y))


def bootstrap_corr(
    x: np.ndarray,
    y: np.ndarray,
    fn: Callable[[np.ndarray, np.ndarray], Optional[float]],
    B: int = BOOT_B,
    seed: int = BOOT_SEED,
) -> dict[str, Any]:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    n = len(x)
    point = fn(x, y)
    rng = np.random.RandomState(seed)
    stats: list[float] = []
    n_undefined = 0
    for _ in range(B):
        idx = rng.randint(0, n, n)
        v = fn(x[idx], y[idx])
        if v is None or not math.isfinite(v):
            n_undefined += 1
            continue
        stats.append(v)
    out = {
        "n": n,
        "estimate": jnum(point),
        "ci_low": None,
        "ci_high": None,
        "ci_crosses_0": None,
        "B": B,
        "seed": seed,
        "n_undefined_resamples": n_undefined,
        "n_defined_resamples": len(stats),
        "method": "percentile_bootstrap_pairs",
    }
    if stats:
        arr = np.asarray(stats, dtype=float)
        lo = float(np.percentile(arr, 2.5, method="linear"))
        hi = float(np.percentile(arr, 97.5, method="linear"))
        out["ci_low"] = lo
        out["ci_high"] = hi
        if point is not None:
            out["ci_crosses_0"] = lo <= 0.0 <= hi
    return out


def wilson_ci(k: int, n: int, z: float = WILSON_Z) -> dict[str, Any]:
    if n <= 0:
        return {"n": n, "k": k, "rate": None, "ci_low": None, "ci_high": None, "method": "wilson", "z": z}
    phat = k / n
    z2 = z * z
    denom = 1.0 + z2 / n
    center = (phat + z2 / (2.0 * n)) / denom
    margin = z * math.sqrt((phat * (1.0 - phat) + z2 / (4.0 * n)) / n) / denom
    return {
        "n": n,
        "k": k,
        "rate": phat,
        "ci_low": center - margin,
        "ci_high": center + margin,
        "method": "wilson",
        "z": z,
    }


def norm_ppf(p: float) -> float:
    """Acklam rational approximation to inverse standard normal CDF."""
    if p <= 0.0 or p >= 1.0:
        raise ValueError("p in (0,1)")
    a = [
        -3.969683028665376e01,
        2.209460984245205e02,
        -2.759285104469687e02,
        1.383577518672690e02,
        -3.066479806614716e01,
        2.506628277459239e00,
    ]
    b = [
        -5.447609879822406e01,
        1.615858368580409e02,
        -1.556989798598866e02,
        6.680131188771972e01,
        -1.328068155288572e01,
    ]
    c = [
        -7.784894002430293e-03,
        -3.223964580411365e-01,
        -2.400758277161838e00,
        -2.549732539343734e00,
        4.374664141464968e00,
        2.938163982698783e00,
    ]
    d = [
        7.784695709041462e-03,
        3.224671290700398e-01,
        2.445134137142996e00,
        3.754408661907416e00,
    ]
    plow = 0.02425
    phigh = 1.0 - plow
    if p < plow:
        q = math.sqrt(-2.0 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
        )
    if p > phigh:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
        )
    q = p - 0.5
    r = q * q
    return (
        (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5])
        * q
        / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0)
    )


def t_ppf(p: float, df: float) -> float:
    """Two-sided-ready inverse Student-t via Cornish–Fisher on Acklam z.

    Documented in ASSUMPTIONS.md. Adequate for n>=10 (week-6 smallest complete n).
    """
    z = norm_ppf(p)
    if df > 1e8:
        return z
    z2 = z * z
    z3 = z2 * z
    z5 = z3 * z2
    z7 = z5 * z2
    g1 = z
    g2 = (z3 + z) / (4.0 * df)
    g3 = (5.0 * z5 + 16.0 * z3 + 3.0 * z) / (96.0 * df * df)
    g4 = (3.0 * z7 + 19.0 * z5 + 17.0 * z3 - 15.0 * z) / (384.0 * df * df * df)
    return g1 + g2 + g3 + g4


def ols_margin_on_signal(x: np.ndarray, y: np.ndarray) -> dict[str, Any]:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    n = int(len(x))
    empty = {
        "n": n,
        "slope": None,
        "intercept": None,
        "se_slope": None,
        "se_intercept": None,
        "df": None,
        "t_crit_95": None,
        "t_method": "acklam_norm_ppf + cornish_fisher_t",
        "slope_ci_low": None,
        "slope_ci_high": None,
        "intercept_ci_low": None,
        "intercept_ci_high": None,
        "slope_ci_crosses_0": None,
        "r_squared": None,
        "undefined_reason": None,
    }
    if n < 3:
        empty["undefined_reason"] = "n<3"
        return empty
    xbar = float(x.mean())
    ybar = float(y.mean())
    xd = x - xbar
    sxx = float(np.dot(xd, xd))
    if sxx <= 0.0:
        empty["undefined_reason"] = "sxx==0"
        return empty
    slope = float(np.dot(xd, y - ybar) / sxx)
    intercept = ybar - slope * xbar
    resid = y - (intercept + slope * x)
    sse = float(np.dot(resid, resid))
    df = n - 2
    s2 = sse / df
    se_slope = math.sqrt(s2 / sxx)
    se_int = math.sqrt(s2 * (1.0 / n + xbar * xbar / sxx))
    tcrit = t_ppf(0.975, float(df))
    sst = float(np.dot(y - ybar, y - ybar))
    r2 = (1.0 - sse / sst) if sst > 0.0 else None
    slo = slope - tcrit * se_slope
    shi = slope + tcrit * se_slope
    return {
        "n": n,
        "slope": slope,
        "intercept": intercept,
        "se_slope": se_slope,
        "se_intercept": se_int,
        "df": df,
        "t_crit_95": tcrit,
        "t_method": "acklam_norm_ppf + cornish_fisher_t",
        "slope_ci_low": slo,
        "slope_ci_high": shi,
        "intercept_ci_low": intercept - tcrit * se_int,
        "intercept_ci_high": intercept + tcrit * se_int,
        "slope_ci_crosses_0": slo <= 0.0 <= shi,
        "r_squared": r2,
        "undefined_reason": None,
    }


def assign_tertiles_by_rank(values: np.ndarray) -> np.ndarray:
    """Fixed tertiles by average rank. No optimized cutoffs.

    T1 if rank <= n/3; T2 if rank <= 2n/3; else T3. Ties share a rank and
    therefore the same tertile when that shared rank does not straddle a cut.
    """
    ranks = rankdata_average(values)
    n = len(values)
    c1 = n / 3.0
    c2 = 2.0 * n / 3.0
    out = np.empty(n, dtype=int)
    for i, r in enumerate(ranks):
        if r <= c1:
            out[i] = 1
        elif r <= c2:
            out[i] = 2
        else:
            out[i] = 3
    return out


def pivot_recon(path: str) -> dict[str, dict[str, Any]]:
    """Long field/reconstructed_value → wide game rows.

    Numeric field is MISSING unless status==DERIVED_PREGAME and value is finite.
    Extra games (not in SCORE_RESULTS 70) are retained here and filtered later.
    """
    wide: dict[str, dict[str, Any]] = {}
    n_rows = 0
    n_missing_status = 0
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            n_rows += 1
            gid = row["game_id"]
            rec = wide.setdefault(
                gid,
                {
                    "game_id": gid,
                    "season": row.get("season"),
                    "week": row.get("week"),
                    "home_team": row.get("home_team"),
                    "away_team": row.get("away_team"),
                    "_field_status": {},
                },
            )
            field = row["field"]
            status = row.get("status") or ""
            rec["_field_status"][field] = status
            raw = row.get("reconstructed_value")
            if field in RECON_NUMERIC:
                if status != "DERIVED_PREGAME":
                    n_missing_status += 1
                    rec[field] = None
                else:
                    rec[field] = fnum(raw)
            elif field in ("home_team", "away_team", "game_id"):
                rec[field] = raw
            elif field == "matchup_week":
                rec["recon_matchup_week"] = raw
    return {"games": wide, "n_rows": n_rows, "n_missing_status": n_missing_status}


def complete_pairs(rows: list[dict[str, Any]], xkey: str, ykey: str) -> tuple[np.ndarray, np.ndarray, list[str]]:
    xs: list[float] = []
    ys: list[float] = []
    gids: list[str] = []
    for r in rows:
        xv = r.get(xkey)
        yv = r.get(ykey)
        if xv is None or yv is None:
            continue
        xs.append(float(xv))
        ys.append(float(yv))
        gids.append(r["game_id"])
    return np.asarray(xs, dtype=float), np.asarray(ys, dtype=float), gids


def su_split(rows: list[dict[str, Any]], sig: str) -> dict[str, Any]:
    """SU win rate when signal>0 vs signal<0. Exclude signal==0 and margin ties."""
    pos_home = 0
    pos_n = 0
    neg_home = 0
    neg_n = 0
    n_sig_zero = 0
    n_margin_tie = 0
    n_missing = 0
    for r in rows:
        s = r.get(sig)
        m = r.get("realized_margin")
        if s is None:
            n_missing += 1
            continue
        if m is None:
            continue
        if m == 0:
            n_margin_tie += 1
            continue
        if s == 0:
            n_sig_zero += 1
            continue
        home_win = 1 if m > 0 else 0
        if s > 0:
            pos_n += 1
            pos_home += home_win
        else:
            neg_n += 1
            neg_home += home_win
    pos = wilson_ci(pos_home, pos_n)
    neg = wilson_ci(neg_home, neg_n)
    return {
        "signal_gt_0": {**pos, "home_wins": pos_home, "meaning": "P(home win | signal>0), ties excluded"},
        "signal_lt_0": {**neg, "home_wins": neg_home, "meaning": "P(home win | signal<0), ties excluded"},
        "n_signal_zero_excluded": n_sig_zero,
        "n_margin_ties_excluded": n_margin_tie,
        "n_signal_missing": n_missing,
    }


def tertile_block(rows: list[dict[str, Any]], sig: str) -> dict[str, Any]:
    x, y, gids = complete_pairs(rows, sig, "realized_margin")
    if len(x) == 0:
        return {"n_complete": 0, "undefined_reason": "n_complete==0", "tertiles": []}
    labels = assign_tertiles_by_rank(x)
    blocks = []
    for t in (1, 2, 3):
        mask = labels == t
        n = int(mask.sum())
        if n == 0:
            blocks.append({"tertile": t, "n": 0, "mean_realized_margin": None, "mean_signal": None})
            continue
        blocks.append(
            {
                "tertile": t,
                "n": n,
                "mean_realized_margin": float(y[mask].mean()),
                "mean_signal": float(x[mask].mean()),
                "min_signal": float(x[mask].min()),
                "max_signal": float(x[mask].max()),
                "label": {1: "lowest_rank_third", 2: "middle_rank_third", 3: "highest_rank_third"}[t],
            }
        )
    means = [b["mean_realized_margin"] for b in blocks if b["mean_realized_margin"] is not None]
    monotonic_up = means == sorted(means) if len(means) == 3 else None
    monotonic_down = means == sorted(means, reverse=True) if len(means) == 3 else None
    return {
        "n_complete": int(len(x)),
        "assignment": "average_rank; T1 if rank<=n/3; T2 if rank<=2n/3; else T3",
        "tertiles": blocks,
        "mean_margin_monotonic_increasing": monotonic_up,
        "mean_margin_monotonic_decreasing": monotonic_down,
    }


def analyze_signal(rows: list[dict[str, Any]], sig: str) -> dict[str, Any]:
    x, y, gids = complete_pairs(rows, sig, "realized_margin")
    xf, _, _ = complete_pairs(rows, sig, "forecast_margin")
    missing_games = [r["game_id"] for r in rows if r.get(sig) is None]
    n_complete = int(len(x))
    block: dict[str, Any] = {
        "signal": sig,
        "n_complete": n_complete,
        "n_missing": len(missing_games),
        "missing_games": missing_games,
        "label": "RETRO_FIT / DEV_RESEARCH exploratory" if sig.startswith(("epa_", "success_", "matchup_")) else "DEV_RESEARCH / RETRO_FIT exploratory",
    }
    if n_complete < 2:
        block["undefined_reason"] = "n_complete<2"
        block["spearman_vs_realized_margin"] = None
        block["pearson_vs_realized_margin"] = None
        block["su_when_signal_sign"] = su_split(rows, sig)
        block["tertiles"] = tertile_block(rows, sig)
        block["ols_realized_margin_on_signal"] = ols_margin_on_signal(x, y) if n_complete else None
        block["week_stratified"] = {}
        block["leave_one_week_out_spearman"] = {}
        block["spearman_vs_forecast_margin"] = None
        return block

    block["spearman_vs_realized_margin"] = bootstrap_corr(x, y, spearman_rho)
    block["pearson_vs_realized_margin"] = bootstrap_corr(x, y, pearson_r)
    block["su_when_signal_sign"] = su_split(rows, sig)
    block["tertiles"] = tertile_block(rows, sig)
    block["ols_realized_margin_on_signal"] = ols_margin_on_signal(x, y)

    week_s: dict[str, Any] = {}
    for w in WEEKS:
        wrows = [r for r in rows if r.get("matchup_week") == w]
        wx, wy, _ = complete_pairs(wrows, sig, "realized_margin")
        week_s[str(w)] = {
            "n_games": len(wrows),
            "n_complete": int(len(wx)),
            "spearman_vs_realized_margin": bootstrap_corr(wx, wy, spearman_rho) if len(wx) >= 2 else None,
            "su_when_signal_sign": su_split(wrows, sig),
        }
    block["week_stratified"] = week_s

    loo: dict[str, Any] = {}
    rhos = []
    for w in WEEKS:
        keep = [r for r in rows if r.get("matchup_week") != w]
        kx, ky, _ = complete_pairs(keep, sig, "realized_margin")
        rho = spearman_rho(kx, ky) if len(kx) >= 2 else None
        loo[f"drop_week_{w}"] = {
            "n_complete": int(len(kx)),
            "spearman_rho": jnum(rho),
        }
        if rho is not None:
            rhos.append(rho)
    loo["range_min"] = min(rhos) if rhos else None
    loo["range_max"] = max(rhos) if rhos else None
    loo["range"] = (max(rhos) - min(rhos)) if rhos else None
    loo["all_same_sign"] = (all(r > 0 for r in rhos) or all(r < 0 for r in rhos)) if rhos else None
    block["leave_one_week_out_spearman"] = loo

    if len(xf) >= 2:
        # association-to-IF only — not a retune
        x_if, y_if, _ = complete_pairs(rows, sig, "forecast_margin")
        block["spearman_vs_forecast_margin"] = {
            **bootstrap_corr(x_if, y_if, spearman_rho),
            "note": "association-to-IF only; not a retune",
        }
    else:
        block["spearman_vs_forecast_margin"] = None
    return block


def week_subset_audit(signal_results: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Whether any apparent signal concentrates in one week or small subset."""
    per_signal = {}
    for sig, res in signal_results.items():
        overall = (res.get("spearman_vs_realized_margin") or {}).get("estimate")
        overall_cross = (res.get("spearman_vs_realized_margin") or {}).get("ci_crosses_0")
        weeks = []
        n_weeks_ci_excl0 = 0
        n_weeks_defined = 0
        driver = None
        max_abs = -1.0
        for w in WEEKS:
            ws = res.get("week_stratified", {}).get(str(w)) or {}
            sp = ws.get("spearman_vs_realized_margin") or {}
            est = sp.get("estimate")
            cross = sp.get("ci_crosses_0")
            n_c = ws.get("n_complete")
            if est is not None:
                n_weeks_defined += 1
                if abs(est) > max_abs:
                    max_abs = abs(est)
                    driver = w
            if cross is False:
                n_weeks_ci_excl0 += 1
            weeks.append(
                {
                    "week": w,
                    "n_complete": n_c,
                    "spearman": est,
                    "ci_crosses_0": cross,
                }
            )
        loo = res.get("leave_one_week_out_spearman") or {}
        loo_vals = []
        drop_deltas = []
        for w in WEEKS:
            v = (loo.get(f"drop_week_{w}") or {}).get("spearman_rho")
            if v is not None:
                loo_vals.append((w, v))
                if overall is not None:
                    drop_deltas.append({"week_dropped": w, "rho_without_week": v, "delta_from_overall": v - overall})
        # concentration: overall CI excludes 0 but most weeks' CIs include 0,
        # or dropping one week flips overall sign / moves estimate by >= 0.10
        flips = []
        large_moves = []
        if overall is not None:
            for d in drop_deltas:
                if overall == 0:
                    continue
                if (overall > 0) != (d["rho_without_week"] > 0) and d["rho_without_week"] != 0:
                    flips.append(d["week_dropped"])
                if abs(d["delta_from_overall"]) >= 0.10:
                    large_moves.append(d)
        flag = False
        reasons = []
        if overall is not None and overall_cross is False and n_weeks_ci_excl0 <= 1 and n_weeks_defined >= 3:
            flag = True
            reasons.append("overall Spearman CI excludes 0 but at most one week CI excludes 0")
        if flips:
            flag = True
            reasons.append(f"dropping week(s) {flips} flips LOO Spearman sign vs overall")
        if large_moves:
            flag = True
            reasons.append("dropping at least one week moves Spearman by >= 0.10")
        if driver is not None and overall is not None and abs(overall) >= 0.15:
            # check if other weeks are near zero while one is large
            others = [w["spearman"] for w in weeks if w["week"] != driver and w["spearman"] is not None]
            drv = next(w["spearman"] for w in weeks if w["week"] == driver)
            if others and drv is not None and abs(drv) >= 0.35 and max(abs(o) for o in others) < 0.15:
                flag = True
                reasons.append(f"week {driver} Spearman |rho|>=0.35 while all other weeks |rho|<0.15")
        per_signal[sig] = {
            "overall_spearman": overall,
            "overall_ci_crosses_0": overall_cross,
            "weeks": weeks,
            "n_weeks_ci_excludes_0": n_weeks_ci_excl0,
            "loo_range_min": loo.get("range_min"),
            "loo_range_max": loo.get("range_max"),
            "loo_range": loo.get("range"),
            "loo_all_same_sign": loo.get("all_same_sign"),
            "loo_drop_deltas": drop_deltas,
            "sign_flip_when_drop_weeks": flips,
            "large_loo_moves": large_moves,
            "largest_abs_week": driver,
            "concentration_flag": flag,
            "concentration_reasons": reasons,
        }
    any_flag = any(v["concentration_flag"] for v in per_signal.values())
    flagged = [k for k, v in per_signal.items() if v["concentration_flag"]]
    return {
        "any_signal_concentrated": any_flag,
        "flagged_signals": flagged,
        "n_sample": len(rows),
        "week_counts": {str(w): sum(1 for r in rows if r.get("matchup_week") == w) for w in WEEKS},
        "per_signal": per_signal,
        "note": "Concentration flags are descriptive (LOO move >=0.10, sign flip, or overall-vs-week CI mismatch). Not a cutoff search.",
    }


def control_if_block(rows: list[dict[str, Any]]) -> dict[str, Any]:
    x, y, _ = complete_pairs(rows, "forecast_margin", "realized_margin")
    return {
        "note": "Control IF forecast_margin vs realized_margin on the sealed 70. Known comparator; not a retune.",
        "n_complete": int(len(x)),
        "spearman_vs_realized_margin": bootstrap_corr(x, y, spearman_rho) if len(x) >= 2 else None,
        "pearson_vs_realized_margin": bootstrap_corr(x, y, pearson_r) if len(x) >= 2 else None,
        "ols_realized_margin_on_forecast_margin": ols_margin_on_signal(x, y) if len(x) >= 3 else None,
        "su_when_signal_sign": su_split(rows, "forecast_margin"),
        "tertiles": tertile_block(rows, "forecast_margin"),
    }


def main() -> int:
    # --- verify pins ---
    pins = {}
    for name, exp in EXPECTED.items():
        path = os.path.join(INPUTS, name) if name.endswith((".json", ".csv")) else os.path.join(HERE, name)
        if name.startswith("EXEC_FREEZE") or name.startswith("OWNER_ACCEPT"):
            path = os.path.join(HERE, name)
        digest = sha256_file(path)
        pins[name] = {"path": path, "sha256": digest, "sha8": digest[:8], "match": digest == exp}
        if name == "SCORE_RESULTS.json" and not digest.startswith("2b9f302e"):
            print("STOP: SCORE_RESULTS sha256 does not start with 2b9f302e", digest, file=sys.stderr)
            return 2
        if digest != exp:
            print(f"STOP: hash mismatch {name}: got {digest} expected {exp}", file=sys.stderr)
            return 2

    score = json.load(open(os.path.join(INPUTS, "SCORE_RESULTS.json")))
    manifest = json.load(open(os.path.join(INPUTS, "SAMPLE_MANIFEST_70.json")))
    score_ids = [r["game_id"] for r in score["rows"]]
    man_ids = [g["game_id"] for g in manifest["games"]]
    if len(score_ids) != 70 or len(set(score_ids)) != 70:
        print("STOP: SCORE_RESULTS is not 70 unique game_ids", file=sys.stderr)
        return 2
    if sorted(score_ids) != sorted(man_ids):
        print("STOP: SCORE_RESULTS game_ids != SAMPLE_MANIFEST_70", file=sys.stderr)
        return 2

    w2 = pivot_recon(os.path.join(INPUTS, "RECON_MATRIX_w2_440314e4.csv"))
    w3 = pivot_recon(os.path.join(INPUTS, "RECON_MATRIX_w3w6_f92aaea3.csv"))
    recon = {}
    recon.update(w2["games"])
    overlap = set(w2["games"]) & set(w3["games"])
    recon.update(w3["games"])

    extra_w2 = sorted(set(w2["games"]) - set(score_ids))
    extra_w3 = sorted(set(w3["games"]) - set(score_ids))
    missing_recon = sorted(set(score_ids) - set(recon))

    rows = []
    for r in score["rows"]:
        gid = r["game_id"]
        rec = recon.get(gid, {})
        wl_h, hw, hl, ht, hd = parse_record(r.get("record_asof_home"))
        wl_a, aw, al, at, ad = parse_record(r.get("record_asof_away"))
        off_h = fnum(rec.get("offense_index_home"))
        off_a = fnum(rec.get("offense_index_away"))
        def_h = fnum(rec.get("defense_index_home"))
        def_a = fnum(rec.get("defense_index_away"))
        epa_off_h = fnum(rec.get("home_off_epa_5g"))
        epa_off_a = fnum(rec.get("away_off_epa_5g"))
        epa_def_h = fnum(rec.get("home_def_epa_allowed_5g"))
        epa_def_a = fnum(rec.get("away_def_epa_allowed_5g"))
        suc_off_h = fnum(rec.get("home_success_offense_5g"))
        suc_off_a = fnum(rec.get("away_success_offense_5g"))
        suc_def_h = fnum(rec.get("home_success_defense_allowed_5g"))
        suc_def_a = fnum(rec.get("away_success_defense_allowed_5g"))
        m_off = fnum(rec.get("matchup_diff_off_epa_5g"))
        m_suc = fnum(rec.get("matchup_diff_success_rate_5g"))

        wl_index_off = sub(off_h, off_a)
        # freeze literal: defense_index_away - defense_index_home (home-favorable)
        wl_index_def = sub(def_a, def_h)
        epa_off = sub(epa_off_h, epa_off_a)
        epa_def = sub(epa_def_a, epa_def_h)
        suc_off = sub(suc_off_h, suc_off_a)
        suc_def = sub(suc_def_a, suc_def_h)

        margin = fnum(r.get("realized_margin"))
        if margin is None:
            hs, aws = fnum(r.get("home_score")), fnum(r.get("away_score"))
            margin = sub(hs, aws)
        if margin is None:
            realized_su = "MISSING"
        elif margin > 0:
            realized_su = 1
        elif margin < 0:
            realized_su = 0
        else:
            realized_su = "TIE"

        row = {
            "game_id": gid,
            "matchup_week": int(r["matchup_week"]),
            "home_team": r.get("home_team"),
            "away_team": r.get("away_team"),
            "record_asof_home": r.get("record_asof_home"),
            "record_asof_away": r.get("record_asof_away"),
            "home_wins": hw,
            "home_losses": hl,
            "home_ties_ignored": ht,
            "home_wl_denom": hd,
            "away_wins": aw,
            "away_losses": al,
            "away_ties_ignored": at,
            "away_wl_denom": ad,
            "home_score": fnum(r.get("home_score")),
            "away_score": fnum(r.get("away_score")),
            "realized_margin": margin,
            "realized_su": realized_su,
            "forecast_margin": fnum(r.get("forecast_margin")),
            "offense_index_home": off_h,
            "offense_index_away": off_a,
            "defense_index_home": def_h,
            "defense_index_away": def_a,
            "home_off_epa_5g": epa_off_h,
            "away_off_epa_5g": epa_off_a,
            "home_def_epa_allowed_5g": epa_def_h,
            "away_def_epa_allowed_5g": epa_def_a,
            "home_success_offense_5g": suc_off_h,
            "away_success_offense_5g": suc_off_a,
            "home_success_defense_allowed_5g": suc_def_h,
            "away_success_defense_allowed_5g": suc_def_a,
            "wl_home_wpct": wl_h,
            "wl_away_wpct": wl_a,
            "wl_diff": sub(wl_h, wl_a),
            "wl_index_off_diff": wl_index_off,
            "wl_index_def_diff": wl_index_def,
            "wl_index_net": add(wl_index_off, wl_index_def),
            "epa_off_diff": epa_off,
            "epa_def_diff": epa_def,
            "epa_net_diff": add(epa_off, epa_def),
            "success_off_diff": suc_off,
            "success_def_diff": suc_def,
            "success_net_diff": add(suc_off, suc_def),
            "matchup_diff_off_epa_5g": m_off,
            "matchup_diff_success_rate_5g": m_suc,
            "epa_success_label": "RETRO_FIT / DEV_RESEARCH only (A1)",
        }
        miss = [k for k in SIGNAL_NAMES if row.get(k) is None]
        row["n_signals_missing"] = len(miss)
        row["signals_missing"] = ";".join(miss) if miss else ""
        rows.append(row)

    rows.sort(key=lambda r: (r["matchup_week"], r["game_id"]))
    if [r["game_id"] for r in rows] and len(rows) != 70:
        print("STOP: joined rows != 70", file=sys.stderr)
        return 2

    games_any_missing = [r["game_id"] for r in rows if r["n_signals_missing"] > 0]
    n_ties = sum(1 for r in rows if r["realized_su"] == "TIE")

    signal_results = {sig: analyze_signal(rows, sig) for sig in SIGNAL_NAMES}
    audit = week_subset_audit(signal_results, rows)
    control = control_if_block(rows)

    # SIGNAL_TABLE
    csv_fields = [
        "game_id",
        "matchup_week",
        "home_team",
        "away_team",
        "record_asof_home",
        "record_asof_away",
        "home_score",
        "away_score",
        "realized_margin",
        "realized_su",
        "forecast_margin",
        *SIGNAL_NAMES,
        "n_signals_missing",
        "signals_missing",
        "epa_success_label",
    ]
    csv_path = os.path.join(HERE, "SIGNAL_TABLE.csv")
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=csv_fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            out = {k: r.get(k) for k in csv_fields}
            w.writerow(out)
    table_json = [{k: r.get(k) for k in csv_fields} | {
        "home_wins": r["home_wins"],
        "home_losses": r["home_losses"],
        "home_wl_denom": r["home_wl_denom"],
        "away_wins": r["away_wins"],
        "away_losses": r["away_losses"],
        "away_wl_denom": r["away_wl_denom"],
        "offense_index_home": r["offense_index_home"],
        "offense_index_away": r["offense_index_away"],
        "defense_index_home": r["defense_index_home"],
        "defense_index_away": r["defense_index_away"],
    } for r in rows]
    json_path = os.path.join(HERE, "SIGNAL_TABLE.json")
    with open(json_path, "w") as f:
        json.dump(table_json, f, indent=2, allow_nan=False)
        f.write("\n")

    selection_hash = sha256_text("\n".join(sorted(score_ids)) + "\n")

    results = {
        "artifact": "nfl-lane-s-discrimination-t4915u",
        "label": "DEV_RESEARCH / RETRO_FIT exploratory",
        "cert": 0,
        "nfl": "NO-GO",
        "publish": False,
        "betting": False,
        "phase": "Phase 1 Lane S ONLY",
        "ticket": "t4915u",
        "exec_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "one_exec": True,
        "sample_n": 70,
        "sample_game_ids_hash": selection_hash,
        "sample_game_ids_hash_match_manifest": selection_hash == manifest.get("selection_hash"),
        "n_ties_realized_margin": n_ties,
        "pins": {
            "control_tip": "02197f58",
            "control_tip_note": "packet tip; DO NOT CHANGE — not rewritten this EXEC",
            "score_results_sha8": "2b9f302e",
            "score_results_sha256": pins["SCORE_RESULTS.json"]["sha256"],
            "sample_manifest_sha8": "861a6264",
            "if_tip_from_score_results": score.get("if_tip"),
            "if_tip_freeze": "6ca03716",
            "w2_tip": "440314e4",
            "w3w6_tip": "f92aaea3",
            "contract": "b41f4b43",
            "exec_freeze_sha256": pins["EXEC_FREEZE_t4915u_LANE_S_ANALYSIS_PLAN.md"]["sha256"],
            "owner_accept_sha256": pins["OWNER_ACCEPT_t4915u_PHASE1_LANE_S.md"]["sha256"],
            "proposal_sha8": "44e3451f",
            "bootstrap_B": BOOT_B,
            "bootstrap_seed": BOOT_SEED,
        },
        "input_hashes": pins,
        "recon_join": {
            "w2_games_in_matrix": len(w2["games"]),
            "w3w6_games_in_matrix": len(w3["games"]),
            "w2_extra_not_in_sample": extra_w2,
            "w3w6_extra_not_in_sample": extra_w3,
            "sample_missing_from_recon": missing_recon,
            "w2_w3_overlap": sorted(overlap),
            "w2_rows": w2["n_rows"],
            "w3w6_rows": w3["n_rows"],
            "w3w6_missing_status_rows": w3["n_missing_status"],
            "repo_tip_crosscheck": "git objects 440314e4 / f92aaea3 not present in this checkout; attached box copies used; shas match freeze 708513db / cdff0115",
        },
        "missing": {
            "rule": "MISSING if denom 0 or field absent/non-finite/non-DERIVED_PREGAME; no impute",
            "games_with_any_signal_missing": games_any_missing,
            "n_games_with_any_signal_missing": len(games_any_missing),
            "n_complete_per_signal": {sig: signal_results[sig]["n_complete"] for sig in SIGNAL_NAMES},
        },
        "control_if": control,
        "signals": signal_results,
        "week_subset_audit_summary": {
            "any_signal_concentrated": audit["any_signal_concentrated"],
            "flagged_signals": audit["flagged_signals"],
            "week_counts": audit["week_counts"],
        },
        "comparisons_frozen_all_reported": True,
        "weight_cutoff_feature_search": False,
        "forecast_regenerated": False,
        "engine_ablation": False,
        "access_2024_25": False,
    }

    with open(os.path.join(HERE, "DISCRIMINATION_RESULTS.json"), "w") as f:
        json.dump(results, f, indent=2, allow_nan=False)
        f.write("\n")

    with open(os.path.join(HERE, "WEEK_SUBSET_AUDIT.json"), "w") as f:
        json.dump(audit, f, indent=2, allow_nan=False)
        f.write("\n")

    # compact stdout for the writer
    print("LANE_S_EXEC_OK n=70 ties=%s any_missing=%s" % (n_ties, games_any_missing))
    print("CONTROL_IF spearman", (control["spearman_vs_realized_margin"] or {}).get("estimate"),
          "CI", (control["spearman_vs_realized_margin"] or {}).get("ci_low"),
          (control["spearman_vs_realized_margin"] or {}).get("ci_high"))
    print("CONTROL_IF ols_slope", (control["ols_realized_margin_on_forecast_margin"] or {}).get("slope"),
          "CI", (control["ols_realized_margin_on_forecast_margin"] or {}).get("slope_ci_low"),
          (control["ols_realized_margin_on_forecast_margin"] or {}).get("slope_ci_high"))
    for sig in SIGNAL_NAMES:
        sp = signal_results[sig]["spearman_vs_realized_margin"] or {}
        su = signal_results[sig]["su_when_signal_sign"]
        ols = signal_results[sig]["ols_realized_margin_on_signal"] or {}
        tert = signal_results[sig]["tertiles"]["tertiles"]
        tmeans = [round(t["mean_realized_margin"], 3) if t["mean_realized_margin"] is not None else None for t in tert]
        print(
            f"{sig:32s} n={signal_results[sig]['n_complete']:2d}  "
            f"rho={sp.get('estimate')}  CI=[{sp.get('ci_low')},{sp.get('ci_high')}] cross0={sp.get('ci_crosses_0')}  "
            f"SU+={ (su['signal_gt_0'].get('rate')) } n+={su['signal_gt_0']['n']}  "
            f"SU-={ (su['signal_lt_0'].get('rate')) } n-={su['signal_lt_0']['n']}  "
            f"ols={ols.get('slope')} cross0={ols.get('slope_ci_crosses_0')}  "
            f"Tmeans={tmeans}  "
            f"IF_rho={(signal_results[sig]['spearman_vs_forecast_margin'] or {}).get('estimate')}"
        )
    print("CONCENTRATION", audit["any_signal_concentrated"], audit["flagged_signals"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
