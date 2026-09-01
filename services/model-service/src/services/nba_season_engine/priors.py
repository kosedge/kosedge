"""NBA season-engine priors (Chapter 1 shell).

TEAM_CARRY_SHRINK is NBA-named — do not import or alias CFB EFF_CARRY_SHRINK.
Chapter 2 player×minutes will rebase this pack; do not treat as finished model.
"""

from __future__ import annotations

ENGINE_VERSION = "nba-season-engine-v0.1"

# Carry 2025–26 team advanced toward league mean for 2026–27 shell.
# Paper-sim set {0.70, 0.80, 0.85, 0.90}; chosen 0.85 (order-preserving, modest compression).
TEAM_CARRY_SHRINK = 0.85

CARRY_FROM_SEASON = "2025-26"
CARRY_TO_SEASON = "2026-27"

PAPER_SIM_S_SET = (0.70, 0.80, 0.85, 0.90)
