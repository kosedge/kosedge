"""Calibration / priors facade for the CFB season engine.

Re-exports ``priors`` so callers can import either module name
(``calibration`` mirrors the NFL package layout).
"""

from __future__ import annotations

from src.services.cfb_season_engine.priors import (  # noqa: F401
    CALIBRATION_TAG,
    ENGINE_VERSION,
    documentation,
    early_season_factor,
    early_season_uncertainty,
    matchup_response_for_week,
    score_noise_sd_for_week,
    win_prob_margin_sd_for_week,
)

__all__ = [
    "CALIBRATION_TAG",
    "ENGINE_VERSION",
    "documentation",
    "early_season_factor",
    "early_season_uncertainty",
    "matchup_response_for_week",
    "score_noise_sd_for_week",
    "win_prob_margin_sd_for_week",
]
