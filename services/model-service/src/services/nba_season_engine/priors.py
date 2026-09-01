"""NBA season-engine priors (Chapter 1 shell + Chapter 2 rebase).

TEAM_CARRY_SHRINK is NBA-named — do not import or alias CFB EFF_CARRY_SHRINK.
Chapter 2 rebases team ratings from player×minutes; Ch1 shrink is a residual cap.
"""

from __future__ import annotations

ENGINE_VERSION = "nba-season-engine-v0.1"

# Carry 2025–26 team advanced toward league mean for 2026–27 shell (Ch1).
# Paper-sim set {0.70, 0.80, 0.85, 0.90}; chosen 0.85. Do not retune in Ch2.
TEAM_CARRY_SHRINK = 0.85

CARRY_FROM_SEASON = "2025-26"
CARRY_TO_SEASON = "2026-27"

PAPER_SIM_S_SET = (0.70, 0.80, 0.85, 0.90)

# Chapter 2 — multi-year player talent weights (23–24 / 24–25 / 25–26).
PLAYER_YEAR_WEIGHTS = {
    "2023-24": 0.20,
    "2024-25": 0.30,
    "2025-26": 0.50,
}

MINUTE_GRID_SUM = 240

# Cap |ch1_net − player_net| when rebasing. Ch1 is residual, not a second full prior.
TEAM_REBASE_RESIDUAL_CAP = 3.0
