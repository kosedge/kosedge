"""Executed root nine fixtures (RETURN 36205). CERT=0. Not a fitted-model claim."""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

from src.services.nfl_ntbb_k_v1.constants import (
    COND_TRANSPOSE_TOL,
    IDENTITY_TOL,
    JOINT_TRANSPOSE_TOL,
    NORM_TOL,
    ORACLE_MAX_ENUMERATED_TOTAL,
    ROOT_EXPECTED_N,
    ROOT_NINE,
)
from src.services.nfl_ntbb_k_v1.law import conditional_log_mass, joint_pmf, log_joint_pmf
from src.services.nfl_ntbb_k_v1.refuse import NtbbKRefuse
from src.services.nfl_ntbb_k_v1.special import fsum, log_betabinom_pmf, nbinom_pmf_series
from src.services.nfl_ntbb_k_v1.table import enumerate_joint


def _params(row: tuple) -> dict[str, float]:
    _name, mu, r, p, c, k0, k3, k7, _group = row
    return {"mu": mu, "r": r, "p": p, "c": c, "k0": k0, "k3": k3, "k7": k7}


def _family(name: str) -> str:
    return name.rsplit("_", 1)[0]


def _by_t(table: dict[str, Any]) -> dict[int, float]:
    acc: dict[int, list[float]] = defaultdict(list)
    for row in table["rows"]:
        acc[row["t"]].append(row["mass"])
    return {t: fsum(vals) for t, vals in acc.items()}


def check_normalization(table: dict[str, Any]) -> float:
    residual = float(table["enumeration_error"])
    if residual > NORM_TOL:
        raise NtbbKRefuse(f"normalization residual {residual}")
    if table["renormalized"]:
        raise NtbbKRefuse("silent renormalize refused")
    return residual


def check_symmetry_p(params: dict[str, float]) -> float:
    if params["p"] != 0.5:
        return 0.0
    residual = 0.0
    for h in range(0, 9):
        for a in range(0, 9):
            residual = max(
                residual,
                abs(joint_pmf(h, a, **params) - joint_pmf(a, h, **params)),
            )
    if residual > JOINT_TRANSPOSE_TOL:
        raise NtbbKRefuse(f"p=0.5 symmetry residual {residual}")
    return residual


def check_transpose(params: dict[str, float]) -> dict[str, float]:
    swapped = dict(params)
    swapped["p"] = 1.0 - params["p"]
    joint = 0.0
    for h in range(0, 8):
        for a in range(0, 8):
            joint = max(joint, abs(joint_pmf(h, a, **params) - joint_pmf(a, h, **swapped)))
    if joint > JOINT_TRANSPOSE_TOL:
        raise NtbbKRefuse(f"joint transpose residual {joint}")
    cond = 0.0
    for t in (0, 3, 7, 12):
        a = conditional_log_mass(t, p=params["p"], c=params["c"], k0=params["k0"], k3=params["k3"], k7=params["k7"])
        b = conditional_log_mass(t, p=swapped["p"], c=swapped["c"], k0=swapped["k0"], k3=swapped["k3"], k7=swapped["k7"])
        for h in range(t + 1):
            cond = max(cond, abs(math.exp(a[h]) - math.exp(b[t - h])))
    if cond > COND_TRANSPOSE_TOL:
        raise NtbbKRefuse(f"conditional transpose residual {cond}")
    return {"conditional": cond, "joint": joint}


def check_total_marginal(table: dict[str, Any], params: dict[str, float]) -> float:
    q = nbinom_pmf_series(r=params["r"], mu=params["mu"], t_max=table["N"])
    by_t = _by_t(table)
    residual = 0.0
    for t, qt in enumerate(q):
        residual = max(residual, abs(by_t.get(t, 0.0) - qt))
    if residual > IDENTITY_TOL:
        raise NtbbKRefuse(f"NB marginal residual {residual}")
    return residual


def check_k0_betabinom(table: dict[str, Any], params: dict[str, float]) -> float:
    if any(params[k] != 0.0 for k in ("k0", "k3", "k7")):
        return 0.0
    alpha = params["p"] * params["c"]
    beta = (1.0 - params["p"]) * params["c"]
    residual = 0.0
    q = nbinom_pmf_series(r=params["r"], mu=params["mu"], t_max=table["N"])
    for row in table["rows"]:
        t, h = row["t"], row["h"]
        if t == 0:
            expect = q[0]
        else:
            expect = q[t] * math.exp(log_betabinom_pmf(h, t, alpha=alpha, beta=beta))
        residual = max(residual, abs(row["mass"] - expect))
    if residual > IDENTITY_TOL:
        raise NtbbKRefuse(f"k=0 beta-binomial residual {residual}")
    return residual


def check_tail_moment(table: dict[str, Any], params: dict[str, float]) -> float:
    if table["moments"]["status"] != "OK":
        raise NtbbKRefuse("moment outputs refused")
    mu = params["mu"]
    total_mean = table["moments"]["total_mean"]
    bound = table["moments"]["moment_bound"]
    gap = abs(mu - total_mean)
    if gap > IDENTITY_TOL + bound:
        raise NtbbKRefuse(f"tail-moment identity residual {gap}")
    if bound > 1e-8:
        raise NtbbKRefuse(f"moment bound {bound} exceeds 1e-8")
    return gap


def run_root_nine() -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    max_n = 0
    by_name: dict[str, dict[str, Any]] = {}
    for row in ROOT_NINE:
        name = row[0]
        params = _params(row)
        table = enumerate_joint(**params)
        family = _family(name)
        expected_n = ROOT_EXPECTED_N[family]
        if table["N"] != expected_n:
            raise NtbbKRefuse(f"{name} N={table['N']} != expected {expected_n}")
        max_n = max(max_n, int(table["N"]))
        residuals = {
            "normalization": check_normalization(table),
            "symmetry": check_symmetry_p(params),
            "total_marginal": check_total_marginal(table, params),
            "tail_moment": check_tail_moment(table, params),
        }
        extras = {
            "k0_betabinom": check_k0_betabinom(table, params),
            "transpose": check_transpose(params),
            "log_pmf_00": log_joint_pmf(0, 0, **params),
        }
        rec = {
            "N": table["N"],
            "enumerated_mass": table["enumerated_mass"],
            "enumeration_error": table["enumeration_error"],
            "expected_N": expected_n,
            "extras": extras,
            "family": family,
            "group": "root",
            "moment_bound": table["moments"]["moment_bound"],
            "name": name,
            "params": params,
            "residuals": residuals,
            "status": "PASS",
            "tail_mass": table["tail_mass"],
        }
        results.append(rec)
        by_name[name] = rec
    if max_n > ORACLE_MAX_ENUMERATED_TOTAL:
        raise NtbbKRefuse(f"max enumerated total {max_n} > oracle {ORACLE_MAX_ENUMERATED_TOTAL}")
    return {
        "fixture_kind": "RETURN_36205_ROOT_NINE",
        "max_enumerated_total": max_n,
        "n_cases": len(results),
        "not_demo_small_nine": True,
        "oracle_max_enumerated_total": ORACLE_MAX_ENUMERATED_TOTAL,
        "oracle_max_enumerated_total_honored": max_n <= ORACLE_MAX_ENUMERATED_TOTAL,
        "results": results,
        "status": "PASS",
    }
