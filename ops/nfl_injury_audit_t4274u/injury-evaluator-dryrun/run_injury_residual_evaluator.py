#!/usr/bin/env python3
"""Injury residual evaluator — dry-run only (Ryan t4315u / t4317u / t4320u).

Scores baseline vs injury-adjusted end to end. No stubs.
Allowed data: sealed le2023 export + OOS rows with season <= 2023, or synthetics.
2024 / 2025 / 2026 are refused. No CLEAR token is read or written.
Holdout is STOPPED. This run is not a holdout opening.

Close proxy label: comparative research, not certified CLV.

HEAD pin: frozen fit C-1 `8e2a15ac`. An ops-only descendant that touches nothing
outside this evaluator directory is allowed so the readiness package can be
committed without retuning the fit.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

REQUIRED_HEAD = "8e2a15ac581277ecda71ea745c3b3477185d733b"
REQUIRED_EXPORT = "d87e6129c451bbdc51d49eb7745a31ebb64ab6108ac58d8f8c4948dcc13e18e8"
REQUIRED_SPEC = "a156459b545e3b7d6a483f1db34cda7a4d32fc3afc70ed499b3adc726b1b6881"
REQUIRED_FIT_OBJECT = "6a5490dbc09b160f4509ea65b3b2257f9703f9d43635092d0da94c1577abb657"
PINNED_SEED = 2708041115  # int("a156459b", 16)
N_BOOT = 10000
HOLM_ALPHA = 0.05
UNSHRUNK_SIGMA = 9.8
K4_LOGLOSS_UPPER = 0.002
K4_BRIER_UPPER = 0.0005
K4_SLOPE_LO = 0.9
K4_SLOPE_HI = 1.1
I2_MIN_NONZERO = 500
FORBIDDEN = {2024, 2025, 2026}
CLOSE_LABEL = "comparative research, not certified CLV"
ALLOWED_HEAD_PREFIXES = ("ops/nfl_injury_audit_t4274u/injury-evaluator-dryrun/",)
KNOWN_ANSWERS = {
    "synthetic_inconclusive": "INCONCLUSIVE",
    "synthetic_fail": "NO CLAIM",
    "synthetic_pass": "VALUE PROVEN",
}

SPEC_STORE = Path("/cursor/stores/self/imv-inputs/IMV_SPEC_NFL_INJURY_ADJUSTMENT_TESTS_v1.txt")
EXPORT = Path("/opt/cursor/artifacts/injury-fit-le2023/sealed_injury_export.json")
FIT_OBJECT = Path("/opt/cursor/artifacts/injury-fit-le2023/fit_object.json")
OOS = Path(
    "/workspace/data/ops/nfl-reopening-packet-20260916/historical-oos/historical_oos_games.csv"
)

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
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def alias(team: str) -> str:
    t = str(team or "").strip().upper()
    return {"LAR": "LA", "STL": "LA", "SD": "LAC", "OAK": "LV", "WSH": "WAS", "JAC": "JAX"}.get(t, t)


def phi(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def clip_p(p: float) -> float:
    return min(1.0 - 1e-15, max(1e-15, p))


def p_home(predicted_margin: float, sigma: float = UNSHRUNK_SIGMA) -> float:
    if sigma <= 0:
        die("unshrunk σ must be > 0")
    return clip_p(phi(predicted_margin / (math.sqrt(2.0) * sigma)))


def p_cover(predicted_margin: float, close_spread: float, sigma: float = UNSHRUNK_SIGMA) -> float:
    return clip_p(phi((predicted_margin + close_spread) / (math.sqrt(2.0) * sigma)))


def p_over(predicted_total: float, close_total: float, sigma: float = UNSHRUNK_SIGMA) -> float:
    return clip_p(phi((predicted_total - close_total) / (math.sqrt(2.0) * sigma)))


def log_loss(y: float, p: float) -> float:
    p = clip_p(p)
    return -(y * math.log(p) + (1.0 - y) * math.log(1.0 - p))


def brier(y: float, p: float) -> float:
    return (p - y) ** 2


def ols_slope(xs: Sequence[float], ys: Sequence[float]) -> Optional[float]:
    n = len(xs)
    if n < 2:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    den = sum((x - mx) ** 2 for x in xs)
    if den == 0:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den


def reliability(ps: Sequence[float], ys: Sequence[float], bins: int = 10) -> List[Dict[str, Any]]:
    out = []
    for i in range(bins):
        lo, hi = i / bins, (i + 1) / bins
        idx = [
            j
            for j, p in enumerate(ps)
            if (p >= lo and p < hi) or (i == bins - 1 and abs(p - hi) < 1e-15)
        ]
        if not idx:
            out.append(
                {
                    "bin": i,
                    "lo": lo,
                    "hi": hi,
                    "n": 0,
                    "mean_p": None,
                    "mean_y": None,
                    "nan_reason": "bin empty; not a stub",
                }
            )
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
    if not xs:
        return None
    return sum(xs) / len(xs)


def clv_points(close: float, actual: float, edge: float) -> Optional[float]:
    if edge == 0:
        return None
    return (close - actual) * (1.0 if edge > 0 else -1.0)


def holm_bonferroni(pvalues: Sequence[Tuple[str, float]], alpha: float = HOLM_ALPHA) -> List[Dict[str, Any]]:
    if len(pvalues) != 9:
        die(f"I-3 requires 9 tests; got {len(pvalues)}")
    if {n for n, _ in pvalues} != set(HOLM_NINE):
        die("I-3 test ids must be the 3x3 family")
    ranked = sorted(pvalues, key=lambda kv: kv[1])
    out = []
    keep = True
    m = 9
    for i, (name, p) in enumerate(ranked):
        thresh = alpha / (m - i)
        sig = bool(keep and p <= thresh)
        if not sig:
            keep = False
        out.append(
            {
                "test_id": name,
                "p": p,
                "holm_rank": i + 1,
                "holm_threshold": thresh,
                "significant": sig,
            }
        )
    return out


def i2_status(n_nonzero: int, n_full_seasons: int) -> str:
    if n_nonzero < I2_MIN_NONZERO or n_full_seasons < 2:
        return "INCONCLUSIVE"
    return "MET"


def i4_decision(i2: str, primary_sig: bool, ci_excludes_0: bool, k4_pass: bool) -> str:
    if i2 != "MET":
        return "INCONCLUSIVE"
    if primary_sig and ci_excludes_0 and k4_pass:
        return "VALUE PROVEN"
    return "NO CLAIM"


def week_block_bootstrap(rows: Sequence[Dict[str, Any]], stat_fn, seed: int = PINNED_SEED) -> Dict[str, Any]:
    if seed != PINNED_SEED:
        die(f"K-3 seed {seed} != PINNED_SEED {PINNED_SEED}")
    if not rows:
        return {
            "n_blocks": 0,
            "obs": None,
            "ci_lo": None,
            "ci_hi": None,
            "p": 1.0,
            "excludes_0": False,
            "seed": seed,
            "n_boot": N_BOOT,
            "nan_reason": "no paired rows; statistic undefined",
        }
    by_week: Dict[Tuple[int, int], List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_week[(int(row["season"]), int(row["week"]))].append(row)
    keys = list(by_week.keys())
    obs = stat_fn(list(rows))
    if obs is None:
        return {
            "n_blocks": len(keys),
            "obs": None,
            "ci_lo": None,
            "ci_hi": None,
            "p": 1.0,
            "excludes_0": False,
            "seed": seed,
            "n_boot": N_BOOT,
            "nan_reason": "statistic undefined on this cohort",
        }
    rng = random.Random(seed)
    boot = []
    for _ in range(N_BOOT):
        drawn: List[Dict[str, Any]] = []
        for __ in range(len(keys)):
            drawn.extend(by_week[keys[rng.randrange(len(keys))]])
        val = stat_fn(drawn)
        boot.append(0.0 if val is None else val)
    lo = percentile(boot, 0.025)
    hi = percentile(boot, 0.975)
    n_le = sum(1 for x in boot if x <= 0.0)
    n_ge = sum(1 for x in boot if x >= 0.0)
    p = min(1.0, 2.0 * min(n_le, n_ge) / float(N_BOOT))
    return {
        "n_blocks": len(keys),
        "obs": obs,
        "ci_lo": lo,
        "ci_hi": hi,
        "p": p,
        "excludes_0": (lo > 0.0) or (hi < 0.0),
        "seed": seed,
        "n_boot": N_BOOT,
        "nan_reason": None,
    }


def current_head() -> str:
    return os.popen("git -C /workspace rev-parse HEAD").read().strip()


def assert_head(head: str) -> None:
    """Frozen-fit HEAD, or an ops-only descendant of it (readiness package commits)."""
    if head == REQUIRED_HEAD:
        return
    ancestor = os.system(
        f"git -C /workspace merge-base --is-ancestor {REQUIRED_HEAD} {head} >/dev/null 2>&1"
    )
    if ancestor != 0:
        die(f"HEAD {head!r} is not frozen fit {REQUIRED_HEAD} or a descendant")
    changed = [
        p
        for p in os.popen(f"git -C /workspace diff --name-only {REQUIRED_HEAD} {head}").read().split()
        if p
    ]
    bad = [p for p in changed if not p.startswith(ALLOWED_HEAD_PREFIXES)]
    if bad:
        die(f"HEAD {head} vs {REQUIRED_HEAD} touches non-evaluator paths: {bad[:20]}")
    log(f"HEAD {head} is ops-only descendant of frozen fit {REQUIRED_HEAD}")


def assert_env() -> str:
    leaked = sorted(k for k in os.environ if k.startswith("NFL_TOTALS_"))
    if leaked:
        die(f"NFL_TOTALS_* must be unset; found {leaked}")
    head = current_head()
    assert_head(head)
    if sha256_file(SPEC_STORE) != REQUIRED_SPEC:
        die("spec sha mismatch")
    if sha256_file(EXPORT) != REQUIRED_EXPORT:
        die("export sha mismatch; not the sealed le2023 file")
    if sha256_file(FIT_OBJECT) != REQUIRED_FIT_OBJECT:
        die("fit_object sha mismatch")
    return head


def load_oos_le2023() -> Dict[Tuple[int, int, str, str], Dict[str, Any]]:
    """Read OOS but never keep 2024+ rows. Filter before storing any field."""
    out: Dict[Tuple[int, int, str, str], Dict[str, Any]] = {}
    n_skipped_holdout = 0
    with OOS.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            try:
                season = int(row["season"])
            except (TypeError, ValueError):
                continue
            if season in FORBIDDEN:
                n_skipped_holdout += 1
                continue
            if season > 2023:
                n_skipped_holdout += 1
                continue
            home = alias(row.get("home") or "")
            away = alias(row.get("away") or "")
            try:
                rec: Dict[str, Any] = {
                    "season": season,
                    "week": int(row["week"]),
                    "home": home,
                    "away": away,
                    "actual_margin": float(row["home_score"]) - float(row["away_score"]),
                    "actual_total": float(row["home_score"]) + float(row["away_score"]),
                    "baseline_margin": -float(row["record_spread"]),
                    "baseline_total": float(row["record_total"]),
                    "close_spread_home": float(row["market_spread_home"]),
                    "close_total": float(row["market_total"]),
                    "close_label": CLOSE_LABEL,
                }
            except (TypeError, ValueError):
                continue
            out[(season, int(row["week"]), home, away)] = rec
    log(f"oos_le2023 n={len(out)} skipped_forbidden_or_future={n_skipped_holdout}")
    if n_skipped_holdout == 0:
        log("note: OOS file contained no 2024+ rows to skip (filter still applied)")
    return out


def load_export_games() -> List[Dict[str, Any]]:
    doc = json.loads(EXPORT.read_text(encoding="utf-8"))
    years = set(int(y) for y in doc.get("fit_years") or [])
    if years & FORBIDDEN:
        die("export fit_years intersects holdout; refuse")
    games = []
    for g in doc.get("games") or []:
        season = int(g["season"])
        if season in FORBIDDEN or season > 2023:
            die(f"export contains holdout season {season}")
        gid = str(g.get("game_id") or "")
        parts = gid.split("_")
        away = home = ""
        if len(parts) >= 4:
            away = alias(parts[2])
            home = alias("_".join(parts[3:]) if len(parts) > 4 else parts[3])
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
    log(f"export games n={len(games)}")
    return games


def full_seasons(weeks_by_season: Dict[int, Iterable[int]]) -> Tuple[int, Dict[str, Any]]:
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


def score_rows(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Full paired scoring. rows already have baseline, close, actual, deltas."""
    n_edge0_base = 0
    n_edge0_adj = 0
    paired: List[Dict[str, Any]] = []
    for r in rows:
        bm, bt = r.get("baseline_margin"), r.get("baseline_total")
        dm, dt = r.get("delta_margin"), r.get("delta_total")
        cs, ct = r.get("close_spread_home"), r.get("close_total")
        am, at = r.get("actual_margin"), r.get("actual_total")
        if None in (bm, bt, dm, dt, cs, ct, am, at):
            continue
        bm, bt, dm, dt = float(bm), float(bt), float(dm), float(dt)
        cs, ct, am, at = float(cs), float(ct), float(am), float(at)
        pred_m_b, pred_m_a = bm, bm + dm
        pred_t_b, pred_t_a = bt, bt + dt
        spread_b, spread_a = -pred_m_b, -pred_m_a
        actual_spread = -am
        edge_b = spread_b - cs
        edge_a = spread_a - cs
        if edge_b == 0:
            n_edge0_base += 1
        if edge_a == 0:
            n_edge0_adj += 1
        clv_b = clv_points(cs, actual_spread, edge_b)
        clv_a = clv_points(cs, actual_spread, edge_a)
        if clv_b is None or clv_a is None:
            continue
        p_b = p_home(pred_m_b)
        p_a = p_home(pred_m_a)
        if abs(p_home(pred_m_b) - p_b) > 1e-6 or abs(p_home(pred_m_a) - p_a) > 1e-6:
            die("T-PHI recompute > 1e-6")
        y_home = 1.0 if am > 0 else 0.0
        y_cover = 1.0 if (am + cs) > 0 else 0.0
        y_over = 1.0 if at > ct else 0.0
        p_cov_b, p_cov_a = p_cover(pred_m_b, cs), p_cover(pred_m_a, cs)
        p_ov_b, p_ov_a = p_over(pred_t_b, ct), p_over(pred_t_a, ct)
        p_close = p_home(-cs)
        edge_tb, edge_ta = pred_t_b - ct, pred_t_a - ct
        tclv_b = clv_points(ct, at, edge_tb)
        tclv_a = clv_points(ct, at, edge_ta)
        ml_b = None if (p_b - p_close) == 0 else (p_close - y_home) * (1.0 if (p_b - p_close) > 0 else -1.0)
        ml_a = None if (p_a - p_close) == 0 else (p_close - y_home) * (1.0 if (p_a - p_close) > 0 else -1.0)
        ats_b = None if edge_b == 0 else (1.0 if ((edge_b > 0 and y_cover == 1) or (edge_b < 0 and y_cover == 0)) else 0.0)
        ats_a = None if edge_a == 0 else (1.0 if ((edge_a > 0 and y_cover == 1) or (edge_a < 0 and y_cover == 0)) else 0.0)
        paired.append(
            {
                "season": r["season"],
                "week": r["week"],
                "spread_clv_delta": clv_a - clv_b,
                "spread_ats_base": ats_b,
                "spread_ats_adj": ats_a,
                "spread_ll_base": log_loss(y_cover, p_cov_b),
                "spread_ll_adj": log_loss(y_cover, p_cov_a),
                "total_clv_delta": None if tclv_a is None or tclv_b is None else tclv_a - tclv_b,
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
                "sigma_base": UNSHRUNK_SIGMA,
                "sigma_adj": UNSHRUNK_SIGMA,
            }
        )
    if any(r["sigma_adj"] < r["sigma_base"] for r in paired):
        die("T-SIGMA: σ_adj < σ_base")

    def col(name: str) -> List[float]:
        return [float(r[name]) for r in paired if r.get(name) is not None]

    def dmean(a: str, b: str) -> Optional[float]:
        xs = [float(r[a]) - float(r[b]) for r in paired if r.get(a) is not None and r.get(b) is not None]
        return mean(xs)

    stats = {
        "n_paired": len(paired),
        "n_edge0_base": n_edge0_base,
        "n_edge0_adj": n_edge0_adj,
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
        "slope_adj": ols_slope(col("p_adj"), col("y_home")),
        "reliability_spread": reliability(col("p_cov_adj"), col("y_cover")),
        "reliability_total": reliability(col("p_over_adj"), col("y_over")),
        "reliability_ml": reliability(col("p_adj"), col("y_home")),
        "rows": paired,
    }
    stats["metric_undefined"] = {
        k: (
            None
            if stats[k] is not None
            else "no row with both arms defined for this metric (usually edge=0 on that market); not a stub"
        )
        for k in HOLM_NINE
    }
    return stats


def test_stat(key: str):
    def _fn(rows: Sequence[Dict[str, Any]]) -> Optional[float]:
        if key == "spread_clv_delta":
            xs = [r["spread_clv_delta"] for r in rows]
        elif key == "spread_ats_delta":
            xs = [
                r["spread_ats_adj"] - r["spread_ats_base"]
                for r in rows
                if r.get("spread_ats_adj") is not None and r.get("spread_ats_base") is not None
            ]
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
            die("unknown test " + key)
        return mean(xs)

    return _fn


def evaluate(name: str, universe: List[Dict[str, Any]], notes: str) -> Dict[str, Any]:
    log(f"evaluate {name} n_universe={len(universe)}")
    weeks: Dict[int, set] = defaultdict(set)
    n_nonzero = 0
    n_nonzero_season: Dict[int, int] = Counter()
    identical: List[Dict[str, Any]] = []
    missing = {
        "n_universe": len(universe),
        "n_incomplete_residual": 0,
        "n_missing_close": 0,
        "n_missing_actual": 0,
        "n_missing_baseline": 0,
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
        identical.append(row)

    n_full, week_detail = full_seasons(weeks)
    i2 = i2_status(n_nonzero, n_full)
    stats = score_rows(identical)
    paired = stats["rows"]
    boot = {k: week_block_bootstrap(paired, test_stat(k)) for k in HOLM_NINE}
    holm = holm_bonferroni([(k, boot[k]["p"]) for k in HOLM_NINE])
    holm_by = {h["test_id"]: h for h in holm}
    ll_boot = week_block_bootstrap(paired, lambda rs: mean([r["ml_ll_adj"] - r["ml_ll_base"] for r in rs]))
    br_boot = week_block_bootstrap(paired, lambda rs: mean([r["brier_adj"] - r["brier_base"] for r in rs]))
    # K-4 calibration slope is the reliability-diagram slope (K-2 10 bins), not raw Bernoulli OLS.
    rel = stats["reliability_ml"]
    slope = ols_slope(
        [b["mean_p"] for b in rel if b["n"] > 0 and b["mean_p"] is not None],
        [b["mean_y"] for b in rel if b["n"] > 0 and b["mean_y"] is not None],
    )
    stats["slope_adj"] = slope
    stats["metric_undefined"]["slope_adj"] = (
        None if slope is not None else "need >=2 occupied reliability bins; not a stub"
    )
    k4_notes = []
    if not paired:
        k4_pass = False
        k4_notes.append("no paired rows; K-4 cannot pass")
    else:
        k4_pass = (
            ll_boot.get("ci_hi") is not None
            and br_boot.get("ci_hi") is not None
            and ll_boot["ci_hi"] <= K4_LOGLOSS_UPPER
            and br_boot["ci_hi"] <= K4_BRIER_UPPER
            and slope is not None
            and K4_SLOPE_LO <= slope <= K4_SLOPE_HI
        )
        if ll_boot.get("ci_hi") is None or ll_boot["ci_hi"] > K4_LOGLOSS_UPPER:
            k4_notes.append(f"logloss_CI_hi {ll_boot.get('ci_hi')} > {K4_LOGLOSS_UPPER}")
        if br_boot.get("ci_hi") is None or br_boot["ci_hi"] > K4_BRIER_UPPER:
            k4_notes.append(f"brier_CI_hi {br_boot.get('ci_hi')} > {K4_BRIER_UPPER}")
        if slope is None:
            k4_notes.append("slope undefined (need >=2 occupied reliability bins); K-4 fail")
        elif not (K4_SLOPE_LO <= slope <= K4_SLOPE_HI):
            k4_notes.append(f"slope {slope} outside [0.9, 1.1]")
    decision = i4_decision(i2, bool(holm_by[PRIMARY]["significant"]), bool(boot[PRIMARY]["excludes_0"]), k4_pass)
    missing["n_missing_close_by_season"] = dict(missing["n_missing_close_by_season"])
    missing["n_missing_actual_by_season"] = dict(missing["n_missing_actual_by_season"])
    missing["n_missing_baseline_by_season"] = dict(missing["n_missing_baseline_by_season"])
    missing["n_incomplete_by_season"] = dict(missing["n_incomplete_by_season"])
    missing["n_universe_by_season"] = dict(missing["n_universe_by_season"])
    missing["n_identical_cohort"] = len(identical)
    missing["n_paired_both_clv"] = stats["n_paired"]
    missing["n_edge0_base"] = stats["n_edge0_base"]
    missing["n_edge0_adj"] = stats["n_edge0_adj"]
    return {
        "name": name,
        "notes": notes,
        "close_label": CLOSE_LABEL,
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
        "metrics": {k: stats[k] for k in list(HOLM_NINE) + [
            "mean_logloss_base",
            "mean_logloss_adj",
            "mean_brier_base",
            "mean_brier_adj",
            "logloss_delta_adj_minus_base",
            "brier_delta_adj_minus_base",
            "slope_adj",
        ]},
        "metric_undefined": stats["metric_undefined"],
        "reliability": {
            "spread": stats["reliability_spread"],
            "total": stats["reliability_total"],
            "ml": stats["reliability_ml"],
        },
        "holm": holm,
        "bootstrap": boot,
        "k4": {
            "logloss_delta_ci_hi": ll_boot.get("ci_hi"),
            "brier_delta_ci_hi": br_boot.get("ci_hi"),
            "slope_adj": slope,
            "thresholds": {
                "logloss_upper": K4_LOGLOSS_UPPER,
                "brier_upper": K4_BRIER_UPPER,
                "slope": [K4_SLOPE_LO, K4_SLOPE_HI],
            },
            "pass": k4_pass,
            "notes": k4_notes,
        },
        "i4": {
            "primary_significant_after_holm": bool(holm_by[PRIMARY]["significant"]),
            "primary_ci_excludes_0": bool(boot[PRIMARY]["excludes_0"]),
            "k4_pass": k4_pass,
            "decision": decision,
            "product_claim": False,
            "i5": "null results reported as null; no product claim",
        },
        "expected_outcome_note": notes,
    }


def join_le2023() -> List[Dict[str, Any]]:
    oos = load_oos_le2023()
    games = load_export_games()
    universe = []
    for g in games:
        key = (g["season"], g["week"], g["home"], g["away"])
        rec = oos.get(key)
        row = {
            "season": g["season"],
            "week": g["week"],
            "home": g["home"],
            "away": g["away"],
            "residual_complete": bool(g["complete"] and g["delta_margin"] is not None and g["delta_total"] is not None),
            "delta_margin": g["delta_margin"],
            "delta_total": g["delta_total"],
            "baseline_margin": None if rec is None else rec["baseline_margin"],
            "baseline_total": None if rec is None else rec["baseline_total"],
            "close_spread_home": None if rec is None else rec["close_spread_home"],
            "close_total": None if rec is None else rec["close_total"],
            "actual_margin": None if rec is None else rec["actual_margin"],
            "actual_total": None if rec is None else rec["actual_total"],
            "close_label": CLOSE_LABEL,
            "joined": rec is not None,
        }
        universe.append(row)
    log(f"le2023 joined={sum(1 for r in universe if r['joined'])} export={len(universe)}")
    return universe


def _erfinv(x: float) -> float:
    a = 0.147
    sgn = 1.0 if x >= 0 else -1.0
    ln = math.log(max(1e-15, 1.0 - x * x))
    t = 2.0 / (math.pi * a) + ln / 2.0
    return sgn * math.sqrt(max(0.0, math.sqrt(t * t - ln / a) - t))


def pred_from_p(p: float) -> float:
    p = min(1.0 - 1e-6, max(1e-6, p))
    return 2.0 * UNSHRUNK_SIGMA * _erfinv(2.0 * p - 1.0)


def synth_game(season: int, week: int, i: int, kind: str, y_home: int, p_adj: float) -> Dict[str, Any]:
    """Known-answer fixtures. kind in {pass, fail, inconclusive}."""
    close_s, close_t = -3.0, 45.0
    if kind == "inconclusive":
        actual_m, actual_t = 3.0, 44.0
        base_m, base_t = 1.0, 45.0
        dm, dt = (0.4, 0.3) if i % 2 == 0 else (0.0, 0.0)
    else:
        pred_a = pred_from_p(p_adj)
        if kind == "pass":
            # Adj closer to the outcome than base; some games straddle close for +ΔCLV.
            pred_b = pred_a - 2.0 if y_home == 1 else pred_a + 2.0
            actual_m = 2.5 if y_home == 1 else -6.0
            actual_t = 47.0 if y_home == 1 else 42.0
            base_t = 44.0
            dt = 2.0 if y_home == 1 else -3.0
        else:
            # FAIL: adj farther from the outcome (worse logloss / Brier).
            pred_b = pred_a + 2.0 if y_home == 1 else pred_a - 2.0
            actual_m = 2.5 if y_home == 1 else -6.0
            actual_t = 47.0 if y_home == 1 else 42.0
            base_t = 45.5
            dt = -4.0 if y_home == 1 else 4.0
        base_m = pred_b
        dm = pred_a - pred_b
    return {
        "season": season,
        "week": week,
        "home": "AAA",
        "away": "BBB",
        "residual_complete": True,
        "delta_margin": dm,
        "delta_total": dt,
        "baseline_margin": base_m,
        "baseline_total": base_t,
        "close_spread_home": close_s,
        "close_total": close_t,
        "actual_margin": actual_m,
        "actual_total": actual_t,
        "close_label": CLOSE_LABEL,
        "joined": True,
    }


def make_synthetic(kind: str) -> List[Dict[str, Any]]:
    rows = []
    if kind == "inconclusive":
        for week in range(1, 5):
            for i in range(10):
                rows.append(synth_game(2018, week, i, "inconclusive", 1, 0.6))
        return rows
    # 2 full 17-week seasons, 18 games/week = 612.
    # y-rate is assigned per reliability bin so mean_y = target p (K-4 slope ~ 1).
    seasons = (2018, 2019)
    slots: List[Tuple[int, int, int, float, int]] = []
    for season in seasons:
        for week in range(1, 18):
            for i in range(18):
                bin_i = i % 10
                p_adj = (bin_i + 0.5) / 10.0
                slots.append((season, week, i, p_adj, bin_i))
    by_bin: Dict[int, List[int]] = defaultdict(list)
    for idx, slot in enumerate(slots):
        by_bin[slot[4]].append(idx)
    y_of = [0] * len(slots)
    for bin_i, idxs in by_bin.items():
        p = (bin_i + 0.5) / 10.0
        n_win = int(round(len(idxs) * p))
        for j, idx in enumerate(idxs):
            y_of[idx] = 1 if j < n_win else 0
    for (season, week, i, p_adj, _bin_i), y_home in zip(slots, y_of):
        rows.append(synth_game(season, week, i, kind, y_home, p_adj))
    return rows


def write_report(path: Path, results: List[Dict[str, Any]], cmd: str, head: str) -> None:
    lines = [
        "# Evaluator dry-run report",
        "",
        f"**Generated:** deterministic (seed={PINNED_SEED}; no wall-clock)",
        f"**Frozen-fit HEAD:** `{REQUIRED_HEAD}`",
        f"**Run HEAD:** `{head}`",
        f"**Spec:** `{REQUIRED_SPEC}`",
        f"**Export:** `{REQUIRED_EXPORT}`",
        f"**Fit object:** `{REQUIRED_FIT_OBJECT}`",
        f"**Seed:** `{PINNED_SEED}`  n_boot={N_BOOT}",
        f"**Close proxy:** {CLOSE_LABEL}",
        f"**Holdout:** STOPPED (Ryan t4315u `d6fca6f0`). No CLEAR. 2024–25 not opened.",
        f"**Readiness:** Ryan t4317u / decision `5c4e6578`. Checker: t4320u.",
        "",
        "Command (no secrets):",
        "",
        "```",
        cmd,
        "```",
        "",
        "## I-1..I-5 and K-2..K-4 (verbatim)",
        "",
        f"- I-1. {I1_VERBATIM}",
        f"- I-2. {I2_VERBATIM}",
        f"- I-3. {I3_VERBATIM}",
        f"- I-4. {I4_VERBATIM}",
        f"- I-5. {I5_VERBATIM}",
        f"- K-2. {K2_VERBATIM}",
        f"- K-3. {K3_VERBATIM}",
        f"- K-4. {K4_VERBATIM}",
        "",
        "Primary = mean CLV delta (spread). 9 tests = 3 markets × 3 metrics. "
        "Non-zero adjustment = Δmargin≠0 or Δtotal≠0. I-4 VALUE PROVEN only if "
        "primary Holm-significant AND CI excludes 0 AND K-4 passes.",
        "",
    ]
    for res in results:
        m = res["missing"]
        k4 = res["k4"]
        i4 = res["i4"]
        lines += [
            f"## Cohort `{res['name']}`",
            "",
            f"{res['notes']}",
            "",
            f"- I-2: `{res['i2']}` — n_nonzero_adjustment={res['n_nonzero_adjustment']} "
            f"by_season={res['n_nonzero_by_season']} full_seasons={res['n_full_seasons']}",
            f"- I-4 decision: **{i4['decision']}** "
            f"(primary_holm={i4['primary_significant_after_holm']}, "
            f"CI_excludes_0={i4['primary_ci_excludes_0']}, k4={i4['k4_pass']})",
            f"- Product claim: {i4['product_claim']} ({i4['i5']})",
            f"- Identical cohort n={m['n_identical_cohort']} ; paired both-CLV n={m['n_paired_both_clv']}",
            f"- Missing: incomplete={m['n_incomplete_residual']} close={m['n_missing_close']} "
            f"actual={m['n_missing_actual']} baseline={m['n_missing_baseline']}",
            f"- Missing by season: incomplete={m['n_incomplete_by_season']} "
            f"close={m['n_missing_close_by_season']} actual={m['n_missing_actual_by_season']} "
            f"baseline={m['n_missing_baseline_by_season']}",
            f"- Universe by season: {m['n_universe_by_season']}",
            f"- edge=0 drops: base={m['n_edge0_base']} adj={m['n_edge0_adj']}",
            f"- K-4: logloss_CI_hi={k4['logloss_delta_ci_hi']} "
            f"brier_CI_hi={k4['brier_delta_ci_hi']} slope={k4['slope_adj']} pass={k4['pass']} {k4['notes']}",
            "",
            "### I-1 metrics (adj − base)",
            "",
            "| metric | value |",
            "|---|---|",
        ]
        for key in HOLM_NINE:
            val = res["metrics"][key]
            why = (res.get("metric_undefined") or {}).get(key) or ""
            shown = val if val is not None else f"undefined — {why}"
            lines.append(f"| `{key}` | {shown} |")
        lines += [
            "",
            "### K-2 win-prob",
            "",
            f"- Brier base={res['metrics']['mean_brier_base']} adj={res['metrics']['mean_brier_adj']}",
            f"- log loss base={res['metrics']['mean_logloss_base']} adj={res['metrics']['mean_logloss_adj']}",
            "",
            "### I-3 Holm (α=0.05)",
            "",
            "| test | p | rank | threshold | significant |",
            "|---|---|---|---|---|",
        ]
        for h in res["holm"]:
            lines.append(
                f"| `{h['test_id']}` | {h['p']} | {h['holm_rank']} | {h['holm_threshold']} | {h['significant']} |"
            )
        lines += ["", "### K-3 primary CI", ""]
        b = res["bootstrap"][PRIMARY]
        lines.append(
            f"spread_clv_delta obs={b['obs']} CI=[{b['ci_lo']}, {b['ci_hi']}] "
            f"excludes_0={b['excludes_0']} p={b['p']} blocks={b['n_blocks']} seed={b['seed']}"
        )
        lines += ["", "### Reliability bins (K-2, 10 bins, counts)", ""]
        for market in ("spread", "total", "ml"):
            lines.append(f"**{market}**")
            lines.append("| bin | n | mean_p | mean_y | note |")
            lines.append("|---|---|---|---|---|")
            for binrow in res["reliability"][market]:
                lines.append(
                    f"| {binrow['bin']} | {binrow['n']} | {binrow['mean_p']} | {binrow['mean_y']} | {binrow.get('nan_reason') or ''} |"
                )
            lines.append("")
        lines.append("Baseline and adjusted used the **same** identical-close cohort. No arm-specific drop after scoring started.")
        lines.append("")
    lines += [
        "## Hard rules observed",
        "",
        "- No 2024/2025/2026 rows scored.",
        "- No CLEAR token created or accepted.",
        "- No product or cert claim (I-5).",
        "- Close proxy labeled comparative research, not certified CLV.",
        "- v1/v2 holdout requests were not edited.",
        "- Submission-readiness (5c4e6578): manifest + logs + metrics + gate table + provenance.",
        "- Package checker (t4320u) verifies those and re-runs fixtures.",
        "",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_provenance(path: Path, cmd: str, head: str, results: List[Dict[str, Any]]) -> None:
    decisions = {r["name"]: r["i4"]["decision"] for r in results}
    lines = [
        "# Provenance — injury residual evaluator dry-run",
        "",
        "No secrets. Command line below is the complete invocation.",
        "",
        "## Decisions / messages",
        "",
        "- Ryan t4315u / decision `d6fca6f0`: holdout STOPPED. No CLEAR. No 2024–25.",
        "- Ryan t4317u / decision `5c4e6578`: submission-readiness gate (a)–(e).",
        "- Standing principle t4320u: reusable automated package checker.",
        "- Spec: IMV_SPEC_NFL_INJURY_ADJUSTMENT_TESTS_v1.txt sha `a156459b` (v2 unused).",
        "",
        "## Code",
        "",
        f"- Frozen-fit HEAD (C-1): `{REQUIRED_HEAD}`",
        f"- Run HEAD: `{head}`",
        f"- Evaluator: `{Path(__file__).resolve()}`",
        "",
        "## Inputs (seeded; checker dies if missing or wrong sha)",
        "",
        f"- Spec store: `{SPEC_STORE}` sha256 `{REQUIRED_SPEC}`",
        f"- Sealed export: `{EXPORT}` sha256 `{REQUIRED_EXPORT}`",
        f"- Fit object: `{FIT_OBJECT}` sha256 `{REQUIRED_FIT_OBJECT}`",
        f"- Fit script (not executed): `/opt/cursor/artifacts/injury-fit-le2023/run_injury_residual_fit.py` sha256 `8d188da27d3c9f802acdca76763e1ca05e714040cc5ea3722e4922853f28167c`",
        f"- OOS (season<=2023 only; 2024+ skipped before store): `{OOS}`",
        f"- Seed: `{PINNED_SEED}` (`int(\"a156459b\", 16)`)",
        f"- n_boot: `{N_BOOT}`",
        f"- Unshrunk σ: `{UNSHRUNK_SIGMA}`",
        "",
        "## Command (no secrets)",
        "",
        "```",
        cmd,
        "```",
        "",
        "## Environment pins",
        "",
        f"- NFL_TOTALS_*: unset ({', '.join(sorted(k for k in os.environ if k.startswith('NFL_TOTALS_'))) or 'none found'})",
        "- WEEK1_KEI_PUBLISH_MUTATE_FAIR: not set by this runner",
        "- Overlays: off (this runner does not enable any overlay)",
        f"- Close proxy label: {CLOSE_LABEL}",
        "- Tokens: none created (no RYAN_CLEAR, no IMV_PASS)",
        "",
        "## Cohort decisions (this run)",
        "",
    ]
    for name, decision in decisions.items():
        expect = KNOWN_ANSWERS.get(name, "legal I-4 outcome only")
        lines.append(f"- `{name}`: **{decision}** (expected {expect})")
    lines += [
        "",
        "## I-5",
        "",
        "No product claim. VALUE PROVEN on synthetic_pass is a known-answer fixture only.",
        "le2023 is comparative research, not certified CLV, not the sealed holdout.",
        "",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Injury residual evaluator dry-run (no holdout)")
    p.add_argument("--out", required=True)
    p.add_argument("--cohorts", default="synthetic_inconclusive,synthetic_fail,synthetic_pass,le2023")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if any(tok.exists() for tok in (Path(args.out) / "RYAN_CLEAR_ON_FROZEN_RECORD", Path(args.out) / "IMV_PASS")):
        die("CLEAR/IMV token present; builder must not create or use tokens")
    head = assert_env()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    cmd = (
        f"python3 /workspace/ops/nfl_injury_audit_t4274u/injury-evaluator-dryrun/"
        f"run_injury_residual_evaluator.py --out {out} --cohorts {args.cohorts}"
    )
    log(f"cmd={cmd}")
    log(f"CLOSE_LABEL={CLOSE_LABEL}")
    log(f"PINNED_SEED={PINNED_SEED}")
    log(f"HEAD={head} frozen_fit={REQUIRED_HEAD}")
    builders = {
        "synthetic_inconclusive": lambda: make_synthetic("inconclusive"),
        "synthetic_fail": lambda: make_synthetic("fail"),
        "synthetic_pass": lambda: make_synthetic("pass"),
        "le2023": join_le2023,
    }
    notes = {
        "synthetic_inconclusive": "Known answer: I-2 shortfall (1 season, n_nonzero<500) → INCONCLUSIVE.",
        "synthetic_fail": "Known answer: 2 full seasons, n>=500, adj worse → I-4 NO CLAIM (FAIL).",
        "synthetic_pass": "Known answer: 2 full seasons, n>=500, primary Holm-significant, CI excludes 0, K-4 passes → VALUE PROVEN on this fixture only. Not a product claim (I-5). Not the holdout.",
        "le2023": "Sealed le2023 export + OOS season<=2023. Close proxy is comparative research, not certified CLV. Not the sealed holdout.",
    }
    results = []
    for name in [c.strip() for c in args.cohorts.split(",") if c.strip()]:
        if name not in builders:
            die("unknown cohort " + name)
        results.append(evaluate(name, builders[name](), notes[name]))
        log(f"{name} decision={results[-1]['i4']['decision']} i2={results[-1]['i2']}")

    slim = []
    for res in results:
        slim.append({k: v for k, v in res.items() if k != "bootstrap" or True})
        # drop paired row payloads from bootstrap copies already without boot samples
    payload = {
        "protocol": "injury-residual-cal-v2",
        "kind": "evaluator_dry_run",
        "holdout": "STOPPED",
        "ryan": {"t4315u": "d6fca6f0", "t4317u": "5c4e6578", "t4320u": "package-checker"},
        "frozen_fit_head": REQUIRED_HEAD,
        "head": head,
        "spec_sha": REQUIRED_SPEC,
        "export_sha": REQUIRED_EXPORT,
        "fit_object_sha": REQUIRED_FIT_OBJECT,
        "seed": PINNED_SEED,
        "n_boot": N_BOOT,
        "close_label": CLOSE_LABEL,
        "command": cmd,
        "known_answers": KNOWN_ANSWERS,
        "cohorts": [{k: v for k, v in r.items()} for r in results],
    }
    (out / "evaluator_results.json").write_text(
        json.dumps(payload, sort_keys=True, indent=2, default=str) + "\n", encoding="utf-8"
    )
    write_report(out / "dry-run-report.md", results, cmd, head)
    write_provenance(out / "provenance.md", cmd, head, results)
    official_out = Path(__file__).resolve().parent / "out"
    if out.resolve() == official_out.resolve():
        write_provenance(out.parent / "provenance.md", cmd, head, results)
    mismatches = []
    for res in results:
        expect = KNOWN_ANSWERS.get(res["name"])
        if expect and res["i4"]["decision"] != expect:
            mismatches.append(f"{res['name']} got {res['i4']['decision']!r} expected {expect!r}")
    if mismatches:
        die("known-answer mismatch: " + "; ".join(mismatches))
    log(f"wrote {out / 'evaluator_results.json'}")
    log(f"wrote {out / 'dry-run-report.md'}")
    log(f"wrote {out / 'provenance.md'}")
    print(json.dumps({r["name"]: r["i4"]["decision"] for r in results}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
