"""nfl-research-opp-adj-epa-v0-ridge-joint (Exp A, t4602u).

Research-only fork of CFB ``research_opp_adj.fit_joint`` math. Does not import
``simulate_nfl_game``, ``LOCKED_SCORING``, or ``config_overrides``.

Model (team-game grain, emit-eligible plays):

    y_{g,i} = μ + h · home_{g,i} + off_i + def_j + ε

Ridge toward a prior with ``n0`` game-equivalents (no extra play-weight λ).
League off/def centered. Rating-model ``h`` is INTERNAL and is never added
into ``rating_diff_home`` / ``margin_A``.

Observation weight of a game k weeks old = ρ^k (ACK 6fcc0af6).
Week-1 prior = ρ_s · prior-season posterior, league-centered.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np

ESTIMATOR_ID = "nfl-research-opp-adj-epa-v0-ridge-joint"
RESEARCH_ONLY = True
NOT_KE_RATINGS = True
DEFAULT_ITERS = 12
N0_BASE = 4.0

# Product 32-team set (aliases applied upstream).
CANONICAL_TEAMS: Tuple[str, ...] = (
    "ARI",
    "ATL",
    "BAL",
    "BUF",
    "CAR",
    "CHI",
    "CIN",
    "CLE",
    "DAL",
    "DEN",
    "DET",
    "GB",
    "HOU",
    "IND",
    "JAX",
    "KC",
    "LAC",
    "LAR",
    "LV",
    "MIA",
    "MIN",
    "NE",
    "NO",
    "NYG",
    "NYJ",
    "PHI",
    "PIT",
    "SEA",
    "SF",
    "TB",
    "TEN",
    "WAS",
)
TEAM_INDEX: Dict[str, int] = {t: i for i, t in enumerate(CANONICAL_TEAMS)}
N_TEAMS = len(CANONICAL_TEAMS)


@dataclass(frozen=True)
class RidgeParams:
    n0: float
    rho: float
    rho_s: float
    iters: int = DEFAULT_ITERS


@dataclass
class FitState:
    off: np.ndarray
    deff: np.ndarray
    mu: float
    hfa_internal: float
    n_obs: int


def _center(off: np.ndarray, deff: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    off = off - float(np.mean(off))
    deff = deff - float(np.mean(deff))
    return off, deff


def _wls_mu_h(resid: np.ndarray, home: np.ndarray, w: np.ndarray) -> Tuple[float, float]:
    """Weighted OLS of resid ~ μ + h·home (joint, not sequential)."""
    sw = float(np.sum(w))
    if sw <= 0.0:
        return 0.0, 0.0
    sx = float(np.sum(w * home))
    sy = float(np.sum(w * resid))
    sxx = float(np.sum(w * home * home))
    sxy = float(np.sum(w * home * resid))
    det = sw * sxx - sx * sx
    if abs(det) < 1e-12:
        return (sy / sw), 0.0
    mu = (sxx * sy - sx * sxy) / det
    hfa = (sw * sxy - sx * sy) / det
    return float(mu), float(hfa)


def fit_joint(
    y: np.ndarray,
    home: np.ndarray,
    off_idx: np.ndarray,
    def_idx: np.ndarray,
    weight: np.ndarray,
    *,
    prior_off: np.ndarray,
    prior_def: np.ndarray,
    n0: float,
    iters: int = DEFAULT_ITERS,
) -> FitState:
    """Joint ridge: offense + opposing defense + internal μ/h. ``n0`` game-eq."""
    n_teams = int(prior_off.shape[0])
    if y.size == 0 or float(np.sum(weight)) <= 0.0:
        off, deff = _center(prior_off.copy(), prior_def.copy())
        return FitState(off=off, deff=deff, mu=0.0, hfa_internal=0.0, n_obs=0)

    off = prior_off.copy()
    deff = prior_def.copy()
    off, deff = _center(off, deff)
    mu = 0.0
    hfa = 0.0
    n0 = float(n0)

    for _ in range(max(1, int(iters))):
        resid = y - off[off_idx] - deff[def_idx]
        mu, hfa = _wls_mu_h(resid, home, weight)
        target = y - mu - hfa * home
        contrib_o = weight * (target - deff[def_idx])
        contrib_d = weight * (target - off[off_idx])
        n_o = np.bincount(off_idx, contrib_o, minlength=n_teams).astype(np.float64)
        n_d = np.bincount(def_idx, contrib_d, minlength=n_teams).astype(np.float64)
        d_o = np.bincount(off_idx, weight, minlength=n_teams).astype(np.float64)
        d_d = np.bincount(def_idx, weight, minlength=n_teams).astype(np.float64)
        ng_o = np.bincount(off_idx, minlength=n_teams).astype(np.float64)
        ng_d = np.bincount(def_idx, minlength=n_teams).astype(np.float64)
        n0_o = np.where(ng_o > 0.0, n0 * (d_o / ng_o), 0.0)
        n0_d = np.where(ng_d > 0.0, n0 * (d_d / ng_d), 0.0)
        den_o = d_o + n0_o
        den_d = d_d + n0_d
        off = np.where(den_o > 0.0, (n_o + n0_o * prior_off) / den_o, prior_off)
        deff = np.where(den_d > 0.0, (n_d + n0_d * prior_def) / den_d, prior_def)
        off, deff = _center(off, deff)

    return FitState(off=off, deff=deff, mu=float(mu), hfa_internal=float(hfa), n_obs=int(y.size))


def shrink_offseason(off: np.ndarray, deff: np.ndarray, rho_s: float) -> Tuple[np.ndarray, np.ndarray]:
    """Week-1 prior = ρ_s · prior-season posterior, league-centered."""
    return _center(float(rho_s) * off, float(rho_s) * deff)


def rating_diff_home(
    off: np.ndarray,
    deff: np.ndarray,
    home_idx: int,
    away_idx: int,
) -> float:
    """EPA/play advantage for home. Does NOT include rating-model h or μ."""
    return float((off[home_idx] + deff[away_idx]) - (off[away_idx] + deff[home_idx]))


def week_weight(rho: float, week_target: int, week_game: int) -> float:
    k = int(week_target) - int(week_game)
    if k < 0:
        k = 0
    return float(rho) ** float(k)


def ols_point(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Unweighted OLS, no ridge. ``x`` is (n, k) design (caller adds intercept)."""
    xtx = x.T @ x
    xty = x.T @ y
    try:
        return np.linalg.solve(xtx, xty)
    except np.linalg.LinAlgError:
        return np.linalg.lstsq(x, y, rcond=None)[0]


def ols_hc1(x: np.ndarray, y: np.ndarray) -> Dict[str, np.ndarray]:
    """OLS with HC1 sandwich SEs. Returns beta, se, resid, n, k."""
    n, k = int(x.shape[0]), int(x.shape[1])
    beta = ols_point(x, y)
    resid = y - x @ beta
    meat = x.T @ ((resid * resid)[:, None] * x)
    try:
        xtx_inv = np.linalg.inv(x.T @ x)
    except np.linalg.LinAlgError:
        xtx_inv = np.linalg.pinv(x.T @ x)
    scale = n / max(n - k, 1)
    var = scale * (xtx_inv @ meat @ xtx_inv)
    se = np.sqrt(np.maximum(np.diag(var), 0.0))
    return {"beta": beta, "se": se, "resid": resid, "n": n, "k": k, "var": var}


def hc1_ci(beta: float, se: float, z: float = 1.96) -> Tuple[float, float]:
    return float(beta - z * se), float(beta + z * se)


def fit_beta_fold(
    rating_diff: np.ndarray,
    actual_margin: np.ndarray,
    home_indicator: np.ndarray,
    *,
    hfa_mode: str,
) -> Dict[str, float]:
    """ONE fold-fit β. Intercept-free when HFA=off. Neutral rows have home_ind=0."""
    y = np.asarray(actual_margin, dtype=np.float64)
    rd = np.asarray(rating_diff, dtype=np.float64)
    if hfa_mode == "off":
        x = rd.reshape(-1, 1)
        fit = ols_hc1(x, y)
        beta = float(fit["beta"][0])
        se = float(fit["se"][0])
        hfa = 0.0
        hfa_se = 0.0
    elif hfa_mode == "fold_fit":
        x = np.column_stack([rd, np.asarray(home_indicator, dtype=np.float64)])
        fit = ols_hc1(x, y)
        beta = float(fit["beta"][0])
        se = float(fit["se"][0])
        hfa = float(fit["beta"][1])
        hfa_se = float(fit["se"][1])
    else:
        raise ValueError(f"unknown hfa_mode={hfa_mode!r}")
    lo, hi = hc1_ci(beta, se)
    return {
        "beta": beta,
        "beta_se_hc1": se,
        "beta_ci95_lo": lo,
        "beta_ci95_hi": hi,
        "hfa": hfa,
        "hfa_se_hc1": hfa_se,
        "n": int(fit["n"]),
        "k": int(fit["k"]),
    }


def predict_margin_a(
    rating_diff: np.ndarray,
    home_indicator: np.ndarray,
    *,
    beta: float,
    hfa: float,
) -> np.ndarray:
    """margin_A = β · rating_diff_home + HFA. HFA=0 at neutral (home_ind=0)."""
    return float(beta) * np.asarray(rating_diff, dtype=np.float64) + float(hfa) * np.asarray(
        home_indicator, dtype=np.float64
    )


def select_cell(
    cells: Sequence[Mapping[str, object]],
    *,
    epsilon: float = 1e-9,
) -> Mapping[str, object]:
    """L1: min inner-CV MAE; ties |ΔMAE|<ε → HFA off, then ρ=0.95, λ=1, ρ_s=0.67."""
    if not cells:
        raise ValueError("empty grid")
    best_mae = min(float(c["mae"]) for c in cells)
    tied = [c for c in cells if abs(float(c["mae"]) - best_mae) < float(epsilon)]

    def _key(c: Mapping[str, object]) -> Tuple:
        return (
            0 if str(c["hfa_mode"]) == "off" else 1,
            abs(float(c["rho"]) - 0.95),
            abs(float(c["lambda"]) - 1.0),
            abs(float(c["rho_s"]) - 0.67),
            str(c.get("cfg_id", "")),
        )

    return sorted(tied, key=_key)[0]


def self_check() -> None:
    """Tiny numeric guards. Not an Exp A run."""
    rng = np.random.default_rng(4141)
    n = 64
    off_idx = np.array([0, 1] * (n // 2), dtype=np.int64)
    def_idx = np.array([1, 0] * (n // 2), dtype=np.int64)
    home = np.array([1.0, 0.0] * (n // 2), dtype=np.float64)
    y = 0.05 * home + np.where(off_idx == 0, 0.12, -0.04) + 0.02 * rng.normal(size=n)
    w = np.ones(n)
    prior = np.zeros(2)
    fit = fit_joint(y, home, off_idx, def_idx, w, prior_off=prior, prior_def=prior, n0=4.0)
    assert fit.off[0] > fit.off[1], (fit.off, fit.deff)
    rd = np.linspace(-0.2, 0.2, 40)
    m = 15.0 * rd + rng.normal(0.0, 0.01, size=40)
    b = fit_beta_fold(rd, m, np.ones(40), hfa_mode="off")
    assert 10.0 < b["beta"] < 20.0, b
    cells = [
        {"cfg_id": "G28", "mae": 10.0, "hfa_mode": "fold_fit", "rho": 0.95, "lambda": 1.0, "rho_s": 0.67},
        {"cfg_id": "G27", "mae": 10.0, "hfa_mode": "off", "rho": 0.95, "lambda": 1.0, "rho_s": 0.67},
    ]
    win = select_cell(cells, epsilon=1e-9)
    assert win["cfg_id"] == "G27", win
    print("[ridge_joint] self_check ok", flush=True)


if __name__ == "__main__":
    self_check()
