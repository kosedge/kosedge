"""Nine fictional mathematical cases. CERT=0. Stdlib oracle, not a fitted-model claim."""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

from src.services.nfl_ntbb_k_v1.constants import (
    IDENTITY_TOL,
    NORM_TOL,
    ORACLE_MAX_ENUMERATED_TOTAL,
    ROOT_NINE,
    TRANSPOSE_TOL,
)
from src.services.nfl_ntbb_k_v1.law import joint_pmf, log_joint_pmf
from src.services.nfl_ntbb_k_v1.refuse import NtbbKRefuse
from src.services.nfl_ntbb_k_v1.special import fsum, log_betabinom_pmf, nbinom_pmf_series
from src.services.nfl_ntbb_k_v1.table import enumerate_joint


def _params(row: tuple) -> dict[str, float]:
    _name, mu, r, p, c, k0, k3, k7, _group = row
    return {"mu": mu, "r": r, "p": p, "c": c, "k0": k0, "k3": k3, "k7": k7}


def _by_t(table: dict[str, Any]) -> dict[int, float]:
    acc: dict[int, list[float]] = defaultdict(list)
    for row in table["rows"]:
        acc[row["t"]].append(row["mass"])
    return {t: fsum(vals) for t, vals in acc.items()}


def _mass_m(table: dict[str, Any], pred) -> float:
    return fsum(row["mass"] for row in table["rows"] if pred(row["m"]))


def check_normalization(table: dict[str, Any]) -> float:
    residual = abs(table["enumeration_error"])
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
    if residual > TRANSPOSE_TOL:
        raise NtbbKRefuse(f"p=0.5 symmetry residual {residual}")
    return residual


def check_transpose(params: dict[str, float]) -> float:
    swapped = dict(params)
    swapped["p"] = 1.0 - params["p"]
    residual = 0.0
    for h in range(0, 8):
        for a in range(0, 8):
            residual = max(
                residual,
                abs(joint_pmf(h, a, **params) - joint_pmf(a, h, **swapped)),
            )
    if residual > TRANSPOSE_TOL:
        raise NtbbKRefuse(f"transpose residual {residual}")
    return residual


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


def check_variance(table: dict[str, Any], params: dict[str, float]) -> float:
    mu = params["mu"]
    r = params["r"]
    expect_var = mu + (mu * mu) / r
    et = fsum(row["t"] * row["mass"] for row in table["rows"])
    et2 = fsum(row["t"] * row["t"] * row["mass"] for row in table["rows"])
    got = et2 - et * et
    residual = abs(got - expect_var)
    # omitted tail can move the second moment; refuse only if far beyond first-moment bound scale
    bound = table["moments"]["moment_bound"]
    if residual > max(IDENTITY_TOL, 2.0 * (bound * table["N"] + 1e-18)):
        raise NtbbKRefuse(f"variance identity residual {residual}")
    return residual


def check_tail_moment(table: dict[str, Any], params: dict[str, float]) -> float:
    if table["moments"]["status"] != "OK":
        raise NtbbKRefuse("moment outputs refused")
    mu = params["mu"]
    total_mean = table["moments"]["total_mean"]
    bound = table["moments"]["moment_bound"]
    gap = mu - total_mean
    if gap < -IDENTITY_TOL:
        raise NtbbKRefuse(f"enumerated E[T] exceeds mu: {gap}")
    if gap - bound > IDENTITY_TOL:
        raise NtbbKRefuse(f"tail-moment identity residual {gap - bound}")
    if bound > 1e-8:
        raise NtbbKRefuse(f"moment bound {bound} exceeds 1e-8")
    return abs(gap)


def run_root_nine() -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    max_n = 0
    for row in ROOT_NINE:
        name, _mu, _r, _p, _c, _k0, _k3, _k7, group = row
        params = _params(row)
        table = enumerate_joint(**params)
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
            "variance": check_variance(table, params),
            "log_pmf_00": log_joint_pmf(0, 0, **params),
        }
        if name == "TIE_TILT":
            base = enumerate_joint(mu=params["mu"], r=params["r"], p=params["p"], c=params["c"])
            extras["tie_mass_delta"] = _mass_m(table, lambda m: m == 0) - _mass_m(
                base, lambda m: m == 0
            )
            if extras["tie_mass_delta"] <= 0:
                raise NtbbKRefuse("k0 did not move tie mass")
        if name == "KEY37":
            base = enumerate_joint(mu=params["mu"], r=params["r"], p=params["p"], c=params["c"])
            extras["m3_delta"] = _mass_m(table, lambda m: abs(m) == 3) - _mass_m(
                base, lambda m: abs(m) == 3
            )
            extras["m7_delta"] = _mass_m(table, lambda m: abs(m) == 7) - _mass_m(
                base, lambda m: abs(m) == 7
            )
            if extras["m3_delta"] <= 0 or extras["m7_delta"] <= 0:
                raise NtbbKRefuse("k3/k7 did not move key-number mass")
        if table["N"] > ORACLE_MAX_ENUMERATED_TOTAL:
            raise NtbbKRefuse(
                f"{name} enumerated total {table['N']} > oracle max {ORACLE_MAX_ENUMERATED_TOTAL}"
            )
        results.append(
            {
                "N": table["N"],
                "enumerated_mass": table["enumerated_mass"],
                "enumeration_error": table["enumeration_error"],
                "extras": extras,
                "group": group,
                "moment_bound": table["moments"]["moment_bound"],
                "name": name,
                "params": params,
                "residuals": residuals,
                "status": "PASS",
                "tail_mass": table["tail_mass"],
            }
        )
    if max_n > ORACLE_MAX_ENUMERATED_TOTAL:
        raise NtbbKRefuse(
            f"max enumerated total {max_n} > oracle {ORACLE_MAX_ENUMERATED_TOTAL}"
        )
    return {
        "max_enumerated_total": max_n,
        "n_cases": len(results),
        "oracle_max_enumerated_total": ORACLE_MAX_ENUMERATED_TOTAL,
        "oracle_max_enumerated_total_honored": max_n <= ORACLE_MAX_ENUMERATED_TOTAL,
        "results": results,
        "status": "PASS",
    }
