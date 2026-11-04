"""lgamma / log-sum-exp / NB / beta-binomial. No SciPy. CERT=0."""

from __future__ import annotations

import math
from typing import Any, Iterable, Sequence

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


def nbinom_success_p(*, r: float, mu: float) -> tuple[float, float]:
    """p=r/(r+mu), q=mu/(r+mu). Refuse domains that collapse in float64."""
    rr = _finite(r, name="r")
    mm = _finite(mu, name="mu")
    if rr <= 0 or mm <= 0:
        raise NtbbKRefuse("nbinom requires r>0 mu>0")
    total = rr + mm
    if total == rr or total == mm:
        raise NtbbKRefuse("UNSUPPORTED_NUMERIC_DOMAIN r+mu lost a summand")
    p = rr / total
    q = mm / total
    if not (0.0 < p < 1.0 and 0.0 < q < 1.0):
        raise NtbbKRefuse("UNSUPPORTED_NUMERIC_DOMAIN p")
    if p + q == p or p + q == q:
        raise NtbbKRefuse("UNSUPPORTED_NUMERIC_DOMAIN p+q")
    return p, q


def log_nbinom_pmf_np(t: int, *, n: float, p: float, q: float) -> float:
    if isinstance(t, bool) or not isinstance(t, int) or t < 0:
        raise NtbbKRefuse("nbinom t must be nonnegative int")
    nn = _finite(n, name="n_success")
    pp = _finite(p, name="p")
    qq = _finite(q, name="q")
    if nn <= 0 or not (0.0 < pp < 1.0) or not (0.0 < qq < 1.0):
        raise NtbbKRefuse("nbinom npq invalid")
    try:
        value = (
            math.lgamma(t + nn)
            - math.lgamma(nn)
            - math.lgamma(t + 1)
            + nn * math.log(pp)
            + t * math.log(qq)
        )
    except ValueError as exc:
        raise NtbbKRefuse("UNSUPPORTED_NUMERIC_DOMAIN lgamma") from exc
    if not math.isfinite(value):
        raise NtbbKRefuse("UNSUPPORTED_NUMERIC_DOMAIN logpmf nonfinite")
    return value


def log_nbinom_pmf(t: int, *, r: float, mu: float) -> float:
    """SciPy nbinom(n=r, p=r/(r+mu)) log PMF. Failures-before-r-successes."""
    p, q = nbinom_success_p(r=r, mu=mu)
    return log_nbinom_pmf_np(t, n=r, p=p, q=q)


def nbinom_pmf_series(*, r: float, mu: float, t_max: int) -> list[float]:
    p, q = nbinom_success_p(r=r, mu=mu)
    if t_max < 0:
        raise NtbbKRefuse("t_max negative")
    log_q = _finite(r, name="r") * math.log(p)
    out: list[float] = []
    rr = _finite(r, name="r")
    for t in range(t_max + 1):
        term = math.exp(log_q)
        if not math.isfinite(term):
            raise NtbbKRefuse("UNSUPPORTED_NUMERIC_DOMAIN pmf overflow")
        out.append(term)
        log_q += math.log(t + rr) - math.log(t + 1.0) + math.log(q)
    return out


def remaining_series_tail(*, n_success: float, p: float, q: float, cutoff: int) -> dict[str, Any]:
    """P(X>cutoff) via remaining-series bound. Not 1−CDF.

    Ratio at index t is (t+n)/(t+1)*q. Geometric remainder is valid only
    after demonstrating a ratio bound ρ<1 over remaining terms.
    """
    if isinstance(cutoff, bool) or not isinstance(cutoff, int) or cutoff < -1:
        raise NtbbKRefuse("tail cutoff must be int >= -1")
    if cutoff == -1:
        return {"estimate": 1.0, "lower": 1.0, "rho": None, "upper": 1.0}
    nn = _finite(n_success, name="n_success")
    pp = _finite(p, name="p")
    qq = _finite(q, name="q")
    rho = ((cutoff + 1 + nn) / (cutoff + 2)) * qq
    if not math.isfinite(rho) or rho <= 0:
        raise NtbbKRefuse("UNSUPPORTED_NUMERIC_DOMAIN tail ratio")
    if rho >= 1.0:
        return {"estimate": None, "lower": 0.0, "rho": rho, "upper": None}
    log_first = log_nbinom_pmf_np(cutoff + 1, n=nn, p=pp, q=qq)
    first = math.exp(log_first)
    if not math.isfinite(first):
        raise NtbbKRefuse("UNSUPPORTED_NUMERIC_DOMAIN tail first term")
    upper = first / (1.0 - rho)
    extra_limit = 4096
    acc: list[float] = []
    log_term = log_first
    t = cutoff + 1
    for _ in range(extra_limit):
        term = math.exp(log_term)
        if not math.isfinite(term):
            raise NtbbKRefuse("UNSUPPORTED_NUMERIC_DOMAIN tail term")
        acc.append(term)
        if term < 1e-22 and t > cutoff + 4:
            break
        log_term += math.log(t + nn) - math.log(t + 1.0) + math.log(qq)
        t += 1
    lower = math.fsum(acc)
    last_t = cutoff + len(acc)
    rho_last = ((last_t + 1 + nn) / (last_t + 2)) * qq
    if not (0.0 < rho_last < 1.0):
        raise NtbbKRefuse("NUMERICAL_TAIL_LIMIT remaining ratio >= 1")
    rem = math.exp(log_nbinom_pmf_np(last_t + 1, n=nn, p=pp, q=qq)) / (1.0 - rho_last)
    estimate = lower + rem
    return {
        "estimate": min(1.0, estimate),
        "lower": min(1.0, lower),
        "rho": rho,
        "upper": min(1.0, max(upper, lower + rem)),
    }


def nbinom_tail(*, r: float, mu: float, cutoff: int) -> dict[str, Any]:
    p, q = nbinom_success_p(r=r, mu=mu)
    return remaining_series_tail(n_success=r, p=p, q=q, cutoff=cutoff)


def nbinom_sf(*, r: float, mu: float, n: int) -> float:
    """Deprecated alias: remaining-series estimate, not 1−CDF."""
    tail = nbinom_tail(r=r, mu=mu, cutoff=n)
    if tail["estimate"] is None:
        raise NtbbKRefuse("NUMERICAL_TAIL_LIMIT no geometric bound")
    return float(tail["estimate"])


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
