"""Finite joint table + tail/moment contract. CERT=0. No silent renormalize."""

from __future__ import annotations

import math
from typing import Any

from src.services.nfl_ntbb_k_v1.constants import (
    CAP_T,
    MASS_PLUS_TAIL_TOL,
    MOMENT_BOUND_MAX,
    TAIL_SF_MAX,
)
from src.services.nfl_ntbb_k_v1.law import _require_finite_k, conditional_log_mass
from src.services.nfl_ntbb_k_v1.refuse import NtbbKRefuse
from src.services.nfl_ntbb_k_v1.special import (
    fsum,
    nbinom_pmf_series,
    nbinom_sf,
    require_prob_params,
)


def choose_tail_n(*, r: float, mu: float) -> int:
    """First N<=512 with P(T>N)<=1e-12. Else NUMERICAL_TAIL_LIMIT."""
    terms = nbinom_pmf_series(r=r, mu=mu, t_max=CAP_T)
    running: list[float] = []
    for t, q in enumerate(terms):
        running.append(q)
        sf = 1.0 - fsum(running)
        if sf <= TAIL_SF_MAX:
            return t
    raise NtbbKRefuse("NUMERICAL_TAIL_LIMIT")


def moment_bound(*, mu: float, r: float, n: int) -> float:
    """mu * P(NB(r+1, p_nb) > N-1), p_nb=r/(r+mu). Spec identity."""
    if n < 0:
        raise NtbbKRefuse("moment N negative")
    # NB(r+1, p) with same p=r/(r+mu) has mean (r+1)*mu/r
    # Spec writes P(NB(r+1,p_nb)>N-1). Implement mu_shift via r' = r+1, same mu_nb?
    # scipy nbinom(n=r+1, p=r/(r+mu)): mean=(r+1)*(1-p)/p = (r+1)*mu/r
    # Survival uses that law. Our nbinom_sf(r=r+1, mu=mu_alt) needs E[T]=(r+1)*mu/r
    mu_shift = (r + 1.0) * mu / r
    return mu * nbinom_sf(r=r + 1.0, mu=mu_shift, n=n - 1)


def enumerate_joint(
    *,
    mu: float,
    r: float,
    p: float,
    c: float,
    k0: float = 0.0,
    k3: float = 0.0,
    k7: float = 0.0,
) -> dict[str, Any]:
    mu_v, r_v, p_v, c_v = require_prob_params(mu=mu, r=r, p=p, c=c)
    k0_v, k3_v, k7_v = _require_finite_k(k0, k3, k7)
    n = choose_tail_n(r=r_v, mu=mu_v)
    q_terms = nbinom_pmf_series(r=r_v, mu=mu_v, t_max=n)
    tail_mass = nbinom_sf(r=r_v, mu=mu_v, n=n)
    rows: list[dict[str, Any]] = []
    masses: list[float] = []
    for t, q in enumerate(q_terms):
        log_cond = conditional_log_mass(t, p=p_v, c=c_v, k0=k0_v, k3=k3_v, k7=k7_v)
        for h, log_c in enumerate(log_cond):
            mass = q * math.exp(log_c)
            a = t - h
            rows.append(
                {
                    "a": a,
                    "h": h,
                    "m": h - a,
                    "mass": mass,
                    "t": t,
                }
            )
            masses.append(mass)
    enumerated = fsum(masses)
    enumeration_error = enumerated + tail_mass - 1.0
    if abs(enumeration_error) > MASS_PLUS_TAIL_TOL:
        raise NtbbKRefuse(
            f"mass+tail refuse |{enumeration_error}| > {MASS_PLUS_TAIL_TOL}"
        )
    bound = moment_bound(mu=mu_v, r=r_v, n=n)
    moments: dict[str, Any]
    if bound > MOMENT_BOUND_MAX:
        moments = {
            "moment_bound": bound,
            "status": "REFUSED_MOMENT",
            "total_mean": None,
            "margin_mean": None,
        }
    else:
        total_mean = fsum(row["t"] * row["mass"] for row in rows)
        margin_mean = fsum(row["m"] * row["mass"] for row in rows)
        moments = {
            "margin_mean": margin_mean,
            "moment_bound": bound,
            "status": "OK",
            "total_mean": total_mean,
        }
    return {
        "N": n,
        "cap": CAP_T,
        "enumerated_mass": enumerated,
        "enumeration_error": enumeration_error,
        "moments": moments,
        "n_rows": len(rows),
        "params": {
            "c": c_v,
            "k0": k0_v,
            "k3": k3_v,
            "k7": k7_v,
            "mu": mu_v,
            "p": p_v,
            "r": r_v,
        },
        "renormalized": False,
        "rows": rows,
        "tail_mass": tail_mass,
    }


def event_interval(enumerated_mass: float, tail_mass: float) -> tuple[float, float]:
    """Consumer interval [event mass, event mass + tail_mass]. Not exact lost-mass values."""
    if enumerated_mass < 0 or tail_mass < 0:
        raise NtbbKRefuse("interval masses must be >= 0")
    return (enumerated_mass, enumerated_mass + tail_mass)


def summarize_spread(table: dict[str, Any], d_text: str) -> dict[str, Any]:
    """Home handicap d as exact integer/half-integer decimal string."""
    d = _parse_line(d_text, name="spread_d")
    win = push = loss = 0.0
    for row in table["rows"]:
        s = row["h"] - row["a"] + d
        if s > 0:
            win += row["mass"]
        elif s == 0:
            push += row["mass"]
        else:
            loss += row["mass"]
    return {
        "d": d_text,
        "intervals": {
            "loss": event_interval(loss, table["tail_mass"]),
            "push": event_interval(push, table["tail_mass"]),
            "win": event_interval(win, table["tail_mass"]),
        },
        "loss": loss,
        "push": push,
        "side": "home",
        "win": win,
    }


def summarize_total(table: dict[str, Any], l_text: str) -> dict[str, Any]:
    line = _parse_line(l_text, name="total_L")
    over = push = under = 0.0
    for row in table["rows"]:
        s = row["h"] + row["a"] - line
        if s > 0:
            over += row["mass"]
        elif s == 0:
            push += row["mass"]
        else:
            under += row["mass"]
    return {
        "L": l_text,
        "intervals": {
            "over": event_interval(over, table["tail_mass"]),
            "push": event_interval(push, table["tail_mass"]),
            "under": event_interval(under, table["tail_mass"]),
        },
        "over": over,
        "push": push,
        "under": under,
    }


def refuse_unknown_settlement(*, period: Any = None, ot: Any = None, tie: Any = None) -> None:
    raise NtbbKRefuse("unknown period/OT/tie settlement refuses settled moneyline/fair odds/EV")


def _parse_line(text: str, *, name: str) -> float:
    if not isinstance(text, str):
        raise NtbbKRefuse(f"{name} must be a decimal string")
    raw = text.strip()
    if raw.count(".") > 1:
        raise NtbbKRefuse(f"{name} bad decimal")
    if "." in raw:
        whole, frac = raw.split(".")
        if frac not in {"0", "5"}:
            raise NtbbKRefuse(f"{name} must be integer or half-integer")
        if whole in {"", "-", "+"}:
            raise NtbbKRefuse(f"{name} bad decimal")
    try:
        value = float(raw)
    except ValueError as exc:
        raise NtbbKRefuse(f"{name} not a number") from exc
    if not math.isfinite(value):
        raise NtbbKRefuse(f"{name} nonfinite")
    twice = value * 2.0
    if abs(twice - round(twice)) > 1e-12:
        raise NtbbKRefuse(f"{name} must be integer or half-integer")
    return value
