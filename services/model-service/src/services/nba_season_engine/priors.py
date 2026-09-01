"""NBA season-engine priors (Ch1 shell + Ch2 rebase + Ch3 situation).

TEAM_CARRY_SHRINK is NBA-named — do not import or alias CFB EFF_CARRY_SHRINK.
Chapter 2 rebases team ratings from player×minutes; Ch1 shrink is a residual cap.
Chapter 3 applies capped situation classes on read — not a second prior.
"""

from __future__ import annotations

ENGINE_VERSION = "nba-season-engine-v0.1"

# Carry 2025–26 team advanced toward league mean for 2026–27 shell (Ch1).
# Paper-sim set {0.70, 0.80, 0.85, 0.90}; chosen 0.85. Do not retune in Ch2/Ch3.
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

# Chapter 3 — situation classes (one coefficient each). Paper-sim on schedule SoT.
# Applied on read to the frozen Ch2 team line. Cap keeps situation ≠ second prior.
SITUATION_HOME_NET = 1.5
SITUATION_B2B_NET = -2.0  # rest class: B2B or 3-in-4 (not stacked)
SITUATION_TRAVEL_NET = -1.0  # fires when |Δtz| ≥ TRAVEL_TZ_BAND_MIN_HOURS
SITUATION_ALTITUDE_NET = -1.5  # visitor at altitude_class venue
SITUATION_NET_CAP = 4.0
TRAVEL_TZ_BAND_MIN_HOURS = 2
PAPER_SIM_HOME_SET = (1.5, 2.0, 2.5, 3.0)
PAPER_SIM_B2B_SET = (-1.0, -1.5, -2.0)
PAPER_SIM_TRAVEL_SET = (-0.5, -1.0, -1.5)
PAPER_SIM_ALTITUDE_SET = (-0.5, -1.0, -1.5)
PAPER_SIM_SIT_CAP_SET = (3.0, 4.0, 5.0)
