"""Research-copy IF joint-score loop + one pre-floor ±d/2 shift.

Does not edit nfl_simulator.py. Imports pinned 52d9e909 / a0051cc4 RO.
"""

from __future__ import annotations

import hashlib
import math
import random
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

JOINT = Path(__file__).resolve().parent
PACKET = JOINT.parent
PHASE4 = PACKET / "phase4"
if str(JOINT) not in sys.path:
    sys.path.insert(0, str(JOINT))
if str(PHASE4) not in sys.path:
    sys.path.insert(0, str(PHASE4))

from pins import (  # noqa: E402
    FW_SHA,
    N_DRAWS,
    SIM_SHA,
    PinRefuse,
    sha256_file,
)
from score_if_w7w17 import (  # noqa: E402
    IF_TREE,
    ScoreRefuse,
    import_if,
    seed_for,
)

from analytic import analytic_pair  # noqa: E402


class JointRefuse(RuntimeError):
    pass


@dataclass
class JointResult:
    game_id: str
    d: float
    seed: int
    N: int
    mu_h: float
    mu_a: float
    mu_h_p: float
    mu_a_p: float
    sigma: float
    H: np.ndarray
    A: np.ndarray
    draw_hash: str
    mean_H: float
    mean_A: float
    mean_D: float
    mean_S: float
    sd_H: float
    sd_A: float
    sd_D: float
    sd_S: float
    corr_HA: float
    cov_MT: float
    var_H: float
    var_A: float
    home_wins: int
    tie_count: int
    home_wp: float
    away_wp: float
    fair_home_ml: int
    fair_away_ml: int
    spread_home: float
    total_raw: float
    floor_emp_H: float
    floor_emp_A: float
    analytic: dict[str, float] = field(default_factory=dict)


def _load_sim() -> Any:
    try:
        sim = import_if()
    except ScoreRefuse as exc:
        raise JointRefuse(str(exc)) from exc
    return sim


def _latent_params(sim: Any, inputs: Any) -> tuple[float, float, float]:
    """Verbatim IF mean/σ construction (simulate_nfl_game l.534–598)."""
    fw = sys.modules["src.services.nfl_handicapping_framework"]
    framework_config = fw.get_nfl_handicapping_config(config_overrides=None)
    matchup_adjustments = sim._build_matchup_adjustments(inputs)
    totals_adjustments = sim._build_totals_adjustments(inputs)
    decomposition = fw.compute_nfl_projection_decomposition(
        offense_index_home=inputs.offense_index_home,
        offense_index_away=inputs.offense_index_away,
        defense_index_home=inputs.defense_index_home,
        defense_index_away=inputs.defense_index_away,
        rest_days_home=inputs.rest_days_home,
        rest_days_away=inputs.rest_days_away,
        matchup_adjustments=matchup_adjustments,
        totals_adjustments=totals_adjustments,
        injury_nowcast_impact_home=inputs.injury_nowcast_impact_home,
        injury_nowcast_impact_away=inputs.injury_nowcast_impact_away,
        injury_nowcast_freshness_home_hours=inputs.injury_nowcast_freshness_home_hours,
        injury_nowcast_freshness_away_hours=inputs.injury_nowcast_freshness_away_hours,
        injury_nowcast_confidence_home=inputs.injury_nowcast_confidence_home,
        injury_nowcast_confidence_away=inputs.injury_nowcast_confidence_away,
        injury_nowcast_offense_multiplier_home=inputs.injury_nowcast_offense_multiplier_home,
        injury_nowcast_offense_multiplier_away=inputs.injury_nowcast_offense_multiplier_away,
        injury_nowcast_defense_multiplier_home=inputs.injury_nowcast_defense_multiplier_home,
        injury_nowcast_defense_multiplier_away=inputs.injury_nowcast_defense_multiplier_away,
        weather_wind_mph=inputs.weather_wind_mph,
        weather_precip_mm=inputs.weather_precip_mm,
        weather_temp_f=inputs.weather_temp_f,
        weather_available=inputs.weather_available,
        travel_miles_home=inputs.travel_miles_home,
        travel_miles_away=inputs.travel_miles_away,
        travel_timezone_delta_home=inputs.travel_timezone_delta_home,
        travel_timezone_delta_away=inputs.travel_timezone_delta_away,
        travel_available=inputs.travel_available,
        home_kav_net_5g=inputs.home_kav_net_5g,
        away_kav_net_5g=inputs.away_kav_net_5g,
        home_kav_offense_5g=inputs.home_kav_offense_5g,
        away_kav_offense_5g=inputs.away_kav_offense_5g,
        home_kav_defense_5g=inputs.home_kav_defense_5g,
        away_kav_defense_5g=inputs.away_kav_defense_5g,
        kav_as_of_week=inputs.kav_as_of_week,
        home_personnel_edge_5g=inputs.home_personnel_edge_5g,
        away_personnel_edge_5g=inputs.away_personnel_edge_5g,
        home_sub_elasticity_5g=inputs.home_sub_elasticity_5g,
        away_sub_elasticity_5g=inputs.away_sub_elasticity_5g,
        home_coach_aggression_5g=inputs.home_coach_aggression_5g,
        away_coach_aggression_5g=inputs.away_coach_aggression_5g,
        home_coach_pace_5g=inputs.home_coach_pace_5g,
        away_coach_pace_5g=inputs.away_coach_pace_5g,
        second_order_as_of_week=inputs.second_order_as_of_week,
        info_velocity_home=inputs.info_velocity_home,
        info_velocity_away=inputs.info_velocity_away,
        hours_since_change_home=inputs.hours_since_change_home,
        hours_since_change_away=inputs.hours_since_change_away,
        config_overrides=None,
    )
    mu_h = max(7.5, float(decomposition["expected_home_points"]))
    mu_a = max(7.0, float(decomposition["expected_away_points"]))
    error_stdev_widen = float(decomposition.get("error_regime_stdev_widen") or 0.0)
    sigma = sim._clamp(
        float(framework_config["priors"]["base_score_stdev"])
        + float(totals_adjustments["stdev_points"])
        + error_stdev_widen,
        7.6,
        12.2,
    )
    return mu_h, mu_a, float(sigma)


def paired_draw_hash(H: np.ndarray, A: np.ndarray) -> str:
    if H.dtype != np.float64 or A.dtype != np.float64:
        raise JointRefuse("draws must be float64")
    if H.shape != A.shape:
        raise JointRefuse("H/A shape mismatch")
    return hashlib.sha256(np.ascontiguousarray(H).tobytes() + np.ascontiguousarray(A).tobytes()).hexdigest()


def derive_from_pairs(H: np.ndarray, A: np.ndarray, sim: Any) -> dict[str, Any]:
    """Every ST/ML/WP/total from one paired array. Ties (D=0) count AWAY."""
    if H.dtype != np.float64 or A.dtype != np.float64:
        raise JointRefuse("draws must be float64")
    n = int(H.size)
    D = H - A
    S = H + A
    home_wins = int(np.sum(D > 0.0))
    tie_count = int(np.sum(D == 0.0))
    home_wp = home_wins / float(n)
    away_wp = 1.0 - home_wp
    mean_H = float(H.mean())
    mean_A = float(A.mean())
    mean_D = float(D.mean())
    mean_S = float(S.mean())
    var_H = float(H.var(ddof=0))
    var_A = float(A.var(ddof=0))
    if var_H == 0.0 or var_A == 0.0:
        corr = float("nan")
    else:
        corr = float(np.corrcoef(H, A)[0, 1])
    return {
        "mean_H": mean_H,
        "mean_A": mean_A,
        "mean_D": mean_D,
        "mean_S": mean_S,
        "sd_H": float(H.std(ddof=0)),
        "sd_A": float(A.std(ddof=0)),
        "sd_D": float(D.std(ddof=0)),
        "sd_S": float(S.std(ddof=0)),
        "var_H": var_H,
        "var_A": var_A,
        "corr_HA": corr,
        "cov_MT": var_H - var_A,
        "home_wins": home_wins,
        "tie_count": tie_count,
        "home_wp": home_wp,
        "away_wp": away_wp,
        "fair_home_ml": int(sim._fair_moneyline_from_prob(home_wp)),
        "fair_away_ml": int(sim._fair_moneyline_from_prob(away_wp)),
        "spread_home": -mean_D,
        "total_raw": mean_S,
        "floor_emp_H": float(np.mean(H <= 0.0)),
        "floor_emp_A": float(np.mean(A <= 0.0)),
    }


def simulate_q2s_joint(
    inputs: Any,
    game_id: str,
    d: float,
    *,
    sim: Any | None = None,
    N: int = N_DRAWS,
) -> JointResult:
    """IF joint-score branch + one inserted pre-floor symmetric shift.

    d = frozen_q2s_margin − frozen_IF_margin.
    μh' = μh + d/2 ; μa' = μa − d/2 after framework floors, before max(0,·).
    """
    if int(N) != N_DRAWS:
        raise JointRefuse(f"N {N} != frozen {N_DRAWS}")
    if not math.isfinite(float(d)):
        raise JointRefuse("nonfinite d")
    sim = sim or _load_sim()
    seed = seed_for(str(game_id))
    mu_h, mu_a, sigma = _latent_params(sim, inputs)
    if not math.isfinite(mu_h) or not math.isfinite(mu_a) or not math.isfinite(sigma):
        raise JointRefuse("nonfinite latent mu/sigma")
    if sigma <= 0.0:
        raise JointRefuse("sigma <= 0")
    mu_h_p = float(mu_h) + float(d) / 2.0
    mu_a_p = float(mu_a) - float(d) / 2.0
    if mu_h_p < 0.0 or mu_a_p < 0.0:
        raise JointRefuse(f"mu' < 0 for {game_id}: {mu_h_p}, {mu_a_p}")
    if not math.isfinite(mu_h_p) or not math.isfinite(mu_a_p):
        raise JointRefuse("nonfinite mu'")
    rng = random.Random(seed)
    H = np.empty(int(N), dtype=np.float64)
    A = np.empty(int(N), dtype=np.float64)
    for i in range(int(N)):
        H[i] = max(0.0, rng.gauss(mu_h_p, sigma))
        A[i] = max(0.0, rng.gauss(mu_a_p, sigma))
    stats = derive_from_pairs(H, A, sim)
    digest = paired_draw_hash(H, A)
    return JointResult(
        game_id=str(game_id),
        d=float(d),
        seed=int(seed),
        N=int(N),
        mu_h=float(mu_h),
        mu_a=float(mu_a),
        mu_h_p=float(mu_h_p),
        mu_a_p=float(mu_a_p),
        sigma=float(sigma),
        H=H,
        A=A,
        draw_hash=digest,
        mean_H=stats["mean_H"],
        mean_A=stats["mean_A"],
        mean_D=stats["mean_D"],
        mean_S=stats["mean_S"],
        sd_H=stats["sd_H"],
        sd_A=stats["sd_A"],
        sd_D=stats["sd_D"],
        sd_S=stats["sd_S"],
        corr_HA=stats["corr_HA"],
        cov_MT=stats["cov_MT"],
        var_H=stats["var_H"],
        var_A=stats["var_A"],
        home_wins=stats["home_wins"],
        tie_count=stats["tie_count"],
        home_wp=stats["home_wp"],
        away_wp=stats["away_wp"],
        fair_home_ml=stats["fair_home_ml"],
        fair_away_ml=stats["fair_away_ml"],
        spread_home=stats["spread_home"],
        total_raw=stats["total_raw"],
        floor_emp_H=stats["floor_emp_H"],
        floor_emp_A=stats["floor_emp_A"],
        analytic=analytic_pair(mu_h_p, mu_a_p, sigma),
    )


def official_if_mus(inputs: Any, game_id: str, *, sim: Any | None = None) -> tuple[float, float, dict]:
    """Pinned official IF mus + markets (no draws). For Q1 legacy compare."""
    sim = sim or _load_sim()
    seed = seed_for(str(game_id))
    projection = sim.simulate_nfl_game_independent_fair(
        inputs,
        simulations=N_DRAWS,
        seed=seed,
        market_spread_home=None,
        market_total=None,
        apply_linear_totals_calibration=False,
    )
    margin_mu, total_mu = sim.independent_fair_mus(projection)
    return float(margin_mu), float(total_mu), projection


def assert_pinned_generator(sim: Any) -> None:
    sim_path = Path(sim.__file__)
    fw_path = IF_TREE / "src/services/nfl_handicapping_framework.py"
    if sha256_file(sim_path) != SIM_SHA:
        raise JointRefuse("simulator sha != 52d9e909")
    if sha256_file(fw_path) != FW_SHA:
        raise JointRefuse("framework sha != a0051cc4")
