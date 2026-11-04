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
    nbinom_success_p,
    nbinom_tail,
    remaining_series_tail,
    require_prob_params,
)


def choose_tail_n(*, r: float, mu: float) -> tuple[int, dict[str, Any]]:
    """First N<=512 whose remaining-series tail upper bound <=1e-12.

    Recomputes diagnostics only for the final N. Not 1−CDF.
    """
    last: dict[str, Any] | None = None
    for n in range(0, CAP_T + 1):
        tail = nbinom_tail(r=r, mu=mu, cutoff=n)
        last = tail
        if tail["upper"] is None:
            continue
        if tail["upper"] <= TAIL_SF_MAX:
            return n, tail
    raise NtbbKRefuse("NUMERICAL_TAIL_LIMIT")


def moment_bound(*, mu: float, r: float, n: int) -> dict[str, Any]:
    """mu * P(NB(r+1, p=r/(r+mu)) > N-1). Same probability, not same mean."""
    if n < 0:
        raise NtbbKRefuse("moment N negative")
    p, q = nbinom_success_p(r=r, mu=mu)
    tail = remaining_series_tail(n_success=r + 1.0, p=p, q=q, cutoff=n - 1)
    if tail["upper"] is None or tail["estimate"] is None:
        raise NtbbKRefuse("NUMERICAL_TAIL_LIMIT moment remaining-series")
    return {
        "bound": mu * float(tail["upper"]),
        "estimate": mu * float(tail["estimate"]),
        "p": p,
        "r_plus_1": r + 1.0,
        "same_mean": False,
        "same_probability": True,
        "tail": tail,
    }


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
    n, tail = choose_tail_n(r=r_v, mu=mu_v)
    q_terms = nbinom_pmf_series(r=r_v, mu=mu_v, t_max=n)
    rows: list[dict[str, Any]] = []
    masses: list[float] = []
    for t, qt in enumerate(q_terms):
        log_cond = conditional_log_mass(t, p=p_v, c=c_v, k0=k0_v, k3=k3_v, k7=k7_v)
        for h, log_c in enumerate(log_cond):
            mass = qt * math.exp(log_c)
            if mass < 0:
                raise NtbbKRefuse("negative row mass")
            if not math.isfinite(mass):
                raise NtbbKRefuse("UNSUPPORTED_NUMERIC_DOMAIN nonfinite mass")
            a = t - h
            rows.append({"a": a, "h": h, "m": h - a, "mass": mass, "t": t})
            masses.append(mass)
    enumerated = fsum(masses)
    tail_lower = float(tail["lower"])
    tail_est = float(tail["estimate"])
    tail_upper = float(tail["upper"])
    enumeration_error = abs(enumerated + tail_est - 1.0)
    if enumeration_error > MASS_PLUS_TAIL_TOL:
        raise NtbbKRefuse(
            f"mass+tail refuse |{enumeration_error}| > {MASS_PLUS_TAIL_TOL}"
        )
    if enumerated + tail_upper + MASS_PLUS_TAIL_TOL < 1.0:
        raise NtbbKRefuse("inconsistent tail upper vs enumerated mass")
    if enumerated + tail_lower - MASS_PLUS_TAIL_TOL > 1.0:
        raise NtbbKRefuse("inconsistent tail lower vs enumerated mass")
    mb = moment_bound(mu=mu_v, r=r_v, n=n)
    bound = mb["bound"]
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
        accuracy = abs(total_mean - mu_v)
        if accuracy > MOMENT_BOUND_MAX + bound:
            raise NtbbKRefuse(
                f"UNSUPPORTED_NUMERIC_DOMAIN moment accuracy {accuracy} > 1e-8+bound"
            )
        moments = {
            "margin_mean": margin_mean,
            "moment_bound": bound,
            "same_probability": True,
            "status": "OK",
            "total_mean": total_mean,
        }
    return {
        "N": n,
        "cap": CAP_T,
        "enumerated_mass": enumerated,
        "enumeration_error": enumeration_error,
        "final_n_diagnostics": {
            "moment": mb,
            "tail_estimate": tail_est,
            "tail_lower": tail_lower,
            "tail_upper": tail_upper,
        },
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
        "tail_mass": tail_est,
        "tail_mass_estimate": tail_est,
        "tail_mass_lower": tail_lower,
        "tail_mass_upper": tail_upper,
    }


def event_interval(enumerated_mass: float, tail_upper_bound: float) -> tuple[float, float]:
    """DESIGN 25194: [max(0, mass), min(1, mass + tail_upper)]."""
    if enumerated_mass < 0 or tail_upper_bound < 0:
        raise NtbbKRefuse("interval masses must be >= 0")
    lo = max(0.0, enumerated_mass)
    hi = min(1.0, enumerated_mass + tail_upper_bound)
    if lo > hi:
        raise NtbbKRefuse("interval lower exceeds upper")
    return (lo, hi)


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
    tail_u = table.get("tail_mass_upper", table["tail_mass"])
    return {
        "d": d_text,
        "intervals": {
            "loss": event_interval(loss, tail_u),
            "push": event_interval(push, tail_u),
            "win": event_interval(win, tail_u),
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
    tail_u = table.get("tail_mass_upper", table["tail_mass"])
    return {
        "L": l_text,
        "intervals": {
            "over": event_interval(over, tail_u),
            "push": event_interval(push, tail_u),
            "under": event_interval(under, tail_u),
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
