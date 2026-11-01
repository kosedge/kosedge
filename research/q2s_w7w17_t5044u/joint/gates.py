"""J/Q acceptance bands — dad9eb89 §4 as amended by a091ce1a for J10 only."""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from sim_q2s_joint import JointResult, derive_from_pairs, paired_draw_hash

N = 4000


def _z(emp: float, analytic: float, se: float) -> float:
    if se <= 0.0 or not math.isfinite(se):
        return float("inf")
    return abs(float(emp) - float(analytic)) / float(se)


def _band_z(z: float) -> str:
    if z <= 2.0:
        return "PASS"
    if z <= 4.0:
        return "COND"
    return "FAIL"


def _band_rel(rel: float) -> str:
    if rel <= 0.03:
        return "PASS"
    if rel <= 0.08:
        return "COND"
    return "FAIL"


def _band_wp(err: float, p: float) -> str:
    # PASS ≤2·√(p(1-p)/N) ≈0.0158 at p=0.5; COND ≤0.03; FAIL >0.03
    thresh = 2.0 * math.sqrt(max(0.0, p * (1.0 - p) / N))
    if err <= thresh:
        return "PASS"
    if err <= 0.03:
        return "COND"
    return "FAIL"


def evaluate_game(
    result: JointResult,
    *,
    margin_mu_q2s: float,
    if_margin_mu: float | None = None,
    if_total_mu: float | None = None,
    if_wp_home: float | None = None,
    sim: Any = None,
) -> dict[str, Any]:
    gates: dict[str, Any] = {}
    ana = result.analytic
    D = result.H - result.A
    S = result.H + result.A

    # J1 spread_home == -mean(D') at 2dp / 0.005
    j1_err = abs(result.spread_home - (-result.mean_D))
    gates["J1"] = {
        "status": "PASS" if j1_err <= 0.005 else "FAIL",
        "err": j1_err,
    }

    # J2 total == mean(S')
    j2_err = abs(result.total_raw - result.mean_S)
    gates["J2"] = {
        "status": "PASS" if j2_err <= 0.005 else "FAIL",
        "err": j2_err,
    }

    # J3 home_wp == #(D'>0)/N exact at 4dp
    raw_wp = result.home_wins / float(result.N)
    j3_ok = round(result.home_wp, 4) == round(raw_wp, 4) and result.home_wp == raw_wp
    gates["J3"] = {"status": "PASS" if j3_ok else "FAIL", "home_wp": result.home_wp}

    # J4 away_wp == 1-home_wp
    j4_err = abs(result.away_wp - (1.0 - result.home_wp))
    gates["J4"] = {"status": "PASS" if j4_err <= 1e-4 else "FAIL", "err": j4_err}

    # J5 ML == f(wp)
    if sim is None:
        gates["J5"] = {"status": "FAIL", "err": "no sim"}
    else:
        exp_h = int(sim._fair_moneyline_from_prob(result.home_wp))
        exp_a = int(sim._fair_moneyline_from_prob(result.away_wp))
        ok = result.fair_home_ml == exp_h and result.fair_away_ml == exp_a
        gates["J5"] = {"status": "PASS" if ok else "FAIL"}

    # J6 identities
    j6a = abs((result.mean_H + result.mean_A) - result.mean_S)
    j6b = abs((result.mean_H - result.mean_A) - result.mean_D)
    gates["J6"] = {
        "status": "PASS" if j6a <= 1e-9 and j6b <= 1e-9 else "FAIL",
        "err_sum": j6a,
        "err_diff": j6b,
    }

    # J7a z vs exact censored means
    se_h = ana["sd_H"] / math.sqrt(N)
    se_a = ana["sd_A"] / math.sqrt(N)
    se_d = ana["sd_D"] / math.sqrt(N)
    se_s = ana["sd_S"] / math.sqrt(N)
    zs = {
        "H": _z(result.mean_H, ana["mean_H"], se_h),
        "A": _z(result.mean_A, ana["mean_A"], se_a),
        "D": _z(result.mean_D, ana["mean_D"], se_d),
        "S": _z(result.mean_S, ana["mean_S"], se_s),
    }
    zmax = max(zs.values())
    gates["J7a"] = {"status": _band_z(zmax), "z": zs, "zmax": zmax}

    # J7b target fidelity
    fid = abs(result.mean_D - float(margin_mu_q2s))
    gates["J7b"] = {
        "status": "FAIL" if fid > 0.67 else "PASS",
        "abs_err": fid,
        "margin_mu_q2s": float(margin_mu_q2s),
        "mean_D": result.mean_D,
    }

    # J8 SD rel err
    rels = {
        "H": abs(result.sd_H - ana["sd_H"]) / ana["sd_H"] if ana["sd_H"] else float("inf"),
        "A": abs(result.sd_A - ana["sd_A"]) / ana["sd_A"] if ana["sd_A"] else float("inf"),
        "D": abs(result.sd_D - ana["sd_D"]) / ana["sd_D"] if ana["sd_D"] else float("inf"),
        "S": abs(result.sd_S - ana["sd_S"]) / ana["sd_S"] if ana["sd_S"] else float("inf"),
    }
    rmax = max(rels.values())
    gates["J8"] = {"status": _band_rel(rmax), "rel": rels, "rmax": rmax}

    # J9 wp vs exact censored P(D'>0)
    p = float(ana["p_D_pos"])
    j9_err = abs(result.home_wp - p)
    gates["J9"] = {
        "status": _band_wp(j9_err, p),
        "err": j9_err,
        "p_analytic": p,
        "home_wp": result.home_wp,
    }

    # J10 corr — a091ce1a
    r = result.corr_HA
    if not math.isfinite(r) or result.var_H == 0.0 or result.var_A == 0.0:
        j10 = "REFUSE"
    elif abs(r) <= 0.05:
        j10 = "PASS"
    elif abs(r) <= 0.08:
        j10 = "COND"
    else:
        j10 = "FAIL"
    gates["J10"] = {
        "status": j10,
        "r": r,
        "analytic_independence": 0.0,
    }

    # J11 spread vs wp
    spr = result.spread_home
    if abs(spr) >= 0.25:
        ok = (spr < 0.0) == (result.home_wp > 0.5)
        gates["J11"] = {"status": "PASS" if ok else "FAIL", "spread": spr}
    else:
        gates["J11"] = {"status": "COND", "spread": spr, "inside_025": True}

    # J14 NOT EMITTED
    gates["J14"] = {"status": "NOT_EMITTED"}

    # Tie mass
    p_tie = result.tie_count / float(result.N)
    if p_tie <= 1e-3:
        tstat = "PASS"
    elif p_tie <= 5e-3:
        tstat = "COND"
    else:
        tstat = "FAIL"
    gates["Tie"] = {"status": tstat, "p_tie": p_tie, "tie_count": result.tie_count}

    # Q5 latent sum
    q5_err = abs((result.mu_h_p + result.mu_a_p) - (result.mu_h + result.mu_a))
    q5_ok = q5_err <= 1e-12 and float(result.H.min()) >= 0.0 and float(result.A.min()) >= 0.0
    gates["Q5"] = {"status": "PASS" if q5_ok else "FAIL", "latent_sum_err": q5_err}

    # Q5 diagnostics (missing = FAIL)
    diag = {
        "floor_mass_H_emp": result.floor_emp_H,
        "floor_mass_A_emp": result.floor_emp_A,
        "floor_mass_H_analytic": ana["floor_H"],
        "floor_mass_A_analytic": ana["floor_A"],
        "mean_H_emp": result.mean_H,
        "mean_A_emp": result.mean_A,
        "mean_H_analytic": ana["mean_H"],
        "mean_A_analytic": ana["mean_A"],
        "var_H_emp": result.var_H,
        "var_A_emp": result.var_A,
        "var_H_analytic": ana["var_H"],
        "var_A_analytic": ana["var_A"],
        "margin_drift_vs_q2s": result.mean_D - float(margin_mu_q2s),
        "total_drift_vs_analytic": result.mean_S - ana["mean_S"],
        "cov_MT_emp": result.cov_MT,
        "cov_MT_analytic": ana["cov_MT"],
    }
    missing = [k for k, v in diag.items() if v is None or (isinstance(v, float) and not math.isfinite(v) and k != "unused")]
    gates["Q5_diag"] = {
        "status": "FAIL" if missing else "reported",
        "missing": missing,
        **diag,
    }

    # Q3 recompute from persisted pairs
    if sim is not None:
        again = derive_from_pairs(result.H, result.A, sim)
        digest = paired_draw_hash(result.H, result.A)
        ok = (
            digest == result.draw_hash
            and again["home_wp"] == result.home_wp
            and again["spread_home"] == result.spread_home
            and again["total_raw"] == result.total_raw
            and again["fair_home_ml"] == result.fair_home_ml
        )
        gates["Q3"] = {"status": "PASS" if ok else "FAIL"}
    else:
        gates["Q3"] = {"status": "FAIL"}

    return gates


def worst_status(gates: dict[str, Any]) -> str:
    order = {"REFUSE": 4, "FAIL": 3, "COND": 2, "NOT_EMITTED": 0, "reported": 0, "PASS": 0}
    worst = "PASS"
    for key, g in gates.items():
        if key == "J14":
            continue
        st = g.get("status")
        if order.get(st, 0) > order.get(worst, 0):
            worst = st
    return worst
