"""v0.13 margin calibration — compress ranking-prior theater (research only).

Live 2026 identity (ESPN roster + SP+ carry + MATCHUP_RESPONSE=1.40) over-
separates FBS vs FBS. Historical W0–2 closes (2022–25) sit near p50 |spread|
= 8.5; the uncalibrated 2026 engine sat near 12 with OSU-class −35–39.

Two knobs, both inspectable:

1. Linear scale then tanh on the strength-path margin (FBS vs FBS).
2. League regression on placeholder / league-average efficiency teams.

Totals stay on the separate pace path. σ is not shrunk to chase ATS.
``used_in_spread`` stays false. FCS sides keep a milder scale.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Optional

from src.services.cfb_season_engine import priors as P
from src.services.cfb_season_engine.fbs_universe import is_official_fbs
from src.services.cfb_season_engine.types import TeamProjectionState

CALIBRATION_ID = "cfb-margin-scale-v0.13-20260814"
CALIBRATION_AS_OF = "2026-08-14"
USED_IN_SPREAD = False

# Knob 1 — FBS vs FBS: scale then tanh. Hist W0–2 p50 |close| ≈ 8.5.
MARGIN_FBS_SCALE = 0.80
MARGIN_TANH_TAU = 26.0
# FCS already labeled / wide-σ; do not crush those gaps into fake 14-pt lines.
MARGIN_FCS_SCALE = 0.94


def _is_fcs_state(state: Optional[TeamProjectionState]) -> bool:
    if state is None:
        return False
    if str(state.source or "").startswith("fcs"):
        return True
    if not is_official_fbs(state.team, include_transition=True):
        return True
    return False


def calibrate_margin(
    raw_margin: float,
    *,
    fcs_matchup: bool = False,
) -> Dict[str, Any]:
    """Compress a home-minus-away strength margin. Does not touch totals."""
    raw = float(raw_margin)
    scale = MARGIN_FCS_SCALE if fcs_matchup else MARGIN_FBS_SCALE
    tau = MARGIN_TANH_TAU
    scaled = raw * scale
    if tau <= 0:
        cal = scaled
    else:
        cal = tau * math.tanh(scaled / tau)
    return {
        "raw_margin": round(raw, 4),
        "calibrated_margin": round(cal, 4),
        "scale": scale,
        "tanh_tau": tau,
        "fcs_matchup": bool(fcs_matchup),
        "calibration_id": CALIBRATION_ID,
        "used_in_spread": USED_IN_SPREAD,
    }


def apply_calibrated_scores(
    home_exp: float,
    away_exp: float,
    *,
    fcs_matchup: bool = False,
) -> Dict[str, Any]:
    """Keep the score midpoint; replace the gap with the calibrated margin."""
    mid = 0.5 * (float(home_exp) + float(away_exp))
    raw = float(home_exp) - float(away_exp)
    block = calibrate_margin(raw, fcs_matchup=fcs_matchup)
    cal = float(block["calibrated_margin"])
    return {
        **block,
        "home_exp_raw": round(float(home_exp), 4),
        "away_exp_raw": round(float(away_exp), 4),
        "home_exp_cal": round(mid + 0.5 * cal, 4),
        "away_exp_cal": round(mid - 0.5 * cal, 4),
        "midpoint": round(mid, 4),
    }


def fcs_matchup_from_states(
    home: TeamProjectionState,
    away: TeamProjectionState,
) -> bool:
    return _is_fcs_state(home) or _is_fcs_state(away)


def documentation() -> Dict[str, Any]:
    return {
        "layer": "calibration",
        "name": "margin_calibration",
        "module": "src.services.cfb_season_engine.margin_calibration",
        "calibration_id": CALIBRATION_ID,
        "as_of": CALIBRATION_AS_OF,
        "used_in_spread": USED_IN_SPREAD,
        "kei": False,
        "formula": (
            "scaled = raw_margin * SCALE; "
            "cal = TAU * tanh(scaled / TAU); "
            "scores keep midpoint; total path unchanged"
        ),
        "knobs": {
            "MARGIN_FBS_SCALE": MARGIN_FBS_SCALE,
            "MARGIN_TANH_TAU": MARGIN_TANH_TAU,
            "MARGIN_FCS_SCALE": MARGIN_FCS_SCALE,
            "LEAGUE_REG_PLACEHOLDER": P.LEAGUE_REG_PLACEHOLDER,
        },
        "note": (
            "Compresses live 2026 identity blowouts toward hist W0–2 close "
            "norms. Does not shrink σ. Does not flip used_in_spread."
        ),
    }
