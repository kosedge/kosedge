"""lgamma / log-sum-exp / NB / beta-binomial. No SciPy. CERT=0."""

from __future__ import annotations

import math
from typing import Iterable, Sequence

from src.services.nfl_ntbb_k_v1.refuse import NtbbKRefuse


def _finite(x: float, *, name: str) -> float:
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        raise NtbbKRefuse(f"{name} bad type {type(x).__name__}")
    value = float(x)
    if not math.isfinite(value):
        raise NtbbKRefuse(f"{name} nonfinite")
    return value


def logsumexp(xs: Sequence[float]) -> float:
    if not xs:
        raise NtbbKRefuse("logsumexp empty")
    finite = [_finite(x, name="logsumexp") for x in xs]
    top = max(finite)
    if top == -math.inf:
        return -math.inf
    acc = 0.0
    for x in finite:
        acc += math.exp(x - top)
    return top + math.log(acc)


def log_beta(x: float, y: float) -> float:
    a = _finite(x, name="beta.x")
    b = _finite(y, name="beta.y")
    if a <= 0 or b <= 0:
        raise NtbbKRefuse("beta arguments must be > 0")
    return math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)


def log_choose(n: int, k: int) -> float:
    if n < 0 or k < 0 or k > n:
        raise NtbbKRefuse("choose domain")
    if k == 0 or k == n:
        return 0.0
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)


def log_nbinom_pmf(t: int, *, r: float, mu: float) -> float:
    """SciPy nbinom(n=r, p=r/(r+mu)) log PMF. Failures-before-r-successes."""
    if isinstance(t, bool) or not isinstance(t, int) or t < 0:
        raise NtbbKRefuse("nbinom t must be nonnegative int")
    rr = _finite(r, name="r")
    mm = _finite(mu, name="mu")
    if rr <= 0 or mm <= 0:
        raise NtbbKRefuse("nbinom requires r>0 mu>0")
    p = rr / (rr + mm)
    # q(t)=Gamma(t+r)/(Gamma(r)Gamma(t+1)) * p^r * (1-p)^t
    return (
        math.lgamma(t + rr)
        - math.lgamma(rr)
        - math.lgamma(t + 1)
        + rr * math.log(p)
        + t * math.log(1.0 - p)
    )


def nbinom_pmf_series(*, r: float, mu: float, t_max: int) -> list[float]:
    rr = _finite(r, name="r")
    mm = _finite(mu, name="mu")
    if rr <= 0 or mm <= 0:
        raise NtbbKRefuse("nbinom requires r>0 mu>0")
    if t_max < 0:
        raise NtbbKRefuse("t_max negative")
    p = rr / (rr + mm)
    log_q = rr * math.log(p)
    out: list[float] = []
    for t in range(t_max + 1):
        out.append(math.exp(log_q))
        log_q += math.log(t + rr) - math.log(t + 1.0) + math.log(1.0 - p)
    return out


def nbinom_sf(*, r: float, mu: float, n: int) -> float:
    """P(T > n) by 1 - fsum(pmf 0..n). n>=-1; n=-1 => 1."""
    if isinstance(n, bool) or not isinstance(n, int) or n < -1:
        raise NtbbKRefuse("sf n must be int >= -1")
    if n == -1:
        return 1.0
    terms = nbinom_pmf_series(r=r, mu=mu, t_max=n)
    cdf = math.fsum(terms)
    sf = 1.0 - cdf
    if not math.isfinite(sf):
        raise NtbbKRefuse("nbinom sf nonfinite")
    return max(0.0, sf)


def log_betabinom_pmf(h: int, t: int, *, alpha: float, beta: float) -> float:
    if any(isinstance(x, bool) or not isinstance(x, int) for x in (h, t)):
        raise NtbbKRefuse("betabinom h,t must be int")
    if t < 0 or h < 0 or h > t:
        raise NtbbKRefuse("betabinom domain")
    a = _finite(alpha, name="alpha")
    b = _finite(beta, name="beta")
    if a <= 0 or b <= 0:
        raise NtbbKRefuse("alpha,beta must be > 0")
    return log_choose(t, h) + log_beta(h + a, t - h + b) - log_beta(a, b)


def require_prob_params(*, mu: float, r: float, p: float, c: float) -> tuple[float, float, float, float]:
    mu_v = _finite(mu, name="mu")
    r_v = _finite(r, name="r")
    p_v = _finite(p, name="p")
    c_v = _finite(c, name="c")
    if mu_v <= 0 or r_v <= 0 or c_v <= 0:
        raise NtbbKRefuse("mu,r,c must be > 0")
    if not (0.0 < p_v < 1.0):
        raise NtbbKRefuse("p must be in (0,1)")
    return mu_v, r_v, p_v, c_v


def fsum(xs: Iterable[float]) -> float:
    return math.fsum(xs)
