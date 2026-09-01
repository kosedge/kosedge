"""WNBA season-engine priors (Chapter 1 shell).

WNBA_TEAM_CARRY_SHRINK is WNBA-named — do not import or alias NBA TEAM_CARRY_SHRINK.
Ch1 shrinks 2026 YTD advanced toward league mean. Ch2 player×minutes rebases.
"""

from __future__ import annotations

ENGINE_VERSION = "wnba-season-engine-v0.1"

# Shrink 2026 YTD team advanced toward league mean (Ch1 midseason shell).
# Paper-sim set {0.70, 0.80, 0.85, 0.90}; chosen 0.85. Do not retune in Ch2.
WNBA_TEAM_CARRY_SHRINK = 0.85

YTD_SEASON = "2026"
PAPER_SIM_S_SET = (0.70, 0.80, 0.85, 0.90)

# Chapter 2 — multi-year player talent weights (2024 / 2025 / 2026-YTD).
PLAYER_YEAR_WEIGHTS = {
    "2024": 0.20,
    "2025": 0.30,
    "2026": 0.50,
}
MINUTE_GRID_SUM = 200  # 40-min × 5 — not NBA 240

# Cap |ch1_net − player_net| when rebasing. Ch1 shrink is residual, not a second prior.
WNBA_TEAM_REBASE_RESIDUAL_CAP = 3.0

PROP_PLAY_CAP_PER_SLATE = 4
ODDS_SPORT_KEY = "basketball_wnba"

# Implied PPG′ neighborhood for Ch2 scorecard (WNBA, not NBA 111–120).
PPG_BAND = (75.0, 91.0)
