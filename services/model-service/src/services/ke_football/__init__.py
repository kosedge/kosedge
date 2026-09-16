"""KE Football v1 — measurement + Phase 2A unit ratings (research only).

Does not write production ratings, KEI, boards, or Team Strength.
``production_promote`` stays false. Phase 2A builds KE Off/Def
Efficiency unit ratings only — not a Team Strength composite.
"""

from __future__ import annotations

PHASE = "unit_ratings_phase2a"
MEASUREMENT_PHASE = "measurement_phase1b"
PRODUCTION_PROMOTE = False
NOT_KE_OVERALL = True
NOT_TEAM_STRENGTH = True
NOT_SCORING = True
NOT_MARKET = True
TAXONOMY = ("RAW", "DERIVED", "ADJUSTED", "MODELED")
PIPELINE_VERSION = "ke-football-v1-unit-ratings-phase2a"
OPP_ADJ_PROMOTED = False
OPP_ADJ_RESULT = "NO_ADJUSTMENT_WINNER"

__all__ = [
    "PHASE",
    "MEASUREMENT_PHASE",
    "PRODUCTION_PROMOTE",
    "OPP_ADJ_PROMOTED",
    "OPP_ADJ_RESULT",
    "NOT_KE_OVERALL",
    "NOT_TEAM_STRENGTH",
    "NOT_SCORING",
    "NOT_MARKET",
    "TAXONOMY",
    "PIPELINE_VERSION",
]
