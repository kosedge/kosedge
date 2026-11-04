"""NTBB-K joint law + conditional normalizer. CERT=0. Synthetic only."""

from __future__ import annotations

import math
from typing import Any

from src.services.nfl_ntbb_k_v1.refuse import NtbbKRefuse
from src.services.nfl_ntbb_k_v1.special import (
    _finite,
    log_betabinom_pmf,
    log_nbinom_pmf,
    logsumexp,
    require_prob_params,
)


def _require_score(x: Any, *, name: str) -> int:
    if isinstance(x, bool) or not isinstance(x, int):
        raise NtbbKRefuse(f"{name} must be a nonnegative int, not {type(x).__name__}")
    if x < 0:
        raise NtbbKRefuse(f"{name} negative")
    return x


def _require_finite_k(k0: Any, k3: Any, k7: Any) -> tuple[float, float, float]:
    out = []
    for name, raw in (("k0", k0), ("k3", k3), ("k7", k7)):
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise NtbbKRefuse(f"{name} bad type")
        value = float(raw)
        if not math.isfinite(value):
            raise NtbbKRefuse(f"{name} nonfinite")
        out.append(value)
    return out[0], out[1], out[2]


def tilt_z(h: int, t: int, *, k0: float, k3: float, k7: float) -> float:
    margin = 2 * h - t
    # Spec: indicators are disjoint.
    if margin == 0:
        return k0
    if abs(margin) == 3:
        return k3
    if abs(margin) == 7:
        return k7
    return 0.0


def conditional_log_mass(
    t: int,
    *,
    p: float,
    c: float,
    k0: float,
    k3: float,
    k7: float,
) -> list[float]:
    """log P(H=h | T=t) for h=0..t after key-number tilt / Z_t."""
    tt = _require_score(t, name="t")
    p_v = _finite(p, name="p")
    c_v = _finite(c, name="c")
    k0_v, k3_v, k7_v = _require_finite_k(k0, k3, k7)
    if not (0.0 < p_v < 1.0) or c_v <= 0:
        raise NtbbKRefuse("conditional p,c invalid")
    alpha = p_v * c_v
    beta = (1.0 - p_v) * c_v
    if not math.isfinite(alpha) or not math.isfinite(beta) or alpha <= 0 or beta <= 0:
        raise NtbbKRefuse("UNSUPPORTED_NUMERIC_DOMAIN alpha/beta")
    if tt == 0:
        # Conditional mass is exactly one; tie tilt does not change q(0).
        return [0.0]
    log_unnorm: list[float] = []
    for h in range(tt + 1):
        log_b = log_betabinom_pmf(h, tt, alpha=alpha, beta=beta)
        z = tilt_z(h, tt, k0=k0_v, k3=k3_v, k7=k7_v)
        log_unnorm.append(log_b + z)
    log_z = logsumexp(log_unnorm)
    return [x - log_z for x in log_unnorm]


def log_joint_pmf(
    h: Any,
    a: Any,
    *,
    mu: float,
    r: float,
    p: float,
    c: float,
    k0: float = 0.0,
    k3: float = 0.0,
    k7: float = 0.0,
) -> float:
    """Exact pointwise log P(H=h,A=a). Uses full conditional normalizer. No truncate."""
    hh = _require_score(h, name="h")
    aa = _require_score(a, name="a")
    mu_v, r_v, p_v, c_v = require_prob_params(mu=mu, r=r, p=p, c=c)
    k0_v, k3_v, k7_v = _require_finite_k(k0, k3, k7)
    t = hh + aa
    log_q = log_nbinom_pmf(t, r=r_v, mu=mu_v)
    log_cond = conditional_log_mass(t, p=p_v, c=c_v, k0=k0_v, k3=k3_v, k7=k7_v)
    return log_q + log_cond[hh]


def joint_pmf(h: Any, a: Any, **params: float) -> float:
    return math.exp(log_joint_pmf(h, a, **params))
