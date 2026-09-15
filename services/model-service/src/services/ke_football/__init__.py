"""KE Football v1 — Phase 1 measurement (research only).

Does not write production ratings, KEI, boards, or Team Strength.
``production_promote`` stays false.
"""

from __future__ import annotations

PHASE = "measurement_phase1"
PRODUCTION_PROMOTE = False
NOT_KE_OVERALL = True
NOT_TEAM_STRENGTH = True
NOT_SCORING = True
NOT_MARKET = True
TAXONOMY = ("RAW", "DERIVED", "ADJUSTED", "MODELED")
PIPELINE_VERSION = "ke-football-v1-measurement-phase1"

__all__ = [
    "PHASE",
    "PRODUCTION_PROMOTE",
    "NOT_KE_OVERALL",
    "NOT_TEAM_STRENGTH",
    "NOT_SCORING",
    "NOT_MARKET",
    "TAXONOMY",
    "PIPELINE_VERSION",
]
