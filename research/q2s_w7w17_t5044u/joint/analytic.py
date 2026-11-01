"""Exact left-censored N(μ,σ) at 0. No scipy."""

from __future__ import annotations

import math

import numpy as np

_SQRT2 = math.sqrt(2.0)
_SQRT2PI = math.sqrt(2.0 * math.pi)


def phi(z: float) -> float:
    return math.exp(-0.5 * float(z) * float(z)) / _SQRT2PI


def Phi(z: float) -> float:
    return 0.5 * (1.0 + math.erf(float(z) / _SQRT2))


def censored_mean(mu: float, sigma: float) -> float:
    """E[max(0, N(mu, sigma))]."""
    if sigma <= 0.0 or not math.isfinite(mu) or not math.isfinite(sigma):
        raise ValueError("nonfinite or nonpositive sigma")
    a = float(mu) / float(sigma)
    return float(mu) * Phi(a) + float(sigma) * phi(a)


def censored_second(mu: float, sigma: float) -> float:
    if sigma <= 0.0 or not math.isfinite(mu) or not math.isfinite(sigma):
        raise ValueError("nonfinite or nonpositive sigma")
    a = float(mu) / float(sigma)
    return (float(mu) ** 2 + float(sigma) ** 2) * Phi(a) + float(mu) * float(sigma) * phi(a)


def censored_var(mu: float, sigma: float) -> float:
    m = censored_mean(mu, sigma)
    return censored_second(mu, sigma) - m * m


def censored_sd(mu: float, sigma: float) -> float:
    return math.sqrt(max(0.0, censored_var(mu, sigma)))


def floor_mass(mu: float, sigma: float) -> float:
    return Phi(-float(mu) / float(sigma))


def p_tie(mu_h: float, mu_a: float, sigma: float) -> float:
    """P(H'=A'=0) = P(H0≤0, A0≤0)."""
    return floor_mass(mu_h, sigma) * floor_mass(mu_a, sigma)


def p_margin_positive(mu_h: float, mu_a: float, sigma: float) -> float:
    """Exact P(D'>0)=P(H'>A') for independent left-censored normals.

    Equals ∫_0^∞ Φ((h−μa)/σ) φ((h−μh)/σ)/σ dh
    (includes the A-censored, H-uncensored mass).
    """
    if sigma <= 0.0:
        raise ValueError("sigma <= 0")
    lo = 0.0
    hi = max(0.0, float(mu_h)) + 12.0 * float(sigma)
    xs, ws = np.polynomial.legendre.leggauss(160)
    mid = 0.5 * (hi + lo)
    half = 0.5 * (hi - lo)
    h = mid + half * xs
    z_h = (h - float(mu_h)) / float(sigma)
    dens = np.exp(-0.5 * z_h * z_h) / _SQRT2PI / float(sigma)
    z_a = (h - float(mu_a)) / float(sigma)
    cdf_a = 0.5 * (1.0 + np.vectorize(math.erf)(z_a / _SQRT2))
    return float(np.dot(ws, cdf_a * dens) * half)


def analytic_pair(mu_h: float, mu_a: float, sigma: float) -> dict[str, float]:
    eh = censored_mean(mu_h, sigma)
    ea = censored_mean(mu_a, sigma)
    vh = censored_var(mu_h, sigma)
    va = censored_var(mu_a, sigma)
    return {
        "mean_H": eh,
        "mean_A": ea,
        "mean_D": eh - ea,
        "mean_S": eh + ea,
        "sd_H": math.sqrt(max(0.0, vh)),
        "sd_A": math.sqrt(max(0.0, va)),
        "sd_D": math.sqrt(max(0.0, vh + va)),
        "sd_S": math.sqrt(max(0.0, vh + va)),
        "var_H": vh,
        "var_A": va,
        "cov_MT": vh - va,
        "floor_H": floor_mass(mu_h, sigma),
        "floor_A": floor_mass(mu_a, sigma),
        "p_tie": p_tie(mu_h, mu_a, sigma),
        "p_D_pos": p_margin_positive(mu_h, mu_a, sigma),
        "analytic_rho_HA": 0.0,
    }
