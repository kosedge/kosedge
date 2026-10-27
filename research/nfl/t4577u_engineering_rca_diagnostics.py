#!/usr/bin/env python3
"""t4577u engineering RCA diagnostics — development data only.

Read-only analysis of the pinned n=2992 EPA/RECORD walk-forward emit.
Does not call Odds API, does not touch holdouts 2024–25, does not change
scoring equations, does not fit a scale-factor curve.

Usage:
  python3 research/nfl/t4577u_engineering_rca_diagnostics.py \\
    --emit-csv /path/to/epa_wf_features_2013_2023.csv \\
    --oos-csv data/ops/nfl-reopening-packet-20260916/historical-oos/historical_oos_games.csv

Expected emit sha256: 02f6b2e2baa425cab7703dd1d3d5064fc0dabfc69e330a846e54d736c49430a2
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

# Locked scoring knobs (nfl-handicap-core-v3.1 / LOCKED_SCORING).
MARGIN_WEIGHT = 16.0
MAX_MARGIN_POINTS = 6.5
OFF_DEF_CLAMP = 0.25
HFA_POINTS = 1.05
TOTAL_WEIGHT = 10.5
MAX_TOTAL_POINTS = 5.0
BASE_TOTAL = 45.3

# team_strength_from_record
REC_OFF_A, REC_OFF_B = 0.90, 0.22
REC_DEF_A, REC_DEF_B = 0.92, 0.20
REC_OFF_LO, REC_OFF_HI = 0.82, 1.18
REC_DEF_LO, REC_DEF_HI = 0.82, 1.20

# epa_to_strength_indices
EPA_OFF_COEF, EPA_DEF_COEF = 0.75, 0.90
EPA_OFF_LO, EPA_OFF_HI = 0.82, 1.22
EPA_DEF_LO, EPA_DEF_HI = 0.82, 1.24

EXPECTED_EMIT_SHA256 = "02f6b2e2baa425cab7703dd1d3d5064fc0dabfc69e330a846e54d736c49430a2"


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _f(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def record_indices(win_pct: float) -> Tuple[float, float]:
    off = _clamp(REC_OFF_A + REC_OFF_B * win_pct, REC_OFF_LO, REC_OFF_HI)
    deff = _clamp(REC_DEF_A + REC_DEF_B * win_pct, REC_DEF_LO, REC_DEF_HI)
    return off, deff


def epa_indices(off_epa: float, def_epa_allowed: float, p_delta: float = 0.0) -> Tuple[float, float]:
    off = _clamp(1.0 + EPA_OFF_COEF * off_epa + 0.18 * p_delta, EPA_OFF_LO, EPA_OFF_HI)
    deff = _clamp(1.0 + EPA_DEF_COEF * (-def_epa_allowed) + 0.14 * p_delta, EPA_DEF_LO, EPA_DEF_HI)
    return off, deff


def efficiency_margin(off_h: float, def_h: float, off_a: float, def_a: float) -> Dict[str, float]:
    off_def_h = _clamp((off_h / max(0.75, def_a)) - 1.0, -OFF_DEF_CLAMP, OFF_DEF_CLAMP)
    off_def_a = _clamp((off_a / max(0.75, def_h)) - 1.0, -OFF_DEF_CLAMP, OFF_DEF_CLAMP)
    raw = (off_def_h - off_def_a) * MARGIN_WEIGHT
    capped = _clamp(raw, -MAX_MARGIN_POINTS, MAX_MARGIN_POINTS)
    raw_tot = (off_def_h + off_def_a) * TOTAL_WEIGHT
    capped_tot = _clamp(raw_tot, -MAX_TOTAL_POINTS, MAX_TOTAL_POINTS)
    return {
        "off_def_home": off_def_h,
        "off_def_away": off_def_a,
        "raw_margin": raw,
        "capped_margin": capped,
        "pred_margin": capped + HFA_POINTS,
        "raw_total_delta": raw_tot,
        "capped_total_delta": capped_tot,
        "pred_total": BASE_TOTAL + capped_tot,
        "off_def_clamped": abs(off_def_h) >= OFF_DEF_CLAMP - 1e-12 or abs(off_def_a) >= OFF_DEF_CLAMP - 1e-12,
        "margin_capped": abs(raw) > MAX_MARGIN_POINTS + 1e-12,
    }


def linreg(x: Sequence[float], y: Sequence[float]) -> Tuple[float, float]:
    n = len(x)
    mx = sum(x) / n
    my = sum(y) / n
    den = sum((xi - mx) ** 2 for xi in x)
    if den <= 0:
        return float("nan"), my
    slope = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y)) / den
    intercept = my - slope * mx
    return slope, intercept


def mae(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(abs(x - y) for x, y in zip(a, b)) / len(a)


def sd(xs: Sequence[float]) -> float:
    return statistics.pstdev(xs) if len(xs) > 1 else 0.0


def theoretical_bounds() -> Dict[str, Any]:
    rec_perfect = efficiency_margin(*record_indices(1.0), *record_indices(0.0))
    rec_even = efficiency_margin(*record_indices(0.0), *record_indices(0.0))
    rec_mid = efficiency_margin(*record_indices(10 / 13), *record_indices(3 / 13))
    # Typical / elite EPA mismatches (pressure=0).
    epa_typ = efficiency_margin(*epa_indices(0.08, -0.04), *epa_indices(-0.04, 0.08))
    epa_elite = efficiency_margin(*epa_indices(0.25, -0.15), *epa_indices(-0.15, 0.20))
    return {
        "locked_knobs": {
            "margin_weight": MARGIN_WEIGHT,
            "max_margin_points": MAX_MARGIN_POINTS,
            "off_def_clamp": OFF_DEF_CLAMP,
            "hfa_points": HFA_POINTS,
            "theoretical_max_abs_margin_efficiency_plus_hfa": MAX_MARGIN_POINTS + HFA_POINTS,
        },
        "record_0_0_vs_0_0": rec_even,
        "record_16_0_vs_0_16": rec_perfect,
        "record_10_3_vs_3_10": rec_mid,
        "epa_typical_plus08_vs_minus04": epa_typ,
        "epa_elite_plus25_vs_minus15": epa_elite,
        "week1_record_all_identical": {
            "offense_index": record_indices(0.0)[0],
            "defense_index": record_indices(0.0)[1],
            "pred_margin": rec_even["pred_margin"],
            "note": "All teams 0-0 map to the same 0.90/0.92 book; only HFA remains.",
        },
        "record_totals_near_cancel": {
            "16_0_vs_0_16_total_delta": rec_perfect["capped_total_delta"],
            "reason": "O and D both come from the same win_pct, so off_def_h + off_def_a ≈ 0.",
        },
    }


def analyze_emit(emit_rows: List[Dict[str, str]], oos_rows: List[Dict[str, str]]) -> Dict[str, Any]:
    oos_key = {
        (int(r["season"]), int(r["week"]), r["home"], r["away"]): r
        for r in oos_rows
        if 2013 <= int(r["season"]) <= 2023
    }
    joined = 0
    unjoined = 0
    rec_pm: List[float] = []
    epa_pm: List[float] = []
    rec_tot: List[float] = []
    epa_tot: List[float] = []
    mkt_pm: List[float] = []
    mkt_tot: List[float] = []
    act_m: List[float] = []
    act_tot: List[float] = []
    rec_decomp: List[float] = []
    rec_mc: List[float] = []
    rec_abs_spread: List[float] = []
    epa_abs_spread: List[float] = []
    mkt_abs_spread: List[float] = []
    week1_rec_margins: List[float] = []
    week1_rec_decomp: List[float] = []
    cap_hits_decomp = 0
    near_hfa_only = 0
    location_counter: Counter[str] = Counter()

    for r in emit_rows:
        key = (int(r["season"]), int(r["week"]), r["home"], r["away"])
        o = oos_key.get(key)
        rec_pm_v = _f(r["record_pred_margin_home"])
        rec_sp = _f(r["record_spread_home"])
        rec_d = _f(r["record_decomp_pred_margin_home"])
        epa_sp = _f(r["epa_trailing_spread_home"])
        mkt_sp = _f(r["market_spread_home"])
        if rec_pm_v is None or epa_sp is None or mkt_sp is None:
            continue
        epa_pm_v = -epa_sp
        mkt_pm_v = -mkt_sp
        rec_pm.append(rec_pm_v)
        epa_pm.append(epa_pm_v)
        rec_tot.append(float(_f(r["record_total"]) or 0.0))
        epa_tot.append(float(_f(r["epa_trailing_total"]) or 0.0))
        mkt_pm.append(mkt_pm_v)
        mkt_tot.append(float(_f(r["market_total"]) or 0.0))
        rec_abs_spread.append(abs(rec_sp or 0.0))
        epa_abs_spread.append(abs(epa_sp))
        mkt_abs_spread.append(abs(mkt_sp))
        if rec_d is not None:
            rec_decomp.append(rec_d)
            rec_mc.append(rec_pm_v)
            if abs(abs(rec_d) - (MAX_MARGIN_POINTS + HFA_POINTS)) < 0.02:
                cap_hits_decomp += 1
            if abs(rec_d - HFA_POINTS) < 0.02:
                near_hfa_only += 1
        if int(r["week"]) == 1:
            week1_rec_margins.append(rec_pm_v)
            if rec_d is not None:
                week1_rec_decomp.append(rec_d)
        loc = (r.get("nflverse_location") or "").strip().lower()
        if loc:
            location_counter[loc] += 1
        if o is None:
            unjoined += 1
            continue
        joined += 1
        hs = _f(o["home_score"])
        aws = _f(o["away_score"])
        if hs is None or aws is None:
            continue
        act_m.append(hs - aws)
        act_tot.append(hs + aws)

    n = len(rec_pm)
    n_act = len(act_m)
    rec_mc_decomp_abs = [abs(a - b) for a, b in zip(rec_mc, rec_decomp)] if rec_mc else []

    out: Dict[str, Any] = {
        "n_emit": len(emit_rows),
        "n_scored": n,
        "n_joined_oos_actuals": joined,
        "n_unjoined_oos": unjoined,
        "n_with_actuals": n_act,
        "apply_market_blend": Counter(r.get("apply_market_blend") for r in emit_rows),
        "epa_status": Counter(r.get("epa_status") for r in emit_rows),
        "simulations": Counter(r.get("simulations") for r in emit_rows),
        "n_postseason_week_gt_18": sum(1 for r in emit_rows if int(r["week"]) > 18),
        "n_week22": sum(1 for r in emit_rows if int(r["week"]) == 22),
        "spread_range": {
            "record_abs_max": max(rec_abs_spread) if rec_abs_spread else None,
            "epa_abs_max": max(epa_abs_spread) if epa_abs_spread else None,
            "market_abs_max": max(mkt_abs_spread) if mkt_abs_spread else None,
            "record_abs_p95": sorted(rec_abs_spread)[int(0.95 * (len(rec_abs_spread) - 1))] if rec_abs_spread else None,
            "epa_abs_p95": sorted(epa_abs_spread)[int(0.95 * (len(epa_abs_spread) - 1))] if epa_abs_spread else None,
            "market_abs_p95": sorted(mkt_abs_spread)[int(0.95 * (len(mkt_abs_spread) - 1))] if mkt_abs_spread else None,
        },
        "means": {
            "record_pred_margin": sum(rec_pm) / n,
            "epa_pred_margin": sum(epa_pm) / n,
            "market_margin": sum(mkt_pm) / n,
            "actual_margin": (sum(act_m) / n_act) if n_act else None,
            "record_total": sum(rec_tot) / n,
            "epa_total": sum(epa_tot) / n,
            "market_total": sum(mkt_tot) / n,
        },
        "sd": {
            "record_pred_margin": sd(rec_pm),
            "epa_pred_margin": sd(epa_pm),
            "market_margin": sd(mkt_pm),
            "actual_margin": sd(act_m) if n_act else None,
            "record_total": sd(rec_tot),
            "epa_total": sd(epa_tot),
            "market_total": sd(mkt_tot),
        },
        "slope_model_on_market": {
            "record": linreg(mkt_pm, rec_pm)[0],
            "epa": linreg(mkt_pm, epa_pm)[0],
        },
        "sd_ratio_model_over_market": {
            "record": sd(rec_pm) / sd(mkt_pm) if sd(mkt_pm) else None,
            "epa": sd(epa_pm) / sd(mkt_pm) if sd(mkt_pm) else None,
            "record_total": sd(rec_tot) / sd(mkt_tot) if sd(mkt_tot) else None,
            "epa_total": sd(epa_tot) / sd(mkt_tot) if sd(mkt_tot) else None,
        },
        "mae_vs_actual": {
            "record": mae(rec_pm[:n_act], act_m) if n_act == n else "join_n_mismatch_see_n_with_actuals",
            "epa": mae(epa_pm[:n_act], act_m) if n_act == n else None,
            "market": mae(mkt_pm[:n_act], act_m) if n_act == n else None,
        },
        "bias_pred_minus_actual": {
            "record": (sum(rec_pm[:n_act]) / n_act - sum(act_m) / n_act) if n_act == n else None,
            "epa": (sum(epa_pm[:n_act]) / n_act - sum(act_m) / n_act) if n_act == n else None,
            "market": (sum(mkt_pm[:n_act]) / n_act - sum(act_m) / n_act) if n_act == n else None,
        },
        "record_mc_vs_decomp": {
            "n": len(rec_mc_decomp_abs),
            "mean_abs_diff": (sum(rec_mc_decomp_abs) / len(rec_mc_decomp_abs)) if rec_mc_decomp_abs else None,
            "max_abs_diff": max(rec_mc_decomp_abs) if rec_mc_decomp_abs else None,
            "mean_mc_minus_decomp": (sum(a - b for a, b in zip(rec_mc, rec_decomp)) / len(rec_mc)) if rec_mc else None,
        },
        "record_cap_and_hfa": {
            "decomp_near_pm_7_55_cap": cap_hits_decomp,
            "decomp_exactly_hfa_1_05": near_hfa_only,
            "week1_n": len(week1_rec_margins),
            "week1_mc_mean": (sum(week1_rec_margins) / len(week1_rec_margins)) if week1_rec_margins else None,
            "week1_decomp_unique": sorted(set(round(x, 4) for x in week1_rec_decomp)),
            "week1_all_decomp_are_hfa": bool(week1_rec_decomp) and all(abs(x - HFA_POINTS) < 0.02 for x in week1_rec_decomp),
        },
        "sign_identity_record": {
            "max_abs_pred_plus_spread": max(
                abs(float(r["record_pred_margin_home"]) + float(r["record_spread_home"]))
                for r in emit_rows
                if r.get("record_pred_margin_home") and r.get("record_spread_home")
            ),
        },
        "nflverse_location_top": location_counter.most_common(8),
    }

    # Join-safe MAE if n_act != n: recompute on paired rows only.
    if n_act != n:
        paired_rec: List[float] = []
        paired_epa: List[float] = []
        paired_mkt: List[float] = []
        paired_act: List[float] = []
        for r in emit_rows:
            key = (int(r["season"]), int(r["week"]), r["home"], r["away"])
            o = oos_key.get(key)
            if o is None:
                continue
            hs, aws = _f(o["home_score"]), _f(o["away_score"])
            rec_pm_v, epa_sp, mkt_sp = _f(r["record_pred_margin_home"]), _f(r["epa_trailing_spread_home"]), _f(r["market_spread_home"])
            if None in (hs, aws, rec_pm_v, epa_sp, mkt_sp):
                continue
            paired_rec.append(rec_pm_v)
            paired_epa.append(-epa_sp)
            paired_mkt.append(-mkt_sp)
            paired_act.append(hs - aws)
        out["mae_vs_actual"] = {
            "n_paired": len(paired_act),
            "record": mae(paired_rec, paired_act),
            "epa": mae(paired_epa, paired_act),
            "market": mae(paired_mkt, paired_act),
        }
        out["bias_pred_minus_actual"] = {
            "n_paired": len(paired_act),
            "record": sum(a - b for a, b in zip(paired_rec, paired_act)) / len(paired_act),
            "epa": sum(a - b for a, b in zip(paired_epa, paired_act)) / len(paired_act),
            "market": sum(a - b for a, b in zip(paired_mkt, paired_act)) / len(paired_act),
        }
        out["slope_actual_on_model"] = {
            "record": linreg(paired_rec, paired_act)[0],
            "epa": linreg(paired_epa, paired_act)[0],
            "market": linreg(paired_mkt, paired_act)[0],
        }
    else:
        out["slope_actual_on_model"] = {
            "record": linreg(rec_pm, act_m)[0],
            "epa": linreg(epa_pm, act_m)[0],
            "market": linreg(mkt_pm, act_m)[0],
        }

    # Super Bowl / London-ish HFA always-on probe.
    sb = [r for r in emit_rows if int(r["week"]) == 22]
    out["week22_super_bowl_hfa_always_on"] = [
        {
            "season": r["season"],
            "home": r["home"],
            "away": r["away"],
            "location": r.get("nflverse_location"),
            "record_decomp_pred_margin_home": r.get("record_decomp_pred_margin_home"),
            "epa_trailing_spread_home": r.get("epa_trailing_spread_home"),
            "market_spread_home": r.get("market_spread_home"),
        }
        for r in sb
    ]
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--emit-csv", required=True)
    ap.add_argument("--oos-csv", required=True)
    ap.add_argument("--out-json", default="")
    args = ap.parse_args()
    emit_path = Path(args.emit_csv)
    oos_path = Path(args.oos_csv)
    emit_sha = _sha256(emit_path)
    with emit_path.open() as fh:
        emit_rows = list(csv.DictReader(fh))
    with oos_path.open() as fh:
        oos_rows = list(csv.DictReader(fh))
    payload = {
        "ticket": "t4577u",
        "label": "RESEARCH_DIAGNOSTIC",
        "cert_candidate": 0,
        "emit_csv": str(emit_path),
        "emit_sha256": emit_sha,
        "emit_sha256_matches_pinned_02f6b2e2": emit_sha == EXPECTED_EMIT_SHA256,
        "oos_csv": str(oos_path),
        "oos_sha256": _sha256(oos_path),
        "theoretical_bounds": theoretical_bounds(),
        "emit_analysis": analyze_emit(emit_rows, oos_rows),
        "database_url": "UNSET" if not __import__("os").environ.get("DATABASE_URL") else "SET_NOT_PRINTED",
    }
    text = json.dumps(payload, indent=2, sort_keys=True)
    if args.out_json:
        Path(args.out_json).write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
