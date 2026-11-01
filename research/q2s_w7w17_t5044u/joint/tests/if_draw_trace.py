"""Research-test tracer for unmodified IF Gaussian draws.

Does not edit nfl_simulator.py. Patches Random.gauss on the already-imported
stdlib module object used by the pinned IF source, records the raw gauss
returns, then floors them in the original H-then-A order.

CERT=0. No outcomes / LOOK / 50bda875 reads.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import numpy as np

JOINT = Path(__file__).resolve().parents[1]
PHASE4 = JOINT.parent / "phase4"
if str(JOINT) not in sys.path:
    sys.path.insert(0, str(JOINT))
if str(PHASE4) not in sys.path:
    sys.path.insert(0, str(PHASE4))

from pins import N_DRAWS  # noqa: E402
from score_if_w7w17 import seed_for  # noqa: E402
from sim_q2s_joint import official_if_mus  # noqa: E402


class TraceRefuse(RuntimeError):
    pass


def trace_official_if_floored_pairs(
    sim: Any,
    inputs: Any,
    game_id: str,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """Run pinned IF and return floored float64 (H0, A0) from its gauss calls."""
    rng_mod = sim.random
    orig_gauss = rng_mod.Random.gauss
    captured: list[tuple[float, float, float]] = []

    def wrapped(self, mu=0.0, sigma=1.0):  # noqa: ANN001
        value = orig_gauss(self, mu, sigma)
        captured.append((float(mu), float(sigma), float(value)))
        return value

    rng_mod.Random.gauss = wrapped
    try:
        off_m, off_t, off_proj = official_if_mus(inputs, game_id, sim=sim)
    finally:
        rng_mod.Random.gauss = orig_gauss

    expected = 2 * N_DRAWS
    if len(captured) != expected:
        raise TraceRefuse(
            f"{game_id}: traced {len(captured)} gauss calls != {expected}"
        )
    raw = np.array([c[2] for c in captured], dtype=np.float64)
    # Original IF order: home then away, then max(0, ·).
    H0 = np.maximum(0.0, raw[0::2])
    A0 = np.maximum(0.0, raw[1::2])
    if H0.shape != (N_DRAWS,) or A0.shape != (N_DRAWS,):
        raise TraceRefuse(f"{game_id}: floored shape {H0.shape}/{A0.shape}")
    if H0.dtype != np.float64 or A0.dtype != np.float64:
        raise TraceRefuse(f"{game_id}: floored dtype {H0.dtype}/{A0.dtype}")
    return H0, A0, {
        "game_id": str(game_id),
        "seed": seed_for(str(game_id)),
        "n_gauss": len(captured),
        "mu_h_traced": float(captured[0][0]),
        "mu_a_traced": float(captured[1][0]),
        "sigma_traced": float(captured[0][1]),
        "official_margin_mu": float(off_m),
        "official_total_mu": float(off_t),
        "official_wp_home": float((off_proj.get("markets") or {})["home_win_prob"]),
        "official_ml_home": int((off_proj.get("markets") or {})["fair_home_ml"]),
        "official_ml_away": int((off_proj.get("markets") or {})["fair_away_ml"]),
    }
